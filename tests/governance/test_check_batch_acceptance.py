from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_check_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "check_batch_acceptance.py"
    spec = importlib.util.spec_from_file_location("check_batch_acceptance", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_batch_report_passes_above_threshold() -> None:
    mod = _load_check_module()
    policy = {
        "min_batch_size": 4,
        "min_speedup_ratio": 1.05,
        "device": "cpu",
        "acceptance_mode": "any_row_meets",
    }
    report = {
        "comparisons": [
            {
                "batch_size": 4,
                "device": "cpu",
                "speedup_ratio": 1.2,
                "mean_sec_sequential": 0.002,
                "mean_sec_batched": 0.0016,
            }
        ]
    }
    assert mod.check_batch_report(report=report, policy=policy) == []


def test_check_batch_report_fails_when_no_row_meets_threshold() -> None:
    mod = _load_check_module()
    policy = {
        "min_batch_size": 4,
        "min_speedup_ratio": 1.05,
        "device": "cpu",
        "acceptance_mode": "any_row_meets",
    }
    report = {
        "comparisons": [
            {"batch_size": 4, "device": "cpu", "speedup_ratio": 1.01},
            {"batch_size": 8, "device": "cpu", "speedup_ratio": 0.9},
        ]
    }
    failures = mod.check_batch_report(report=report, policy=policy)
    assert failures


def test_check_batch_report_any_row_meets_passes() -> None:
    mod = _load_check_module()
    policy = {
        "min_batch_size": 4,
        "min_speedup_ratio": 1.05,
        "device": "cpu",
        "acceptance_mode": "any_row_meets",
    }
    report = {
        "comparisons": [
            {"batch_size": 4, "device": "cpu", "speedup_ratio": 0.7},
            {"batch_size": 8, "device": "cpu", "speedup_ratio": 1.2},
        ]
    }
    assert mod.check_batch_report(report=report, policy=policy) == []
