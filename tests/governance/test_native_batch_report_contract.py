from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_batch_report_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "batch_solve_report.py"
    spec = importlib.util.spec_from_file_location("batch_solve_report", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_batch_solve_report_includes_batch_story_and_both_paths() -> None:
    mod = _load_batch_report_module()
    summary = {
        "rows": [
            {"path": "native_microbatch", "mean_sec": 0.2, "batch_size": 4, "device": "cpu"},
            {"path": "native_compiled_real_batch", "mean_sec": 0.19, "batch_size": 4, "device": "cpu"},
        ]
    }
    payload = mod.build_batch_solve_report_payload(summary=summary, source=Path("in.json"))
    assert payload["schema_version"] == "conicshield_batch_solve_report/v2"
    assert payload["batch_story"] in ("viability_only", "throughput_win", "below_viability")
    assert "batch_story_advisory" in payload
    row = payload["comparisons"][0]
    assert row["mean_sec_sequential"] == 0.2
    assert row["mean_sec_batched"] == 0.19
    assert row["speedup_ratio"] == payload["summary"]["max_speedup_ratio"]


def test_committed_latest_batch_report_has_batch_story() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "benchmarks" / "reports" / "batch_solve_report.latest.json"
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("example_only"):
        return
    assert payload.get("schema_version") == "conicshield_batch_solve_report/v2"
    assert payload.get("batch_story") in ("viability_only", "throughput_win", "below_viability")
