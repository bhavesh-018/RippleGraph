"""
RippleGraph - Pydantic Data Models & Schemas

Defines type-safe Pydantic v2 models for:
  - Graph nodes (Service, API, ContractVersion, Incident, Mitigation)
  - Change proposals evaluated by the Change Rehearsal Agent
  - Evaluation statuses and findings produced across Stages 1-4
  - React Flow topology serialization payloads
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ServiceTier(str, Enum):
    PLATFORM = "platform"
    CORE = "core"
    SUPPORTING = "supporting"


class ServiceEvaluationStatus(str, Enum):
    INCOMPATIBLE = "incompatible"
    POTENTIAL_DOWNSTREAM = "potential_downstream"
    COMPATIBLE = "compatible"
    UNAFFECTED = "unaffected"


# =============================================================================
# Graph Node Schemas
# =============================================================================

class ServiceNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique service identifier (e.g. auth-service)")
    name: str = Field(..., description="Human-readable service name")
    tier: ServiceTier = Field(..., description="Service criticality tier")
    owner_team: str = Field(..., description="Responsible engineering team")
    repo: str = Field(..., description="Source code repository path")
    description: Optional[str] = Field(default=None, description="Service responsibility summary")
    icon: Optional[str] = Field(default="Server", description="Frontend icon identifier")
    runtime: Optional[str] = Field(default=None, description="Technology runtime (e.g. Go 1.22, Python 3.12)")
    version: Optional[str] = Field(default="v1.0.0", description="Current deployed semantic version")
    port: Optional[int] = Field(default=8080, description="Internal service network port")


class APINode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique API identifier (e.g. auth-token-api)")
    name: str = Field(..., description="Human-readable API name")
    protocol: str = Field(default="REST", description="Protocol: REST, gRPC, etc.")
    path: str = Field(..., description="Endpoint path or gRPC method")
    service_id: Optional[str] = Field(default=None, description="Providing service ID")


class ContractVersionNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique contract version ID (e.g. cv-auth-v1)")
    name: str = Field(..., description="Contract name")
    version: str = Field(..., description="Semantic version string (e.g. 1.0, 2.0)")
    api_id: str = Field(..., description="Target API ID this contract applies to")
    status: str = Field(default="active", description="active, proposed, or transitional")
    breaking_change: bool = Field(default=False, description="Flag indicating breaking schema changes")
    description: str = Field(..., description="Contract description and summary of claims")
    claims: Optional[str] = Field(default=None, description="Serialized JSON claims dictionary")


class MitigationNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique mitigation ID (e.g. MIT-101)")
    title: str = Field(..., description="Mitigation title")
    description: str = Field(..., description="Strategy and implementation guidelines")
    validation_method: str = Field(..., description="Automated testing or canary validation procedure")


class IncidentNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique incident ID (e.g. INC-101)")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Detailed description of outage")
    severity: str = Field(..., description="critical, high, medium, low")
    root_cause: str = Field(..., description="Post-mortem root cause analysis")
    occurred_at: str = Field(..., description="ISO 8601 date string of incident occurrence")
    claim_types: List[str] = Field(default_factory=list, description="Claim tags associated with the failure")
    affected_service_id: Optional[str] = Field(default=None, description="Impacted service ID")
    mitigation: Optional[MitigationNode] = Field(default=None, description="Resolved playbook mitigation")


# =============================================================================
# Change Proposals & Investigation Schemas
# =============================================================================

class ChangeProposal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default="CHG-001", description="Change proposal identifier")
    title: str = Field(..., description="Change proposal title")
    proposing_service: str = Field(default="auth-service", description="Service originating the change")
    target_api: str = Field(default="auth-token-api", description="API endpoint being modified")
    proposed_contract_id: str = Field(default="cv-auth-v2", description="Proposed ContractVersion ID")
    claim_types: List[str] = Field(
        default_factory=lambda: ["field_rename", "sub", "roles", "exp", "token_format"],
        description="Claim types affected by this change (used for incident correlation)",
    )
    description: str = Field(..., description="Detailed explanation of the proposed change")


class ChangeCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    proposing_service: str
    proposing_service_name: str
    target_api: str
    target_api_name: str
    proposed_contract_id: str
    risk_level: str = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, SAFE")
    impact_scope: str = Field(default="Direct Blast Radius")
    claim_types: List[str] = Field(default_factory=list)
    description: str


class InvestigationRequest(BaseModel):
    change_id: Optional[str] = Field(default="CHG-001", description="Change proposal ID to evaluate")
    change: Optional[ChangeProposal] = Field(default=None, description="Optional custom change proposal")
    memory_enabled: bool = Field(
        default=True,
        description="Whether to recall and apply prior investigation findings with temporal decay",
    )
    disconnect_graph: bool = Field(
        default=False,
        description="Proof Mode: Simulates running without FalkorDB to demonstrate failure of flat/non-graph evaluation",
    )


class FindingNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique finding ID (e.g. FND-001)")
    investigation_id: str = Field(..., description="Originating investigation run ID")
    service_id: str = Field(..., description="Evaluated service ID")
    service_name: Optional[str] = Field(default=None, description="Evaluated service name")
    category: str = Field(
        ...,
        description="Finding category: DIRECT_INCOMPATIBILITY, TRANSITIVE_RISK, COMPATIBLE_CONSUMER, UNAFFECTED",
    )
    status: ServiceEvaluationStatus = Field(..., description="Assigned evaluation status")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    reasons: List[str] = Field(default_factory=list, description="Audit justification for this status")
    missing_claims: List[str] = Field(default_factory=list, description="Missing claims required by service")
    dependency_chains: List[List[str]] = Field(default_factory=list, description="Call chains from target to origin")
    hop_depth: int = Field(default=0, ge=0, description="Hop depth from change origin")
    recommended_mitigation_id: Optional[str] = Field(default=None, description="Associated Mitigation ID")
    recommended_contract_id: Optional[str] = Field(default=None, description="Suggested transitional contract")
    relevant_incidents: List[str] = Field(default_factory=list, description="Matched incident IDs")
    rejected_red_herrings: List[str] = Field(default_factory=list, description="Rejected red-herring incident IDs")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of finding creation")
    decayed_confidence: Optional[float] = Field(default=None, description="Decayed confidence score from memory")
    days_old: Optional[float] = Field(default=None, description="Age of prior finding in days")
    decay_factor: Optional[float] = Field(default=None, description="Mathematical decay factor applied")
    reaffirmed: Optional[bool] = Field(default=False, description="Whether this finding was reaffirmed by memory")
    is_stale: Optional[bool] = Field(default=False, description="Whether prior finding was flagged as stale/resolved")
    staleness_reason: Optional[str] = Field(default=None, description="Explanation of why finding is stale or resolved")


class InvestigationResponse(BaseModel):
    investigation_id: str
    change_id: str
    change_title: str
    memory_enabled: bool
    disconnect_graph: bool = Field(
        default=False,
        description="Whether this investigation was executed with FalkorDB disconnected in Proof Mode",
    )
    warning: Optional[str] = Field(
        default=None,
        description="System warnings or graph availability notes",
    )
    summary: Dict[str, int] = Field(
        description="Counts of incompatible, potential_downstream, compatible, unaffected",
    )
    recommended_migration_contract: Optional[str] = Field(
        default="cv-auth-v1-extended",
        description="Recommended non-breaking transitional contract",
    )
    findings: List[FindingNode]
    red_herrings_rejected: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float = Field(default=0.0)


# =============================================================================
# React Flow Canvas Schemas
# =============================================================================

class ReactFlowNode(BaseModel):
    id: str
    type: str = "serviceNode"
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    data: Dict[str, Any]


class ReactFlowEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "smoothstep"
    animated: bool = False
    label: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class TopologyResponse(BaseModel):
    nodes: List[ReactFlowNode]
    edges: List[ReactFlowEdge]
    total_services: int
    total_dependencies: int
