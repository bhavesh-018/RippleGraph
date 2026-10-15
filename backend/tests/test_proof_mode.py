"""
Tests for Feature 8: "Remove FalkorDB" Proof Mode

Verifies that:
  1. When disconnect_graph is False (normal mode), FalkorDB graph reasoning detects
     multi-hop breaking changes (payment-service and checkout-service incompatible).
  2. When disconnect_graph is True (Proof Mode), flat non-graph execution fails to
     traverse dependencies, returning 0 incompatible consumers and an audit warning.
  3. The REST API /api/investigations endpoint correctly accepts and responds to
     the disconnect_graph flag.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from orchestrator.pipeline import run_pipeline


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_pipeline_with_disconnect_graph_simulates_failure():
    """Proof Mode should return zero breaking changes and an explicit blind spot warning."""
    result = run_pipeline(change_id="CHG-001", disconnect_graph=True)

    assert result["disconnect_graph"] is True
    assert result["summary"]["incompatible"] == 0
    assert result["summary"]["potential_downstream"] == 0
    assert result["recommended_migration_contract"] is None
    assert "PROOF MODE" in result["warning"]
    assert len(result["findings"]) == 1
    assert result["findings"][0]["category"] == "GRAPH_REASONING_OFFLINE"
    assert result["findings"][0]["confidence"] == 0.0


def test_pipeline_connected_vs_disconnected_comparison():
    """Directly contrasts FalkorDB graph traversal against the disconnected baseline."""
    connected = run_pipeline(change_id="CHG-001", disconnect_graph=False)
    disconnected = run_pipeline(change_id="CHG-001", disconnect_graph=True)

    # Connected mode traverses multi-hop dependencies
    assert connected["disconnect_graph"] is False
    assert connected["summary"]["incompatible"] >= 2
    assert connected["recommended_migration_contract"] == "cv-auth-v1-extended"

    # Disconnected mode has complete blind spot
    assert disconnected["disconnect_graph"] is True
    assert disconnected["summary"]["incompatible"] == 0
    assert disconnected["warning"] is not None


def test_api_investigations_endpoint_proof_mode(client):
    """POST /api/investigations with disconnect_graph=True returns proof mode payload."""
    payload = {
        "change_id": "CHG-001",
        "memory_enabled": False,
        "disconnect_graph": True,
    }
    response = client.post("/api/investigations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["disconnect_graph"] is True
    assert data["summary"]["incompatible"] == 0
    assert data["warning"] is not None
    assert len(data["findings"]) == 1
    assert data["findings"][0]["category"] == "GRAPH_REASONING_OFFLINE"
