"""Load ``benchmarks/PUBLISHED_RUN_INDEX.json`` (integrity pointers for governed published bundles)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Final, Literal, cast

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
    "COMMUNITY_METADATA.json",
)

EvidenceTier = Literal[
    "contract_fixture",
    "structural_export",
    "vendor_reference",
    "vendor_native",
]

_PARITY_RUN_ID = re.compile(
    r"benchmarks/published_runs/(?P<rid>[a-zA-Z0-9][a-zA-Z0-9._-]*)",
    re.MULTILINE,
)

_MINIMAL_FIXTURE_SUFFIX = "tests/fixtures/offline_graph_export_minimal.json"


def published_run_index_path(repo_root: Path | None = None) -> Path:
    root = repo_root if repo_root is not None else Path.cwd()
    return root / "benchmarks" / "PUBLISHED_RUN_INDEX.json"


def load_published_run_index(*, repo_root: Path | None = None) -> dict[str, Any]:
    path = published_run_index_path(repo_root=repo_root)
    if not path.is_file():
        raise FileNotFoundError(path)
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _summary_rows(run_dir: Path) -> list[dict[str, Any]]:
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        return []
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if isinstance(summary, list):
        return [row for row in summary if isinstance(row, dict)]
    return []


def classify_evidence_tier(*, run_dir: Path) -> EvidenceTier:
    """Infer evidence tier from ``RUN_PROVENANCE.json`` and ``summary.json``."""
    prov_path = run_dir / "RUN_PROVENANCE.json"
    rows = _summary_rows(run_dir)
    has_native_row = any(row.get("label") == "shielded-native-moreau" for row in rows)
    native_solve_ms = 0.0
    for row in rows:
        if row.get("label") == "shielded-native-moreau":
            native_solve_ms = float(row.get("solve_time_p50_ms") or 0.0)
            break

    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        tier = prov.get("evidence_tier")
        if tier in (
            "contract_fixture",
            "structural_export",
            "vendor_reference",
            "vendor_native",
        ):
            return cast(EvidenceTier, tier)
        mode = str(prov.get("projector_mode", ""))
        source = str(prov.get("source_export_json", "")).replace("\\", "/")
        if _MINIMAL_FIXTURE_SUFFIX in source and mode == "passthrough":
            return "contract_fixture"
        if prov.get("host_realistic_evidence") and mode == "passthrough":
            return "structural_export"
        if mode == "real_projector":
            if has_native_row and native_solve_ms > 0.0:
                return "vendor_native"
            return "vendor_reference"

    if has_native_row and native_solve_ms > 0.0:
        return "vendor_native"
    if rows and any(float(row.get("solve_time_p50_ms") or 0.0) > 0.0 for row in rows):
        return "vendor_reference"
    return "contract_fixture"


def parity_fixture_source_run_id(*, repo_root: Path | None = None) -> str | None:
    """``run_id`` promoted into ``tests/fixtures/parity_reference/`` per REGENERATION_NOTE, if any."""
    root = repo_root if repo_root is not None else Path.cwd()
    note_path = root / "tests" / "fixtures" / "parity_reference" / "REGENERATION_NOTE.md"
    if not note_path.is_file():
        return None
    text = note_path.read_text(encoding="utf-8")
    m = re.search(
        r"regenerate_parity_fixture\.py --source benchmarks/published_runs/([a-zA-Z0-9][a-zA-Z0-9._-]*)",
        text,
    )
    if m:
        return m.group(1).strip().rstrip("/.")
    for rid in run_ids_from_parity_regeneration_note(repo_root=root):
        if f"published_runs/{rid}" in text and "synced from" in text:
            return rid
    return None


def build_run_catalog_metadata(*, run_dir: Path, repo_root: Path | None = None) -> dict[str, Any]:
    """Machine-readable bundle catalog for index entries and published README sync."""
    root = repo_root if repo_root is not None else Path.cwd()
    rid = run_dir.name
    tier = classify_evidence_tier(run_dir=run_dir)
    prov: dict[str, Any] = {}
    if (run_dir / "RUN_PROVENANCE.json").is_file():
        prov = cast(dict[str, Any], json.loads((run_dir / "RUN_PROVENANCE.json").read_text(encoding="utf-8")))
    rows = _summary_rows(run_dir)
    has_native = any(row.get("label") == "shielded-native-moreau" for row in rows)
    gov_state: str | None = None
    if (run_dir / "governance_status.json").is_file():
        gov = cast(dict[str, Any], json.loads((run_dir / "governance_status.json").read_text(encoding="utf-8")))
        gov_state = str(gov.get("state")) if gov.get("state") is not None else None
    fixture_rid = parity_fixture_source_run_id(repo_root=root)
    return {
        "run_id": rid,
        "evidence_tier": tier,
        "host_realistic": bool(prov.get("host_realistic_evidence")),
        "includes_native_arm": has_native,
        "parity_fixture_source": fixture_rid == rid if fixture_rid else False,
        "has_solver_versions": (run_dir / "solver_versions.json").is_file(),
        "projector_mode": prov.get("projector_mode"),
        "governance_state": gov_state,
        "is_family_current_run": False,
    }


def enrich_catalog_with_current_run(*, catalog: dict[str, Any], current_run_id: str | None) -> dict[str, Any]:
    out = dict(catalog)
    out["is_family_current_run"] = bool(current_run_id) and catalog.get("run_id") == current_run_id
    return out


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


def assert_index_covers_present_optional_files(*, repo_root: Path | None = None) -> None:
    """Every optional integrity filename present on disk must appear in the index."""
    root = repo_root if repo_root is not None else Path.cwd()
    payload = load_published_run_index(repo_root=root)
    for run in payload.get("runs", []):
        rid = str(run.get("run_id", ""))
        rel = str(run.get("repository_relative_path", "")).replace("\\", "/")
        base = root / Path(rel)
        integrity = run.get("integrity") or {}
        if not isinstance(integrity, dict):
            raise AssertionError(f"run {rid}: integrity must be a dict")
        keys = set(integrity.keys())
        for name in PUBLISHED_RUN_OPTIONAL_INTEGRITY_FILENAMES:
            if (base / name).is_file() and name not in keys:
                raise AssertionError(
                    f"run {rid}: on-disk optional file {name!r} is not listed in "
                    f"PUBLISHED_RUN_INDEX integrity (have {sorted(keys)}); "
                    f"run: python scripts/refresh_published_run_index.py"
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


def assert_canonical_evidence_tiers(*, repo_root: Path | None = None) -> None:
    """Lock expected evidence tiers for canonical published runs (see tests/governance)."""
    root = repo_root if repo_root is not None else Path.cwd()
    expected: dict[str, EvidenceTier] = {
        "host-realistic-20260525": "vendor_native",
        "wsl-real-20260409-132450": "vendor_reference",
        "wsl-native-20260409-091141": "vendor_native",
    }
    for run_id, want in expected.items():
        run_dir = root / "benchmarks" / "published_runs" / run_id
        if not run_dir.is_dir():
            raise AssertionError(f"missing canonical published run directory: {run_dir}")
        got = classify_evidence_tier(run_dir=run_dir)
        if got != want:
            raise AssertionError(
                f"run {run_id}: evidence_tier {got!r} != expected {want!r}; "
                f"update RUN_PROVENANCE or governance tests"
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
