"""
RippleGraph - Tests for Graph Cypher Tools
"""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from graph.tools import find_direct_consumers


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure the FalkorDB graph is seeded with baseline data."""
    seed(skip_verification=True)


def test_find_direct_consumers_auth_api():
    """Test discovering all direct consumers of auth-token-api."""
    consumers = find_direct_consumers("auth-token-api")

    # 6 unique services accept contracts for auth-token-api
    assert len(consumers) == 6

    consumer_map = {c["service_id"]: c for c in consumers}
    expected_ids = {
        "payment-service",
        "user-service",
        "session-service",
        "checkout-service",
        "audit-service",
        "notification-service",
    }
    assert set(consumer_map.keys()) == expected_ids

    # user-service accepts both v1 and v2
    user_svc = consumer_map["user-service"]
    assert "cv-auth-v1" in user_svc["accepted_contract_ids"]
    assert "cv-auth-v2" in user_svc["accepted_contract_ids"]
    assert len(user_svc["accepted_contracts"]) == 2

    # payment-service accepts only v1
    payment_svc = consumer_map["payment-service"]
    assert payment_svc["accepted_contract_ids"] == ["cv-auth-v1"]
    assert payment_svc["tier"] == "core"
    assert payment_svc["owner_team"] == "payments"


def test_find_direct_consumers_nonexistent_api():
    """Test querying an unknown API returns an empty list."""
    consumers = find_direct_consumers("unknown-api-999")
    assert consumers == []
