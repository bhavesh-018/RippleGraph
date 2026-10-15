"""
RippleGraph - Tests for Change Proposals Catalog & Multi-Scenario Pipeline

Tests:
  - GET /api/changes returns all 6 built-in change scenarios
  - GET /api/changes/{id} returns specific proposal details
  - Running pipeline with CHG-003 (Payment currency change)
  - Running pipeline with CHG-005 (Inventory additive change)
  - Topology endpoint returns rich metadata (icon, runtime, version, port)
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from orchestrator.pipeline import run_pipeline


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_list_changes_endpoint(client):
    """Verify GET /api/changes returns 6 diverse change proposals."""
    response = client.get("/api/changes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6

    change_ids = {c["id"] for c in data}
    expected_ids = {"CHG-001", "CHG-002", "CHG-003", "CHG-004", "CHG-005", "CHG-006"}
    assert expected_ids.issubset(change_ids)

    # Validate schema fields
    for item in data:
        assert "id" in item
        assert "title" in item
        assert "proposing_service" in item
        assert "target_api" in item
        assert "proposed_contract_id" in item
        assert "risk_level" in item
        assert "description" in item


def test_get_single_change_endpoint(client):
    """Verify GET /api/changes/{id} returns correct proposal."""
    response = client.get("/api/changes/CHG-003")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "CHG-003"
    assert data["proposing_service"] == "payment-service"
    assert data["target_api"] == "payment-charge-api"
    assert data["proposed_contract_id"] == "cv-payment-v2"
    assert data["risk_level"] == "HIGH"


def test_get_nonexistent_change_returns_404(client):
    """Verify GET /api/changes/{unknown} returns 404."""
    response = client.get("/api/changes/CHG-999")
    assert response.status_code == 404


def test_pipeline_execution_chg003_payment():
    """Verify running pipeline with CHG-003 detects payment breaking change."""
    res = run_pipeline(change_id="CHG-003", memory_enabled=False)
    assert res["change_id"] == "CHG-003"
    assert len(res["findings"]) > 0

    findings_by_service = {f["service_id"]: f for f in res["findings"]}
    # checkout-service and audit-service consume payment-charge-api cv-payment-v1
    assert "checkout-service" in findings_by_service
    assert findings_by_service["checkout-service"]["status"] == "incompatible"


def test_pipeline_execution_chg005_additive_inventory():
    """Verify CHG-005 (additive inventory field) results in zero incompatible services."""
    res = run_pipeline(change_id="CHG-005", memory_enabled=False)
    assert res["change_id"] == "CHG-005"
    assert res["summary"]["incompatible"] == 0


def test_topology_returns_rich_service_metadata(client):
    """Verify GET /api/graph/topology returns icon, runtime, version, and port."""
    response = client.get("/api/graph/topology")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 10

    auth_node = next(n for n in data["nodes"] if n["id"] == "auth-service")
    node_data = auth_node["data"]
    assert node_data["icon"] == "Shield"
    assert "Go" in node_data["runtime"]
    assert "version" in node_data
    assert node_data["port"] == 8001
    assert len(node_data["description"]) > 0
