"""
Tests for Feature 1: Live Graph Traversal Animation (SSE Streaming)

Verifies:
  1. SSEMessage.to_sse_format() produces valid W3C text/event-stream output.
  2. stream_investigation() yields the mandatory event sequence (STAGE_CHANGED first,
     COMPLETE last) for the connected happy path.
  3. stream_investigation(disconnect_graph=True) yields exactly STAGE_CHANGED +
     COMPLETE (Proof Mode path — no graph traversal events).
  4. GET /api/investigations/stream responds with media_type=text/event-stream and
     delivers at least one SSE line containing "event:".
  5. Every data line emitted is valid JSON parseable back to a dict.
"""

import json
import pytest
import asyncio

from fastapi.testclient import TestClient

from main import app
from schemas.sse import SSEMessage, SSEEventType, StageChangedPayload, CompletePayload
from orchestrator.stream import stream_investigation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_sse_lines(raw_text: str) -> list:
    """Parse raw SSE text into a list of {event, data} dicts."""
    messages = []
    current = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = json.loads(line[len("data:"):].strip())
        elif line == "" and current:
            messages.append(current)
            current = {}
    if current:
        messages.append(current)
    return messages


async def _collect_generator(gen) -> list:
    """Collect all chunks from an async generator into a list of strings."""
    chunks = []
    async for chunk in gen:
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Unit: SSEMessage serialisation
# ---------------------------------------------------------------------------

class TestSSEMessageFormat:
    def test_to_sse_format_contains_event_line(self):
        msg = SSEMessage(
            event=SSEEventType.STAGE_CHANGED,
            data=StageChangedPayload(
                stage_id="investigator",
                stage_name="Stage 1: Investigator",
                description="Discovering direct consumers.",
            ).model_dump(),
        )
        text = msg.to_sse_format()
        assert text.startswith("event: STAGE_CHANGED\n")

    def test_to_sse_format_has_data_line_with_valid_json(self):
        payload = CompletePayload(
            investigation_id="INV-TEST001",
            change_id="CHG-001",
            summary={"incompatible": 1, "potential_downstream": 0, "compatible": 0, "unaffected": 0},
            recommended_contract="cv-auth-v1-extended",
            execution_time_ms=123.45,
        )
        msg = SSEMessage(event=SSEEventType.COMPLETE, data=payload.model_dump())
        text = msg.to_sse_format()

        lines = text.strip().split("\n")
        data_line = next(l for l in lines if l.startswith("data:"))
        parsed = json.loads(data_line[len("data:"):].strip())
        assert parsed["investigation_id"] == "INV-TEST001"
        assert parsed["summary"]["incompatible"] == 1

    def test_to_sse_format_ends_with_double_newline(self):
        msg = SSEMessage(
            event=SSEEventType.CONSUMERS_FOUND,
            data={"api_id": "auth-token-api", "consumer_service_ids": []},
        )
        assert msg.to_sse_format().endswith("\n\n")


# ---------------------------------------------------------------------------
# Unit: stream_investigation generator — Proof Mode (disconnect_graph=True)
# ---------------------------------------------------------------------------

class TestStreamGeneratorProofMode:
    def test_proof_mode_yields_exactly_two_events(self):
        """Proof Mode must only emit STAGE_CHANGED + COMPLETE — no graph traversal."""
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    disconnect_graph=True,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        event_types = [m["event"] for m in messages]

        assert len(messages) == 2
        assert event_types[0] == SSEEventType.STAGE_CHANGED.value
        assert event_types[-1] == SSEEventType.COMPLETE.value

    def test_proof_mode_complete_has_zero_incompatible(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    disconnect_graph=True,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        complete_msg = next(m for m in messages if m["event"] == SSEEventType.COMPLETE.value)

        assert complete_msg["data"]["summary"]["incompatible"] == 0
        assert complete_msg["data"]["change_id"] == "CHG-001"


# ---------------------------------------------------------------------------
# Unit: stream_investigation generator — Connected Happy Path
# ---------------------------------------------------------------------------

class TestStreamGeneratorConnectedPath:
    def test_connected_first_event_is_stage_changed(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    memory_enabled=False,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        assert messages[0]["event"] == SSEEventType.STAGE_CHANGED.value

    def test_connected_last_event_is_complete(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    memory_enabled=False,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        assert messages[-1]["event"] == SSEEventType.COMPLETE.value

    def test_connected_emits_consumers_found_event(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    memory_enabled=False,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        event_types = [m["event"] for m in messages]
        assert SSEEventType.CONSUMERS_FOUND.value in event_types

    def test_connected_all_data_lines_are_valid_json(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    memory_enabled=False,
                    pace_delay_s=0.0,
                )
            )
        )
        raw = "".join(chunks)
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                parsed = json.loads(payload)
                assert isinstance(parsed, dict)

    def test_connected_complete_has_investigation_id(self):
        chunks = asyncio.get_event_loop().run_until_complete(
            _collect_generator(
                stream_investigation(
                    change_id="CHG-001",
                    memory_enabled=False,
                    pace_delay_s=0.0,
                )
            )
        )
        messages = _collect_sse_lines("".join(chunks))
        complete = next(m for m in messages if m["event"] == SSEEventType.COMPLETE.value)
        assert complete["data"]["investigation_id"].startswith("INV-")
        assert complete["data"]["execution_time_ms"] > 0


# ---------------------------------------------------------------------------
# Integration: GET /api/investigations/stream via TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestStreamEndpoint:
    def test_stream_endpoint_returns_200(self, client):
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-001", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        assert response.status_code == 200

    def test_stream_endpoint_content_type_is_event_stream(self, client):
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-001", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_endpoint_body_contains_event_lines(self, client):
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-001", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        assert "event:" in response.text

    def test_stream_endpoint_proof_mode_complete_event_present(self, client):
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-001", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        messages = _collect_sse_lines(response.text)
        event_types = [m["event"] for m in messages]
        assert SSEEventType.COMPLETE.value in event_types

    def test_stream_endpoint_cache_control_header(self, client):
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-001", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        assert response.headers.get("cache-control") == "no-cache"

    def test_stream_endpoint_unknown_change_falls_back_to_chg001(self, client):
        """Unknown change_id must fall back to CHG-001 without error."""
        response = client.get(
            "/api/investigations/stream",
            params={"change_id": "CHG-UNKNOWN", "disconnect_graph": True, "pace_delay_s": 0.0},
        )
        assert response.status_code == 200
        messages = _collect_sse_lines(response.text)
        complete = next((m for m in messages if m["event"] == SSEEventType.COMPLETE.value), None)
        assert complete is not None
        assert complete["data"]["change_id"] == "CHG-001"
