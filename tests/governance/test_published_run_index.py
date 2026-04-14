from __future__ import annotations

from pathlib import Path

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.benchmark_paths import resolve_run_directory
from conicshield.published_run_index import (
    assert_index_includes_required_hashes,
    assert_parity_note_run_ids_indexed,
    load_published_run_index,
    run_ids_from_parity_regeneration_note,
    verify_index_integrity,
)


def test_parity_regeneration_note_run_ids_are_indexed() -> None:
    """REGENERATION_NOTE must cite only governed run_ids present in PUBLISHED_RUN_INDEX."""
    root = Path(__file__).resolve().parents[2]
    ids = run_ids_from_parity_regeneration_note(repo_root=root)
    assert ids, "expected at least one benchmarks/published_runs/<run_id> in REGENERATION_NOTE.md"
    assert_parity_note_run_ids_indexed(repo_root=root)


def test_published_run_index_matches_disk_and_bundles() -> None:
    """Governed runs in ``PUBLISHED_RUN_INDEX.json`` resolve, validate, and match SHA-256."""
    root = Path(__file__).resolve().parents[2]
    assert_index_includes_required_hashes(repo_root=root)
    verify_index_integrity(repo_root=root)
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        rid = str(run["run_id"])
        resolved = resolve_run_directory(rid)
        assert resolved.resolve() == (root / "benchmarks" / "published_runs" / rid).resolve()
        validate_run_bundle(resolved)
