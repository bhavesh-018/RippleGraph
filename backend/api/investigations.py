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
from fastapi.responses import StreamingResponse

from graph.client import get_graph
from orchestrator.pipeline import run_pipeline
from orchestrator.stream import stream_investigation
from schemas.graph import InvestigationRequest, InvestigationResponse, FindingNode

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])

logger = logging.getLogger("ripplegraph.api.investigations")


@router.get("/stream")
async def stream_investigation_endpoint(
    change_id: str = "CHG-001",
    memory_enabled: bool = True,
    disconnect_graph: bool = False,
    pace_delay_s: float = 0.35,
):
    """
    Stream investigation execution events in real time using Server-Sent Events (SSE).
    Enables live React Flow graph node highlights and traversal edge animations.
    """
    return StreamingResponse(
        stream_investigation(
            change_id=change_id,
            memory_enabled=memory_enabled,
            disconnect_graph=disconnect_graph,
            pace_delay_s=pace_delay_s,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
            disconnect_graph=request.disconnect_graph,
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

@router.get("/{investigation_id}/findings/{finding_id}/evidence")
async def get_finding_evidence(investigation_id: str, finding_id: str):
    """
    Return the full evidence graph for a specific finding:
    connected Service, Incidents (with Mitigations), and ContractVersion.
    """
    import json as _json

    def _parse(raw):
        try:
            return _json.loads(raw) if raw else []
        except Exception:
            return []

    graph = get_graph()

    # Fetch finding node properties from FalkorDB
    try:
        fnd_res = graph.query(
            "MATCH (f:Finding {id: $fid}) "
            "RETURN f.id, f.service_id, f.service_name, f.category, f.status, "
            "       f.confidence, f.reasons, f.missing_claims, f.dependency_chains, "
            "       f.hop_depth, f.relevant_incidents, f.recommended_contract_id",
            {"fid": finding_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {exc}")

    if not fnd_res.result_set:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found.")

    row = fnd_res.result_set[0]
    fid, svc_id, svc_name, cat, fstatus, conf, reasons_raw, missing_raw, chains_raw, hop, incidents_raw, rec_contract = row

    finding_data = {
        "id": fid,
        "service_id": svc_id,
        "service_name": svc_name,
        "category": cat,
        "status": fstatus,
        "confidence": float(conf) if conf else 0.0,
        "reasons": _parse(reasons_raw),
        "missing_claims": _parse(missing_raw),
        "dependency_chains": _parse(chains_raw),
        "hop_depth": int(hop) if hop else 0,
        "relevant_incidents": _parse(incidents_raw),
        "recommended_contract_id": rec_contract or None,
    }

    # Fetch connected Service node
    service = None
    try:
        svc_res = graph.query(
            "MATCH (f:Finding {id: $fid})-[:ABOUT_SERVICE]->(s:Service) "
            "RETURN s.id, s.name, s.tier, s.owner_team, s.description, s.runtime, s.port",
            {"fid": finding_id},
        )
        if svc_res.result_set:
            r = svc_res.result_set[0]
            service = {"id": r[0], "name": r[1], "tier": r[2], "owner_team": r[3],
                       "description": r[4], "runtime": r[5], "port": r[6]}
    except Exception:
        pass

    # Fetch connected Incidents + their Mitigations
    incidents = []
    try:
        inc_res = graph.query(
            "MATCH (f:Finding {id: $fid})-[:SUPPORTED_BY]->(i:Incident) "
            "OPTIONAL MATCH (i)-[:MITIGATED_BY]->(m:Mitigation) "
            "RETURN i.id, i.title, i.severity, i.description, i.occurred_at, "
            "       m.id, m.title, m.description, m.validation_method",
            {"fid": finding_id},
        )
        for r in inc_res.result_set:
            mitigation = None
            if r[5]:
                mitigation = {"id": r[5], "title": r[6], "description": r[7], "validation_method": r[8]}
            incidents.append({"id": r[0], "title": r[1], "severity": r[2],
                               "description": r[3], "occurred_at": r[4], "mitigation": mitigation})
    except Exception:
        pass

    # Fetch connected ContractVersion
    contract = None
    try:
        cv_res = graph.query(
            "MATCH (f:Finding {id: $fid})-[:ABOUT_CONTRACT]->(cv:ContractVersion) "
            "RETURN cv.id, cv.version, cv.description, cv.status",
            {"fid": finding_id},
        )
        if cv_res.result_set:
            r = cv_res.result_set[0]
            contract = {"id": r[0], "version": r[1], "description": r[2], "status": r[3]}
    except Exception:
        pass

    return {
        "finding": finding_data,
        "service": service,
        "incidents": incidents,
        "contract": contract,
    }
