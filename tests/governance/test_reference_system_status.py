from __future__ import annotations

import json
from pathlib import Path


def _load_status_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "generate_reference_system_status.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("generate_reference_system_status", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, root


def test_reference_system_status_builds() -> None:
    mod, root = _load_status_module()
    payload = mod.build_reference_system_status(repo_root=root)
    assert payload["schema_version"] == "conicshield_reference_system_status/v1"
    assert payload["flagship_run_id"] == "host-realistic-20260525"
    assert payload["reference_authority_aligned"] is True
    assert payload["full_cycle_refresh_count"] >= 1
    assert payload["full_refresh_cadence_ok"] is True
    assert payload["batch_public_narrative"] == "viability_only"
    assert payload["cadence_policy_ok"] is True
    community = payload.get("community_dataset") or {}
    assert community.get("api_module") == "conicshield.published_runs"
    assert community.get("published_run_count", 0) >= 1
    assert community.get("onboarding_doc") == "docs/COMMUNITY_LAYER.md"
    assert "reference-authority" in (payload.get("ci_merge_checks") or [])


def test_committed_reference_system_status_check() -> None:
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "reports" / "reference_system_status.json"
    assert path.is_file(), "run: python scripts/generate_reference_system_status.py"
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_reference_system_status.py"), "--check"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("batch_story")
