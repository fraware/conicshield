"""Load ``benchmarks/PUBLISHED_RUN_INDEX.json`` (integrity pointers for governed published bundles)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Final, cast

# Must match ``validate_run_bundle`` required files in ``conicshield.artifacts.validator`` — hashed for every run.
PUBLISHED_RUN_REQUIRED_INTEGRITY_FILENAMES: Final[tuple[str, ...]] = (
    "config.json",
    "config.schema.json",
    "summary.json",
    "summary.schema.json",
    "episodes.jsonl",
    "episodes.schema.json",
    "transition_bank.json",
)

# Hashed when present (governance, provenance, release metadata, optional README).
PUBLISHED_RUN_OPTIONAL_INTEGRITY_FILENAMES: Final[tuple[str, ...]] = (
    "governance_status.json",
    "governance_status.schema.json",
    "RUN_PROVENANCE.json",
    "governance_decision.md",
    "release_decision.json",
    "solver_versions.json",
    "README.md",
)

_PARITY_RUN_ID = re.compile(
    r"benchmarks/published_runs/(?P<rid>[a-zA-Z0-9][a-zA-Z0-9._-]*)",
    re.MULTILINE,
)


def published_run_index_path(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path.cwd()
    return root / "benchmarks" / "PUBLISHED_RUN_INDEX.json"


def load_published_run_index(*, repo_root: Path | None = None) -> dict[str, Any]:
    path = published_run_index_path(repo_root=repo_root)
    if not path.is_file():
        raise FileNotFoundError(path)
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def run_ids_from_parity_regeneration_note(*, repo_root: Path | None = None) -> list[str]:
    """Parse REGENERATION_NOTE for ``benchmarks/published_runs/<run_id>`` path mentions."""
    root = repo_root if repo_root is not None else Path.cwd()
    path = root / "tests" / "fixtures" / "parity_reference" / "REGENERATION_NOTE.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[str] = []
    for m in _PARITY_RUN_ID.finditer(text):
        rid = m.group("rid").strip().rstrip("/.")
        if rid and rid not in seen:
            seen.add(rid)
            out.append(rid)
    return out


def assert_parity_note_run_ids_indexed(*, repo_root: Path | None = None) -> None:
    """Raise ``AssertionError`` if REGENERATION_NOTE cites a ``run_id`` missing from ``PUBLISHED_RUN_INDEX``."""
    root = repo_root if repo_root is not None else Path.cwd()
    note_ids = run_ids_from_parity_regeneration_note(repo_root=root)
    if not note_ids:
        return
    payload = load_published_run_index(repo_root=root)
    governed = {str(x) for x in (payload.get("governed_run_ids") or [])}
    for rid in note_ids:
        if rid not in governed:
            raise AssertionError(
                f"parity REGENERATION_NOTE references run_id {rid!r} not listed in "
                f"benchmarks/PUBLISHED_RUN_INDEX.json governed_run_ids {sorted(governed)}"
            )


def assert_index_includes_required_hashes(*, repo_root: Path | None = None) -> None:
    """Every indexed run must record SHA-256 for the validator-required bundle surface."""
    root = repo_root if repo_root is not None else Path.cwd()
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        rid = str(run.get("run_id", ""))
        integrity = run.get("integrity") or {}
        if not isinstance(integrity, dict):
            raise AssertionError(f"run {rid}: integrity must be a dict")
        keys = set(integrity.keys())
        for name in PUBLISHED_RUN_REQUIRED_INTEGRITY_FILENAMES:
            if name not in keys:
                raise AssertionError(
                    f"run {rid}: PUBLISHED_RUN_INDEX missing required integrity entry {name!r} "
                    f"(have {sorted(keys)}); run: python scripts/refresh_published_run_index.py"
                )


def verify_index_integrity(*, repo_root: Path | None = None) -> None:
    """Raise ``AssertionError`` if any recorded SHA-256 does not match the file on disk."""
    root = repo_root if repo_root is not None else Path.cwd()
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        rel = str(run.get("repository_relative_path", "")).replace("\\", "/")
        base = root / Path(rel)
        if not base.is_dir():
            raise AssertionError(f"missing run directory: {base}")
        integrity = run.get("integrity") or {}
        for fname, meta in integrity.items():
            if not isinstance(meta, dict):
                continue
            expected = meta.get("sha256")
            if not expected:
                continue
            fp = base / fname
            if not fp.is_file():
                raise AssertionError(f"missing integrity file: {fp}")
            h = hashlib.sha256()
            with fp.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            got = h.hexdigest()
            if got != str(expected):
                raise AssertionError(f"sha256 mismatch for {fp}: expected {expected}, got {got}")
