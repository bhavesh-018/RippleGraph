"""
RippleGraph - Graph Seed Script

Seeds the FalkorDB graph with the complete synthetic microservice ecosystem:
  - 10 services with dependency topology
  - 10 APIs (one per service)
  - 3 ContractVersions (v1, v2, v1-extended transitional)
  - 6 Incidents including INC-105 (deliberate red herring)
  - 6 Mitigations linked to incidents

Run directly:
    python backend/graph/seed.py

Or via the API:
    POST /api/seed/reset
"""

import json
import logging
import sys
from pathlib import Path

# Allow running from the project root or backend/ directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.client import get_graph, reset_graph

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# Node definitions
# =============================================================================

SERVICES = [
    {
        "id": "auth-service",
        "name": "Auth Service",
        "tier": "platform",
        "owner_team": "identity",
        "repo": "platform/auth-service",
    },
    {
        "id": "payment-service",
        "name": "Payment Service",
        "tier": "core",
        "owner_team": "payments",
        "repo": "commerce/payment-service",
    },
    {
        "id": "user-service",
        "name": "User Service",
        "tier": "core",
        "owner_team": "identity",
        "repo": "platform/user-service",
    },
    {
        "id": "session-service",
        "name": "Session Service",
        "tier": "platform",
        "owner_team": "identity",
        "repo": "platform/session-service",
    },
    {
        "id": "checkout-service",
        "name": "Checkout Service",
        "tier": "core",
        "owner_team": "commerce",
        "repo": "commerce/checkout-service",
    },
    {
        "id": "order-service",
        "name": "Order Service",
        "tier": "core",
        "owner_team": "commerce",
        "repo": "commerce/order-service",
    },
    {
        "id": "inventory-service",
        "name": "Inventory Service",
        "tier": "supporting",
        "owner_team": "commerce",
        "repo": "commerce/inventory-service",
    },
    {
        "id": "analytics-service",
        "name": "Analytics Service",
        "tier": "supporting",
        "owner_team": "data",
        "repo": "data/analytics-service",
    },
    {
        "id": "audit-service",
        "name": "Audit Service",
        "tier": "supporting",
        "owner_team": "compliance",
        "repo": "platform/audit-service",
    },
    {
        "id": "notification-service",
        "name": "Notification Service",
        "tier": "supporting",
        "owner_team": "platform",
        "repo": "platform/notification-service",
    },
]

# DEPENDS_ON edges: (dependent, provider)
# Read as: dependent calls/relies on provider
DEPENDS_ON_EDGES = [
    ("payment-service", "auth-service"),
    ("user-service", "auth-service"),
    ("session-service", "auth-service"),
    ("checkout-service", "payment-service"),
    ("checkout-service", "auth-service"),
    ("order-service", "checkout-service"),
    ("order-service", "inventory-service"),
    ("analytics-service", "checkout-service"),
    ("audit-service", "auth-service"),
    ("audit-service", "payment-service"),
    ("notification-service", "auth-service"),
]

APIS = [
    {
        "id": "auth-token-api",
        "name": "Auth Token API",
        "protocol": "REST",
        "path": "/api/v1/token",
        "service_id": "auth-service",
    },
    {
        "id": "payment-charge-api",
        "name": "Payment Charge API",
        "protocol": "REST",
        "path": "/api/v1/charge",
        "service_id": "payment-service",
    },
    {
        "id": "user-profile-api",
        "name": "User Profile API",
        "protocol": "REST",
        "path": "/api/v1/users",
        "service_id": "user-service",
    },
    {
        "id": "session-refresh-api",
        "name": "Session Refresh API",
        "protocol": "REST",
        "path": "/api/v1/session/refresh",
        "service_id": "session-service",
    },
    {
        "id": "checkout-create-api",
        "name": "Checkout Create API",
        "protocol": "REST",
        "path": "/api/v1/checkout",
        "service_id": "checkout-service",
    },
    {
        "id": "order-create-api",
        "name": "Order Create API",
        "protocol": "REST",
        "path": "/api/v1/orders",
        "service_id": "order-service",
    },
    {
        "id": "inventory-query-api",
        "name": "Inventory Query API",
        "protocol": "REST",
        "path": "/api/v1/inventory",
        "service_id": "inventory-service",
    },
    {
        "id": "analytics-events-api",
        "name": "Analytics Events API",
        "protocol": "gRPC",
        "path": "/analytics.EventService/Ingest",
        "service_id": "analytics-service",
    },
    {
        "id": "audit-log-api",
        "name": "Audit Log API",
        "protocol": "gRPC",
        "path": "/audit.LogService/Write",
        "service_id": "audit-service",
    },
    {
        "id": "notification-send-api",
        "name": "Notification Send API",
        "protocol": "REST",
        "path": "/api/v1/notify",
        "service_id": "notification-service",
    },
]


# =============================================================================
# =============================================================================
# Contract versions
# =============================================================================

# claims encodes the field names and descriptions the contract publishes.
# Consumers register which version they accept via ACCEPTS_CONTRACT edges.
# The compatibility check diffs proposed claims against consumer-accepted claims.

CONTRACT_VERSIONS = [
    {
        "id": "cv-auth-v1",
        "name": "Auth Token v1",
        "version": "1.0",
        "status": "active",
        "api_id": "auth-token-api",
        "breaking_change": False,
        "description": "Legacy JWT contract. Uses sub, exp (unix timestamp), and roles.",
        "claims": json.dumps({
            "sub": "string - subject identifier",
            "exp": "integer - unix timestamp expiry",
            "roles": "string[] - permission roles",
        }),
    },
    {
        "id": "cv-auth-v2",
        "name": "Auth Token v2",
        "version": "2.0",
        "status": "proposed",
        "api_id": "auth-token-api",
        "breaking_change": True,
        "description": "Proposed breaking change. Renames sub->subject_id, exp->expires_at (ISO 8601), roles->scopes.",
        "claims": json.dumps({
            "subject_id": "string - subject identifier (renamed from sub)",
            "expires_at": "string - ISO 8601 expiry (renamed from exp)",
            "scopes": "string[] - permission scopes (renamed from roles)",
        }),
    },
    {
        "id": "cv-auth-v1-extended",
        "name": "Auth Token v1-extended (Transitional)",
        "version": "1.5",
        "status": "transitional",
        "breaking_change": False,
        "api_id": "auth-token-api",
        "description": "Dual-support contract. Publishes both old and new field names simultaneously.",
        "claims": json.dumps({
            "sub": "string - preserved for v1 compatibility",
            "subject_id": "string - new v2 claim name",
            "exp": "integer - preserved for v1 compatibility",
            "expires_at": "string - new v2 claim name (ISO 8601)",
            "roles": "string[] - preserved for v1 compatibility",
            "scopes": "string[] - new v2 claim name",
        }),
    },
]

# Which ContractVersion each service currently accepts on auth-token-api
# payment-service accepts ONLY v1 (strict - breaks on v2 immediately)
# user-service accepts both v1 and v2 (compatible)
# session-service accepts v1 (sensitive to expiry claim changes)
# checkout-service accepts v1 (indirectly via payment)
# audit-service accepts v1 (reads auth tokens from logs)
# notification-service accepts v1 (sends auth-gated notifications)
ACCEPTS_CONTRACT_EDGES = [
    ("payment-service",      "cv-auth-v1"),
    ("user-service",         "cv-auth-v1"),
    ("user-service",         "cv-auth-v2"),
    ("session-service",      "cv-auth-v1"),
    ("checkout-service",     "cv-auth-v1"),
    ("audit-service",        "cv-auth-v1"),
    ("notification-service", "cv-auth-v1"),
]


# =============================================================================
# Historical Incidents
# =============================================================================

# INC-105 is a deliberate red herring: same domain keyword ('token'), but caused by
# an unhandled payload parse error and retry storm rather than a breaking claim rename.
# The Stage 3 Reviewer must deterministically reject INC-105 during token migrations.

INCIDENTS = [
    {
        "id": "INC-101",
        "title": "Payment Token Rejection",
        "description": "Payment Service rejected all authentication tokens during a prior migration because the token format was unsupported. Downstream services experienced cascading failures.",
        "severity": "critical",
        "root_cause": "Consumer contract compatibility was not validated before migration. Payment expected v1 claims (sub, exp, roles) but received tokens in an updated format.",
        "occurred_at": "2026-03-15",
        "claim_types": "token_format,field_rename,sub,roles",
        "affected_svc": "payment-service",
        "mitigation_id": "MIT-101",
    },
    {
        "id": "INC-102",
        "title": "Checkout Authorization Cascade Failure",
        "description": "Checkout requests experienced widespread authorization failures because Payment Service could not validate supplied tokens during a prior migration.",
        "severity": "critical",
        "root_cause": "End-to-end authorization path across Checkout and Payment was not tested before rollout. Checkout inherited Payment's incompatibility.",
        "occurred_at": "2026-03-15",
        "claim_types": "downstream_auth,token_format,field_rename",
        "affected_svc": "checkout-service",
        "mitigation_id": "MIT-102",
    },
    {
        "id": "INC-103",
        "title": "Session Refresh Failures",
        "description": "Session Service refresh calls failed after an authentication change altered expiry-claim handling. Active user sessions were invalidated unexpectedly, causing 4,200 forced logouts.",
        "severity": "high",
        "root_cause": "Expiry claim field rename (exp->expires_at) and format change (unix->ISO 8601) broke the session refresh parser. Compatibility was not included in pre-migration validation.",
        "occurred_at": "2026-05-02",
        "claim_types": "expiry_claim,session_compat,expires_at,exp",
        "affected_svc": "session-service",
        "mitigation_id": "MIT-103",
    },
    {
        "id": "INC-104",
        "title": "Order Cascade from Payment Outage",
        "description": "Order Service failed to process incoming checkout orders for 47 minutes after Payment and Checkout became unavailable due to token format rejection.",
        "severity": "critical",
        "root_cause": "Order Service has no queue or fallback when Checkout and Payment are unavailable. Token format mismatch cascaded downstream to order processing.",
        "occurred_at": "2026-03-15",
        "claim_types": "payment_dependency,token_format,downstream_cascade",
        "affected_svc": "order-service",
        "mitigation_id": "MIT-104",
    },
    {
        # RED HERRING - same domain (token) but different claim type.
        # The Reviewer should correctly reject this for the v1->v2 change
        # because INC-105 is about parse error handling and payload storms, not field renaming.
        "id": "INC-105",
        "title": "Notification Storm on Token Parse Error",
        "description": "Notification Service triggered a retry storm after receiving tokens it could not parse, resulting in 18,000 duplicate notifications sent to users over 12 minutes.",
        "severity": "medium",
        "root_cause": "Notification Service lacked graceful handling for unrecognized token claim formats. Error retry loop ran without backoff, causing message duplication.",
        "occurred_at": "2025-11-18",
        "claim_types": "error_handling,token_parse,retry_storm",
        "affected_svc": "notification-service",
        "mitigation_id": "MIT-105",
    },
    {
        "id": "INC-106",
        "title": "Audit Trail Gap from Token Expiry Mismatch",
        "description": "Audit Service failed to record security events for 23 minutes because token expiry validation rejected all incoming tokens after the exp claim format changed.",
        "severity": "high",
        "root_cause": "Audit Service strictly validates token expiry using exp as a unix timestamp integer. The rename to expires_at with ISO 8601 string format caused validations to fail silently.",
        "occurred_at": "2026-05-02",
        "claim_types": "expiry_claim,audit_security,field_rename,expires_at,exp",
        "affected_svc": "audit-service",
        "mitigation_id": "MIT-106",
    },
]


# =============================================================================
# Mitigations
# =============================================================================

MITIGATIONS = [
    {
        "id": "MIT-101",
        "title": "Dual Version Token Support",
        "description": "Implement a transition period supporting both v1 and v2 token formats simultaneously. Use cv-auth-v1-extended as the migration path. Add automated contract compatibility tests to CI before any token migration proceeds.",
        "validation_method": "Integration tests with both token formats in staging; canary rollout with 5% traffic; automated contract compatibility matrix check",
    },
    {
        "id": "MIT-102",
        "title": "End-to-End Authorization Testing",
        "description": "Run end-to-end authorization tests covering the full Checkout -> Payment authorization path before any auth contract rollout. Validate in a staging environment that mirrors production dependencies.",
        "validation_method": "E2E test suite: Checkout + Payment auth flow; staging environment with production-mirrored service versions",
    },
    {
        "id": "MIT-103",
        "title": "Session Expiry Compatibility Validation",
        "description": "Test expiry claim parsing and session refresh behavior against the proposed contract before migration. Add expiry claim format (unix vs ISO 8601) to the contract compatibility validation matrix.",
        "validation_method": "Session refresh regression tests; expiry field format validator; load test session refresh under both formats",
    },
    {
        "id": "MIT-104",
        "title": "Payment Dependency Circuit Breaker",
        "description": "Implement a circuit breaker in Order Service for the Payment and Checkout dependencies. Add graceful degradation: queue order operations when Checkout or Payment is unavailable rather than failing immediately.",
        "validation_method": "Chaos engineering: Payment failure -> verify Order queues and retries; circuit breaker trip threshold testing",
    },
    {
        "id": "MIT-105",
        "title": "Token Parse Error Graceful Handling",
        "description": "Add graceful fallback in Notification Service for unrecognized token claim formats. Implement exponential backoff with jitter and a dead-letter queue for parse failures to prevent retry storms.",
        "validation_method": "Unit tests for unrecognized token format; DLQ monitoring alert; retry storm simulation test",
    },
    {
        "id": "MIT-106",
        "title": "Audit Token Refresh and Gap Alerting",
        "description": "Implement a token refresh mechanism in Audit Service with support for both unix timestamp and ISO 8601 expiry formats. Add real-time alerting for audit trail gaps exceeding 60 seconds.",
        "validation_method": "Dual expiry format support unit tests; audit gap alert fire test; 30-day audit trail integrity check",
    },
]


# =============================================================================
# Seed functions
# =============================================================================

def _seed_services(graph) -> None:
    logger.info("Seeding %d services...", len(SERVICES))
    for svc in SERVICES:
        graph.query(
            """
            MERGE (s:Service {id: $id})
            SET s.name       = $name,
                s.tier       = $tier,
                s.owner_team = $owner_team,
                s.repo       = $repo
            """,
            {"id": svc["id"], "name": svc["name"], "tier": svc["tier"],
             "owner_team": svc["owner_team"], "repo": svc["repo"]},
        )

    logger.info("Seeding %d DEPENDS_ON edges...", len(DEPENDS_ON_EDGES))
    for dependent, provider in DEPENDS_ON_EDGES:
        graph.query(
            """
            MATCH (a:Service {id: $dep}), (b:Service {id: $prov})
            MERGE (a)-[:DEPENDS_ON]->(b)
            """,
            {"dep": dependent, "prov": provider},
        )


def _seed_apis(graph) -> None:
    logger.info("Seeding %d APIs...", len(APIS))
    for api in APIS:
        graph.query(
            """
            MERGE (a:API {id: $id})
            SET a.name       = $name,
                a.protocol   = $protocol,
                a.path       = $path
            """,
            {"id": api["id"], "name": api["name"],
             "protocol": api["protocol"], "path": api["path"]},
        )
        graph.query(
            """
            MATCH (s:Service {id: $svc_id}), (a:API {id: $api_id})
            MERGE (s)-[:PROVIDES_API]->(a)
            """,
            {"svc_id": api["service_id"], "api_id": api["id"]},
        )


def _seed_contracts(graph) -> None:
    logger.info("Seeding %d ContractVersions...", len(CONTRACT_VERSIONS))
    for cv in CONTRACT_VERSIONS:
        graph.query(
            """
            MERGE (c:ContractVersion {id: $id})
            SET c.name            = $name,
                c.version         = $version,
                c.status          = $status,
                c.api_id          = $api_id,
                c.breaking_change = $breaking_change,
                c.description     = $description,
                c.claims          = $claims,
                c.claims_json     = $claims
            """,
            {
                "id": cv["id"],
                "name": cv["name"],
                "version": cv["version"],
                "status": cv["status"],
                "api_id": cv["api_id"],
                "breaking_change": cv["breaking_change"],
                "description": cv["description"],
                "claims": cv["claims"],
            },
        )
        graph.query(
            """
            MATCH (a:API {id: $api_id}), (c:ContractVersion {id: $cv_id})
            MERGE (a)-[:HAS_CONTRACT]->(c)
            """,
            {"api_id": cv["api_id"], "cv_id": cv["id"]},
        )

    logger.info("Seeding %d ACCEPTS_CONTRACT edges...", len(ACCEPTS_CONTRACT_EDGES))
    for svc_id, cv_id in ACCEPTS_CONTRACT_EDGES:
        graph.query(
            """
            MATCH (s:Service {id: $svc_id}), (c:ContractVersion {id: $cv_id})
            MERGE (s)-[:ACCEPTS_CONTRACT]->(c)
            """,
            {"svc_id": svc_id, "cv_id": cv_id},
        )


def _seed_incidents(graph) -> None:
    logger.info("Seeding %d Incidents...", len(INCIDENTS))
    for inc in INCIDENTS:
        graph.query(
            """
            MERGE (i:Incident {id: $id})
            SET i.title       = $title,
                i.description = $description,
                i.severity    = $severity,
                i.root_cause  = $root_cause,
                i.occurred_at = $occurred_at,
                i.claim_types = $claim_types
            """,
            {
                "id": inc["id"],
                "title": inc["title"],
                "description": inc["description"],
                "severity": inc["severity"],
                "root_cause": inc["root_cause"],
                "occurred_at": inc["occurred_at"],
                "claim_types": inc["claim_types"],
            },
        )
        graph.query(
            """
            MATCH (i:Incident {id: $inc_id}), (s:Service {id: $svc_id})
            MERGE (i)-[:AFFECTED]->(s)
            """,
            {"inc_id": inc["id"], "svc_id": inc["affected_svc"]},
        )


def _seed_mitigations(graph) -> None:
    logger.info("Seeding %d Mitigations...", len(MITIGATIONS))
    for m in MITIGATIONS:
        graph.query(
            """
            MERGE (mit:Mitigation {id: $id})
            SET mit.title             = $title,
                mit.description       = $description,
                mit.validation_method = $validation_method
            """,
            {
                "id": m["id"],
                "title": m["title"],
                "description": m["description"],
                "validation_method": m["validation_method"],
            },
        )

    logger.info("Linking Incidents to Mitigations (MITIGATED_BY)...")
    for inc in INCIDENTS:
        if inc.get("mitigation_id"):
            graph.query(
                """
                MATCH (i:Incident {id: $inc_id}), (m:Mitigation {id: $mit_id})
                MERGE (i)-[:MITIGATED_BY]->(m)
                """,
                {"inc_id": inc["id"], "mit_id": inc["mitigation_id"]},
            )


def seed(skip_verification: bool = False) -> None:
    """Run the complete seed sequence and optional verification."""
    logger.info("Resetting graph...")
    reset_graph()

    graph = get_graph()

    _seed_services(graph)
    _seed_apis(graph)
    _seed_contracts(graph)
    _seed_incidents(graph)
    _seed_mitigations(graph)

    logger.info("Seed complete (services + APIs + contracts + incidents + mitigations).")

    if not skip_verification:
        verify(graph)


def verify(graph=None) -> bool:
    """
    Run the 10-point verification suite.
    Returns True if all assertions pass, raises AssertionError otherwise.
    """
    if graph is None:
        graph = get_graph()

    errors = []

    def check(label: str, cypher: str, params: dict, expected: int) -> None:
        result = graph.query(cypher, params)
        actual = len(result.result_set)
        status = "OK" if actual == expected else "FAIL"
        logger.info("[%s] %s - expected %d, got %d", status, label, expected, actual)
        if actual != expected:
            errors.append(f"{label}: expected {expected}, got {actual}")

    # Assertion 1: 10 service nodes
    check("A1 - Service count", "MATCH (s:Service) RETURN s", {}, 10)

    # Assertion 2: 10 API nodes
    check("A2 - API count", "MATCH (a:API) RETURN a", {}, 10)

    # Assertion 3: 10 PROVIDES_API edges
    check("A3 - PROVIDES_API edges", "MATCH (:Service)-[r:PROVIDES_API]->(:API) RETURN r", {}, 10)

    # Assertion 4: 11 DEPENDS_ON edges
    check("A4 - DEPENDS_ON edges", "MATCH ()-[r:DEPENDS_ON]->() RETURN r", {}, 11)

    # Assertion 5: auth-service has 6 direct dependents
    check(
        "A5 - auth-service direct dependents",
        "MATCH (s:Service)-[:DEPENDS_ON]->(a:Service {id: $id}) RETURN s",
        {"id": "auth-service"},
        6,
    )

    # Assertion 6: checkout-service is reachable from auth-service
    # Two valid paths exist:
    #   (1) checkout -> auth (direct dependency)
    #   (2) checkout -> payment -> auth (transitive)
    check(
        "A6 - checkout reachable from auth (direct + transitive)",
        """
        MATCH (c:Service {id: $checkout})-[:DEPENDS_ON*1..2]->(a:Service {id: $auth})
        RETURN c
        """,
        {"checkout": "checkout-service", "auth": "auth-service"},
        2,
    )

    # Assertion 7: 3 ContractVersions exist
    check("A7 - ContractVersion count", "MATCH (cv:ContractVersion) RETURN cv", {}, 3)

    # Assertion 8: 6 Incidents exist
    check("A8 - Incident count", "MATCH (i:Incident) RETURN i", {}, 6)

    # Assertion 9: 6 Mitigation nodes exist
    check("A9 - Mitigation count", "MATCH (m:Mitigation) RETURN m", {}, 6)

    # Assertion 10: 6 MITIGATED_BY edges exist
    check("A10 - MITIGATED_BY edges", "MATCH ()-[r:MITIGATED_BY]->() RETURN r", {}, 6)

    if errors:
        for e in errors:
            logger.error("ASSERTION FAILED: %s", e)
        raise AssertionError(f"{len(errors)} verification assertion(s) failed.")

    logger.info("All 10 verification assertions passed.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RippleGraph seed script")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run full 8-point verification after seeding (requires all data to be present)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run verification only without re-seeding",
    )
    args = parser.parse_args()

    if args.verify_only:
        verify()
    elif args.verify:
        seed(skip_verification=False)
    else:
        # Default: seed without full verification so incremental builds don't crash
        seed(skip_verification=True)
        logger.info("Seeded successfully. Run with --verify for full assertion check.")
