"""
RippleGraph - Investigation History Schemas

Defines Pydantic models for the /api/investigations/history endpoint,
providing typed, structured summaries of past investigation runs.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class InvestigationSummary(BaseModel):
    """Lightweight summary of a single past investigation run."""

    investigation_id: str = Field(..., description="Unique investigation run ID")
    change_id: str = Field(..., description="Change proposal ID evaluated")
    change_title: str = Field(..., description="Human-readable change title")
    status: str = Field(..., description="Pipeline status: completed, failed, partial")
    memory_enabled: bool = Field(
        ..., description="Whether Stage-2 memory recall was active"
    )
    disconnect_graph: bool = Field(
        default=False,
        description="Whether this was a Proof Mode (disconnected graph) run",
    )
    created_at: str = Field(..., description="ISO 8601 timestamp of investigation start")
    findings_count: int = Field(
        default=0, description="Total number of findings produced"
    )
    incompatible_count: int = Field(
        default=0, description="Number of INCOMPATIBLE findings"
    )
    at_risk_count: int = Field(
        default=0, description="Number of POTENTIAL_DOWNSTREAM findings"
    )
    compatible_count: int = Field(
        default=0, description="Number of COMPATIBLE findings"
    )
    unaffected_count: int = Field(
        default=0, description="Number of UNAFFECTED findings"
    )
    avg_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Mean confidence across all findings"
    )
    execution_time_ms: Optional[float] = Field(
        default=None, description="Pipeline wall-clock time in milliseconds"
    )


class InvestigationHistoryResponse(BaseModel):
    """Paginated history of all investigation runs."""

    total: int = Field(..., description="Total number of stored investigation runs")
    investigations: List[InvestigationSummary] = Field(
        default_factory=list,
        description="List of investigation summaries, newest first",
    )
