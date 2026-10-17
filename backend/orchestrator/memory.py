"""
RippleGraph - Stage 2: Memory Engine

Retrieves prior Finding nodes from FalkorDB for affected services,
then applies mathematical temporal and hop confidence decay so that
repeated risks are surfaced with higher confidence and stale findings
gracefully lose weight over time.

Decay formula (C24):
  decayed = base_confidence * exp(-lambda * days_old) * (1 - 0.1 * hop_depth)
  lambda = 0.05 per day
  Re-affirmed findings (same service, same status) are boosted to min 0.95.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ripplegraph.memory")

# Decay rate: confidence halves roughly every 14 days
DECAY_LAMBDA = 0.05

# Minimum decayed confidence floor (never drop below this)
DECAY_FLOOR = 0.20

# Boost applied when a prior finding re-affirms the same risk
REAFFIRM_BOOST = 0.95


def get_prior_findings_with_decay(
    service_ids: List[str],
    current_investigation_id: str,
    graph: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Stage 2: Fetch prior Finding nodes from FalkorDB for the given service IDs
    and apply temporal + hop depth confidence decay.

    Args:
        service_ids:              List of service IDs in the current blast radius.
        current_investigation_id: ID of the current run (excluded from prior queries).
        graph:                    Optional FalkorDB graph handle (injected in tests).

    Returns:
        List of prior finding dicts enriched with:
          - decayed_confidence  float   post-decay confidence score
          - days_old            float   age of the finding in days
          - decay_factor        float   the multiplied decay value applied
          - reaffirmed          bool    True if boosted due to repeated risk
    """
    if graph is None:
        from graph.client import get_graph
        graph = get_graph()

    if not service_ids:
        logger.info("[Stage 2] No service IDs provided, skipping memory retrieval.")
        return []

    logger.info(
        "[Stage 2] Fetching prior findings for %d service(s) (excluding %s)",
        len(service_ids),
        current_investigation_id,
    )

    cypher = """
    MATCH (f:Finding)-[:ABOUT_SERVICE]->(s:Service)
    WHERE f.investigation_id <> $current_inv_id
    RETURN f.id, f.investigation_id, f.service_id, f.service_name,
           f.status, f.confidence, f.hop_depth, f.created_at
    ORDER BY f.created_at DESC
    """

    try:
        res = graph.query(cypher, {"current_inv_id": current_investigation_id})
    except Exception as exc:
        logger.warning("[Stage 2] Prior findings query failed: %s", exc)
        return []

    target_set = set(service_ids)
    now = datetime.now(timezone.utc)

    raw_findings = []
    for row in res.result_set:
        fnd_id, inv_id, svc_id, svc_name, status, confidence, hop_depth, created_at = row
        if svc_id not in target_set:
            continue
        raw_findings.append({
            "id": fnd_id,
            "investigation_id": inv_id,
            "service_id": svc_id,
            "service_name": svc_name or svc_id,
            "status": status,
            "confidence": float(confidence) if confidence is not None else 1.0,
            "hop_depth": int(hop_depth) if hop_depth is not None else 0,
            "created_at": created_at,
        })

    logger.info("[Stage 2] Retrieved %d raw prior finding(s)", len(raw_findings))

    # Apply decay to each finding
    decayed = [_apply_decay(f, now) for f in raw_findings]

    # Keep only the most recent (highest decayed confidence) finding per service
    best_by_svc: Dict[str, Dict[str, Any]] = {}
    for f in decayed:
        svc = f["service_id"]
        if svc not in best_by_svc or f["decayed_confidence"] > best_by_svc[svc]["decayed_confidence"]:
            best_by_svc[svc] = f

    result = list(best_by_svc.values())
    logger.info(
        "[Stage 2] Memory retrieval complete. %d unique service(s) with prior findings.",
        len(result),
    )
    return result


def _apply_decay(finding: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    """
    Apply temporal and hop depth decay to a single prior finding.

    Formula:
      decayed = base * exp(-lambda * days_old) * (1 - 0.1 * hop_depth)
      clamped to [DECAY_FLOOR, 1.0]
    """
    base_confidence = finding["confidence"]
    hop_depth = finding["hop_depth"]
    created_at_raw = finding.get("created_at", "")

    # Parse created_at to compute age
    days_old = _parse_days_old(created_at_raw, now)

    # Temporal decay component
    time_decay = math.exp(-DECAY_LAMBDA * days_old)

    # Hop depth penalty (each hop reduces confidence by 10%)
    hop_penalty = max(1.0 - 0.1 * hop_depth, 0.0)

    # Combined decay
    decayed = base_confidence * time_decay * hop_penalty
    decayed = max(decayed, DECAY_FLOOR)
    decayed = min(decayed, 1.0)
    decayed = round(decayed, 4)

    decay_factor = round(time_decay * hop_penalty, 4)

    return {
        **finding,
        "days_old": round(days_old, 2),
        "decay_factor": decay_factor,
        "decayed_confidence": decayed,
        "reaffirmed": False,
    }


def apply_memory_to_findings(
    current_findings: List[Dict[str, Any]],
    prior_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge prior decayed findings into the current findings list.

    Rules:
    - If a prior finding matches the same service AND same risk status,
      boost the current finding's confidence to max(current, REAFFIRM_BOOST).
    - Append a reason noting the memory-backed boost.
    - Marks the prior finding as reaffirmed.

    Args:
        current_findings: Findings produced by Stage 3 Reviewer.
        prior_findings:   Decayed prior findings from get_prior_findings_with_decay().

    Returns:
        Updated current_findings list with boosted confidence where applicable.
    """
    prior_by_svc: Dict[str, Dict[str, Any]] = {
        f["service_id"]: f for f in prior_findings
    }

    for finding in current_findings:
        svc_id = finding["service_id"]
        prior = prior_by_svc.get(svc_id)
        if prior is None:
            finding.setdefault("decayed_confidence", None)
            finding.setdefault("days_old", None)
            finding.setdefault("decay_factor", None)
            finding.setdefault("reaffirmed", False)
            finding.setdefault("is_stale", False)
            finding.setdefault("staleness_reason", None)
            continue

        # Propagate mathematical decay metadata from prior finding
        finding["decayed_confidence"] = prior.get("decayed_confidence")
        finding["days_old"] = prior.get("days_old")
        finding["decay_factor"] = prior.get("decay_factor")

        current_status = finding["status"]
        prior_status = prior.get("status", "")

        # Re-affirmation: same risk status seen before
        if current_status == prior_status and current_status in ("incompatible", "potential_downstream"):
            old_confidence = finding["confidence"]
            boosted = max(old_confidence, REAFFIRM_BOOST)
            finding["confidence"] = round(boosted, 4)
            finding["reaffirmed"] = True
            finding["is_stale"] = False
            finding.setdefault("reasons", []).append(
                f"Memory boost: prior investigation '{prior['investigation_id']}' "
                f"also flagged this service as {prior_status} "
                f"(decayed confidence {prior['decayed_confidence']:.2f}). "
                f"Confidence raised from {old_confidence:.2f} to {boosted:.2f}."
            )
            prior["reaffirmed"] = True
            logger.info(
                "[Stage 2] Reaffirmed %s: confidence %.2f -> %.2f",
                svc_id,
                old_confidence,
                boosted,
            )
        elif prior_status in ("incompatible", "potential_downstream") and current_status == "compatible":
            # Prior incompatibility is now resolved! Flag as stale
            finding["reaffirmed"] = False
            finding["is_stale"] = True
            finding["staleness_reason"] = (
                f"Prior investigation '{prior['investigation_id']}' flagged this service as {prior_status}, "
                f"but current contract evaluation resolved the incompatibility."
            )
            finding.setdefault("reasons", []).append(
                f"Memory staleness: prior finding '{prior.get('id', '')}' ({prior_status}) is now stale. "
                f"Service is currently compatible."
            )
            logger.info("[Stage 2] Stale prior finding detected for %s (now compatible)", svc_id)
        else:
            finding["reaffirmed"] = False
            finding["is_stale"] = False
            # Different status from prior run: note the divergence but don't change
            finding.setdefault("reasons", []).append(
                f"Memory context: prior investigation '{prior['investigation_id']}' "
                f"found {prior_status} for this service "
                f"(decayed confidence {prior['decayed_confidence']:.2f}). "
                f"Current assessment: {current_status}."
            )

    return current_findings


def _parse_days_old(created_at_raw: str, now: datetime) -> float:
    """Parse an ISO timestamp string and return age in days. Returns 0.0 on failure."""
    if not created_at_raw:
        return 0.0
    try:
        # Handle both offset-aware and naive timestamps
        ts = datetime.fromisoformat(created_at_raw)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = now - ts
        return max(delta.total_seconds() / 86400.0, 0.0)
    except (ValueError, TypeError):
        logger.debug("[Stage 2] Could not parse created_at: %s", created_at_raw)
        return 0.0
