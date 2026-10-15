"""
RippleGraph - Topology API

Provides GET /api/graph/topology to fetch the full 10-service dependency graph
formatted directly for React Flow canvas consumption.
"""

from typing import Any, Dict, List
from fastapi import APIRouter
from graph.client import get_graph
from schemas.graph import ReactFlowEdge, ReactFlowNode, TopologyResponse

router = APIRouter(prefix="/api/graph", tags=["Topology"])

# Initial hierarchical layout coordinates (X, Y) for clean initial visual presentation
DEFAULT_LAYOUT = {
    "auth-service": {"x": 400.0, "y": 60.0},
    "session-service": {"x": 160.0, "y": 180.0},
    "user-service": {"x": 300.0, "y": 280.0},
    "payment-service": {"x": 560.0, "y": 180.0},
    "audit-service": {"x": 780.0, "y": 180.0},
    "notification-service": {"x": 40.0, "y": 180.0},
    "checkout-service": {"x": 500.0, "y": 380.0},
    "order-service": {"x": 420.0, "y": 520.0},
    "inventory-service": {"x": 660.0, "y": 520.0},
    "analytics-service": {"x": 200.0, "y": 520.0},
}


@router.get("/topology", response_model=TopologyResponse)
async def get_graph_topology():
    """
    Fetch the complete ecosystem graph formatted for React Flow canvas.

    Returns:
        - nodes: list of ReactFlowNode objects with service metadata and initial coordinates
        - edges: list of ReactFlowEdge objects representing DEPENDS_ON relationships
        - total_services: count of services (10)
        - total_dependencies: count of dependency edges (11)
    """
    graph = get_graph()

    # 1. Fetch services with rich metadata
    svc_res = graph.query(
        """
        MATCH (s:Service)
        RETURN s.id, s.name, s.tier, s.owner_team, s.repo,
               s.description, s.icon, s.runtime, s.version, s.port
        ORDER BY s.id
        """
    )

    # 2. Fetch APIs provided by each service
    api_res = graph.query(
        "MATCH (s:Service)-[:PROVIDES_API]->(a:API) RETURN s.id, a.id, a.name, a.protocol, a.path"
    )
    apis_by_svc: Dict[str, List[Dict[str, Any]]] = {}
    for svc_id, a_id, a_name, proto, path in api_res.result_set:
        apis_by_svc.setdefault(svc_id, []).append({
            "id": a_id,
            "name": a_name,
            "protocol": proto,
            "path": path,
        })

    # 3. Fetch accepted contract versions by service
    contract_res = graph.query(
        "MATCH (s:Service)-[:ACCEPTS_CONTRACT]->(c:ContractVersion) RETURN s.id, c.id, c.version ORDER BY c.version"
    )
    contracts_by_svc: Dict[str, List[Dict[str, str]]] = {}
    for svc_id, c_id, c_ver in contract_res.result_set:
        contracts_by_svc.setdefault(svc_id, []).append({
            "contract_id": c_id,
            "version": c_ver,
        })

    # 4. Construct React Flow nodes
    nodes: List[ReactFlowNode] = []
    for row in svc_res.result_set:
        svc_id, name, tier, owner_team, repo = row[0], row[1], row[2], row[3], row[4]
        desc = row[5] if len(row) > 5 and row[5] else ""
        icon = row[6] if len(row) > 6 and row[6] else "Server"
        runtime = row[7] if len(row) > 7 and row[7] else "Python 3.12"
        version = row[8] if len(row) > 8 and row[8] else "v1.0.0"
        port = row[9] if len(row) > 9 and row[9] else 8080

        pos = DEFAULT_LAYOUT.get(svc_id, {"x": 200.0, "y": 200.0})
        node_data = {
            "id": svc_id,
            "name": name,
            "label": name,
            "tier": tier,
            "owner_team": owner_team,
            "repo": repo,
            "description": desc,
            "icon": icon,
            "runtime": runtime,
            "version": version,
            "port": port,
            "status": "unaffected",
            "apis": apis_by_svc.get(svc_id, []),
            "accepted_contracts": contracts_by_svc.get(svc_id, []),
        }
        nodes.append(ReactFlowNode(
            id=svc_id,
            type="serviceNode",
            position=pos,
            data=node_data,
        ))

    # 5. Fetch DEPENDS_ON edges
    edge_res = graph.query(
        "MATCH (a:Service)-[r:DEPENDS_ON]->(b:Service) RETURN a.id, b.id ORDER BY a.id, b.id"
    )
    edges: List[ReactFlowEdge] = []
    for dependent, provider in edge_res.result_set:
        edge_id = f"e-{dependent}-{provider}"
        edges.append(ReactFlowEdge(
            id=edge_id,
            source=dependent,
            target=provider,
            type="smoothstep",
            animated=False,
            label="DEPENDS_ON",
            data={"dependent": dependent, "provider": provider},
        ))

    return TopologyResponse(
        nodes=nodes,
        edges=edges,
        total_services=len(nodes),
        total_dependencies=len(edges),
    )
