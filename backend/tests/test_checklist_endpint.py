"""
RippleGraph - Tests for Feature 5: Mitigation Checklist Export
GET /api/investigations/{investigation_id}/checklist

Covers:
  - 200 response with correct content-type (text/markdown)
  - Content-Disposition header present with correct filename format
  - Response body contains required Markdown sections
  - Summary table is present and has correct columns
  - At least one finding section present for CHG-001 investigation
  - BREAKING services appear in checklist with correct markers
  - Missing claims section present for incompatible findings
  - Historical Evidence section present when incidents exist
  - Playbook mitigation steps included when available
  - Next Steps section present at the end
  - 404 returned for non-existent investigation_id
  - 404 detail message mentions the missing ID
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from orchestrator.pipeline import run_pipeline
from main import app


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Ensure FalkorDB is seeded with baseline data before running checklist tests."""
    seed(skip_verification=True)


@pytest.fixture(scope="session")
def investigation_result():
    """Run CHG-001 pipeline once and return the result (memory OFF for clean baseline)."""
    return run_pipeline(change_id="CHG-001", memory_enabled=False)


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def checklist_response(investigation_result):
    """
    Fetch the checklist response once for the session and return the raw text.
    Uses a separate client context to avoid fixture scope conflicts.
    """
    with TestClient(app) as c:
        inv_id = investigation_result["investigation_id"]
        resp = c.get(f"/api/investigations/{inv_id}/checklist")
        return resp


# ---------------------------------------------------------------------------
# Point 1: HTTP response metadata
# ---------------------------------------------------------------------------

def test_checklist_returns_200(checklist_response):
    """GET checklist must return 200 for a valid investigation."""
    assert checklist_response.status_code == 200, (
        f"Expected 200, got {checklist_response.status_code}: {checklist_response.text[:200]}"
    )


def test_checklist_content_type_is_markdown(checklist_response):
    """Content-Type must be text/markdown."""
    assert "text/markdown" in checklist_response.headers.get("content-type", ""), (
        f"Expected text/markdown, got {checklist_response.headers.get('content-type')}"
    )


def test_checklist_content_disposition_header_present(checklist_response):
    """Content-Disposition must be present for file download."""
    disposition = checklist_response.headers.get("content-disposition", "")
    assert "attachment" in disposition, (
        f"Expected 'attachment' in Content-Disposition, got: {disposition}"
    )


def test_checklist_filename_contains_investigation_id(checklist_response, investigation_result):
    """Content-Disposition filename must contain the investigation ID."""
    disposition = checklist_response.headers.get("content-disposition", "")
    inv_id = investigation_result["investigation_id"]
    assert inv_id in disposition, (
        f"Expected investigation ID '{inv_id}' in Content-Disposition: {disposition}"
    )


def test_checklist_filename_has_md_extension(checklist_response):
    """Content-Disposition filename must end with .md."""
    disposition = checklist_response.headers.get("content-disposition", "")
    assert ".md" in disposition, (
        f"Expected .md in Content-Disposition: {disposition}"
    )


# ---------------------------------------------------------------------------
# Point 2: Markdown structure — required sections
# ---------------------------------------------------------------------------

def test_checklist_has_main_title(checklist_response):
    """Checklist must start with the RippleGraph title heading."""
    body = checklist_response.text
    assert "# 🛡 RippleGraph" in body, "Missing main title heading"


def test_checklist_has_investigation_metadata(checklist_response, investigation_result):
    """Checklist must include investigation ID and change metadata."""
    body = checklist_response.text
    inv_id = investigation_result["investigation_id"]
    assert inv_id in body, f"Investigation ID '{inv_id}' not found in checklist"
    assert "CHG-001" in body, "Change ID 'CHG-001' not found in checklist"


def test_checklist_has_summary_section(checklist_response):
    """Checklist must have a '## Summary' section."""
    body = checklist_response.text
    assert "## Summary" in body, "Missing '## Summary' section"


def test_checklist_summary_has_table_headers(checklist_response):
    """Summary table must have Service, Status, Confidence, Hop columns."""
    body = checklist_response.text
    assert "| Service |" in body, "Missing 'Service' column in summary table"
    assert "| Status |" in body or "Status" in body, "Missing 'Status' column"
    assert "Confidence" in body, "Missing 'Confidence' column"
    assert "Hop" in body, "Missing 'Hop' column"


def test_checklist_has_findings_section(checklist_response):
    """Checklist must have a '## Findings & Action Items' section."""
    body = checklist_response.text
    assert "## Findings & Action Items" in body, "Missing findings section"


def test_checklist_has_next_steps_section(checklist_response):
    """Checklist must have a '## Next Steps' section at the end."""
    body = checklist_response.text
    assert "## Next Steps" in body, "Missing Next Steps section"


def test_checklist_next_steps_mentions_blast_radius(checklist_response):
    """Next Steps must reference re-running RippleGraph."""
    body = checklist_response.text
    assert "RippleGraph" in body.split("## Next Steps")[-1], (
        "Next Steps section does not mention RippleGraph"
    )


# ---------------------------------------------------------------------------
# Point 3: Finding content — incompatible services
# ---------------------------------------------------------------------------

def test_checklist_contains_breaking_emoji(checklist_response):
    """Checklist must contain 🔴 emoji for BREAKING/INCOMPATIBLE services."""
    body = checklist_response.text
    assert "🔴" in body, "No breaking (🔴) services found in checklist — expected for CHG-001"


def test_checklist_contains_incompatible_status(checklist_response):
    """Checklist must contain INCOMPATIBLE status label."""
    body = checklist_response.text
    assert "INCOMPATIBLE" in body, "INCOMPATIBLE status not found in checklist"


def test_checklist_contains_agent_confidence(checklist_response):
    """Each finding section must include 'Agent Confidence' metric."""
    body = checklist_response.text
    assert "Agent Confidence" in body, "Missing 'Agent Confidence' in finding sections"


def test_checklist_contains_missing_claims(checklist_response):
    """Checklist must contain missing claims checkboxes for incompatible findings."""
    body = checklist_response.text
    assert "Missing Claims" in body, "Missing claims section not found in checklist"
    assert "- [ ]" in body, "No checklist checkboxes (- [ ]) found for missing claims"


def test_checklist_contains_historical_evidence(checklist_response):
    """Checklist must contain 'Historical Evidence' section with incident references."""
    body = checklist_response.text
    assert "Historical Evidence" in body, "Missing 'Historical Evidence' section"


def test_checklist_contains_playbook_mitigation(checklist_response):
    """Checklist must contain ✅ **Playbook:** mitigation entries (bold markdown format)."""
    body = checklist_response.text
    assert "✅ **Playbook:**" in body, "No playbook mitigation entries found"


def test_checklist_contains_audit_justification(checklist_response):
    """Checklist must include 'Audit Justification' blockquotes."""
    body = checklist_response.text
    assert "Audit Justification" in body, "Missing 'Audit Justification' section"


def test_checklist_contains_recommended_contract(checklist_response):
    """Checklist must include 'Recommended Migration Contract' for incompatible findings."""
    body = checklist_response.text
    assert "Recommended Migration Contract" in body, "Missing recommended contract field"


def test_checklist_generated_footer_present(checklist_response):
    """Checklist must end with the RippleGraph agent footer."""
    body = checklist_response.text
    assert "_Generated by RippleGraph" in body, "Missing generator footer"


# ---------------------------------------------------------------------------
# Point 4: 404 for non-existent investigation
# ---------------------------------------------------------------------------

def test_checklist_404_for_nonexistent_investigation(client):
    """GET checklist for a bogus investigation_id must return 404."""
    response = client.get("/api/investigations/INV-DOES-NOT-EXIST/checklist")
    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}"
    )


def test_checklist_404_detail_message(client):
    """404 response must include a descriptive detail message with the missing ID."""
    response = client.get("/api/investigations/INV-DOES-NOT-EXIST/checklist")
    data = response.json()
    assert "detail" in data, "404 response must have a 'detail' key"
    assert "INV-DOES-NOT-EXIST" in data["detail"], (
        f"detail message should mention the missing ID: {data['detail']}"
    )
