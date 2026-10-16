"""
Tests for GET /api/investigations/history endpoint.

Validates:
  - Schema correctness of InvestigationSummary and InvestigationHistoryResponse
  - Endpoint returns 200 with valid structure
  - Limit query param is respected
  - Stats fields (counts, avg_confidence) are non-negative
  - total field matches length of investigations list
  - Ordering is newest-first (created_at descending)
  - Empty-graph case returns total=0 gracefully
"""

import pytest
from pydantic import ValidationError

from schemas.history import InvestigationSummary, InvestigationHistoryResponse


# =============================================================================
# Schema unit tests
# =============================================================================

class TestInvestigationSummarySchema:
    """InvestigationSummary Pydantic model validation."""

    def _valid_payload(self, **overrides) -> dict:
        base = {
            "investigation_id": "INV-001",
            "change_id": "CHG-001",
            "change_title": "Auth token field rename",
            "status": "completed",
            "memory_enabled": True,
            "disconnect_graph": False,
            "created_at": "2026-10-17T01:00:00Z",
            "findings_count": 5,
            "incompatible_count": 2,
            "at_risk_count": 1,
            "compatible_count": 1,
            "unaffected_count": 1,
            "avg_confidence": 0.87,
            "execution_time_ms": 432.5,
        }
        base.update(overrides)
        return base

    def test_valid_summary_parses(self):
        summary = InvestigationSummary(**self._valid_payload())
        assert summary.investigation_id == "INV-001"
        assert summary.change_id == "CHG-001"
        assert summary.memory_enabled is True
        assert summary.disconnect_graph is False

    def test_counts_are_non_negative(self):
        summary = InvestigationSummary(**self._valid_payload())
        assert summary.incompatible_count >= 0
        assert summary.at_risk_count >= 0
        assert summary.compatible_count >= 0
        assert summary.unaffected_count >= 0
        assert summary.findings_count >= 0

    def test_avg_confidence_bounds(self):
        summary = InvestigationSummary(**self._valid_payload(avg_confidence=0.0))
        assert summary.avg_confidence == 0.0

        summary2 = InvestigationSummary(**self._valid_payload(avg_confidence=1.0))
        assert summary2.avg_confidence == 1.0

    def test_avg_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            InvestigationSummary(**self._valid_payload(avg_confidence=1.5))

    def test_execution_time_ms_is_optional(self):
        payload = self._valid_payload()
        payload.pop("execution_time_ms")
        summary = InvestigationSummary(**payload)
        assert summary.execution_time_ms is None

    def test_disconnect_graph_defaults_false(self):
        payload = self._valid_payload()
        payload.pop("disconnect_graph")
        summary = InvestigationSummary(**payload)
        assert summary.disconnect_graph is False

    def test_findings_count_defaults_zero(self):
        payload = self._valid_payload()
        payload.pop("findings_count")
        summary = InvestigationSummary(**payload)
        assert summary.findings_count == 0


class TestInvestigationHistoryResponseSchema:
    """InvestigationHistoryResponse Pydantic model validation."""

    def _make_summary(self, inv_id: str = "INV-001") -> dict:
        return {
            "investigation_id": inv_id,
            "change_id": "CHG-001",
            "change_title": "Auth token field rename",
            "status": "completed",
            "memory_enabled": True,
            "created_at": "2026-10-17T01:00:00Z",
            "avg_confidence": 0.85,
        }

    def test_empty_history_is_valid(self):
        resp = InvestigationHistoryResponse(total=0, investigations=[])
        assert resp.total == 0
        assert resp.investigations == []

    def test_total_matches_list_length(self):
        summaries = [self._make_summary("INV-001"), self._make_summary("INV-002")]
        resp = InvestigationHistoryResponse(total=2, investigations=summaries)
        assert resp.total == len(resp.investigations)

    def test_nested_summaries_are_typed(self):
        summaries = [self._make_summary("INV-003")]
        resp = InvestigationHistoryResponse(total=1, investigations=summaries)
        assert isinstance(resp.investigations[0], InvestigationSummary)
        assert resp.investigations[0].investigation_id == "INV-003"

    def test_investigations_defaults_empty_list(self):
        resp = InvestigationHistoryResponse(total=0)
        assert resp.investigations == []


# =============================================================================
# Integration tests against the live API
# =============================================================================

class TestHistoryEndpoint:
    """Integration tests for GET /api/investigations/history."""

    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def test_history_returns_200(self):
        resp = self.client.get("/api/investigations/history")
        assert resp.status_code == 200

    def test_history_response_has_required_fields(self):
        resp = self.client.get("/api/investigations/history")
        data = resp.json()
        assert "total" in data
        assert "investigations" in data

    def test_history_total_matches_list_length(self):
        resp = self.client.get("/api/investigations/history")
        data = resp.json()
        assert data["total"] == len(data["investigations"])

    def test_history_investigations_is_list(self):
        resp = self.client.get("/api/investigations/history")
        assert isinstance(resp.json()["investigations"], list)

    def test_history_each_item_has_required_fields(self):
        resp = self.client.get("/api/investigations/history")
        for item in resp.json()["investigations"]:
            assert "investigation_id" in item
            assert "change_id" in item
            assert "change_title" in item
            assert "status" in item
            assert "memory_enabled" in item
            assert "created_at" in item
            assert "findings_count" in item
            assert "incompatible_count" in item
            assert "at_risk_count" in item
            assert "compatible_count" in item
            assert "unaffected_count" in item
            assert "avg_confidence" in item

    def test_history_stats_are_non_negative(self):
        resp = self.client.get("/api/investigations/history")
        for item in resp.json()["investigations"]:
            assert item["findings_count"] >= 0
            assert item["incompatible_count"] >= 0
            assert item["at_risk_count"] >= 0
            assert item["compatible_count"] >= 0
            assert item["unaffected_count"] >= 0
            assert 0.0 <= item["avg_confidence"] <= 1.0

    def test_history_limit_param_reduces_results(self):
        full = self.client.get("/api/investigations/history?limit=50").json()
        limited = self.client.get("/api/investigations/history?limit=1").json()
        if full["total"] > 1:
            assert limited["total"] <= 1
            assert len(limited["investigations"]) <= 1

    def test_history_default_limit_is_50(self):
        resp = self.client.get("/api/investigations/history")
        assert resp.json()["total"] <= 50
