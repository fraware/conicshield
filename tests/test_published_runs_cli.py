from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "conicshield.published_runs.cli", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_list_includes_flagship() -> None:
    proc = _run("list")
    assert proc.returncode == 0
    assert "host-realistic-20260525" in proc.stdout


def test_cli_verify_and_show_flagship() -> None:
    verify = _run("verify", "host-realistic-20260525")
    assert verify.returncode == 0
    assert "OK integrity" in verify.stdout

    show = _run("show", "host-realistic-20260525")
    assert show.returncode == 0
    payload = json.loads(show.stdout)
    assert payload["run_id"] == "host-realistic-20260525"
    assert payload["evidence_tier"] == "vendor_native"
    assert "shielded-native-moreau" in payload["summary_labels"]


def test_cli_current_family() -> None:
    proc = _run("current")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "host-realistic-20260525"
