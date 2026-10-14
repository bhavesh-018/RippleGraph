"""
RippleGraph - Seed Verification Test Suite

Tests that the FalkorDB graph was correctly populated with:
  - 10 Service nodes
  - 10 API nodes
  - 10 PROVIDES_API edges
  - 11 DEPENDS_ON edges
  - 3 ContractVersion nodes with proper statuses
  - 6 Incidents with INC-105 red herring metadata
  - 6 Mitigations linked via MITIGATED_BY edges
  - Compatibility partition on auth-token-api
"""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.client import get_graph
from graph.seed import seed


@pytest.fixture(scope="session", autouse=True)
def setup_graph():
    """Ensure graph is freshly seeded before running tests."""
    seed(skip_verification=True)


def test_service_nodes():
    """Verify that all 10 core services are present."""
    g = get_graph()
    res = g.query("MATCH (s:Service) RETURN s.id")
    services = {row[0] for row in res.result_set}
    expected = {
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
    assert services == expected, f"Missing or extra services: {expected ^ services}"


def test_api_nodes_and_provides_edges():
    """Verify 10 API nodes and that each service exposes its corresponding API."""
    g = get_graph()
    res_apis = g.query("MATCH (a:API) RETURN a.id")
    assert len(res_apis.result_set) == 10

    res_edges = g.query("MATCH (s:Service)-[:PROVIDES_API]->(a:API) RETURN s.id, a.id")
    assert len(res_edges.result_set) == 10


def test_dependency_topology():
    """Verify exactly 11 DEPENDS_ON edges exist."""
    g = get_graph()
    res = g.query("MATCH ()-[r:DEPENDS_ON]->() RETURN r")
    assert len(res.result_set) == 11


def test_auth_service_direct_dependents():
    """Verify auth-service has exactly 6 direct dependent services."""
    g = get_graph()
    res = g.query(
        "MATCH (s:Service)-[:DEPENDS_ON]->(a:Service {id: $id}) RETURN s.id",
        {"id": "auth-service"},
    )
    direct_dependents = {row[0] for row in res.result_set}
    expected = {
        "payment-service",
        "user-service",
        "session-service",
        "checkout-service",
        "audit-service",
        "notification-service",
    }
    assert direct_dependents == expected


def test_checkout_reachability_paths():
    """
    Verify checkout-service reaches auth-service via 2 distinct paths:
      1. checkout -> auth (direct)
      2. checkout -> payment -> auth (transitive)
    """
    g = get_graph()
    res = g.query(
        """
        MATCH (c:Service {id: $checkout})-[:DEPENDS_ON*1..2]->(a:Service {id: $auth})
        RETURN c.id
        """,
        {"checkout": "checkout-service", "auth": "auth-service"},
    )
    assert len(res.result_set) == 2


def test_contract_versions():
    """Verify 3 ContractVersions exist and are linked to auth-token-api."""
    g = get_graph()
    res = g.query("MATCH (c:ContractVersion) RETURN c.id, c.breaking_change")
    contracts = {row[0]: row[1] for row in res.result_set}

    assert "cv-auth-v1" in contracts
    assert "cv-auth-v2" in contracts
    assert "cv-auth-v1-extended" in contracts

    assert contracts["cv-auth-v1"] is False or contracts["cv-auth-v1"] == "false"
    assert contracts["cv-auth-v2"] is True or contracts["cv-auth-v2"] == "true"
    assert contracts["cv-auth-v1-extended"] is False or contracts["cv-auth-v1-extended"] == "false"

    res_has = g.query(
        "MATCH (a:API {id: 'auth-token-api'})-[:HAS_CONTRACT]->(c:ContractVersion) RETURN c.id"
    )
    assert len(res_has.result_set) == 3


def test_contract_compatibility_partition():
    """
    Verify contract compatibility boundaries:
      - user-service accepts both v1 and v2 (compatible)
      - payment-service, session-service, checkout-service, audit-service, notification-service accept only v1
    """
    g = get_graph()
    incompat_res = g.query(
        """
        MATCH (s:Service)-[:ACCEPTS_CONTRACT]->(:ContractVersion {id: 'cv-auth-v1'})
        WHERE NOT (s)-[:ACCEPTS_CONTRACT]->(:ContractVersion {id: 'cv-auth-v2'})
        RETURN s.id
        """
    )
    incompatible = {row[0] for row in incompat_res.result_set}
    assert incompatible == {
        "payment-service",
        "session-service",
        "checkout-service",
        "audit-service",
        "notification-service",
    }

    compat_res = g.query(
        """
        MATCH (s:Service)-[:ACCEPTS_CONTRACT]->(:ContractVersion {id: 'cv-auth-v2'})
        RETURN s.id
        """
    )
    compatible = {row[0] for row in compat_res.result_set}
    assert "user-service" in compatible


def test_incidents_and_red_herring():
    """
    Verify 6 Incident nodes exist and INC-105 is flagged as the red herring
    affecting notification-service with payload storm claim types.
    """
    g = get_graph()
    res = g.query("MATCH (i:Incident) RETURN i.id")
    assert len(res.result_set) == 6

    rh_res = g.query(
        """
        MATCH (i:Incident {id: 'INC-105'})-[:AFFECTED]->(s:Service)
        RETURN s.id, i.claim_types
        """
    )
    assert len(rh_res.result_set) == 1
    svc_id, claim_types = rh_res.result_set[0]
    assert svc_id == "notification-service"
    assert "error_handling" in claim_types
    assert "retry_storm" in claim_types


def test_mitigations_and_linkage():
    """Verify 6 Mitigations exist and each Incident is linked via MITIGATED_BY."""
    g = get_graph()
    res_m = g.query("MATCH (m:Mitigation) RETURN m.id")
    assert len(res_m.result_set) == 6

    res_rel = g.query("MATCH (i:Incident)-[:MITIGATED_BY]->(m:Mitigation) RETURN i.id, m.id")
    assert len(res_rel.result_set) == 6
