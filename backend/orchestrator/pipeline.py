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
from orchestrator.memory import (
    get_prior_findings_with_decay,
    apply_memory_to_findings,
)

logger = logging.getLogger("ripplegraph.pipeline")

# Built-in change proposals (seeded alongside graph data)
BUILTIN_CHANGES: Dict[str, Dict[str, Any]] = {
    "CHG-001": {
        "id": "CHG-001",
        "title": "Auth Token Field Rename: sub -> subject_id, roles -> scopes",
        "proposing_service": "auth-service",
        "proposing_service_name": "Auth Service",
        "target_api": "auth-token-api",
        "target_api_name": "Auth Token API",
        "proposed_contract_id": "cv-auth-v2",
        "risk_level": "CRITICAL",
        "impact_scope": "Multi-Hop Cascade (4 Hops)",
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
        "proposing_service_name": "Auth Service",
        "target_api": "auth-token-api",
        "target_api_name": "Auth Token API",
        "proposed_contract_id": "cv-auth-v1-extended",
        "risk_level": "SAFE",
        "impact_scope": "Zero Incompatible (Rolling Migration)",
        "claim_types": ["field_rename", "sub", "subject_id", "roles", "scopes", "token_format"],
        "description": (
            "Deploy the transitional contract cv-auth-v1-extended that supports both "
            "old claims (sub, roles) and new claims (subject_id, scopes) simultaneously. "
            "This allows a rolling migration without a coordinated cutover."
        ),
    },
    "CHG-003": {
        "id": "CHG-003",
        "title": "Payment Precision: amount (float) -> amount_cents (int), currency -> currency_iso",
        "proposing_service": "payment-service",
        "proposing_service_name": "Payment Service",
        "target_api": "payment-charge-api",
        "target_api_name": "Payment Charge API",
        "proposed_contract_id": "cv-payment-v2",
        "risk_level": "HIGH",
        "impact_scope": "Commerce Gateway Breakage (3 Hops)",
        "claim_types": ["currency", "amount_cents", "field_rename", "payment_format"],
        "description": (
            "Migrate floating-point currency representation to integer cents and enforce "
            "ISO-4217 standard currency codes. Affects checkout-service and downstream accounting."
        ),
    },
    "CHG-004": {
        "id": "CHG-004",
        "title": "Checkout Identity Schema: user_id -> account_uuid, shipping -> delivery_details",
        "proposing_service": "checkout-service",
        "proposing_service_name": "Checkout Service",
        "target_api": "checkout-create-api",
        "target_api_name": "Checkout Create API",
        "proposed_contract_id": "cv-checkout-v2",
        "risk_level": "HIGH",
        "impact_scope": "Order Fulfillment & Analytics (2 Hops)",
        "claim_types": ["user_id", "account_uuid", "shipping_address", "field_rename"],
        "description": (
            "Replaces legacy user_id strings with global account UUIDs and normalizes "
            "shipping addresses into delivery_details objects for multi-modal fulfillment."
        ),
    },
    "CHG-005": {
        "id": "CHG-005",
        "title": "Inventory Availability: Additive reserved_quantity Field",
        "proposing_service": "inventory-service",
        "proposing_service_name": "Inventory Service",
        "target_api": "inventory-query-api",
        "target_api_name": "Inventory Query API",
        "proposed_contract_id": "cv-inventory-v2",
        "risk_level": "SAFE",
        "impact_scope": "Backward Compatible Additive Update",
        "claim_types": ["inventory", "reserved_quantity", "additive"],
        "description": (
            "Adds reserved_quantity field to inventory stock responses without removing "
            "or renaming any existing fields. Existing order-service consumers remain compatible."
        ),
    },
    "CHG-006": {
        "id": "CHG-006",
        "title": "User Profile Schema: phone string -> contact_channels Object",
        "proposing_service": "user-service",
        "proposing_service_name": "User Service",
        "target_api": "user-profile-api",
        "target_api_name": "User Profile API",
        "proposed_contract_id": "cv-user-v2",
        "risk_level": "MEDIUM",
        "impact_scope": "Notification Dispatch Pipeline",
        "claim_types": ["phone", "contact_channels", "field_rename", "profile_format"],
        "description": (
            "Deprecates unstructured phone string in user profiles in favor of a structured "
            "contact_channels object specifying SMS, voice, and WhatsApp delivery preferences."
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

    # ---- Stage 2: Memory (prior findings retrieval with temporal decay) ----
    prior_findings: List[Dict[str, Any]] = []
    if memory_enabled:
        logger.info("[Pipeline] --- Stage 2: MEMORY ON (retrieving prior findings with decay) ---")
        prior_findings = get_prior_findings_with_decay(
            service_ids=investigator_output["all_affected_service_ids"],
            current_investigation_id=investigation_id,
            graph=graph,
        )
        logger.info(
            "[Pipeline] Prior findings retrieved: %d (with temporal+hop decay applied)",
            len(prior_findings),
        )
    else:
        logger.info("[Pipeline] --- Stage 2: MEMORY OFF (cold start, no prior context) ---")

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

    # Apply memory-backed confidence adjustments after reviewer classification
    if memory_enabled and prior_findings:
        logger.info("[Pipeline] Applying memory reaffirmation boosts to %d finding(s)", len(findings))
        findings = apply_memory_to_findings(findings, prior_findings)

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

