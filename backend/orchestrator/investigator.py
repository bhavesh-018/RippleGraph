"""
RippleGraph - Stage 1: Investigator

Executes deterministic Cypher-powered discovery to build the raw evidence
footprint for a given change proposal. Runs all four graph tools in sequence:

  1. find_direct_consumers       - who calls the target API right now
  2. check_contract_compatibility - which consumers break under proposed contract
  3. traverse_downstream_deps    - multi-hop blast radius (up to 4 hops)
  4. get_relevant_incidents      - historical incidents filtered by claim type
"""

import logging
from typing import Any, Dict, List, Optional

from graph.client import get_graph
from graph.tools import (
    check_contract_compatibility,
    find_direct_consumers,
    get_relevant_incidents,
    traverse_downstream_dependencies,
)

logger = logging.getLogger("ripplegraph.investigator")


def run_investigator(
    change: Dict[str, Any],
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Stage 1: Run Cypher-powered discovery for a change proposal.

    Args:
        change: A dict representing the ChangeProposal with keys:
                  - id              (str)  e.g. "CHG-001"
                  - title           (str)
                  - proposing_service (str) e.g. "auth-service"
                  - target_api      (str)  e.g. "auth-token-api"
                  - proposed_contract_id (str) e.g. "cv-auth-v2"
                  - claim_types     (list[str])
                  - description     (str)
        graph: Optional FalkorDB graph handle (injected in tests).

    Returns:
        A dict with keys:
          - change_id
          - target_api
          - proposed_contract_id
          - claim_types
          - direct_consumers      list[dict]
          - compatibility_report  dict
          - downstream_services   list[dict]
          - relevant_incidents    list[dict]
          - all_affected_service_ids  list[str]  (direct + downstream IDs)
    """
    if graph is None:
        graph = get_graph()

    change_id = change.get("id", "CHG-001")
    target_api = change.get("target_api", "auth-token-api")
    proposed_contract_id = change.get("proposed_contract_id", "cv-auth-v2")
    proposing_service = change.get("proposing_service", "auth-service")
    claim_types: List[str] = change.get("claim_types", [])

    logger.info(
        "[Stage 1] Investigator started | change=%s api=%s contract=%s",
        change_id,
        target_api,
        proposed_contract_id,
    )

    # Step 1: Discover all direct consumers of the target API
    logger.info("[Stage 1] Finding direct consumers of API: %s", target_api)
    direct_consumers = find_direct_consumers(target_api, graph=graph)
    logger.info("[Stage 1] Found %d direct consumer(s)", len(direct_consumers))

    # Step 2: Check contract compatibility for each direct consumer
    logger.info("[Stage 1] Checking contract compatibility: %s", proposed_contract_id)
    compatibility_report = check_contract_compatibility(
        proposed_contract_id,
        graph=graph,
    )
    logger.info(
        "[Stage 1] Compatibility: %d compatible, %d incompatible",
        compatibility_report["compatible_count"],
        compatibility_report["incompatible_count"],
    )

    # Step 3: Traverse downstream blast radius from the proposing service
    logger.info("[Stage 1] Traversing downstream from: %s", proposing_service)
    downstream_services = traverse_downstream_dependencies(
        proposing_service,
        max_depth=4,
        graph=graph,
    )
    logger.info("[Stage 1] Found %d downstream service(s)", len(downstream_services))

    # Step 4: Collect all affected service IDs (direct + downstream)
    direct_ids = {c["service_id"] for c in direct_consumers}
    downstream_ids = {s["service_id"] for s in downstream_services}
    all_affected_ids = sorted(direct_ids | downstream_ids)

    # Step 5: Retrieve relevant historical incidents, filtered by claim type
    logger.info(
        "[Stage 1] Querying incidents for %d services with claim_types=%s",
        len(all_affected_ids),
        claim_types,
    )
    relevant_incidents = get_relevant_incidents(
        service_ids=all_affected_ids if all_affected_ids else None,
        active_claim_types=claim_types if claim_types else None,
        graph=graph,
    )
    relevant_count = sum(1 for i in relevant_incidents if i["relevance_status"] == "RELEVANT")
    rejected_count = sum(1 for i in relevant_incidents if i["relevance_status"] == "REJECTED_RED_HERRING")
    logger.info(
        "[Stage 1] Incidents: %d relevant, %d rejected as red herrings",
        relevant_count,
        rejected_count,
    )

    logger.info("[Stage 1] Investigator complete.")

    return {
        "change_id": change_id,
        "target_api": target_api,
        "proposed_contract_id": proposed_contract_id,
        "claim_types": claim_types,
        "direct_consumers": direct_consumers,
        "compatibility_report": compatibility_report,
        "downstream_services": downstream_services,
        "relevant_incidents": relevant_incidents,
        "all_affected_service_ids": all_affected_ids,
    }
