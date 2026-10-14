"""
RippleGraph - Connected Data Graph Tools

Deterministic Cypher query tools used by the Change Rehearsal Agent
to traverse FalkorDB topology and evaluate blast radius in single-digit ms.
"""

import json
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


def check_contract_compatibility(
    proposed_contract_id: str,
    consumer_service_ids: Optional[List[str]] = None,
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Evaluate deterministic compatibility between a proposed ContractVersion
    and consumer services.

    For each consumer service:
      1. If the service already has an ACCEPTS_CONTRACT edge to proposed_contract_id,
         it is immediately marked COMPATIBLE.
      2. Otherwise, we diff the claims published by the proposed contract against
         the claims expected by each contract version the consumer currently accepts.
         If any claim key required by an accepted version is missing in the proposed
         claims, the service is marked INCOMPATIBLE and the missing claims are reported.

    Returns a dict with overall metrics and individual service compatibility results.
    """
    if graph is None:
        graph = get_graph()

    # 1. Fetch proposed contract details
    prop_res = graph.query(
        """
        MATCH (c:ContractVersion {id: $id})
        RETURN c.id, c.name, c.version, c.api_id, c.claims, c.breaking_change
        """,
        {"id": proposed_contract_id},
    )
    if not prop_res.result_set:
        raise ValueError(f"ContractVersion '{proposed_contract_id}' not found in graph.")

    (
        prop_id,
        prop_name,
        prop_version,
        api_id,
        prop_claims_raw,
        prop_breaking,
    ) = prop_res.result_set[0]

    try:
        proposed_claims: Dict[str, Any] = json.loads(prop_claims_raw) if prop_claims_raw else {}
    except (json.JSONDecodeError, TypeError):
        proposed_claims = {}

    proposed_claim_keys = set(proposed_claims.keys())

    # 2. Find direct consumers if not specified
    if consumer_service_ids is None:
        consumers = find_direct_consumers(api_id, graph=graph)
    else:
        # Fetch requested consumer services that accept contracts on this API
        all_consumers = find_direct_consumers(api_id, graph=graph)
        requested_set = set(consumer_service_ids)
        consumers = [c for c in all_consumers if c["service_id"] in requested_set]

    # 3. Cache claims for all accepted contracts to avoid repeated queries
    contracts_res = graph.query(
        "MATCH (c:ContractVersion) RETURN c.id, c.claims, c.version"
    )
    contracts_claims_map: Dict[str, Dict[str, Any]] = {}
    for c_id, c_claims_raw, c_ver in contracts_res.result_set:
        try:
            contracts_claims_map[c_id] = json.loads(c_claims_raw) if c_claims_raw else {}
        except (json.JSONDecodeError, TypeError):
            contracts_claims_map[c_id] = {}

    results = []
    compatible_count = 0
    incompatible_count = 0

    for consumer in consumers:
        svc_id = consumer["service_id"]
        svc_name = consumer["service_name"]
        accepted_ids = consumer["accepted_contract_ids"]

        # Check if already accepts proposed version
        if proposed_contract_id in accepted_ids:
            results.append({
                "service_id": svc_id,
                "service_name": svc_name,
                "tier": consumer["tier"],
                "owner_team": consumer["owner_team"],
                "is_compatible": True,
                "accepted_contract_ids": accepted_ids,
                "missing_claims": [],
                "reasons": [f"Service explicitly accepts proposed contract '{proposed_contract_id}'."],
            })
            compatible_count += 1
            continue

        # Diff against all currently accepted versions
        all_missing_for_svc = set()
        incompat_reasons = []

        for acc_id in accepted_ids:
            acc_claims = contracts_claims_map.get(acc_id, {})
            acc_keys = set(acc_claims.keys())
            missing = acc_keys - proposed_claim_keys
            if missing:
                all_missing_for_svc.update(missing)
                sorted_missing = sorted(list(missing))
                incompat_reasons.append(
                    f"Contract '{acc_id}' expects claims {sorted_missing} not provided by '{proposed_contract_id}'."
                )

        if all_missing_for_svc:
            results.append({
                "service_id": svc_id,
                "service_name": svc_name,
                "tier": consumer["tier"],
                "owner_team": consumer["owner_team"],
                "is_compatible": False,
                "accepted_contract_ids": accepted_ids,
                "missing_claims": sorted(list(all_missing_for_svc)),
                "reasons": incompat_reasons,
            })
            incompatible_count += 1
        else:
            results.append({
                "service_id": svc_id,
                "service_name": svc_name,
                "tier": consumer["tier"],
                "owner_team": consumer["owner_team"],
                "is_compatible": True,
                "accepted_contract_ids": accepted_ids,
                "missing_claims": [],
                "reasons": ["All expected claims are satisfied by proposed contract."],
            })
            compatible_count += 1

    return {
        "proposed_contract_id": prop_id,
        "proposed_contract_name": prop_name,
        "proposed_version": prop_version,
        "api_id": api_id,
        "total_consumers_checked": len(consumers),
        "compatible_count": compatible_count,
        "incompatible_count": incompatible_count,
        "results": results,
    }


def traverse_downstream_dependencies(
    service_id: str,
    max_depth: int = 4,
    graph: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Traverse multi-hop reverse DEPENDS_ON edges starting from service_id to discover
    all transitive downstream dependents within max_depth hops.

    Traverses downstream along reverse DEPENDS_ON:
        (downstream:Service)-[:DEPENDS_ON]->...->(origin:Service)

    Returns a list of downstream service dictionaries, ordered by (min_hop_distance, service_id):
        - service_id: downstream service identifier
        - service_name: human-readable name of service
        - tier: service tier (platform, core, supporting)
        - owner_team: owning team
        - repo: repository path
        - min_hop_distance: shortest hop distance from target service (1 to max_depth)
        - dependency_chains: all paths from downstream caller to origin service
    """
    if graph is None:
        graph = get_graph()

    # 1. Fetch metadata for all services
    svc_res = graph.query("MATCH (s:Service) RETURN s.id, s.name, s.tier, s.owner_team, s.repo")
    svc_meta = {
        row[0]: {
            "service_id": row[0],
            "service_name": row[1],
            "tier": row[2],
            "owner_team": row[3],
            "repo": row[4],
        }
        for row in svc_res.result_set
    }

    if service_id not in svc_meta:
        raise ValueError(f"Service '{service_id}' not found in graph.")

    # 2. Fetch all DEPENDS_ON edges (consumer calls provider)
    edge_res = graph.query("MATCH (a:Service)-[:DEPENDS_ON]->(b:Service) RETURN a.id, b.id")

    # Reverse adjacency: provider -> list of immediate callers/dependents
    downstream_adj: Dict[str, List[str]] = {}
    for consumer, provider in edge_res.result_set:
        downstream_adj.setdefault(provider, []).append(consumer)

    # 3. Breadth-First Search from origin service up to max_depth
    from collections import deque

    queue = deque([(service_id, 0, [service_id])])
    visited: Dict[str, Dict[str, Any]] = {}

    while queue:
        curr, depth, path = queue.popleft()

        if depth > 0:
            if curr not in visited:
                visited[curr] = {
                    **svc_meta[curr],
                    "min_hop_distance": depth,
                    "dependency_chains": [path],
                }
            else:
                # Record additional alternate paths if not already seen
                if path not in visited[curr]["dependency_chains"]:
                    visited[curr]["dependency_chains"].append(path)

        if depth < max_depth:
            for nxt in downstream_adj.get(curr, []):
                # Avoid cycles in path
                if nxt not in path:
                    queue.append((nxt, depth + 1, [nxt] + path))

    # Sort deterministically by shortest hop distance, then service_id
    return sorted(
        visited.values(),
        key=lambda x: (x["min_hop_distance"], x["service_id"]),
    )


