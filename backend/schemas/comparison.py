"""
RippleGraph - Schemas for Feature 2: Memory Comparison & Visual Diff
POST /api/investigations/compare
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ServiceMemoryDelta(BaseModel):
    service_id: str
    service_name: str
    status_with_memory: str
    status_without_memory: str
    confidence_with_memory: float = Field(..., ge=0.0, le=1.0)
    confidence_without_memory: float = Field(..., ge=0.0, le=1.0)
    confidence_delta: float
    confidence_gain_pct: float
    memory_reaffirmed: bool = False
    prior_finding_cited: Optional[str] = None
    prior_investigation_id: Optional[str] = None
    memory_explanation: Optional[str] = None
    missing_claims: List[str] = Field(default_factory=list)


class MemoryComparisonSummary(BaseModel):
    change_id: str
    change_title: str
    avg_confidence_with_memory: float
    avg_confidence_without_memory: float
    avg_confidence_delta: float
    overall_confidence_gain_pct: float
    reaffirmed_count: int
    total_services_analyzed: int
    execution_time_with_memory_ms: float
    execution_time_without_memory_ms: float
    memory_verdict: str


class MemoryComparisonResponse(BaseModel):
    change_id: str
    summary: MemoryComparisonSummary
    deltas: List[ServiceMemoryDelta]
    investigation_id_with_memory: str
    investigation_id_without_memory: str
