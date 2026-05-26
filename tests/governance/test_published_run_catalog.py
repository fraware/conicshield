from __future__ import annotations

import json
from pathlib import Path

from conicshield.published_run_index import (
    build_run_catalog_metadata,
    load_published_run_index,
    parity_fixture_source_run_id,
)


def test_index_entries_include_catalog() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        catalog = run.get("catalog")
        assert isinstance(catalog, dict), f"missing catalog for {run.get('run_id')}"
        assert catalog.get("evidence_tier")
        assert "includes_native_arm" in catalog


def test_flagship_catalog_is_vendor_native_current() -> None:
    root = Path(__file__).resolve().parents[2]
    run_dir = root / "benchmarks" / "published_runs" / "host-realistic-20260525"
    catalog = build_run_catalog_metadata(run_dir=run_dir, repo_root=root)
    assert catalog["evidence_tier"] == "vendor_native"
    assert catalog["host_realistic"] is True
    assert catalog["includes_native_arm"] is True


def test_parity_fixture_source_is_wsl_real() -> None:
    root = Path(__file__).resolve().parents[2]
    assert parity_fixture_source_run_id(repo_root=root) == "wsl-real-20260409-132450"
