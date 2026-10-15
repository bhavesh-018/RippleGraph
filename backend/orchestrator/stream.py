"""
RippleGraph - Investigation SSE Stream Generator

Streams the 4-stage Change Rehearsal pipeline step-by-step as Server-Sent Events (SSE).
Yields W3C-formatted SSE strings with deliberate pacing so React Flow node and edge
animations can be observed in real time as the agent traverses the dependency graph.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from graph.client import get_graph
from graph.tools import (
    find_direct_consumers,
    check_contract_compatibility,
    traverse_downstream_dependencies,
    get_relevant_incidents,
)
from orchestrator.pipeline import BUILTIN_CHANGES, run_pipeline
from orchestrator.memory import (
    get_prior_findings_with_decay,
    apply_memory_to_findings,
)
from orchestrator.reviewer import run_reviewer
from orchestrator.persist import persist_investigation
from schemas.sse import (
    SSEEventType,
    SSEMessage,
    StageChangedPayload,
    ConsumersFoundPayload,
    CompatibilityCheckedPayload,
    DownstreamPathPayload,
    MemoryRecalledPayload,
    FindingProducedPayload,
    CompletePayload,
)

logger = logging.getLogger("ripplegraph.stream")


async def stream_investigation(
    change_id: str = "CHG-001",
    memory_enabled: bool = True,
    disconnect_graph: bool = False,
    pace_delay_s: float = 0.35,
    graph: Optional[Any] = None,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous generator yielding SSE formatted text blocks for live graph animation.

    Args:
        change_id:        Target change proposal ID (e.g. "CHG-001").
        memory_enabled:   Whether to apply Stage 2 memory retrieval with temporal decay.
        disconnect_graph: If True (Proof Mode), simulates FalkorDB being offline.
        pace_delay_s:     Sleep duration between discrete traversal events.
        graph:            Optional graph client handle.
    """
    start_ms = time.monotonic()
    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    # Resolve change proposal
    if change_id in BUILTIN_CHANGES:
        change = BUILTIN_CHANGES[change_id]
    else:
        change = BUILTIN_CHANGES["CHG-001"]

    # ---- Proof Mode: FalkorDB Disconnected Stream ----
    if disconnect_graph:
        yield SSEMessage(
            event=SSEEventType.STAGE_CHANGED,
            data=StageChangedPayload(
                stage_id="investigator",
                stage_name="Proof Mode: FalkorDB Offline",
                description="Flat table lookup active with zero graph adjacency traversal.",
            ).model_dump(),
        ).to_sse_format()

        await asyncio.sleep(pace_delay_s)

        elapsed_ms = (time.monotonic() - start_ms) * 1000
        yield SSEMessage(
            event=SSEEventType.COMPLETE,
            data=CompletePayload(
                investigation_id=investigation_id,
                change_id=change["id"],
                summary={"incompatible": 0, "potential_downstream": 0, "compatible": 0, "unaffected": 1},
                recommended_contract=None,
                execution_time_ms=round(elapsed_ms, 2),
            ).model_dump(),
        ).to_sse_format()
        return

    if graph is None:
        graph = get_graph()

    # ---- Stage 1: Investigator ----
    yield SSEMessage(
        event=SSEEventType.STAGE_CHANGED,
        data=StageChangedPayload(
            stage_id="investigator",
            stage_name="Stage 1: Investigator",
            description="Discovering direct consumers via FalkorDB dependency edges.",
        ).model_dump(),
    ).to_sse_format()

    await asyncio.sleep(pace_delay_s)

    target_api = change.get("target_api", "auth-token-api")
    proposed_contract_id = change.get("proposed_contract_id", "cv-auth-v2")
    proposing_service = change.get("proposing_service", "auth-service")

    # 1. Discover direct consumers
    consumers = find_direct_consumers(target_api, graph=graph)
    consumer_ids = [c["id"] for c in consumers]

    yield SSEMessage(
        event=SSEEventType.CONSUMERS_FOUND,
        data=ConsumersFoundPayload(
            api_id=target_api,
            consumer_service_ids=consumer_ids,
        ).model_dump(),
    ).to_sse_format()

    await asyncio.sleep(pace_delay_s)

    # 2. Check contract compatibility per consumer
    compat_results = check_contract_compatibility(
        proposed_contract_id=proposed_contract_id,
        consumer_service_ids=consumer_ids,
        graph=graph,
    )

    incompatible_service_ids: List[str] = []
    for c_res in compat_results:
        svc_id = c_res["service_id"]
        status = c_res["status"].upper()
        if status == "INCOMPATIBLE":
            incompatible_service_ids.append(svc_id)

        yield SSEMessage(
            event=SSEEventType.COMPATIBILITY_CHECKED,
            data=CompatibilityCheckedPayload(
                service_id=svc_id,
                service_name=c_res.get("service_name", svc_id),
                status=status,
                contract_id=proposed_contract_id,
                missing_claims=c_res.get("missing_claims", []),
            ).model_dump(),
        ).to_sse_format()

        await asyncio.sleep(pace_delay_s)

    # 3. Traverse downstream dependencies
    downstream_paths = traverse_downstream_dependencies(
        origin_service_id=proposing_service,
        max_depth=4,
        graph=graph,
    )

    for path_item in downstream_paths:
        path_services = path_item.get("path", [])
        depth = path_item.get("depth", len(path_services) - 1)

        yield SSEMessage(
            event=SSEEventType.DOWNSTREAM_PATH,
            data=DownstreamPathPayload(
                path=path_services,
                depth=depth,
                status="potential_downstream",
            ).model_dump(),
        ).to_sse_format()

        await asyncio.sleep(pace_delay_s * 0.8)

    # ---- Stage 2: Memory ----
    yield SSEMessage(
        event=SSEEventType.STAGE_CHANGED,
        data=StageChangedPayload(
            stage_id="memory",
            stage_name="Stage 2: Memory",
            description="Recalling prior findings from FalkorDB with temporal decay.",
        ).model_dump(),
    ).to_sse_format()

    await asyncio.sleep(pace_delay_s)

    prior_findings: List[Dict[str, Any]] = []
    all_affected_ids = list(set(consumer_ids + incompatible_service_ids))
    if memory_enabled:
        prior_findings = get_prior_findings_with_decay(
            service_ids=all_affected_ids,
            current_investigation_id=investigation_id,
            graph=graph,
        )

        yield SSEMessage(
            event=SSEEventType.MEMORY_RECALLED,
            data=MemoryRecalledPayload(
                findings_count=len(prior_findings),
                prior_finding_ids=[f.get("id", "") for f in prior_findings],
                applied_to_services=[f.get("service_id", "") for f in prior_findings],
            ).model_dump(),
        ).to_sse_format()

        await asyncio.sleep(pace_delay_s)

    # ---- Stage 3: Reviewer ----
    yield SSEMessage(
        event=SSEEventType.STAGE_CHANGED,
        data=StageChangedPayload(
            stage_id="reviewer",
            stage_name="Stage 3: Reviewer",
            description="Adversarial validation and historical incident red-herring rejection.",
        ).model_dump(),
    ).to_sse_format()

    await asyncio.sleep(pace_delay_s)

    # Synthesize investigator output structure
    incidents = get_relevant_incidents(
        claim_types=change.get("claim_types", []),
        service_ids=all_affected_ids,
        graph=graph,
    )
    investigator_output = {
        "direct_consumers": consumers,
        "compatibility_results": compat_results,
        "downstream_paths": downstream_paths,
        "incidents": incidents,
        "all_affected_service_ids": all_affected_ids,
    }

    reviewer_output = run_reviewer(
        change=change,
        investigator_output=investigator_output,
        investigation_id=investigation_id,
        prior_findings=prior_findings if memory_enabled else None,
    )

    findings = reviewer_output["findings"]
    red_herrings = reviewer_output["red_herrings"]

    if memory_enabled and prior_findings:
        findings = apply_memory_to_findings(findings, prior_findings)

    for finding in findings:
        yield SSEMessage(
            event=SSEEventType.FINDING_PRODUCED,
            data=FindingProducedPayload(
                finding_id=finding["id"],
                service_id=finding["service_id"],
                service_name=finding.get("service_name"),
                category=finding["category"],
                status=finding["status"],
                confidence=finding["confidence"],
                hop_depth=finding.get("hop_depth", 0),
            ).model_dump(),
        ).to_sse_format()

        await asyncio.sleep(pace_delay_s * 0.6)

    # ---- Stage 4: Persist ----
    yield SSEMessage(
        event=SSEEventType.STAGE_CHANGED,
        data=StageChangedPayload(
            stage_id="persist",
            stage_name="Stage 4: Persist",
            description="Persisting investigation nodes and edges into FalkorDB memory.",
        ).model_dump(),
    ).to_sse_format()

    persist_investigation(
        investigation_id=investigation_id,
        change=change,
        findings=findings,
        red_herrings=red_herrings,
        memory_enabled=memory_enabled,
        graph=graph,
    )

    await asyncio.sleep(pace_delay_s * 0.5)

    # ---- Final Complete Event ----
    elapsed_ms = (time.monotonic() - start_ms) * 1000
    summary = {
        "incompatible": sum(1 for f in findings if f["status"] == "incompatible"),
        "potential_downstream": sum(1 for f in findings if f["status"] == "potential_downstream"),
        "compatible": sum(1 for f in findings if f["status"] == "compatible"),
        "unaffected": sum(1 for f in findings if f["status"] == "unaffected"),
    }
    recommended_contract = "cv-auth-v1-extended" if summary["incompatible"] > 0 else None

    yield SSEMessage(
        event=SSEEventType.COMPLETE,
        data=CompletePayload(
            investigation_id=investigation_id,
            change_id=change["id"],
            summary=summary,
            recommended_contract=recommended_contract,
            execution_time_ms=round(elapsed_ms, 2),
        ).model_dump(),
    ).to_sse_format()
