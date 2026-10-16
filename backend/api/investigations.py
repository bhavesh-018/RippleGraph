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
from schemas.history import InvestigationSummary, InvestigationHistoryResponse

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


from pydantic import BaseModel
from orchestrator.comparison import compare_investigation_memory
from schemas.comparison import MemoryComparisonResponse


class CompareRequest(BaseModel):
    change_id: str = "CHG-001"


@router.post("/compare", response_model=MemoryComparisonResponse)
async def compare_memory_post(req: Optional[CompareRequest] = None):
    """
    Execute Change Rehearsal with Memory ON vs Memory OFF and return
    side-by-side confidence deltas and reaffirmation insights.
    """
    change_id = req.change_id if req else "CHG-001"
    try:
        return compare_investigation_memory(change_id=change_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Memory comparison failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")


@router.get("/compare", response_model=MemoryComparisonResponse)
async def compare_memory_get(change_id: str = "CHG-001"):
    """
    GET convenience endpoint for memory comparison.
    """
    try:
        return compare_investigation_memory(change_id=change_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Memory comparison failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}")


@router.get("/history", response_model=InvestigationHistoryResponse)
async def list_investigation_history(limit: int = 50):
    """
    Return a rich, stats-enriched timeline of all past investigation runs,
    ordered by creation time descending (newest first).

    For each run, the response includes per-status finding counts and
    average confidence, enabling the frontend History Timeline to display
    at-a-glance health badges without a second request.

    Query params:
      - limit  (int, default 50)  Maximum number of runs to return.
    """
    graph = get_graph()

    # Fetch all investigation nodes
    try:
        inv_res = graph.query(
            "MATCH (inv:Investigation) "
            "RETURN inv.id, inv.change_id, inv.change_title, inv.status, "
            "       inv.memory_enabled, inv.created_at "
            "ORDER BY inv.created_at DESC "
            f"LIMIT {int(limit)}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph query failed: {exc}")

    summaries: list[InvestigationSummary] = []
    for row in inv_res.result_set:
        inv_id, change_id, change_title, status, memory_enabled, created_at = row

        # Fetch finding stats for this investigation
        try:
            fnd_res = graph.query(
                "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding) "
                "RETURN f.status, f.confidence",
                {"id": inv_id},
            )
        except Exception:
            fnd_res = None

        incompatible = at_risk = compatible = unaffected = 0
        confidences: list[float] = []

        if fnd_res:
            for frow in fnd_res.result_set:
                fstatus, fconf = frow
                conf_val = float(fconf) if fconf is not None else 0.0
                confidences.append(conf_val)
                if fstatus == "incompatible":
                    incompatible += 1
                elif fstatus == "potential_downstream":
                    at_risk += 1
                elif fstatus == "compatible":
                    compatible += 1
                elif fstatus == "unaffected":
                    unaffected += 1

        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        total_findings = incompatible + at_risk + compatible + unaffected

        summaries.append(
            InvestigationSummary(
                investigation_id=inv_id,
                change_id=change_id or "",
                change_title=change_title or "",
                status=status or "unknown",
                memory_enabled=bool(memory_enabled),
                disconnect_graph=False,
                created_at=created_at or "",
                findings_count=total_findings,
                incompatible_count=incompatible,
                at_risk_count=at_risk,
                compatible_count=compatible,
                unaffected_count=unaffected,
                avg_confidence=avg_conf,
                execution_time_ms=None,
            )
        )

    return InvestigationHistoryResponse(total=len(summaries), investigations=summaries)


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

@router.get("/{investigation_id}/checklist")
async def export_checklist(investigation_id: str):
    """
    Generate a downloadable Markdown mitigation checklist from all findings
    for a given investigation. Returned as a file attachment.
    """
    import json as _json
    from datetime import datetime
    from fastapi.responses import Response as FastAPIResponse

    def _parse(raw):
        try:
            return _json.loads(raw) if raw else []
        except Exception:
            return []

    graph = get_graph()

    # Fetch investigation node
    try:
        inv_res = graph.query(
            "MATCH (inv:Investigation {id: $id}) "
            "RETURN inv.id, inv.change_id, inv.change_title, inv.status, inv.created_at",
            {"id": investigation_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not inv_res.result_set:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found.")

    inv_id, change_id, change_title, inv_status, created_at = inv_res.result_set[0]

    # Fetch all findings with related evidence (join produces one row per incident)
    try:
        fnd_res = graph.query(
            "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding) "
            "OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(i:Incident)-[:MITIGATED_BY]->(m:Mitigation) "
            "OPTIONAL MATCH (f)-[:ABOUT_CONTRACT]->(cv:ContractVersion) "
            "RETURN f.id, f.service_name, f.status, f.confidence, f.hop_depth, "
            "       f.reasons, f.missing_claims, f.recommended_contract_id, "
            "       i.id, i.title, i.severity, "
            "       m.id, m.title, m.description, m.validation_method, "
            "       cv.id, cv.version "
            "ORDER BY f.confidence DESC",
            {"id": investigation_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Aggregate: join produces duplicate rows when a finding has multiple incidents
    findings_map: Dict[str, Any] = {}
    for row in fnd_res.result_set:
        (fid, svc_name, fstatus, fconf, hop,
         reasons_raw, missing_raw, rec_contract,
         inc_id, inc_title, inc_sev,
         mit_id, mit_title, mit_desc, mit_val,
         cv_id, cv_ver) = row

        if fid not in findings_map:
            findings_map[fid] = {
                "id": fid,
                "service_name": svc_name or fid,
                "status": fstatus or "",
                "confidence": float(fconf) if fconf else 0.0,
                "hop_depth": int(hop) if hop else 0,
                "reasons": _parse(reasons_raw),
                "missing_claims": _parse(missing_raw),
                "recommended_contract_id": rec_contract or None,
                "incidents": [],
                "contract": None,
            }

        f = findings_map[fid]

        if inc_id and not any(i["id"] == inc_id for i in f["incidents"]):
            mitigation = None
            if mit_id:
                mitigation = {
                    "id": mit_id, "title": mit_title,
                    "description": mit_desc, "validation_method": mit_val,
                }
            f["incidents"].append({
                "id": inc_id, "title": inc_title,
                "severity": inc_sev, "mitigation": mitigation,
            })

        if cv_id and not f["contract"]:
            f["contract"] = {"id": cv_id, "version": cv_ver}

    # ── Build Markdown ────────────────────────────────────────────────────────
    lines = [
        "# 🛡 RippleGraph — Mitigation Checklist", "",
        f"**Investigation:** `{inv_id}`  ",
        f"**Change:** {change_title} (`{change_id}`)  ",
        f"**Status:** {inv_status}  ",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "", "---", "",
        "## Summary", "",
        "| Service | Status | Confidence | Hop |",
        "|---------|--------|------------|-----|",
    ]

    for f in findings_map.values():
        icon = (
            "🔴" if "incompatible" in f["status"].lower()
            else "🟡" if "potential" in f["status"].lower()
            else "🟢"
        )
        lines.append(
            f"| {f['service_name']} | {icon} {f['status'].upper()} "
            f"| {int(f['confidence'] * 100)}% | Hop {f['hop_depth']} |"
        )

    lines += ["", "---", "", "## Findings & Action Items", ""]

    for idx, f in enumerate(findings_map.values(), 1):
        icon = (
            "🔴" if "incompatible" in f["status"].lower()
            else "🟡" if "potential" in f["status"].lower()
            else "🟢"
        )
        lines += [
            f"### {idx}. {f['service_name']} {icon}", "",
            f"- **Status:** `{f['status'].upper()}`",
            f"- **Agent Confidence:** {int(f['confidence'] * 100)}%",
            f"- **Hop Depth:** {f['hop_depth']}",
        ]

        if f["reasons"]:
            lines += ["", "**Audit Justification:**"]
            for r in f["reasons"]:
                lines.append(f"> {r}")

        if f["missing_claims"]:
            lines += ["", "**Missing Claims (must be added to new contract):**"]
            for c in f["missing_claims"]:
                lines.append(f"- [ ] `{c}`")

        if f["recommended_contract_id"]:
            lines += ["", f"**Recommended Migration Contract:** `{f['recommended_contract_id']}`"]

        if f["incidents"]:
            lines += ["", "**Historical Evidence:**"]
            for inc in f["incidents"]:
                sev = (inc.get("severity") or "").upper()
                lines.append(f"- **[{inc['id']}]** {inc['title']} _(Severity: {sev})_")
                if inc.get("mitigation"):
                    m = inc["mitigation"]
                    lines += [
                        f"  - ✅ **Playbook:** {m['title']}",
                        f"  - {m['description']}",
                        f"  - **Validation:** {m['validation_method']}",
                    ]

        if f["contract"]:
            lines += ["", f"**Transitional Contract:** `{f['contract']['id']}` v{f['contract']['version']}"]

        lines += ["", "---", ""]

    lines += [
        "## Next Steps", "",
        "1. Review all BREAKING services above and assign mitigation owners.",
        "2. Apply recommended migration contracts to each affected service.",
        "3. Re-run RippleGraph after contract updates to confirm blast radius is resolved.",
        "",
        "_Generated by RippleGraph Change Rehearsal Agent_",
    ]

    return FastAPIResponse(
        content="\n".join(lines),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="ripplgraph-checklist-{inv_id}.md"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


