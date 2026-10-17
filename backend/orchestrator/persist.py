"""
RippleGraph - Stage 4: Graph Persistence

Writes verified investigation results back to FalkorDB as permanent graph memory.
Creates the following nodes and typed edges:

  (:Investigation {id, change_id, status, memory_enabled, created_at})
  (:Finding      {id, service_id, category, status, confidence, ...})

  (inv)-[:PRODUCED]       -> (finding)
  (finding)-[:ABOUT_SERVICE]  -> (:Service)
  (finding)-[:SUPPORTED_BY]   -> (:Incident)
  (finding)-[:RECOMMENDS]     -> (:Mitigation)
  (finding)-[:ABOUT_CONTRACT] -> (:ContractVersion)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from graph.client import get_graph

logger = logging.getLogger("ripplegraph.persist")


def persist_investigation(
    investigation_id: str,
    change: Dict[str, Any],
    findings: List[Dict[str, Any]],
    red_herrings: List[Dict[str, Any]],
    memory_enabled: bool = True,
    graph: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Stage 4: Persist investigation and all verified findings to FalkorDB.

    Args:
        investigation_id: Unique ID for this investigation run (e.g. INV-abc12345).
        change:           ChangeProposal dict.
        findings:         Verified Finding dicts from Stage 3 reviewer.
        red_herrings:     Rejected incident records from Stage 3 reviewer.
        memory_enabled:   Whether memory was active for this run.
        graph:            Optional FalkorDB graph handle (injected in tests).

    Returns:
        Dict with persisted investigation_id, finding_ids written, and edge counts.
    """
    if graph is None:
        graph = get_graph()

    change_id = change.get("id", "CHG-001")

    logger.info(
        "[Stage 4] Persisting investigation %s | change=%s | findings=%d",
        investigation_id,
        change_id,
        len(findings),
    )

    # 1. Create Investigation node
    _create_investigation_node(graph, investigation_id, change, memory_enabled)

    # 2. Persist each Finding node and its typed edges
    finding_ids = []
    edges_written = 0

    for finding in findings:
        fnd_id = finding["id"]
        finding_ids.append(fnd_id)

        # Create Finding node
        _create_finding_node(graph, finding)

        # (inv)-[:PRODUCED]->(finding)
        _create_edge(graph, investigation_id, "Investigation", fnd_id, "Finding", "PRODUCED")
        edges_written += 1

        # (finding)-[:ABOUT_SERVICE]->(service)
        svc_id = finding.get("service_id")
        if svc_id:
            _create_edge(graph, fnd_id, "Finding", svc_id, "Service", "ABOUT_SERVICE")
            edges_written += 1

        # (finding)-[:SUPPORTED_BY]->(incident) for each relevant incident
        for inc_id in finding.get("relevant_incidents", []):
            _create_edge(graph, fnd_id, "Finding", inc_id, "Incident", "SUPPORTED_BY")
            edges_written += 1

        # (finding)-[:ABOUT_CONTRACT]->(contract) if recommended
        rec_contract = finding.get("recommended_contract_id")
        if rec_contract:
            _create_edge(graph, fnd_id, "Finding", rec_contract, "ContractVersion", "ABOUT_CONTRACT")
            edges_written += 1

        logger.info(
            "[Stage 4] Written finding %s for service %s (status=%s)",
            fnd_id,
            svc_id,
            finding.get("status"),
        )

    logger.info(
        "[Stage 4] Persistence complete. findings_written=%d edges_written=%d",
        len(finding_ids),
        edges_written,
    )

    return {
        "investigation_id": investigation_id,
        "finding_ids": finding_ids,
        "findings_written": len(finding_ids),
        "edges_written": edges_written,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_investigation_node(
    graph: Any,
    investigation_id: str,
    change: Dict[str, Any],
    memory_enabled: bool,
) -> None:
    """Create or merge an Investigation node in FalkorDB."""
    cypher = """
    MERGE (inv:Investigation {id: $id})
    ON CREATE SET
        inv.change_id       = $change_id,
        inv.change_title    = $change_title,
        inv.status          = 'COMPLETE',
        inv.memory_enabled  = $memory_enabled,
        inv.created_at      = $created_at
    """
    from datetime import datetime, timezone
    graph.query(cypher, {
        "id": investigation_id,
        "change_id": change.get("id", "CHG-001"),
        "change_title": change.get("title", ""),
        "memory_enabled": memory_enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def _create_finding_node(graph: Any, finding: Dict[str, Any]) -> None:
    """Create a Finding node in FalkorDB with all properties."""
    reasons_json = json.dumps(finding.get("reasons", []))
    missing_json = json.dumps(finding.get("missing_claims", []))
    chains_json = json.dumps(finding.get("dependency_chains", []))
    incidents_json = json.dumps(finding.get("relevant_incidents", []))

    cypher = """
    MERGE (f:Finding {id: $id})
    ON CREATE SET
        f.investigation_id      = $investigation_id,
        f.service_id            = $service_id,
        f.service_name          = $service_name,
        f.category              = $category,
        f.status                = $status,
        f.confidence            = $confidence,
        f.reasons               = $reasons,
        f.missing_claims        = $missing_claims,
        f.dependency_chains     = $dependency_chains,
        f.hop_depth             = $hop_depth,
        f.recommended_contract_id = $recommended_contract_id,
        f.relevant_incidents    = $relevant_incidents,
        f.created_at            = $created_at,
        f.decayed_confidence    = $decayed_confidence,
        f.days_old              = $days_old,
        f.decay_factor          = $decay_factor,
        f.reaffirmed            = $reaffirmed,
        f.is_stale              = $is_stale,
        f.staleness_reason      = $staleness_reason
    """
    graph.query(cypher, {
        "id": finding["id"],
        "investigation_id": finding.get("investigation_id", ""),
        "service_id": finding.get("service_id", ""),
        "service_name": finding.get("service_name", ""),
        "category": finding.get("category", ""),
        "status": finding.get("status", ""),
        "confidence": finding.get("confidence", 1.0),
        "reasons": reasons_json,
        "missing_claims": missing_json,
        "dependency_chains": chains_json,
        "hop_depth": finding.get("hop_depth", 0),
        "recommended_contract_id": finding.get("recommended_contract_id") or "",
        "relevant_incidents": incidents_json,
        "created_at": finding.get("created_at", ""),
        "decayed_confidence": finding.get("decayed_confidence") if finding.get("decayed_confidence") is not None else -1.0,
        "days_old": finding.get("days_old") if finding.get("days_old") is not None else -1.0,
        "decay_factor": finding.get("decay_factor") if finding.get("decay_factor") is not None else -1.0,
        "reaffirmed": bool(finding.get("reaffirmed", False)),
        "is_stale": bool(finding.get("is_stale", False)),
        "staleness_reason": finding.get("staleness_reason") or "",
    })


def _create_edge(
    graph: Any,
    from_id: str,
    from_label: str,
    to_id: str,
    to_label: str,
    rel_type: str,
) -> None:
    """
    Create a directed relationship between two nodes using MERGE to avoid duplicates.
    Uses literal string construction since FalkorDB does not support parameterized
    relationship type names.
    """
    cypher = (
        f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) "
        f"MERGE (a)-[:{rel_type}]->(b)"
    )
    graph.query(cypher, {"from_id": from_id, "to_id": to_id})
