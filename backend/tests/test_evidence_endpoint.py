"""
RippleGraph - Tests for Feature 3: Evidence Path Inspector
GET /api/investigations/{investigation_id}/findings/{finding_id}/evidence

Covers:
  - 200 response for a valid finding
  - Response structure has required top-level keys: finding, service, incidents, contract
  - finding data fields are populated and correct types
  - service node is returned and connected via ABOUT_SERVICE edge
  - service has correct fields (id, name, tier, owner_team)
  - incidents returned for incompatible findings (SUPPORTED_BY edges)
  - incidents include mitigation playbook data when available
  - contract returned when ABOUT_CONTRACT edge exists
  - reasons list is non-empty for incompatible findings
  - missing_claims list is non-empty for incompatible findings
  - dependency_chains is a list of lists
  - 404 returned for a non-existent finding_id
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from graph.client import get_graph
from orchestrator.pipeline import run_pipeline
from main import app


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure FalkorDB is seeded with baseline data before running evidence tests."""
    seed(skip_verification=True)


@pytest.fixture(scope="session")
def investigation_result():
    """Run CHG-001 pipeline once and return the result (memory OFF for clean baseline)."""
    return run_pipeline(change_id="CHG-001", memory_enabled=False)


@pytest.fixture(scope="session")
def real_finding_ids(investigation_result):
    """
    Fetch the real FND-xxx finding IDs from FalkorDB for the investigation
    produced by the pipeline fixture. Returns a dict of service_id -> finding_id.
    """
    graph = get_graph()
    inv_id = investigation_result["investigation_id"]
    res = graph.query(
        "MATCH (inv:Investigation {id: $id})-[:PRODUCED]->(f:Finding) "
        "RETURN f.id, f.service_id, f.status "
        "ORDER BY f.confidence DESC",
        {"id": inv_id},
    )
    return {
        row[1]: {"finding_id": row[0], "status": row[2]}
        for row in res.result_set
    }


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Helper: pick an incompatible finding (payment-service or checkout-service)
# ---------------------------------------------------------------------------

def _get_incompatible_finding(real_finding_ids):
    """Return (investigation_id placeholder, finding_id) for an incompatible service."""
    for svc_id in ("payment-service", "checkout-service", "session-service"):
        entry = real_finding_ids.get(svc_id)
        if entry and entry["status"] == "incompatible":
            return entry["finding_id"]
    pytest.skip("No incompatible finding available for evidence test")


# ---------------------------------------------------------------------------
# Point 1: 200 response and top-level structure
# ---------------------------------------------------------------------------

def test_evidence_endpoint_returns_200(client, investigation_result, real_finding_ids):
    """GET evidence endpoint must return 200 for a valid finding."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    response = client.get(f"/api/investigations/{inv_id}/findings/{finding_id}/evidence")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_evidence_response_has_required_top_level_keys(client, investigation_result, real_finding_ids):
    """Evidence response must have keys: finding, service, incidents, contract."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    required = {"finding", "service", "incidents", "contract"}
    assert required.issubset(data.keys()), (
        f"Missing top-level keys: {required - data.keys()}"
    )


# ---------------------------------------------------------------------------
# Point 2: finding sub-object fields
# ---------------------------------------------------------------------------

def test_evidence_finding_has_required_fields(client, investigation_result, real_finding_ids):
    """finding object must contain all required fields."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    finding = data["finding"]
    required_fields = {
        "id", "service_id", "service_name", "category", "status",
        "confidence", "reasons", "missing_claims", "dependency_chains",
        "hop_depth", "relevant_incidents", "recommended_contract_id",
    }
    assert required_fields.issubset(finding.keys()), (
        f"Missing finding fields: {required_fields - finding.keys()}"
    )


def test_evidence_finding_status_is_incompatible(client, investigation_result, real_finding_ids):
    """Finding status for payment/checkout-service must be 'incompatible'."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    assert data["finding"]["status"] == "incompatible", (
        f"Expected 'incompatible', got '{data['finding']['status']}'"
    )


def test_evidence_finding_confidence_is_float_between_0_and_1(client, investigation_result, real_finding_ids):
    """Confidence must be a float in [0.0, 1.0]."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    conf = data["finding"]["confidence"]
    assert isinstance(conf, float), f"Expected float, got {type(conf)}"
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"


def test_evidence_finding_reasons_non_empty_for_incompatible(client, investigation_result, real_finding_ids):
    """reasons list must be non-empty for an incompatible finding."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    reasons = data["finding"]["reasons"]
    assert isinstance(reasons, list), "reasons must be a list"
    assert len(reasons) >= 1, f"Expected at least 1 reason, got {reasons}"


def test_evidence_finding_missing_claims_non_empty_for_incompatible(client, investigation_result, real_finding_ids):
    """missing_claims must be non-empty for an incompatible finding."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    missing = data["finding"]["missing_claims"]
    assert isinstance(missing, list), "missing_claims must be a list"
    assert len(missing) >= 1, f"Expected missing claims, got {missing}"


def test_evidence_finding_dependency_chains_is_list_of_lists(client, investigation_result, real_finding_ids):
    """dependency_chains must be a list (each item is a list of service IDs)."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    chains = data["finding"]["dependency_chains"]
    assert isinstance(chains, list), "dependency_chains must be a list"
    for chain in chains:
        assert isinstance(chain, list), f"Each chain must be a list, got {type(chain)}"


# ---------------------------------------------------------------------------
# Point 3: service sub-object
# ---------------------------------------------------------------------------

def test_evidence_service_is_not_null(client, investigation_result, real_finding_ids):
    """service must not be null — ABOUT_SERVICE edge must exist after persist."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    assert data["service"] is not None, "service must be returned (ABOUT_SERVICE edge missing)"


def test_evidence_service_has_correct_fields(client, investigation_result, real_finding_ids):
    """service object must contain id, name, tier, owner_team, description, runtime, port."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    service = data["service"]
    required_fields = {"id", "name", "tier", "owner_team", "description", "runtime", "port"}
    assert required_fields.issubset(service.keys()), (
        f"Missing service fields: {required_fields - service.keys()}"
    )


def test_evidence_service_id_matches_finding_service_id(client, investigation_result, real_finding_ids):
    """service.id must match finding.service_id."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    assert data["service"]["id"] == data["finding"]["service_id"], (
        "service.id does not match finding.service_id"
    )


# ---------------------------------------------------------------------------
# Point 4: incidents and mitigations
# ---------------------------------------------------------------------------

def test_evidence_incidents_is_a_list(client, investigation_result, real_finding_ids):
    """incidents must be a list (may be empty if no SUPPORTED_BY edges)."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    assert isinstance(data["incidents"], list), "incidents must be a list"


def test_evidence_incidents_have_required_fields(client, investigation_result, real_finding_ids):
    """Each incident must have id, title, severity, description, occurred_at, mitigation."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    for inc in data["incidents"]:
        required = {"id", "title", "severity", "description", "occurred_at", "mitigation"}
        assert required.issubset(inc.keys()), (
            f"Incident missing fields: {required - inc.keys()}"
        )


def test_evidence_incident_mitigations_have_correct_fields(client, investigation_result, real_finding_ids):
    """Mitigations inside incidents must have id, title, description, validation_method."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    for inc in data["incidents"]:
        if inc["mitigation"] is not None:
            mit = inc["mitigation"]
            required = {"id", "title", "description", "validation_method"}
            assert required.issubset(mit.keys()), (
                f"Mitigation missing fields: {required - mit.keys()}"
            )


# ---------------------------------------------------------------------------
# Point 5: contract sub-object
# ---------------------------------------------------------------------------

def test_evidence_contract_is_none_or_has_required_fields(client, investigation_result, real_finding_ids):
    """contract must be None or have id, version, description, status."""
    inv_id = investigation_result["investigation_id"]
    finding_id = _get_incompatible_finding(real_finding_ids)
    data = client.get(
        f"/api/investigations/{inv_id}/findings/{finding_id}/evidence"
    ).json()
    contract = data["contract"]
    if contract is not None:
        required = {"id", "version", "description", "status"}
        assert required.issubset(contract.keys()), (
            f"Contract missing fields: {required - contract.keys()}"
        )


# ---------------------------------------------------------------------------
# Point 6: 404 for non-existent finding
# ---------------------------------------------------------------------------

def test_evidence_404_for_nonexistent_finding_id(client, investigation_result):
    """GET evidence for a bogus finding_id must return 404."""
    inv_id = investigation_result["investigation_id"]
    response = client.get(
        f"/api/investigations/{inv_id}/findings/FND-DOES-NOT-EXIST/evidence"
    )
    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}"
    )


def test_evidence_404_detail_message(client, investigation_result):
    """404 response must include a descriptive detail message."""
    inv_id = investigation_result["investigation_id"]
    response = client.get(
        f"/api/investigations/{inv_id}/findings/FND-DOES-NOT-EXIST/evidence"
    )
    data = response.json()
    assert "detail" in data, "404 response must have a 'detail' key"
    assert "FND-DOES-NOT-EXIST" in data["detail"], (
        f"detail message should mention the missing ID: {data['detail']}"
    )
