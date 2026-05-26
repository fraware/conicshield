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
    policy = {"min_batch_size": 4, "min_speedup_ratio": 1.05, "device": "cpu"}
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


def test_check_batch_report_fails_below_threshold() -> None:
    mod = _load_check_module()
    policy = {"min_batch_size": 4, "min_speedup_ratio": 1.05, "device": "cpu"}
    report = {
        "comparisons": [
            {"batch_size": 4, "device": "cpu", "speedup_ratio": 1.01},
        ]
    }
    failures = mod.check_batch_report(report=report, policy=policy)
    assert failures
