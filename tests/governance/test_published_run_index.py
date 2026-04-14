from __future__ import annotations

from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.benchmark_paths import resolve_run_directory
from conicshield.published_run_index import load_published_run_index, verify_index_integrity


def test_published_run_index_matches_disk_and_bundles() -> None:
    """Governed runs in ``PUBLISHED_RUN_INDEX.json`` resolve, validate, and match SHA-256."""
    root = Path(__file__).resolve().parents[2]
    verify_index_integrity(repo_root=root)
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        rid = str(run["run_id"])
        resolved = resolve_run_directory(rid)
        assert resolved.resolve() == (root / "benchmarks" / "published_runs" / rid).resolve()
        validate_run_bundle(resolved)
