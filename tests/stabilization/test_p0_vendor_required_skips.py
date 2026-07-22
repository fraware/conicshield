"""CS-SOLVER-003: vendor CI false confidence via skips."""

from __future__ import annotations

import pytest

from tests.stabilization.vendor_required import skip_or_fail_vendor, vendor_required


def test_vendor_required_mode_fails_on_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scaffolding proof: CONICSHIELD_VENDOR_REQUIRED=1 converts skips into failures."""
    monkeypatch.setenv("CONICSHIELD_VENDOR_REQUIRED", "1")
    assert vendor_required() is True
    with pytest.raises(pytest.fail.Exception, match="CONICSHIELD_VENDOR_REQUIRED"):
        skip_or_fail_vendor("simulated missing Moreau license")


def test_vendor_optional_mode_still_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONICSHIELD_VENDOR_REQUIRED", raising=False)
    assert vendor_required() is False
    with pytest.raises(pytest.skip.Exception, match="simulated"):
        skip_or_fail_vendor("simulated missing Moreau license")


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-003: vendor CI workflow does not set CONICSHIELD_VENDOR_REQUIRED=1 yet (S7)",
)
def test_vendor_ci_workflow_sets_vendor_required_env() -> None:
    from pathlib import Path

    text = Path(".github/workflows/solver-ci.yml").read_text(encoding="utf-8")
    assert "CONICSHIELD_VENDOR_REQUIRED" in text
    assert "CONICSHIELD_VENDOR_REQUIRED: 1" in text or 'CONICSHIELD_VENDOR_REQUIRED: "1"' in text
