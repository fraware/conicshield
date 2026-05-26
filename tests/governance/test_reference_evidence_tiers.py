from __future__ import annotations

from pathlib import Path

from conicshield.published_run_index import classify_evidence_tier


def test_classify_evidence_tier_canonical_runs() -> None:
    root = Path(__file__).resolve().parents[2]
    published = root / "benchmarks" / "published_runs"
    assert classify_evidence_tier(run_dir=published / "host-realistic-20260525") == "structural_export"
    assert classify_evidence_tier(run_dir=published / "wsl-real-20260409-132450") == "vendor_reference"
    assert classify_evidence_tier(run_dir=published / "wsl-native-20260409-091141") == "vendor_native"
