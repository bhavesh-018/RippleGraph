"""
RippleGraph - Tests for Graph Cypher Tools
"""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from graph.tools import check_contract_compatibility, find_direct_consumers


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


def test_check_contract_compatibility_v2_breaking():
    """
    Test proposing cv-auth-v2 (breaking change):
    - user-service is compatible (accepts cv-auth-v2).
    - 5 other consumers are incompatible due to missing claims (sub, exp, roles).
    """
    report = check_contract_compatibility("cv-auth-v2")

    assert report["proposed_contract_id"] == "cv-auth-v2"
    assert report["total_consumers_checked"] == 6
    assert report["compatible_count"] == 1
    assert report["incompatible_count"] == 5

    res_by_id = {r["service_id"]: r for r in report["results"]}

    # user-service is compatible
    assert res_by_id["user-service"]["is_compatible"] is True
    assert res_by_id["user-service"]["missing_claims"] == []

    # payment-service is incompatible
    payment_res = res_by_id["payment-service"]
    assert payment_res["is_compatible"] is False
    assert set(payment_res["missing_claims"]) == {"sub", "exp", "roles"}


def test_check_contract_compatibility_v1_extended_safe():
    """
    Test proposing cv-auth-v1-extended (transitional format):
    - All 6 consumers must be compatible because it satisfies both v1 and v2 claims.
    """
    report = check_contract_compatibility("cv-auth-v1-extended")

    assert report["proposed_contract_id"] == "cv-auth-v1-extended"
    assert report["total_consumers_checked"] == 6
    assert report["compatible_count"] == 6
    assert report["incompatible_count"] == 0

    for r in report["results"]:
        assert r["is_compatible"] is True
        assert r["missing_claims"] == []


def test_check_contract_compatibility_consumer_filter():
    """Test filtering check to a specific subset of consumer services."""
    report = check_contract_compatibility(
        "cv-auth-v2",
        consumer_service_ids=["payment-service", "user-service"],
    )

    assert report["total_consumers_checked"] == 2
    assert report["compatible_count"] == 1
    assert report["incompatible_count"] == 1


def test_check_contract_compatibility_unknown_contract():
    """Test error raised when proposed contract does not exist."""
    with pytest.raises(ValueError, match="not found in graph"):
        check_contract_compatibility("nonexistent-cv")

