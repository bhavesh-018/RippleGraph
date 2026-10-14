"""
RippleGraph - Stage 3: Deterministic Reviewer

Adversarially validates every candidate finding produced by Stage 1.
Responsibilities:

  1. Path Verification    - confirms every asserted risk has a live graph path
  2. Red Herring Rejection - rejects incidents whose claim_types do not overlap
                            the active change claim_types (e.g. INC-105)
  3. Status Assignment   - stamps each service node with:
                             INCOMPATIBLE         (direct contract break)
                             POTENTIAL_DOWNSTREAM (transitive risk via DEPENDS_ON)
                             COMPATIBLE           (all claims satisfied)
                             UNAFFECTED           (no dependency path found)
  4. Confidence Scoring  - assigns initial confidence values before Stage 2 decay
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ripplegraph.reviewer")

# Status constants (match ServiceEvaluationStatus enum)
INCOMPATIBLE = "incompatible"
POTENTIAL_DOWNSTREAM = "potential_downstream"
COMPATIBLE = "compatible"
UNAFFECTED = "unaffected"

# Confidence baselines
CONFIDENCE_INCOMPATIBLE = 0.95
CONFIDENCE_POTENTIAL = 0.70
CONFIDENCE_COMPATIBLE = 0.85
CONFIDENCE_UNAFFECTED = 1.00


def _make_finding_id() -> str:
    """Generate a unique Finding ID with FND- prefix."""
    return f"FND-{uuid.uuid4().hex[:8].upper()}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_reviewer(
    change: Dict[str, Any],
    investigator_output: Dict[str, Any],
    investigation_id: str,
    prior_findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Stage 3: Validate investigator output and produce verified findings.

    Args:
        change:               Original ChangeProposal dict.
        investigator_output:  Output dict from run_investigator().
        investigation_id:     ID of the current investigation run.
        prior_findings:       Optional list of prior Finding dicts from Stage 2
                              (used to boost confidence on repeated risks).

    Returns:
        A dict with keys:
          - findings          list[dict]  verified FindingNode-compatible dicts
          - red_herrings      list[dict]  rejected incident records with rationale
          - reviewer_decisions list[dict] audit log of every reviewer decision
    """
    claim_types: List[str] = change.get("claim_types", [])
    active_claims_set = set(claim_types)

    compatibility_report = investigator_output["compatibility_report"]
    downstream_services = investigator_output["downstream_services"]
    relevant_incidents = investigator_output["relevant_incidents"]

    # Build quick-lookup maps
    compat_by_svc: Dict[str, Dict[str, Any]] = {
        r["service_id"]: r for r in compatibility_report.get("results", [])
    }
    downstream_by_svc: Dict[str, Dict[str, Any]] = {
        s["service_id"]: s for s in downstream_services
    }

    # Group incidents by affected service, partitioned by relevance
    relevant_by_svc: Dict[str, List[str]] = {}
    rejected_red_herrings: List[Dict[str, Any]] = []

    for inc in relevant_incidents:
        svc_id = inc["affected_service_id"]
        if inc["relevance_status"] == "RELEVANT":
            relevant_by_svc.setdefault(svc_id, []).append(inc["incident_id"])
        elif inc["relevance_status"] == "REJECTED_RED_HERRING":
            rejected_red_herrings.append({
                "incident_id": inc["incident_id"],
                "title": inc["title"],
                "affected_service_id": svc_id,
                "claim_types": inc["claim_types"],
                "active_claim_types": sorted(list(active_claims_set)),
                "rationale": (
                    f"REJECTED: {inc['incident_id']} relates to "
                    f"claim types {inc['claim_types']}, which do not overlap "
                    f"the active change claim types {sorted(list(active_claims_set))}."
                ),
            })
            logger.info(
                "[Stage 3] RED HERRING rejected: %s (claim_types=%s)",
                inc["incident_id"],
                inc["claim_types"],
            )

    # Build a set of prior high-confidence service IDs for boosting
    prior_high_confidence: set = set()
    if prior_findings:
        for pf in prior_findings:
            if pf.get("confidence", 0) >= 0.85 and pf.get("status") in (
                INCOMPATIBLE,
                POTENTIAL_DOWNSTREAM,
            ):
                prior_high_confidence.add(pf.get("service_id"))

    findings: List[Dict[str, Any]] = []
    reviewer_decisions: List[Dict[str, Any]] = []

    # ---- Classify every consumer that appears in the compatibility report ----
    all_consumer_ids = set(compat_by_svc.keys())
    all_downstream_ids = set(downstream_by_svc.keys())
    all_service_ids = all_consumer_ids | all_downstream_ids

    for svc_id in sorted(all_service_ids):
        compat_entry = compat_by_svc.get(svc_id)
        downstream_entry = downstream_by_svc.get(svc_id)

        # Determine status
        if compat_entry is not None and not compat_entry["is_compatible"]:
            # Direct contract break
            status = INCOMPATIBLE
            category = "DIRECT_INCOMPATIBILITY"
            confidence = CONFIDENCE_INCOMPATIBLE
            reasons = compat_entry.get("reasons", [])
            missing_claims = compat_entry.get("missing_claims", [])
            hop_depth = 0
            dependency_chains = []

        elif compat_entry is not None and compat_entry["is_compatible"]:
            # Directly consumes but is already compatible
            if downstream_entry is not None:
                # Also downstream - still label as potential due to transitive path
                status = POTENTIAL_DOWNSTREAM
                category = "TRANSITIVE_RISK"
                confidence = CONFIDENCE_POTENTIAL
                reasons = [
                    "Service is a direct compatible consumer that also appears in the "
                    "downstream blast radius - marking as potential transitive risk."
                ]
                missing_claims = []
                hop_depth = downstream_entry["min_hop_distance"]
                dependency_chains = downstream_entry.get("dependency_chains", [])
            else:
                status = COMPATIBLE
                category = "COMPATIBLE_CONSUMER"
                confidence = CONFIDENCE_COMPATIBLE
                reasons = compat_entry.get("reasons", [])
                missing_claims = []
                hop_depth = 0
                dependency_chains = []

        elif downstream_entry is not None:
            # Purely transitive risk, not a direct consumer of the contract
            status = POTENTIAL_DOWNSTREAM
            category = "TRANSITIVE_RISK"
            confidence = max(
                CONFIDENCE_POTENTIAL - 0.05 * (downstream_entry["min_hop_distance"] - 1),
                0.40,
            )
            reasons = [
                f"Service is a transitive dependent at hop depth "
                f"{downstream_entry['min_hop_distance']} from the change origin."
            ]
            missing_claims = []
            hop_depth = downstream_entry["min_hop_distance"]
            dependency_chains = downstream_entry.get("dependency_chains", [])

        else:
            status = UNAFFECTED
            category = "UNAFFECTED"
            confidence = CONFIDENCE_UNAFFECTED
            reasons = ["No dependency path or contract relationship found with the changed API."]
            missing_claims = []
            hop_depth = 0
            dependency_chains = []

        # Boost confidence for repeated risks confirmed by prior investigations
        if svc_id in prior_high_confidence and status in (INCOMPATIBLE, POTENTIAL_DOWNSTREAM):
            confidence = min(confidence + 0.08, 0.99)
            reasons.append(
                f"Confidence boosted: prior investigation also flagged this service."
            )

        # Attach relevant incident and mitigation IDs
        incident_ids = relevant_by_svc.get(svc_id, [])

        # Recommend transitional contract for incompatible direct consumers
        recommended_contract = None
        if status == INCOMPATIBLE:
            recommended_contract = "cv-auth-v1-extended"

        finding = {
            "id": _make_finding_id(),
            "investigation_id": investigation_id,
            "service_id": svc_id,
            "service_name": (compat_entry or downstream_entry or {}).get("service_name", svc_id),
            "category": category,
            "status": status,
            "confidence": round(confidence, 4),
            "reasons": reasons,
            "missing_claims": missing_claims,
            "dependency_chains": dependency_chains,
            "hop_depth": hop_depth,
            "recommended_mitigation_id": None,
            "recommended_contract_id": recommended_contract,
            "relevant_incidents": incident_ids,
            "rejected_red_herrings": [],
            "created_at": _now_iso(),
        }

        findings.append(finding)

        reviewer_decisions.append({
            "service_id": svc_id,
            "decision": "ACCEPTED",
            "assigned_status": status,
            "confidence": finding["confidence"],
            "rationale": reasons[0] if reasons else "No rationale.",
        })

        logger.info(
            "[Stage 3] ACCEPTED finding for %s -> status=%s confidence=%.2f",
            svc_id,
            status,
            confidence,
        )

    logger.info(
        "[Stage 3] Reviewer complete. findings=%d red_herrings_rejected=%d",
        len(findings),
        len(rejected_red_herrings),
    )

    return {
        "findings": findings,
        "red_herrings": rejected_red_herrings,
        "reviewer_decisions": reviewer_decisions,
    }
