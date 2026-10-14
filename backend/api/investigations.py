"""
RippleGraph - Investigations API

Provides:
  POST /api/investigations         - Start the 4-stage Change Rehearsal pipeline
  GET  /api/investigations         - List all investigation runs from FalkorDB
  GET  /api/investigations/{id}    - Fetch a single investigation by ID
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from graph.client import get_graph
from orchestrator.pipeline import run_pipeline
from schemas.graph import InvestigationRequest, InvestigationResponse, FindingNode

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])

logger = logging.getLogger("ripplegraph.api.investigations")


@router.post("", response_model=InvestigationResponse)
async def start_investigation(request: InvestigationRequest):
    """
    Trigger the 4-stage Change Rehearsal pipeline for a given change proposal.

    Body:
      - change_id      (str, optional)  ID of a built-in change ("CHG-001", "CHG-002").
      - change         (obj, optional)  Custom ChangeProposal if not using a built-in.
      - memory_enabled (bool)           Whether to apply Stage 2 memory retrieval.

    Returns a fully populated InvestigationResponse with findings, red herrings,
    confidence scores, and execution timing.
    """
    change_override: Optional[Dict[str, Any]] = None
    if request.change is not None:
        change_override = request.change.model_dump()

    try:
        result = run_pipeline(
            change_id=request.change_id or "CHG-001",
            change_override=change_override,
            memory_enabled=request.memory_enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Pipeline execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    # Coerce findings dicts into FindingNode models for serialization
    findings_models = [FindingNode(**f) for f in result["findings"]]
    result["findings"] = findings_models

    return InvestigationResponse(**result)


@router.get("", response_model=List[Dict[str, Any]])
async def list_investigations():
    """
    Return all Investigation run summaries stored in FalkorDB,
    ordered by creation time descending.
    """
    graph = get_graph()
    try:
        res = graph.query(
            "MATCH (inv:Investigation) "
            "RETURN inv.id, inv.change_id, inv.change_title, inv.status, "
            "       inv.memory_enabled, inv.created_at "
            "ORDER BY inv.created_at DESC"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {exc}")

    investigations = []
    for row in res.result_set:
        inv_id, change_id, change_title, status, memory_enabled, created_at = row
        investigations.append({
            "investigation_id": inv_id,
            "change_id": change_id,
            "change_title": change_title,
            "status": status,
            "memory_enabled": bool(memory_enabled),
            "created_at": created_at,
        })

    return investigations


@router.get("/{investigation_id}", response_model=Dict[str, Any])
async def get_investigation(investigation_id: str):
    """
    Fetch a single investigation run and all its findings from FalkorDB.
    """
    graph = get_graph()

    # Fetch investigation node
    try:
        inv_res = graph.query(
            "MATCH (inv:Investigation {id: $id}) "
            "RETURN inv.id, inv.change_id, inv.change_title, inv.status, "
            "       inv.memory_enabled, inv.created_at",
            {"id": investigation_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {exc}")

    if not inv_res.result_set:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found.")

    inv_id, change_id, change_title, status, memory_enabled, created_at = inv_res.result_set[0]

    # Fetch linked findings
    try:
        fnd_res = graph.query(
            "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding) "
            "RETURN f.id, f.service_id, f.service_name, f.category, "
            "       f.status, f.confidence, f.hop_depth, f.created_at "
            "ORDER BY f.confidence DESC",
            {"id": investigation_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Findings query failed: {exc}")

    findings = []
    for row in fnd_res.result_set:
        fnd_id, svc_id, svc_name, cat, st, conf, hop, fnd_at = row
        findings.append({
            "id": fnd_id,
            "service_id": svc_id,
            "service_name": svc_name,
            "category": cat,
            "status": st,
            "confidence": float(conf) if conf else 0.0,
            "hop_depth": int(hop) if hop else 0,
            "created_at": fnd_at,
        })

    return {
        "investigation_id": inv_id,
        "change_id": change_id,
        "change_title": change_title,
        "status": status,
        "memory_enabled": bool(memory_enabled),
        "created_at": created_at,
        "findings": findings,
        "findings_count": len(findings),
    }
