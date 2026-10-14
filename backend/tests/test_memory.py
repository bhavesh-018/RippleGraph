"""
RippleGraph - Tests for Stage 2 Memory Engine (C23 + C24)

Covers:
  - Prior finding retrieval from FalkorDB after Investigation A is persisted
  - Temporal decay reduces confidence for older findings
  - Hop depth penalty reduces confidence proportionally
  - Reaffirmation boosts confidence to >= 0.95 for repeated risks
  - Memory disabled run produces valid findings without prior context
  - apply_memory_to_findings merges correctly
  - _parse_days_old handles valid, invalid, and missing timestamps
  - DECAY_FLOOR is respected
"""

import sys
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.seed import seed
from orchestrator.pipeline import run_pipeline
from orchestrator.memory import (
    DECAY_LAMBDA,
    DECAY_FLOOR,
    REAFFIRM_BOOST,
    _apply_decay,
    _parse_days_old,
    apply_memory_to_findings,
    get_prior_findings_with_decay,
)


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded_and_investigation_a():
    """Seed FalkorDB and run Investigation A so prior findings exist."""
    seed(skip_verification=True)
    run_pipeline(change_id="CHG-001", memory_enabled=False)


# ---------------------------------------------------------------------------
# C23: Prior finding retrieval
# ---------------------------------------------------------------------------

def test_get_prior_findings_returns_list():
    """get_prior_findings_with_decay must return a list."""
    result = get_prior_findings_with_decay(
        service_ids=["payment-service", "checkout-service"],
        current_investigation_id="INV-DOES-NOT-EXIST",
    )
    assert isinstance(result, list)


def test_get_prior_findings_contains_payment_service():
    """payment-service must appear in prior findings after Investigation A."""
    result = get_prior_findings_with_decay(
        service_ids=["payment-service"],
        current_investigation_id="INV-DOES-NOT-EXIST",
    )
    service_ids = [f["service_id"] for f in result]
    assert "payment-service" in service_ids, (
        f"payment-service not found in prior findings: {service_ids}"
    )


def test_get_prior_findings_has_decayed_confidence():
    """Every returned finding must have a decayed_confidence field."""
    result = get_prior_findings_with_decay(
        service_ids=["payment-service"],
        current_investigation_id="INV-DOES-NOT-EXIST",
    )
    for f in result:
        assert "decayed_confidence" in f, f"Missing decayed_confidence in {f['id']}"
        assert 0.0 <= f["decayed_confidence"] <= 1.0


def test_get_prior_findings_has_days_old():
    """Every returned finding must have a days_old field >= 0."""
    result = get_prior_findings_with_decay(
        service_ids=["payment-service"],
        current_investigation_id="INV-DOES-NOT-EXIST",
    )
    for f in result:
        assert "days_old" in f
        assert f["days_old"] >= 0.0


def test_get_prior_findings_empty_service_ids():
    """Empty service_ids list must return empty list without error."""
    result = get_prior_findings_with_decay(
        service_ids=[],
        current_investigation_id="INV-DOES-NOT-EXIST",
    )
    assert result == []


def test_get_prior_findings_excludes_current_investigation():
    """Prior findings must not include findings from the current investigation."""
    inv_a = run_pipeline(change_id="CHG-001", memory_enabled=False)
    current_id = inv_a["investigation_id"]

    result = get_prior_findings_with_decay(
        service_ids=["payment-service"],
        current_investigation_id=current_id,
    )
    for f in result:
        assert f["investigation_id"] != current_id, (
            f"Current investigation's own finding leaked into prior results: {f}"
        )


# ---------------------------------------------------------------------------
# C24: Temporal decay math
# ---------------------------------------------------------------------------

def test_apply_decay_fresh_finding_high_confidence():
    """A finding created just now with hop=0 should retain near-full confidence."""
    now = datetime.now(timezone.utc)
    finding = {
        "id": "FND-TEST",
        "investigation_id": "INV-TEST",
        "service_id": "payment-service",
        "service_name": "Payment Service",
        "status": "incompatible",
        "confidence": 0.95,
        "hop_depth": 0,
        "created_at": now.isoformat(),
    }
    result = _apply_decay(finding, now)
    # exp(-0.05 * 0) * (1 - 0.1 * 0) = 1.0 * 1.0 = 1.0
    assert result["decayed_confidence"] >= 0.90, (
        f"Fresh finding should retain high confidence, got {result['decayed_confidence']}"
    )


def test_apply_decay_14_day_old_finding():
    """A 14-day-old finding should lose roughly half its confidence (lambda=0.05)."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(days=14)
    finding = {
        "id": "FND-TEST",
        "investigation_id": "INV-TEST",
        "service_id": "checkout-service",
        "service_name": "Checkout Service",
        "status": "potential_downstream",
        "confidence": 1.0,
        "hop_depth": 0,
        "created_at": created.isoformat(),
    }
    result = _apply_decay(finding, now)
    expected = math.exp(-DECAY_LAMBDA * 14)
    assert abs(result["decayed_confidence"] - expected) < 0.02, (
        f"Expected ~{expected:.3f}, got {result['decayed_confidence']}"
    )


def test_apply_decay_hop_depth_penalty():
    """hop_depth=3 must reduce confidence by 30% on top of time decay."""
    now = datetime.now(timezone.utc)
    finding = {
        "id": "FND-TEST",
        "investigation_id": "INV-TEST",
        "service_id": "order-service",
        "service_name": "Order Service",
        "status": "potential_downstream",
        "confidence": 1.0,
        "hop_depth": 3,
        "created_at": now.isoformat(),
    }
    result = _apply_decay(finding, now)
    # exp(-0.05 * 0) * (1 - 0.1 * 3) = 1.0 * 0.7 = 0.70
    assert abs(result["decayed_confidence"] - 0.70) < 0.02, (
        f"Expected ~0.70 with hop_depth=3, got {result['decayed_confidence']}"
    )


def test_apply_decay_floor_respected():
    """Extremely old findings must not drop below DECAY_FLOOR."""
    now = datetime.now(timezone.utc)
    very_old = now - timedelta(days=365)
    finding = {
        "id": "FND-TEST",
        "investigation_id": "INV-TEST",
        "service_id": "analytics-service",
        "service_name": "Analytics Service",
        "status": "potential_downstream",
        "confidence": 0.50,
        "hop_depth": 4,
        "created_at": very_old.isoformat(),
    }
    result = _apply_decay(finding, now)
    assert result["decayed_confidence"] >= DECAY_FLOOR, (
        f"Decay floor {DECAY_FLOOR} violated, got {result['decayed_confidence']}"
    )


def test_apply_decay_confidence_never_exceeds_one():
    """Decayed confidence must never exceed 1.0."""
    now = datetime.now(timezone.utc)
    finding = {
        "id": "FND-TEST",
        "investigation_id": "INV-TEST",
        "service_id": "payment-service",
        "service_name": "Payment Service",
        "status": "incompatible",
        "confidence": 1.0,
        "hop_depth": 0,
        "created_at": now.isoformat(),
    }
    result = _apply_decay(finding, now)
    assert result["decayed_confidence"] <= 1.0


def test_parse_days_old_valid_iso():
    """_parse_days_old must return correct days for a known timestamp."""
    now = datetime.now(timezone.utc)
    five_days_ago = now - timedelta(days=5)
    days = _parse_days_old(five_days_ago.isoformat(), now)
    assert abs(days - 5.0) < 0.01


def test_parse_days_old_invalid_string():
    """_parse_days_old must return 0.0 for unparseable strings."""
    now = datetime.now(timezone.utc)
    result = _parse_days_old("not-a-date", now)
    assert result == 0.0


def test_parse_days_old_empty_string():
    """_parse_days_old must return 0.0 for empty string."""
    now = datetime.now(timezone.utc)
    result = _parse_days_old("", now)
    assert result == 0.0


# ---------------------------------------------------------------------------
# C24: apply_memory_to_findings reaffirmation logic
# ---------------------------------------------------------------------------

def test_apply_memory_reaffirms_same_status():
    """Same status prior finding must boost current confidence to >= REAFFIRM_BOOST."""
    current_findings = [
        {
            "id": "FND-NEW",
            "service_id": "payment-service",
            "status": "incompatible",
            "confidence": 0.95,
            "reasons": ["Direct incompatibility."],
        }
    ]
    prior_findings = [
        {
            "service_id": "payment-service",
            "investigation_id": "INV-OLD",
            "status": "incompatible",
            "decayed_confidence": 0.80,
            "reaffirmed": False,
        }
    ]
    result = apply_memory_to_findings(current_findings, prior_findings)
    assert result[0]["confidence"] >= REAFFIRM_BOOST, (
        f"Expected confidence >= {REAFFIRM_BOOST}, got {result[0]['confidence']}"
    )


def test_apply_memory_different_status_no_boost():
    """Different status must add context reason but NOT boost confidence."""
    current_findings = [
        {
            "id": "FND-NEW",
            "service_id": "user-service",
            "status": "compatible",
            "confidence": 0.85,
            "reasons": ["All claims satisfied."],
        }
    ]
    prior_findings = [
        {
            "service_id": "user-service",
            "investigation_id": "INV-OLD",
            "status": "incompatible",
            "decayed_confidence": 0.70,
            "reaffirmed": False,
        }
    ]
    result = apply_memory_to_findings(current_findings, prior_findings)
    assert result[0]["confidence"] == 0.85, (
        "Confidence must not change when status diverges from prior finding."
    )
    # But a context reason must be appended
    assert len(result[0]["reasons"]) > 1


def test_apply_memory_no_prior_leaves_findings_unchanged():
    """If no prior findings exist for a service, the finding must be unchanged."""
    current_findings = [
        {
            "id": "FND-NEW",
            "service_id": "inventory-service",
            "status": "unaffected",
            "confidence": 1.0,
            "reasons": ["No dependency path found."],
        }
    ]
    result = apply_memory_to_findings(current_findings, [])
    assert result[0]["confidence"] == 1.0
    assert len(result[0]["reasons"]) == 1
