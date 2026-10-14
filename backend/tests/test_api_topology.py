"""
RippleGraph - Tests for Topology API (GET /api/graph/topology)
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from main import app


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure graph is seeded before testing topology endpoint."""
    seed(skip_verification=True)


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


def test_get_topology_success(client):
    """Test GET /api/graph/topology returns complete React Flow graph."""
    response = client.get("/api/graph/topology")
    assert response.status_code == 200
    data = response.json()

    # Validate high-level counts
    assert data["total_services"] == 10
    assert data["total_dependencies"] == 11
    assert len(data["nodes"]) == 10
    assert len(data["edges"]) == 11

    # Validate node structure
    node_map = {n["id"]: n for n in data["nodes"]}
    expected_services = {
        "auth-service",
        "payment-service",
        "user-service",
        "session-service",
        "checkout-service",
        "order-service",
        "inventory-service",
        "analytics-service",
        "audit-service",
        "notification-service",
    }
    assert set(node_map.keys()) == expected_services

    # Spot-check auth-service node
    auth_node = node_map["auth-service"]
    assert auth_node["type"] == "serviceNode"
    assert "x" in auth_node["position"]
    assert "y" in auth_node["position"]
    assert auth_node["data"]["name"] == "Auth Service"
    assert auth_node["data"]["tier"] == "platform"
    assert auth_node["data"]["status"] == "unaffected"

    # Spot-check auth-service APIs
    apis = auth_node["data"]["apis"]
    assert len(apis) == 1
    assert apis[0]["id"] == "auth-token-api"

    # Spot-check user-service accepted contracts
    user_node = node_map["user-service"]
    accepted_cvs = {c["contract_id"] for c in user_node["data"]["accepted_contracts"]}
    assert "cv-auth-v1" in accepted_cvs
    assert "cv-auth-v2" in accepted_cvs

    # Validate edges structure
    edge_pairs = {(e["source"], e["target"]) for e in data["edges"]}
    assert ("checkout-service", "payment-service") in edge_pairs
    assert ("payment-service", "auth-service") in edge_pairs
    assert ("order-service", "checkout-service") in edge_pairs

    for edge in data["edges"]:
        assert edge["label"] == "DEPENDS_ON"
        assert edge["type"] == "smoothstep"
        assert edge["animated"] is False
