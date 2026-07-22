"""CS-SOLVER-003: vendor CI false confidence via skips."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.stabilization.vendor_required import skip_or_fail_vendor, vendor_required


def test_vendor_required_mode_fails_on_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """CONICSHIELD_VENDOR_REQUIRED=1 converts skips into failures."""
    monkeypatch.setenv("CONICSHIELD_VENDOR_REQUIRED", "1")
    assert vendor_required() is True
    with pytest.raises(pytest.fail.Exception, match="CONICSHIELD_VENDOR_REQUIRED"):
        skip_or_fail_vendor("simulated missing Moreau license")


def test_vendor_optional_mode_still_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONICSHIELD_VENDOR_REQUIRED", raising=False)
    assert vendor_required() is False
    with pytest.raises(pytest.skip.Exception, match="simulated"):
        skip_or_fail_vendor("simulated missing Moreau license")


def test_vendor_ci_workflow_sets_vendor_required_env() -> None:
    text = Path(".github/workflows/solver-ci.yml").read_text(encoding="utf-8")
    assert "CONICSHIELD_VENDOR_REQUIRED" in text
    assert 'CONICSHIELD_VENDOR_REQUIRED: "1"' in text or "CONICSHIELD_VENDOR_REQUIRED: 1" in text
    assert "assert_vendor_ci_evidence.py" in text
    assert "vendor_mandatory_native_solves.py" in text
    assert "python -m moreau check" in text
    assert "junitxml" in text


def test_vendor_evidence_gate_rejects_zero_executed(tmp_path: Path) -> None:
    junit = tmp_path / "empty.junit.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="2" skipped="2" failures="0" errors="0">
  <testcase classname="tests.vendor.native.test_native_moreau_projector" name="test_a">
    <skipped message="no moreau"/>
  </testcase>
  <testcase classname="tests.vendor.native.test_native_moreau_projector" name="test_b">
    <skipped message="no license"/>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )
    evidence = tmp_path / "mandatory.json"
    evidence.write_text(
        '{"native_solve_count": 0, "known_feasible_ok": false, '
        '"known_infeasible_or_failure_policy_ok": false}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/assert_vendor_ci_evidence.py",
            "--junit",
            str(junit),
            "--native-evidence",
            str(evidence),
            "--min-executed",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "no vendor test executed" in (proc.stderr or "") or "native solve" in (proc.stderr or "")
