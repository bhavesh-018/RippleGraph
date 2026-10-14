"""
RippleGraph - Connected Data Graph Tools

Deterministic Cypher query tools used by the Change Rehearsal Agent
to traverse FalkorDB topology and evaluate blast radius in single-digit ms.
"""

from typing import Any, Dict, List, Optional
from graph.client import get_graph


def find_direct_consumers(
    api_id: str,
    graph: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Find all services that directly consume a given API via ACCEPTS_CONTRACT edges.

    Traverses:
        (API)-[:HAS_CONTRACT]->(ContractVersion)<-[:ACCEPTS_CONTRACT]-(Service)

    Returns a list of consumer service dictionaries, each containing:
        - service_id: unique identifier of the consumer service
        - service_name: human-readable name of the service
        - tier: service criticality tier (e.g. platform, core, supporting)
        - owner_team: responsible engineering team
        - repo: repository location
        - accepted_contract_ids: list of ContractVersion IDs accepted by this service
        - accepted_contracts: list of dicts with id and version for each accepted contract
    """
    if graph is None:
        graph = get_graph()

    cypher = """
    MATCH (api:API {id: $api_id})-[:HAS_CONTRACT]->(cv:ContractVersion)<-[:ACCEPTS_CONTRACT]-(s:Service)
    RETURN s.id AS service_id,
           s.name AS service_name,
           s.tier AS tier,
           s.owner_team AS owner_team,
           s.repo AS repo,
           cv.id AS contract_id,
           cv.version AS version
    ORDER BY s.id, cv.version
    """

    res = graph.query(cypher, {"api_id": api_id})

    # Group by service so each consumer appears once with all accepted versions
    consumers_by_id: Dict[str, Dict[str, Any]] = {}
    for row in res.result_set:
        svc_id, name, tier, owner_team, repo, contract_id, version = row
        if svc_id not in consumers_by_id:
            consumers_by_id[svc_id] = {
                "service_id": svc_id,
                "service_name": name,
                "tier": tier,
                "owner_team": owner_team,
                "repo": repo,
                "accepted_contract_ids": [],
                "accepted_contracts": [],
            }
        consumers_by_id[svc_id]["accepted_contract_ids"].append(contract_id)
        consumers_by_id[svc_id]["accepted_contracts"].append({
            "contract_id": contract_id,
            "version": version,
        })

    return list(consumers_by_id.values())
