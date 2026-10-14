"""
RippleGraph - Tests for Graph Cypher Tools
"""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from graph.tools import (
    check_contract_compatibility,
    find_direct_consumers,
    get_relevant_incidents,
    traverse_downstream_dependencies,
)


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


def test_traverse_downstream_payment_service():
    """
    Test downstream discovery from payment-service:
      - Hop 1 callers: checkout-service, audit-service
      - Hop 2 transitive: order-service, analytics-service (via checkout-service)
    """
    downstream = traverse_downstream_dependencies("payment-service", max_depth=4)

    assert len(downstream) == 4
    by_id = {d["service_id"]: d for d in downstream}

    # Verify Hop 1
    assert by_id["checkout-service"]["min_hop_distance"] == 1
    assert by_id["audit-service"]["min_hop_distance"] == 1

    # Verify Hop 2
    assert by_id["order-service"]["min_hop_distance"] == 2
    assert by_id["analytics-service"]["min_hop_distance"] == 2

    # Verify dependency chain
    order_chains = by_id["order-service"]["dependency_chains"]
    assert ["order-service", "checkout-service", "payment-service"] in order_chains


def test_traverse_downstream_depth_limiting():
    """Test restricting max_depth limits the traversal frontier."""
    # Depth 1 only returns direct callers
    direct_only = traverse_downstream_dependencies("payment-service", max_depth=1)
    assert len(direct_only) == 2
    assert {d["service_id"] for d in direct_only} == {"checkout-service", "audit-service"}


def test_traverse_downstream_leaf_service():
    """Test a leaf service with no callers returns an empty downstream list."""
    leaf = traverse_downstream_dependencies("analytics-service", max_depth=4)
    assert leaf == []


def test_traverse_downstream_unknown_service():
    """Test querying an unknown service raises ValueError."""
    with pytest.raises(ValueError, match="not found in graph"):
        traverse_downstream_dependencies("unknown-service-xyz")


def test_get_relevant_incidents_all():
    """Test fetching all incidents without filter returns 6 linked incidents."""
    incidents = get_relevant_incidents()
    assert len(incidents) == 6

    inc_by_id = {i["incident_id"]: i for i in incidents}
    assert "INC-101" in inc_by_id
    assert "INC-105" in inc_by_id

    # Verify mitigation linkage
    inc_101 = inc_by_id["INC-101"]
    assert inc_101["affected_service_id"] == "payment-service"
    assert inc_101["mitigation"] is not None
    assert inc_101["mitigation"]["id"] == "MIT-101"
    assert "Dual Version" in inc_101["mitigation"]["title"]


def test_get_relevant_incidents_service_filter():
    """Test restricting incident retrieval to specific affected services."""
    incidents = get_relevant_incidents(service_ids=["payment-service", "checkout-service"])
    assert len(incidents) == 2
    assert {i["incident_id"] for i in incidents} == {"INC-101", "INC-102"}


def test_get_relevant_incidents_red_herring_filtering():
    """
    Test adversarial red herring rejection on INC-105:
    When change claims are identity token renames (field_rename, sub, roles),
    INC-101 is RELEVANT, while INC-105 is flagged as REJECTED_RED_HERRING.
    """
    active_claims = ["field_rename", "sub", "roles", "token_format"]
    incidents = get_relevant_incidents(active_claim_types=active_claims)

    inc_by_id = {i["incident_id"]: i for i in incidents}

    # INC-101 matches
    inc_101 = inc_by_id["INC-101"]
    assert inc_101["relevance_status"] == "RELEVANT"
    assert set(inc_101["matching_claim_types"]) == {"field_rename", "sub", "roles", "token_format"}
    assert inc_101["rejection_reason"] is None

    # INC-105 is a red herring (error_handling, token_parse, retry_storm)
    inc_105 = inc_by_id["INC-105"]
    assert inc_105["relevance_status"] == "REJECTED_RED_HERRING"
    assert inc_105["matching_claim_types"] == []
    assert inc_105["rejection_reason"] is not None
    assert "do not match active change claim types" in inc_105["rejection_reason"]


def test_get_relevant_incidents_empty_service_filter():
    """Test service with no incidents returns an empty list."""
    incidents = get_relevant_incidents(service_ids=["inventory-service"])
    assert incidents == []



