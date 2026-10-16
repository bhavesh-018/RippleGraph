"""
RippleGraph - Natural Language Graph Query API

Provides:
  GET  /api/graph/nl-query  - Convert a natural language question to Cypher,
                              execute it against FalkorDB, and return structured results.

The endpoint enables users to ask plain English questions about the service
dependency graph (e.g. "Which services depend on auth-service?") and get
back structured data + the generated Cypher for full transparency.

Safety: All Cypher is validated read-only before execution. Write operations
are rejected at the orchestrator layer.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from graph.client import get_graph
from orchestrator.gemini import nl_to_cypher

router = APIRouter(prefix="/api/graph", tags=["Natural Language Query"])
logger = logging.getLogger("ripplegraph.api.nl_query")


def _serialize_row(row: list) -> List[Any]:
    """Convert a FalkorDB result row to a JSON-serializable list."""
    out = []
    for cell in row:
        if cell is None:
            out.append(None)
        elif isinstance(cell, (int, float, bool, str)):
            out.append(cell)
        elif hasattr(cell, "__dict__"):
            # FalkorDB Node or Edge object
            props = {}
            try:
                props = dict(cell.properties)
            except Exception:
                props = {"_repr": str(cell)}
            out.append(props)
        else:
            out.append(str(cell))
    return out


@router.get("/nl-query")
async def natural_language_query(
    question: str = Query(
        ...,
        description="Natural language question about the service graph",
        min_length=5,
        max_length=500,
    ),
    context: str = Query(
        default="",
        description="Optional context (e.g. currently selected change ID)",
        max_length=200,
    ),
) -> Dict[str, Any]:
    """
    Convert a natural language question into a FalkorDB Cypher query using Gemini,
    execute it, and return structured results alongside the generated Cypher.

    The generated Cypher is always included in the response for full transparency —
    users can see exactly what query was run against their graph.

    Safety: Any Cypher containing write operations is rejected before execution.

    Example questions:
      - "Which services depend on auth-service?"
      - "What incidents affected the payment service?"
      - "Show me all incompatible findings from the last investigation"
      - "Which services accept contract version cv-auth-v1?"
    """
    # Step 1: Generate Cypher from natural language via Gemini
    try:
        cypher = nl_to_cypher(question, extra_context=context or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Step 2: Execute the validated Cypher against FalkorDB
    graph = get_graph()
    try:
        result = graph.query(cypher)
    except Exception as exc:
        logger.exception("Cypher execution failed for query: %s | error: %s", cypher, exc)
        raise HTTPException(
            status_code=422,
            detail=f"Cypher execution failed: {exc}. Generated query: {cypher}",
        )

    # Step 3: Serialize results
    raw_header = getattr(result, "header", None) or []
    columns: List[str] = []
    for col in raw_header:
        if isinstance(col, (list, tuple)) and len(col) >= 2:
            columns.append(str(col[1]))
        elif isinstance(col, (list, tuple)) and len(col) == 1:
            columns.append(str(col[0]))
        else:
            columns.append(str(col))

    rows: List[List[Any]] = [_serialize_row(row) for row in result.result_set]

    # Build column-keyed records for easier frontend consumption
    records: List[Dict[str, Any]] = []
    for row in rows:
        if columns:
            records.append(dict(zip(columns, row)))
        else:
            records.append({"values": row})

    return {
        "question": question,
        "cypher": cypher,
        "columns": columns,
        "records": records,
        "total": len(records),
        "model": "gemini-1.5-flash",
    }
