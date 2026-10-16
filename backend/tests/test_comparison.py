"""
RippleGraph - Tests for Feature 2: Memory ON vs OFF Comparison & Visual Diff
Tests backend/orchestrator/comparison.py and POST/GET /api/investigations/compare
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from orchestrator.comparison import compare_investigation_memory
from main import app


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure FalkorDB is seeded with baseline graph data."""
    seed(skip_verification=True)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_compare_function_returns_expected_keys():
    res = compare_investigation_memory(change_id="CHG-001")
    assert "change_id" in res
    assert "summary" in res
    assert "deltas" in res
    assert "investigation_id_with_memory" in res
    assert "investigation_id_without_memory" in res
    assert res["change_id"] == "CHG-001"


def test_compare_summary_structure():
    res = compare_investigation_memory(change_id="CHG-001")
    summary = res["summary"]
    assert "avg_confidence_with_memory" in summary
    assert "avg_confidence_without_memory" in summary
    assert "avg_confidence_delta" in summary
    assert "overall_confidence_gain_pct" in summary
    assert "reaffirmed_count" in summary
    assert "total_services_analyzed" in summary
    assert "memory_verdict" in summary
    assert summary["total_services_analyzed"] > 0
    assert 0.0 <= summary["avg_confidence_with_memory"] <= 1.0


def test_compare_deltas_content():
    res = compare_investigation_memory(change_id="CHG-001")
    deltas = res["deltas"]
    assert len(deltas) > 0

    services = {d["service_id"] for d in deltas}
    # Payment and checkout must be among the analyzed services for CHG-001
    assert "payment-service" in services or "checkout-service" in services

    for d in deltas:
        assert "service_id" in d
        assert "service_name" in d
        assert "status_with_memory" in d
        assert "status_without_memory" in d
        assert "confidence_with_memory" in d
        assert "confidence_without_memory" in d
        assert "confidence_delta" in d
        assert "confidence_gain_pct" in d
        assert isinstance(d["memory_reaffirmed"], bool)


def test_compare_reaffirmation_boost():
    """Verify that memory either maintains or boosts confidence over cold start."""
    res = compare_investigation_memory(change_id="CHG-001")
    summary = res["summary"]
    # With memory should be >= cold start
    assert summary["avg_confidence_with_memory"] >= summary["avg_confidence_without_memory"]


def test_compare_invalid_change_id_raises():
    with pytest.raises(ValueError) as exc_info:
        compare_investigation_memory(change_id="INVALID-CHG")
    assert "Unknown change_id" in str(exc_info.value)


def test_compare_api_post_endpoint_returns_200(client):
    resp = client.post("/api/investigations/compare", json={"change_id": "CHG-001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_id"] == "CHG-001"
    assert "summary" in data
    assert "deltas" in data
    assert len(data["deltas"]) > 0


def test_compare_api_get_endpoint_returns_200(client):
    resp = client.get("/api/investigations/compare?change_id=CHG-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["change_id"] == "CHG-001"
    assert "summary" in data
    assert "deltas" in data


def test_compare_api_invalid_change_returns_400(client):
    resp = client.post("/api/investigations/compare", json={"change_id": "UNKNOWN-999"})
    assert resp.status_code == 400
    assert "Unknown change_id" in resp.json()["detail"]
