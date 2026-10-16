"""
RippleGraph - Model Context Protocol (MCP) Server

Exposes RippleGraph's FalkorDB property graph, deterministic graph tools,
and natural language query capabilities to any MCP-compatible AI agent
(e.g., Claude Desktop, Cursor, Antigravity IDE, custom LLM agents).

Tools exposed:
  - find_direct_consumers: Discover immediate consumers of an API
  - check_contract_compatibility: Deterministic claim-diff compatibility check
  - traverse_downstream_dependencies: Multi-hop reverse dependency blast radius
  - get_relevant_incidents: Incident history with adversarial red-herring filter
  - query_graph_cypher: Safe, read-only Cypher query execution on FalkorDB
  - ask_graph: Natural language question -> Gemini Cypher -> FalkorDB results

Resources exposed:
  - graph://schema: RippleGraph node labels, properties, and relationship types
  - graph://services: All registered services and their tiers in the graph

Prompts exposed:
  - rehearse-change: Guided change rehearsal prompt for evaluating blast radius

Transport:
  Default stdio transport when run directly (`python mcp_server.py`).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer

from graph.client import get_graph
from graph.tools import (
    check_contract_compatibility as _check_contract_compatibility,
    find_direct_consumers as _find_direct_consumers,
    get_relevant_incidents as _get_relevant_incidents,
    traverse_downstream_dependencies as _traverse_downstream_dependencies,
)
from orchestrator.gemini import _is_safe_cypher, nl_to_cypher

logger = logging.getLogger("ripplegraph.mcp")

# Initialize MCP Server
server = MCPServer(
    name="RippleGraph",
    description="FalkorDB Graph-backed Change Rehearsal and Blast Radius Reasoning",
)


# =============================================================================
# Tools
# =============================================================================


@server.tool(
    name="find_direct_consumers",
    description=(
        "Find all services that directly consume a given API via ACCEPTS_CONTRACT edges. "
        "Traverses (API)-[:HAS_CONTRACT]->(ContractVersion)<-[:ACCEPTS_CONTRACT]-(Service)."
    ),
)
def find_direct_consumers(api_id: str) -> str:
    """Find immediate consumer services for an API ID."""
    try:
        consumers = _find_direct_consumers(api_id)
        return json.dumps(consumers, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@server.tool(
    name="check_contract_compatibility",
    description=(
        "Evaluate deterministic compatibility between a proposed ContractVersion "
        "and consumer services by diffing claim JSON structures. Identifies exact missing claims."
    ),
)
def check_contract_compatibility(
    proposed_contract_id: str,
    consumer_service_ids: Optional[List[str]] = None,
) -> str:
    """Check deterministic claim compatibility for a proposed contract."""
    try:
        res = _check_contract_compatibility(
            proposed_contract_id=proposed_contract_id,
            consumer_service_ids=consumer_service_ids,
        )
        return json.dumps(res, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@server.tool(
    name="traverse_downstream_dependencies",
    description=(
        "Traverse multi-hop reverse DEPENDS_ON edges starting from service_id to discover "
        "all transitive downstream dependents within max_depth hops (breadth-first search)."
    ),
)
def traverse_downstream_dependencies(service_id: str, max_depth: int = 4) -> str:
    """Compute transitive multi-hop blast radius for a given service."""
    try:
        deps = _traverse_downstream_dependencies(service_id=service_id, max_depth=max_depth)
        return json.dumps(deps, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@server.tool(
    name="get_relevant_incidents",
    description=(
        "Fetch historical incidents tied to specified services and evaluate claim-type "
        "relevance to detect and reject irrelevant red-herring incidents."
    ),
)
def get_relevant_incidents(
    service_ids: Optional[List[str]] = None,
    active_claim_types: Optional[List[str]] = None,
) -> str:
    """Retrieve filtered historical incidents and mitigations from FalkorDB."""
    try:
        incidents = _get_relevant_incidents(
            service_ids=service_ids,
            active_claim_types=active_claim_types,
        )
        return json.dumps(incidents, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@server.tool(
    name="query_graph_cypher",
    description=(
        "Execute a raw READ-ONLY Cypher query directly against FalkorDB. "
        "Write operations (CREATE, DELETE, SET, MERGE, REMOVE, DROP) are strictly forbidden."
    ),
)
def query_graph_cypher(cypher: str) -> str:
    """Run a safe read-only Cypher query against FalkorDB."""
    if not _is_safe_cypher(cypher):
        return json.dumps({
            "error": "Query rejected: Write operations are not allowed in read-only Cypher tool."
        })

    try:
        graph = get_graph()
        result = graph.query(cypher)
        raw_header = getattr(result, "header", None) or []
        columns: List[str] = []
        for col in raw_header:
            if isinstance(col, (list, tuple)) and len(col) >= 2:
                columns.append(str(col[1]))
            elif isinstance(col, (list, tuple)) and len(col) == 1:
                columns.append(str(col[0]))
            else:
                columns.append(str(col))

        rows: List[List[Any]] = []
        for row in getattr(result, "result_set", []):
            formatted_row = []
            for cell in row:
                if hasattr(cell, "properties"):
                    formatted_row.append(dict(cell.properties))
                else:
                    formatted_row.append(cell)
            rows.append(formatted_row)

        records = [dict(zip(columns, r)) if columns else {"values": r} for r in rows]
        return json.dumps({"columns": columns, "records": records, "total": len(records)}, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"Cypher execution error: {exc}"})


@server.tool(
    name="ask_graph",
    description=(
        "Ask a plain English natural language question about the RippleGraph service topology. "
        "Gemini translates the question into safe read-only Cypher and executes it on FalkorDB."
    ),
)
def ask_graph(question: str) -> str:
    """Convert natural language question to Cypher via Gemini and execute on FalkorDB."""
    try:
        cypher = nl_to_cypher(question)
        graph = get_graph()
        result = graph.query(cypher)

        raw_header = getattr(result, "header", None) or []
        columns: List[str] = []
        for col in raw_header:
            if isinstance(col, (list, tuple)) and len(col) >= 2:
                columns.append(str(col[1]))
            elif isinstance(col, (list, tuple)) and len(col) == 1:
                columns.append(str(col[0]))
            else:
                columns.append(str(col))

        rows: List[List[Any]] = []
        for row in getattr(result, "result_set", []):
            formatted_row = []
            for cell in row:
                if hasattr(cell, "properties"):
                    formatted_row.append(dict(cell.properties))
                else:
                    formatted_row.append(cell)
            rows.append(formatted_row)

        records = [dict(zip(columns, r)) if columns else {"values": r} for r in rows]
        return json.dumps({
            "question": question,
            "generated_cypher": cypher,
            "columns": columns,
            "records": records,
            "total": len(records),
        }, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# =============================================================================
# Resources
# =============================================================================


@server.resource(
    uri="graph://schema",
    name="RippleGraph Property Graph Schema",
    description="Node labels, key properties, and relationships in FalkorDB",
    mime_type="text/markdown",
)
def get_graph_schema() -> str:
    """Return the RippleGraph property graph schema."""
    return """# RippleGraph Graph Schema

## Nodes
- **Service**: `id`, `name`, `tier`, `owner_team`, `repo`, `runtime`, `version`, `port`
- **API**: `id`, `name`, `protocol`, `path`, `service_id`
- **ContractVersion**: `id`, `name`, `version`, `status`, `claims`, `breaking_change`
- **Incident**: `id`, `title`, `severity`, `description`, `root_cause`, `occurred_at`, `claim_types`
- **Mitigation**: `id`, `title`, `description`, `validation_method`
- **Finding**: `id`, `service_id`, `service_name`, `category`, `status`, `confidence`, `hop_depth`
- **Investigation**: `id`, `change_id`, `change_title`, `status`, `memory_enabled`, `created_at`

## Relationships
- `(:Service)-[:EXPOSES]->(:API)`
- `(:Service)-[:DEPENDS_ON]->(:Service)`
- `(:Service)-[:ACCEPTS_CONTRACT]->(:ContractVersion)`
- `(:API)-[:HAS_CONTRACT]->(:ContractVersion)`
- `(:Incident)-[:AFFECTED]->(:Service)`
- `(:Incident)-[:MITIGATED_BY]->(:Mitigation)`
- `(:Investigation)-[:PRODUCED]->(:Finding)`
- `(:Finding)-[:ABOUT_SERVICE]->(:Service)`
"""


@server.resource(
    uri="graph://services",
    name="RippleGraph Services List",
    description="List of all registered microservices and their criticality tiers",
    mime_type="application/json",
)
def get_graph_services() -> str:
    """Return list of all services in the graph."""
    try:
        graph = get_graph()
        res = graph.query("MATCH (s:Service) RETURN s.id, s.name, s.tier, s.owner_team ORDER BY s.tier, s.id")
        services = [
            {"id": row[0], "name": row[1], "tier": row[2], "owner_team": row[3]}
            for row in res.result_set
        ]
        return json.dumps(services, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# =============================================================================
# Prompts
# =============================================================================


@server.prompt(
    name="rehearse-change",
    description="Guided prompt to investigate the blast radius of a proposed contract change",
)
def rehearse_change_prompt(change_id: str) -> str:
    """Generate prompt instructions for rehearsing a contract change."""
    return f"""You are the RippleGraph Change Rehearsal Agent.
Investigate the proposed contract change '{change_id}'.

Step 1: Check which API and ContractVersion are affected by querying the graph.
Step 2: Use `find_direct_consumers` to find all services directly accepting that contract.
Step 3: Use `check_contract_compatibility` to deterministically verify claim compatibility.
Step 4: Use `traverse_downstream_dependencies` to discover multi-hop callers that may suffer transitive impact.
Step 5: Use `get_relevant_incidents` to find past incident precedent (rejecting red herrings).
Step 6: Formulate an evidence-grounded risk verdict (CRITICAL, HIGH, MEDIUM, LOW) and provide actionable mitigations.
"""


if __name__ == "__main__":
    # Start the MCP server using standard I/O transport
    logger.info("Starting RippleGraph MCP Server...")
    server.run()
