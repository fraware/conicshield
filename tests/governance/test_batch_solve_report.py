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


def test_batch_solve_report_speedup_ratio() -> None:
    mod = _load_batch_report_module()
    summary = {
        "rows": [
            {"path": "native_microbatch", "mean_sec": 0.2, "batch_size": 4, "device": "cpu"},
            {"path": "native_compiled_real_batch", "mean_sec": 0.1, "batch_size": 4, "device": "cpu"},
        ]
    }
    payload = mod.build_batch_solve_report_payload(summary=summary, source=Path("in.json"))
    assert payload["summary"]["pairs"] == 1
    assert payload["comparisons"][0]["speedup_ratio"] == 2.0


def test_write_batch_solve_report_skips_empty(tmp_path: Path) -> None:
    mod = _load_batch_report_module()
    inp = tmp_path / "performance_summary.json"
    inp.write_text(json.dumps({"rows": [{"path": "cvxpy_moreau", "mean_sec": 1.0}]}), encoding="utf-8")
    out = tmp_path / "batch_solve_report.json"
    assert mod.write_batch_solve_report(summary_path=inp, out_path=out) is None
    assert not out.exists()
