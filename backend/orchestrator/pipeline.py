"""
RippleGraph - Investigation Pipeline Runner

Orchestrates the 4-stage Change Rehearsal pipeline:

  Stage 1: Investigator   - Cypher-powered blast radius discovery
  Stage 2: Memory         - Prior finding retrieval with temporal decay (if memory_enabled)
  Stage 3: Reviewer       - Adversarial validation and red herring rejection
  Stage 4: Persist        - Write findings as permanent graph memory

Returns a fully populated InvestigationResponse dict.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from graph.client import get_graph
from orchestrator.investigator import run_investigator
from orchestrator.reviewer import run_reviewer
from orchestrator.persist import persist_investigation

logger = logging.getLogger("ripplegraph.pipeline")

# Built-in change proposals (seeded alongside graph data)
BUILTIN_CHANGES: Dict[str, Dict[str, Any]] = {
    "CHG-001": {
        "id": "CHG-001",
        "title": "Auth Token Field Rename: sub -> subject_id, roles -> scopes",
        "proposing_service": "auth-service",
        "target_api": "auth-token-api",
        "proposed_contract_id": "cv-auth-v2",
        "claim_types": ["field_rename", "sub", "roles", "exp", "token_format"],
        "description": (
            "Rename core JWT fields: 'sub' to 'subject_id' and 'roles' to 'scopes'. "
            "This is a breaking contract change that will invalidate all consumers "
            "that extract the original 'sub' or 'roles' claims directly."
        ),
    },
    "CHG-002": {
        "id": "CHG-002",
        "title": "Auth Token Migration: Deploy cv-auth-v1-extended Transitional Contract",
        "proposing_service": "auth-service",
        "target_api": "auth-token-api",
        "proposed_contract_id": "cv-auth-v1-extended",
        "claim_types": ["field_rename", "sub", "subject_id", "roles", "scopes", "token_format"],
        "description": (
            "Deploy the transitional contract cv-auth-v1-extended that supports both "
            "old claims (sub, roles) and new claims (subject_id, scopes) simultaneously. "
            "This allows a rolling migration without a coordinated cutover."
        ),
    },
}


def _make_investigation_id() -> str:
    return f"INV-{uuid.uuid4().hex[:8].upper()}"


def run_pipeline(
    change_id: Optional[str] = "CHG-001",
    change_override: Optional[Dict[str, Any]] = None,
    memory_enabled: bool = True,
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Execute the full 4-stage Change Rehearsal pipeline.

    Args:
        change_id:       ID of a built-in change proposal (e.g. "CHG-001").
        change_override: Custom change proposal dict. Takes precedence over change_id.
        memory_enabled:  If True, run Stage 2 memory retrieval with temporal decay.
        graph:           Optional FalkorDB graph handle (injected in tests).

    Returns:
        A dict compatible with InvestigationResponse schema.
    """
    start_ms = time.monotonic()
    investigation_id = _make_investigation_id()

    if graph is None:
        graph = get_graph()

    # Resolve the change proposal
    if change_override is not None:
        change = change_override
    elif change_id in BUILTIN_CHANGES:
        change = BUILTIN_CHANGES[change_id]
    else:
        raise ValueError(
            f"Unknown change_id '{change_id}'. "
            f"Available: {list(BUILTIN_CHANGES.keys())}"
        )

    logger.info(
        "[Pipeline] Starting investigation %s | change=%s | memory=%s",
        investigation_id,
        change["id"],
        memory_enabled,
    )

    # ---- Stage 1: Investigator ----
    logger.info("[Pipeline] --- Stage 1: INVESTIGATOR ---")
    investigator_output = run_investigator(change, graph=graph)

    # ---- Stage 2: Memory (prior findings retrieval) ----
    prior_findings: List[Dict[str, Any]] = []
    if memory_enabled:
        logger.info("[Pipeline] --- Stage 2: MEMORY (retrieving prior findings) ---")
        prior_findings = _fetch_prior_findings(
            investigator_output["all_affected_service_ids"],
            investigation_id,
            graph=graph,
        )
        logger.info("[Pipeline] Prior findings retrieved: %d", len(prior_findings))
    else:
        logger.info("[Pipeline] --- Stage 2: MEMORY DISABLED (cold start) ---")

    # ---- Stage 3: Reviewer ----
    logger.info("[Pipeline] --- Stage 3: REVIEWER ---")
    reviewer_output = run_reviewer(
        change=change,
        investigator_output=investigator_output,
        investigation_id=investigation_id,
        prior_findings=prior_findings if memory_enabled else None,
    )

    findings = reviewer_output["findings"]
    red_herrings = reviewer_output["red_herrings"]

    # ---- Stage 4: Persist ----
    logger.info("[Pipeline] --- Stage 4: PERSIST ---")
    persist_investigation(
        investigation_id=investigation_id,
        change=change,
        findings=findings,
        red_herrings=red_herrings,
        memory_enabled=memory_enabled,
        graph=graph,
    )

    elapsed_ms = (time.monotonic() - start_ms) * 1000

    # Build summary counts
    summary = {
        "incompatible": sum(1 for f in findings if f["status"] == "incompatible"),
        "potential_downstream": sum(1 for f in findings if f["status"] == "potential_downstream"),
        "compatible": sum(1 for f in findings if f["status"] == "compatible"),
        "unaffected": sum(1 for f in findings if f["status"] == "unaffected"),
    }

    logger.info(
        "[Pipeline] Complete in %.1f ms | summary=%s",
        elapsed_ms,
        summary,
    )

    # Recommended contract: suggest transitional if any incompatible findings exist
    recommended_contract = None
    if summary["incompatible"] > 0:
        recommended_contract = "cv-auth-v1-extended"

    return {
        "investigation_id": investigation_id,
        "change_id": change["id"],
        "change_title": change["title"],
        "memory_enabled": memory_enabled,
        "summary": summary,
        "recommended_migration_contract": recommended_contract,
        "findings": findings,
        "red_herrings_rejected": red_herrings,
        "execution_time_ms": round(elapsed_ms, 2),
    }


def _fetch_prior_findings(
    service_ids: List[str],
    current_investigation_id: str,
    graph: Any,
) -> List[Dict[str, Any]]:
    """
    Retrieve prior Finding nodes from FalkorDB for the given service IDs,
    excluding the current investigation run.

    Returns a list of raw finding dicts with status and confidence for Stage 2 boosting.
    """
    if not service_ids:
        return []

    # Query all findings about the affected services from previous investigations
    cypher = """
    MATCH (f:Finding)-[:ABOUT_SERVICE]->(s:Service)
    WHERE f.investigation_id <> $current_inv_id
    RETURN f.id, f.investigation_id, f.service_id, f.status, f.confidence, f.created_at
    ORDER BY f.created_at DESC
    """
    try:
        res = graph.query(cypher, {"current_inv_id": current_investigation_id})
    except Exception as exc:
        logger.warning("[Stage 2] Could not fetch prior findings: %s", exc)
        return []

    target_set = set(service_ids)
    prior: List[Dict[str, Any]] = []

    for row in res.result_set:
        fnd_id, inv_id, svc_id, status, confidence, created_at = row
        if svc_id in target_set:
            prior.append({
                "id": fnd_id,
                "investigation_id": inv_id,
                "service_id": svc_id,
                "status": status,
                "confidence": float(confidence) if confidence else 0.0,
                "created_at": created_at,
            })

    return prior
