"""Load ``benchmarks/PUBLISHED_RUN_INDEX.json`` (integrity pointers for governed published bundles)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, cast

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
