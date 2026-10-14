"""
RippleGraph - End-to-End Pipeline Integration Tests (C22)

Covers:
  - Full 4-stage pipeline execution for CHG-001 (breaking auth token rename)
  - Stage 1: correct direct consumers and downstream services discovered
  - Stage 3: payment-service marked INCOMPATIBLE, checkout-service POTENTIAL_DOWNSTREAM
  - Stage 3: INC-105 rejected as red herring
  - Stage 4: Investigation and Finding nodes persisted to FalkorDB
  - Stage 2: second run with memory enabled retrieves prior findings
  - Pipeline with memory disabled (cold start) works independently
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from graph.client import get_graph
from orchestrator.pipeline import run_pipeline


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure FalkorDB is seeded with baseline data before running pipeline tests."""
    seed(skip_verification=True)


# ---------------------------------------------------------------------------
# Pipeline execution fixture (runs CHG-001 once for the whole session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def investigation_a():
    """Run Investigation A: CHG-001 breaking auth token rename, memory OFF (clean run)."""
    result = run_pipeline(change_id="CHG-001", memory_enabled=False)
    return result


@pytest.fixture(scope="session")
def investigation_b(investigation_a):
    """Run Investigation B: same CHG-001, memory ON (retrieves prior findings)."""
    result = run_pipeline(change_id="CHG-001", memory_enabled=True)
    return result


# ---------------------------------------------------------------------------
# C22 Point 1: Pipeline returns required top-level keys
# ---------------------------------------------------------------------------

def test_pipeline_returns_required_keys(investigation_a):
    """Pipeline result must contain all required top-level keys."""
    required = {
        "investigation_id",
        "change_id",
        "change_title",
        "memory_enabled",
        "summary",
        "findings",
        "red_herrings_rejected",
        "execution_time_ms",
    }
    assert required.issubset(investigation_a.keys()), (
        f"Missing keys: {required - investigation_a.keys()}"
    )


def test_pipeline_change_id_is_chg001(investigation_a):
    """change_id in result must match the requested change."""
    assert investigation_a["change_id"] == "CHG-001"


def test_pipeline_executes_in_reasonable_time(investigation_a):
    """Pipeline must complete within 10 seconds (10000 ms)."""
    assert investigation_a["execution_time_ms"] < 10_000, (
        f"Pipeline too slow: {investigation_a['execution_time_ms']:.1f} ms"
    )


# ---------------------------------------------------------------------------
# C22 Point 2: Summary counts are non-zero and self-consistent
# ---------------------------------------------------------------------------

def test_pipeline_summary_has_incompatible_services(investigation_a):
    """At least one service must be INCOMPATIBLE for CHG-001 breaking change."""
    summary = investigation_a["summary"]
    assert summary["incompatible"] >= 1, (
        f"Expected incompatible > 0, got summary={summary}"
    )


def test_pipeline_summary_has_potential_downstream(investigation_a):
    """At least one service must be POTENTIAL_DOWNSTREAM (transitive risk)."""
    summary = investigation_a["summary"]
    assert summary["potential_downstream"] >= 1, (
        f"Expected potential_downstream > 0, got summary={summary}"
    )


def test_pipeline_summary_counts_match_findings(investigation_a):
    """Sum of summary counts must equal total number of findings."""
    summary = investigation_a["summary"]
    total = sum(summary.values())
    assert total == len(investigation_a["findings"]), (
        f"Summary total {total} != findings count {len(investigation_a['findings'])}"
    )


# ---------------------------------------------------------------------------
# C22 Point 3: payment-service is INCOMPATIBLE
# ---------------------------------------------------------------------------

def test_payment_service_is_incompatible(investigation_a):
    """payment-service must be INCOMPATIBLE under CHG-001 (strict v1-only claims)."""
    findings = investigation_a["findings"]
    payment_finding = next(
        (f for f in findings if f["service_id"] == "payment-service"), None
    )
    assert payment_finding is not None, "No finding found for payment-service"
    assert payment_finding["status"] == "incompatible", (
        f"Expected payment-service INCOMPATIBLE, got {payment_finding['status']}"
    )


def test_payment_service_has_high_confidence(investigation_a):
    """payment-service INCOMPATIBLE finding must have confidence >= 0.90."""
    findings = investigation_a["findings"]
    payment_finding = next(
        (f for f in findings if f["service_id"] == "payment-service"), None
    )
    assert payment_finding is not None
    assert payment_finding["confidence"] >= 0.90, (
        f"Expected confidence >= 0.90, got {payment_finding['confidence']}"
    )


def test_payment_service_recommends_transitional_contract(investigation_a):
    """payment-service finding must recommend cv-auth-v1-extended as mitigation."""
    findings = investigation_a["findings"]
    payment_finding = next(
        (f for f in findings if f["service_id"] == "payment-service"), None
    )
    assert payment_finding is not None
    assert payment_finding["recommended_contract_id"] == "cv-auth-v1-extended", (
        f"Expected cv-auth-v1-extended, got {payment_finding['recommended_contract_id']}"
    )


# ---------------------------------------------------------------------------
# C22 Point 4: checkout-service is INCOMPATIBLE (direct consumer of cv-auth-v1)
#              order-service is POTENTIAL_DOWNSTREAM (transitive via checkout)
# ---------------------------------------------------------------------------

def test_checkout_service_is_incompatible(investigation_a):
    """checkout-service accepts cv-auth-v1 directly, so it must be INCOMPATIBLE."""
    findings = investigation_a["findings"]
    checkout_finding = next(
        (f for f in findings if f["service_id"] == "checkout-service"), None
    )
    assert checkout_finding is not None, "No finding found for checkout-service"
    assert checkout_finding["status"] == "incompatible", (
        f"Expected checkout-service INCOMPATIBLE, got {checkout_finding['status']}"
    )


def test_order_service_is_potential_downstream(investigation_a):
    """order-service depends on checkout-service, so it must be POTENTIAL_DOWNSTREAM."""
    findings = investigation_a["findings"]
    order_finding = next(
        (f for f in findings if f["service_id"] == "order-service"), None
    )
    assert order_finding is not None, "No finding found for order-service"
    assert order_finding["status"] == "potential_downstream", (
        f"Expected order-service POTENTIAL_DOWNSTREAM, got {order_finding['status']}"
    )
    assert order_finding["hop_depth"] >= 1, (
        f"Expected hop_depth >= 1, got {order_finding['hop_depth']}"
    )


# ---------------------------------------------------------------------------
# C22 Point 5: INC-105 rejected as red herring
# ---------------------------------------------------------------------------

def test_inc105_rejected_as_red_herring(investigation_a):
    """INC-105 must appear in red_herrings_rejected (not relevant to field_rename)."""
    red_herrings = investigation_a["red_herrings_rejected"]
    inc105 = next(
        (r for r in red_herrings if r["incident_id"] == "INC-105"), None
    )
    assert inc105 is not None, (
        "INC-105 was not rejected as a red herring. "
        f"Red herrings found: {[r['incident_id'] for r in red_herrings]}"
    )


def test_inc105_rationale_mentions_claim_mismatch(investigation_a):
    """INC-105 rejection rationale must reference claim type mismatch."""
    red_herrings = investigation_a["red_herrings_rejected"]
    inc105 = next(
        (r for r in red_herrings if r["incident_id"] == "INC-105"), None
    )
    assert inc105 is not None
    rationale = inc105.get("rationale", "")
    assert "claim" in rationale.lower(), (
        f"Expected 'claim' in rationale, got: {rationale}"
    )


# ---------------------------------------------------------------------------
# C22 Point 6: Stage 4 persistence - Investigation node in FalkorDB
# ---------------------------------------------------------------------------

def test_investigation_node_persisted_to_falkordb(investigation_a):
    """Investigation node must exist in FalkorDB after pipeline run."""
    graph = get_graph()
    inv_id = investigation_a["investigation_id"]
    res = graph.query(
        "MATCH (inv:Investigation {id: $id}) RETURN inv.id, inv.change_id",
        {"id": inv_id},
    )
    assert len(res.result_set) == 1, (
        f"Investigation node '{inv_id}' not found in FalkorDB"
    )
    assert res.result_set[0][1] == "CHG-001"


def test_finding_nodes_persisted_to_falkordb(investigation_a):
    """Finding nodes must exist in FalkorDB linked to the Investigation."""
    graph = get_graph()
    inv_id = investigation_a["investigation_id"]
    res = graph.query(
        "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding) RETURN f.id",
        {"id": inv_id},
    )
    assert len(res.result_set) >= 1, (
        f"No Finding nodes linked to investigation '{inv_id}' in FalkorDB"
    )


def test_finding_about_service_edges_exist(investigation_a):
    """ABOUT_SERVICE edges must link findings to Service nodes in FalkorDB."""
    graph = get_graph()
    inv_id = investigation_a["investigation_id"]
    res = graph.query(
        "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding)-[:ABOUT_SERVICE]->(s:Service) "
        "RETURN f.id, s.id",
        {"id": inv_id},
    )
    assert len(res.result_set) >= 1, (
        "No ABOUT_SERVICE edges found for findings of investigation '%s'" % inv_id
    )


# ---------------------------------------------------------------------------
# C22 Point 7: Memory-enabled Investigation B retrieves prior findings
# ---------------------------------------------------------------------------

def test_investigation_b_has_memory_enabled(investigation_b):
    """Investigation B must have memory_enabled=True."""
    assert investigation_b["memory_enabled"] is True


def test_investigation_b_produces_findings(investigation_b):
    """Investigation B (memory ON) must still produce findings."""
    assert len(investigation_b["findings"]) >= 1


def test_investigation_b_payment_incompatible(investigation_b):
    """payment-service must still be INCOMPATIBLE in Investigation B."""
    findings = investigation_b["findings"]
    payment_finding = next(
        (f for f in findings if f["service_id"] == "payment-service"), None
    )
    assert payment_finding is not None
    assert payment_finding["status"] == "incompatible"


# ---------------------------------------------------------------------------
# C22 Point 8: CHG-002 transitional contract - no INCOMPATIBLE findings
# ---------------------------------------------------------------------------

def test_chg002_transitional_no_incompatible():
    """CHG-002 (transitional contract) must produce zero INCOMPATIBLE findings."""
    result = run_pipeline(change_id="CHG-002", memory_enabled=False)
    summary = result["summary"]
    assert summary["incompatible"] == 0, (
        f"Expected 0 incompatible for CHG-002, got summary={summary}"
    )


# ---------------------------------------------------------------------------
# C22 Point 9: Invalid change_id raises ValueError
# ---------------------------------------------------------------------------

def test_invalid_change_id_raises_error():
    """Passing an unknown change_id must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown change_id"):
        run_pipeline(change_id="CHG-999")


# ---------------------------------------------------------------------------
# C22 Point 10: Recommended migration contract present when incompatible
# ---------------------------------------------------------------------------

def test_recommended_migration_contract_set(investigation_a):
    """recommended_migration_contract must be cv-auth-v1-extended for CHG-001."""
    assert investigation_a["recommended_migration_contract"] == "cv-auth-v1-extended", (
        f"Got: {investigation_a['recommended_migration_contract']}"
    )
