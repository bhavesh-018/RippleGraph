"""
Tests for RippleGraph Model Context Protocol (MCP) Server.

Covers:
  - Tool registration and schemas
  - Tool execution: find_direct_consumers, check_contract_compatibility,
    traverse_downstream_dependencies, get_relevant_incidents
  - Tool safety: query_graph_cypher write-operation rejection
  - Resources: schema and services
  - Prompts: rehearse-change
"""

import json
from unittest.mock import patch, MagicMock
import pytest

import mcp_server


class TestMCPServerTools:
    """Test tools exposed on MCPServer."""

    def test_server_metadata(self):
        assert mcp_server.server.name == "RippleGraph"

    def test_find_direct_consumers_tool(self):
        result_str = mcp_server.find_direct_consumers("auth-token-api")
        data = json.loads(result_str)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "service_id" in data[0]

    def test_check_contract_compatibility_tool(self):
        result_str = mcp_server.check_contract_compatibility("cv-auth-v2")
        data = json.loads(result_str)
        assert "proposed_contract_id" in data
        assert data["proposed_contract_id"] == "cv-auth-v2"
        assert "total_consumers_checked" in data

    def test_traverse_downstream_dependencies_tool(self):
        result_str = mcp_server.traverse_downstream_dependencies("auth-service", max_depth=2)
        data = json.loads(result_str)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "min_hop_distance" in data[0]

    def test_get_relevant_incidents_tool(self):
        result_str = mcp_server.get_relevant_incidents(
            service_ids=["auth-service"],
            active_claim_types=["claims.jwt.sub"],
        )
        data = json.loads(result_str)
        assert isinstance(data, list)

    def test_query_graph_cypher_read_only(self):
        result_str = mcp_server.query_graph_cypher("MATCH (s:Service) RETURN s.name LIMIT 1")
        data = json.loads(result_str)
        assert "records" in data
        assert "columns" in data

    def test_query_graph_cypher_rejects_writes(self):
        result_str = mcp_server.query_graph_cypher("CREATE (s:Service {id: 'bad'})")
        data = json.loads(result_str)
        assert "error" in data
        assert "Write operations are not allowed" in data["error"]

    def test_ask_graph_tool_mocked(self):
        with patch("mcp_server.nl_to_cypher", return_value="MATCH (s:Service) RETURN s.name LIMIT 1"):
            result_str = mcp_graph = mcp_server.ask_graph("Which services are in the graph?")
            data = json.loads(result_str)
            assert "records" in data
            assert data["generated_cypher"] == "MATCH (s:Service) RETURN s.name LIMIT 1"


class TestMCPServerResourcesAndPrompts:
    """Test resources and prompts exposed on MCPServer."""

    def test_graph_schema_resource(self):
        schema = mcp_server.get_graph_schema()
        assert "RippleGraph Graph Schema" in schema
        assert "Service" in schema
        assert "ContractVersion" in schema

    def test_graph_services_resource(self):
        services_str = mcp_server.get_graph_services()
        services = json.loads(services_str)
        assert isinstance(services, list)
        assert len(services) > 0
        assert any(s["id"] == "auth-service" for s in services)

    def test_rehearse_change_prompt(self):
        prompt = mcp_server.rehearse_change_prompt("CHG-001")
        assert "CHG-001" in prompt
        assert "find_direct_consumers" in prompt
        assert "traverse_downstream_dependencies" in prompt
