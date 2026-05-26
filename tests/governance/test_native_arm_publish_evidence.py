"""Release CURRENT.json must point at a published bundle whose summary evidences the native arm."""

from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_FLAGSHIP_RUN_ID = "host-realistic-20260525"
_FAMILY_ID = "conicshield-transition-bank-v1"


def test_current_release_is_host_realistic_flagship() -> None:
    """Family release pointer matches flagship vendor-native external-evidence run."""
    root = _repo_root()
    current_path = root / "benchmarks" / "releases" / _FAMILY_ID / "CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    assert current.get("current_run_id") == _FLAGSHIP_RUN_ID
    assert current.get("state") == "published"
    assert current.get("parity_gate") == "green"
    assert current.get("promotion_gate") == "green"

    registry = json.loads((root / "benchmarks" / "registry.json").read_text(encoding="utf-8"))
    fam = next(f for f in registry["benchmark_families"] if f["family_id"] == _FAMILY_ID)
    assert fam["current_run_id"] == _FLAGSHIP_RUN_ID

    bundle_paths = current.get("benchmark_bundle_paths") or []
    assert f"benchmarks/published_runs/{_FLAGSHIP_RUN_ID}" in bundle_paths


def test_current_run_summary_includes_shielded_native_moreau_row() -> None:
    """Native-arm credibility: the bundle for ``current_run_id`` lists ``shielded-native-moreau`` with timings."""
    root = _repo_root()
    current_path = root / "benchmarks" / "releases" / _FAMILY_ID / "CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    assert "shielded-native-moreau" in (current.get("publishable_arms") or [])

    rid = str(current["current_run_id"])
    assert rid == _FLAGSHIP_RUN_ID
    summary_path = root / "benchmarks" / "published_runs" / rid / "summary.json"
    assert summary_path.is_file(), f"missing summary for current_run_id {rid}"

    rows = json.loads(summary_path.read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    native = next((r for r in rows if isinstance(r, dict) and r.get("label") == "shielded-native-moreau"), None)
    assert native is not None, f"no shielded-native-moreau row in {summary_path}"
    p50 = native.get("solve_time_p50_ms")
    assert isinstance(p50, int | float) and p50 >= 0.0
    assert float(p50) < 1e6, "solve_time_p50_ms should be a realistic ms value"
