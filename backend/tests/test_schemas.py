"""
RippleGraph - Tests for Pydantic Models & Schemas
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.graph import (
    ChangeProposal,
    FindingNode,
    IncidentNode,
    InvestigationRequest,
    InvestigationResponse,
    MitigationNode,
    ServiceEvaluationStatus,
    ServiceNode,
    ServiceTier,
    TopologyResponse,
)


def test_service_node_validation():
    """Test valid ServiceNode serialization."""
    svc = ServiceNode(
        id="payment-service",
        name="Payment Service",
        tier=ServiceTier.CORE,
        owner_team="payments",
        repo="commerce/payment-service",
    )
    assert svc.id == "payment-service"
    assert svc.tier == ServiceTier.CORE


def test_service_node_invalid_tier():
    """Test invalid tier raises validation error."""
    with pytest.raises(ValidationError):
        ServiceNode(
            id="bad-svc",
            name="Bad Service",
            tier="invalid_tier",  # type: ignore
            owner_team="bad",
            repo="bad/repo",
        )


def test_change_proposal_defaults():
    """Test default values on ChangeProposal."""
    change = ChangeProposal(
        title="JWT v2 Migration",
        description="Renaming sub to subject_id",
    )
    assert change.id == "CHG-001"
    assert change.proposing_service == "auth-service"
    assert change.target_api == "auth-token-api"
    assert change.proposed_contract_id == "cv-auth-v2"
    assert "field_rename" in change.claim_types


def test_finding_node_confidence_bounds():
    """Test finding confidence score is bounded between 0.0 and 1.0."""
    finding = FindingNode(
        id="FND-001",
        investigation_id="INV-001",
        service_id="payment-service",
        category="DIRECT_INCOMPATIBILITY",
        status=ServiceEvaluationStatus.INCOMPATIBLE,
        confidence=0.95,
        reasons=["Missing claims: sub, exp, roles"],
    )
    assert finding.confidence == 0.95
    assert finding.status == ServiceEvaluationStatus.INCOMPATIBLE

    # Confidence > 1.0 should fail
    with pytest.raises(ValidationError):
        FindingNode(
            id="FND-002",
            investigation_id="INV-001",
            service_id="payment-service",
            category="DIRECT_INCOMPATIBILITY",
            status=ServiceEvaluationStatus.INCOMPATIBLE,
            confidence=1.5,
        )


def test_investigation_response_serialization():
    """Test complete investigation response schema serialization."""
    finding = FindingNode(
        id="FND-001",
        investigation_id="INV-001",
        service_id="payment-service",
        category="DIRECT_INCOMPATIBILITY",
        status=ServiceEvaluationStatus.INCOMPATIBLE,
        confidence=1.0,
    )
    resp = InvestigationResponse(
        investigation_id="INV-001",
        change_id="CHG-001",
        change_title="JWT v2 Migration",
        memory_enabled=True,
        summary={"incompatible": 1, "potential_downstream": 0, "compatible": 0, "unaffected": 0},
        findings=[finding],
    )
    assert resp.investigation_id == "INV-001"
    assert len(resp.findings) == 1
    assert resp.recommended_migration_contract == "cv-auth-v1-extended"


def test_topology_response_schema():
    """Test React Flow topology response serialization."""
    topo = TopologyResponse(
        nodes=[{"id": "auth-service", "data": {"label": "Auth Service"}}],  # type: ignore
        edges=[{"id": "e1", "source": "payment-service", "target": "auth-service"}],  # type: ignore
        total_services=1,
        total_dependencies=1,
    )
    assert topo.total_services == 1
    assert topo.nodes[0].id == "auth-service"
    assert topo.edges[0].source == "payment-service"
