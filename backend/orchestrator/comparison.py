"""
RippleGraph - Investigation Memory Comparison Engine
Feature 2: Memory ON vs OFF Comparison & Visual Diff
"""

import logging
import re
from typing import Any, Dict, List, Optional

from orchestrator.pipeline import run_pipeline, BUILTIN_CHANGES

logger = logging.getLogger("ripplegraph.comparison")


def compare_investigation_memory(
    change_id: str = "CHG-001",
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Execute Change Rehearsal twice:
      1. Memory OFF (Cold Start)
      2. Memory ON (FalkorDB Temporal Graph Memory)

    Computes per-service confidence deltas, reaffirmation statuses,
    and aggregate metrics to visually demonstrate Track 2 value.
    """
    if change_id not in BUILTIN_CHANGES:
        raise ValueError(
            f"Unknown change_id '{change_id}'. "
            f"Available: {list(BUILTIN_CHANGES.keys())}"
        )

    change = BUILTIN_CHANGES[change_id]

    # Ensure at least one baseline run exists in FalkorDB so memory has history to recall
    # If no prior findings exist, run a silent priming run
    _ensure_memory_history(change_id, graph=graph)

    # 1. Run without memory (Cold Start)
    logger.info("[Comparison] Running investigation WITHOUT memory (cold start)...")
    res_without = run_pipeline(
        change_id=change_id,
        memory_enabled=False,
        graph=graph,
    )

    # 2. Run with memory (FalkorDB graph memory enabled)
    logger.info("[Comparison] Running investigation WITH memory (FalkorDB enabled)...")
    res_with = run_pipeline(
        change_id=change_id,
        memory_enabled=True,
        graph=graph,
    )

    findings_without = {f["service_id"]: f for f in res_without.get("findings", [])}
    findings_with = {f["service_id"]: f for f in res_with.get("findings", [])}

    all_service_ids = list(dict.fromkeys(list(findings_with.keys()) + list(findings_without.keys())))

    deltas: List[Dict[str, Any]] = []
    reaffirmed_count = 0

    for svc_id in all_service_ids:
        fw = findings_with.get(svc_id, {})
        fwo = findings_without.get(svc_id, {})

        svc_name = fw.get("service_name") or fwo.get("service_name") or svc_id
        status_with = fw.get("status", "unaffected")
        status_without = fwo.get("status", "unaffected")

        conf_with = float(fw.get("confidence", 0.0))
        conf_without = float(fwo.get("confidence", 0.0))

        delta = round(conf_with - conf_without, 4)
        gain_pct = round(((conf_with - conf_without) / max(conf_without, 0.01)) * 100, 1)

        # Check for memory boost and extract explanation
        reasons_with = fw.get("reasons", [])
        memory_exp = None
        prior_inv_id = None
        is_reaffirmed = False

        for r in reasons_with:
            if "Memory boost:" in r or "Memory context:" in r:
                memory_exp = r
                m = re.search(r"prior investigation '([^']+)'", r)
                if m:
                    prior_inv_id = m.group(1)
            if "Memory boost:" in r:
                is_reaffirmed = True

        if is_reaffirmed or delta > 0.05:
            is_reaffirmed = True
            reaffirmed_count += 1

        missing = fw.get("missing_claims", []) or fwo.get("missing_claims", [])

        deltas.append({
            "service_id": svc_id,
            "service_name": svc_name,
            "status_with_memory": status_with,
            "status_without_memory": status_without,
            "confidence_with_memory": conf_with,
            "confidence_without_memory": conf_without,
            "confidence_delta": delta,
            "confidence_gain_pct": gain_pct,
            "memory_reaffirmed": is_reaffirmed,
            "prior_finding_cited": fw.get("id"),
            "prior_investigation_id": prior_inv_id,
            "memory_explanation": memory_exp,
            "missing_claims": missing,
        })

    # Summary metrics
    conf_with_list = [d["confidence_with_memory"] for d in deltas if d["confidence_with_memory"] > 0]
    conf_without_list = [d["confidence_without_memory"] for d in deltas if d["confidence_without_memory"] > 0]

    val_with = sum(conf_with_list) / max(len(conf_with_list), 1) if conf_with_list else 0.0
    val_without = sum(conf_without_list) / max(len(conf_without_list), 1) if conf_without_list else 0.0

    avg_with = round(val_with, 4)
    avg_without = round(val_without, 4)
    avg_delta = round(avg_with - avg_without, 4)
    overall_gain_pct = round(((avg_with - avg_without) / max(avg_without, 0.01)) * 100, 1)

    if reaffirmed_count > 0:
        verdict = (
            f"FalkorDB Temporal Memory reaffirmed {reaffirmed_count} critical failure mode(s) "
            f"from prior investigations with a +{overall_gain_pct}% average confidence boost, "
            f"eliminating cold-start ambiguity."
        )
    else:
        verdict = (
            "Cold-start baseline established. Subsequent rehearsals will leverage "
            "this investigation's graph nodes with temporal decay."
        )

    summary = {
        "change_id": change["id"],
        "change_title": change["title"],
        "avg_confidence_with_memory": avg_with,
        "avg_confidence_without_memory": avg_without,
        "avg_confidence_delta": avg_delta,
        "overall_confidence_gain_pct": overall_gain_pct,
        "reaffirmed_count": reaffirmed_count,
        "total_services_analyzed": len(deltas),
        "execution_time_with_memory_ms": res_with.get("execution_time_ms", 0.0),
        "execution_time_without_memory_ms": res_without.get("execution_time_ms", 0.0),
        "memory_verdict": verdict,
    }

    return {
        "change_id": change_id,
        "summary": summary,
        "deltas": deltas,
        "investigation_id_with_memory": res_with.get("investigation_id", ""),
        "investigation_id_without_memory": res_without.get("investigation_id", ""),
    }


def _ensure_memory_history(change_id: str, graph: Optional[Any] = None) -> None:
    """Check if FalkorDB has prior findings; if not, execute a baseline run to prime memory."""
    if graph is None:
        from graph.client import get_graph
        graph = get_graph()

    try:
        res = graph.query("MATCH (f:Finding) RETURN count(f) AS cnt")
        count = res.result_set[0][0] if res.result_set else 0
        if count == 0:
            logger.info("[Comparison] Priming FalkorDB with baseline investigation...")
            run_pipeline(change_id=change_id, memory_enabled=False, graph=graph)
    except Exception as exc:
        logger.warning("[Comparison] Error checking/priming memory history: %s", exc)
