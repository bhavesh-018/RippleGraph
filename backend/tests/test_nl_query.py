"""
Tests for the Natural Language Graph Query feature.

Covers:
  - _is_safe_cypher: read-only safety validation
  - _clean_cypher: markdown fence stripping
  - nl_to_cypher: Gemini integration (mocked to avoid real API calls)
  - GET /api/graph/nl-query: endpoint integration tests (mocked Gemini)
"""

import pytest
from unittest.mock import patch, MagicMock


# =============================================================================
# Unit tests: _is_safe_cypher
# =============================================================================

class TestIsSafeCypher:
    """Read-only safety guard for Gemini-generated Cypher."""

    from orchestrator.gemini import _is_safe_cypher

    def test_simple_match_is_safe(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MATCH (s:Service) RETURN s.name") is True

    def test_optional_match_is_safe(self):
        from orchestrator.gemini import _is_safe_cypher
        q = "MATCH (s:Service) OPTIONAL MATCH (s)-[:DEPENDS_ON]->(d) RETURN s.name, d.name"
        assert _is_safe_cypher(q) is True

    def test_order_by_is_safe(self):
        from orchestrator.gemini import _is_safe_cypher
        q = "MATCH (inv:Investigation) RETURN inv.id ORDER BY inv.created_at DESC LIMIT 10"
        assert _is_safe_cypher(q) is True

    def test_created_at_column_is_safe(self):
        """created_at contains 'CREATE' as substring but is not a write op."""
        from orchestrator.gemini import _is_safe_cypher
        q = "MATCH (inv:Investigation) RETURN inv.created_at"
        assert _is_safe_cypher(q) is True

    def test_create_node_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("CREATE (s:Service {id: 'x'})") is False

    def test_delete_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MATCH (s) DELETE s") is False

    def test_detach_delete_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MATCH (s) DETACH DELETE s") is False

    def test_set_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MATCH (s) SET s.name = 'x'") is False

    def test_merge_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MERGE (s:Service {id: 'x'})") is False

    def test_remove_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("MATCH (s) REMOVE s.name") is False

    def test_drop_is_rejected(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("DROP INDEX ON :Service(id)") is False

    def test_case_insensitive_rejection(self):
        from orchestrator.gemini import _is_safe_cypher
        assert _is_safe_cypher("match (s) delete s") is False
        assert _is_safe_cypher("match (s) set s.x = 1") is False


# =============================================================================
# Unit tests: _clean_cypher
# =============================================================================

class TestCleanCypher:
    """Markdown fence stripping from Gemini output."""

    def test_plain_cypher_unchanged(self):
        from orchestrator.gemini import _clean_cypher
        q = "MATCH (s:Service) RETURN s.name"
        assert _clean_cypher(q) == q

    def test_strips_cypher_fence(self):
        from orchestrator.gemini import _clean_cypher
        raw = "```cypher\nMATCH (s:Service) RETURN s.name\n```"
        assert _clean_cypher(raw) == "MATCH (s:Service) RETURN s.name"

    def test_strips_plain_fence(self):
        from orchestrator.gemini import _clean_cypher
        raw = "```\nMATCH (s:Service) RETURN s.name\n```"
        assert _clean_cypher(raw) == "MATCH (s:Service) RETURN s.name"

    def test_strips_leading_trailing_whitespace(self):
        from orchestrator.gemini import _clean_cypher
        raw = "  MATCH (s:Service) RETURN s.name  "
        assert _clean_cypher(raw) == "MATCH (s:Service) RETURN s.name"

    def test_empty_string_returns_empty(self):
        from orchestrator.gemini import _clean_cypher
        assert _clean_cypher("") == ""
        assert _clean_cypher("```cypher\n\n```") == ""


# =============================================================================
# Unit tests: nl_to_cypher (Gemini mocked)
# =============================================================================

class TestNlToCypher:
    """nl_to_cypher integration — Gemini is mocked to avoid real API calls."""

    @pytest.fixture(autouse=True)
    def mock_gemini_key(self, monkeypatch):
        from orchestrator import gemini
        monkeypatch.setattr(gemini.settings, "gemini_api_key", "test-api-key")

    def _make_mock_response(self, text: str):
        mock_resp = MagicMock()
        mock_resp.text = text
        return mock_resp

    def test_returns_clean_cypher(self):
        from orchestrator.gemini import nl_to_cypher
        expected = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        mock_resp = self._make_mock_response(expected)

        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.return_value = mock_resp
            result = nl_to_cypher("List all services")

        assert result == expected

    def test_strips_markdown_fences(self):
        from orchestrator.gemini import nl_to_cypher
        raw = "```cypher\nMATCH (s:Service) RETURN s.name LIMIT 20\n```"
        mock_resp = self._make_mock_response(raw)

        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.return_value = mock_resp
            result = nl_to_cypher("List all services")

        assert "```" not in result
        assert "MATCH" in result

    def test_raises_on_missing_api_key(self):
        from orchestrator.gemini import nl_to_cypher
        with patch("orchestrator.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            mock_settings.gemini_model = "gemini-1.5-flash"
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                nl_to_cypher("List all services")

    def test_raises_on_empty_response(self):
        from orchestrator.gemini import nl_to_cypher
        mock_resp = self._make_mock_response("")

        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.return_value = mock_resp
            with pytest.raises(ValueError, match="empty"):
                nl_to_cypher("List all services")

    def test_raises_on_write_op_in_response(self):
        from orchestrator.gemini import nl_to_cypher
        mock_resp = self._make_mock_response("CREATE (s:Service {id: 'hacked'})")

        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.return_value = mock_resp
            with pytest.raises(ValueError, match="write operations"):
                nl_to_cypher("Create a new service")

    def test_raises_on_api_error(self):
        from orchestrator.gemini import nl_to_cypher
        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.side_effect = Exception("network error")
            with pytest.raises(RuntimeError, match="Gemini API error"):
                nl_to_cypher("List all services")

    def test_accepts_extra_context(self):
        from orchestrator.gemini import nl_to_cypher
        expected = "MATCH (s:Service) RETURN s.name LIMIT 20"
        mock_resp = self._make_mock_response(expected)

        with patch("orchestrator.gemini.genai.Client") as MockClient:
            MockClient.return_value.models.generate_content.return_value = mock_resp
            result = nl_to_cypher("List all services", extra_context="CHG-001")

        assert result == expected


# =============================================================================
# Integration tests: GET /api/graph/nl-query
# =============================================================================

class TestNlQueryEndpoint:
    """Integration tests for the FastAPI endpoint (Gemini mocked)."""

    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        self.client = TestClient(app)

    def _mock_cypher(self, cypher: str):
        """Context manager that patches nl_to_cypher to return a fixed Cypher."""
        return patch("api.nl_query.nl_to_cypher", return_value=cypher)

    def test_missing_question_returns_422(self):
        resp = self.client.get("/api/graph/nl-query")
        assert resp.status_code == 422

    def test_question_too_short_returns_422(self):
        resp = self.client.get("/api/graph/nl-query?question=hi")
        assert resp.status_code == 422

    def test_valid_question_returns_200(self):
        cypher = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        assert resp.status_code == 200

    def test_response_contains_required_fields(self):
        cypher = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        data = resp.json()
        assert "question" in data
        assert "cypher" in data
        assert "columns" in data
        assert "records" in data
        assert "total" in data

    def test_response_echoes_question(self):
        cypher = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        assert resp.json()["question"] == "List all services"

    def test_response_contains_generated_cypher(self):
        cypher = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        assert resp.json()["cypher"] == cypher

    def test_total_matches_records_length(self):
        cypher = "MATCH (s:Service) RETURN s.name AS service_name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        data = resp.json()
        assert data["total"] == len(data["records"])

    def test_gemini_value_error_returns_400(self):
        with patch("api.nl_query.nl_to_cypher", side_effect=ValueError("GEMINI_API_KEY is not set")):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        assert resp.status_code == 400

    def test_gemini_runtime_error_returns_502(self):
        with patch("api.nl_query.nl_to_cypher", side_effect=RuntimeError("Gemini API error: network")):
            resp = self.client.get("/api/graph/nl-query?question=List all services")
        assert resp.status_code == 502

    def test_context_param_accepted(self):
        cypher = "MATCH (s:Service) RETURN s.name LIMIT 20"
        with self._mock_cypher(cypher):
            resp = self.client.get("/api/graph/nl-query?question=List all services&context=CHG-001")
        assert resp.status_code == 200
