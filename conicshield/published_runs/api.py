"""Stable consumer API for committed published benchmark bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conicshield.governance.community_metadata import build_community_metadata
from conicshield.published_run_index import (
    classify_evidence_tier,
    load_published_run_index,
    published_run_index_path,
)
from conicshield.published_runs.models import (
    CommunityMetadata,
    IntegrityEntry,
    PublishedRunBundle,
    PublishedRunIndexEntry,
    SummaryRow,
)


def _repo_root(repo_root: Path | None) -> Path:
    return repo_root if repo_root is not None else Path.cwd()


def _parse_community(data: dict[str, Any]) -> CommunityMetadata:
    host = bool(data.get("host_realistic", data.get("host_realistic_evidence", False)))
    fixture = bool(
        data.get("parity_fixture_source", data.get("parity_fixture_gold_for_repo", False))
    )
    tier = data.get("evidence_tier", "contract_fixture")
    return CommunityMetadata(
        schema_version=str(data.get("schema_version", "")),
        run_id=str(data["run_id"]),
        family_id=str(data.get("family_id", "")),
        evidence_tier=tier,  # type: ignore[arg-type]
        host_realistic=host,
        includes_native_arm=bool(data.get("includes_native_arm", False)),
        projector_mode=data.get("projector_mode"),
        is_family_current_run=bool(data.get("is_family_current_run", False)),
        parity_fixture_source=fixture,
        export_kind=data.get("export_kind"),
        source_export=data.get("source_export"),
        parity_status=str(data.get("parity_status", "unknown")),
        recommended_uses=tuple(str(x) for x in (data.get("recommended_uses") or [])),
        known_limitations=tuple(str(x) for x in (data.get("known_limitations") or [])),
        solver_stack=data.get("solver_stack"),
    )


def _index_entry(run: dict[str, Any]) -> PublishedRunIndexEntry:
    integrity_raw = run.get("integrity") or {}
    integrity = tuple(
        IntegrityEntry(path=str(fname), sha256=str(meta["sha256"]))
        for fname, meta in sorted(integrity_raw.items())
        if isinstance(meta, dict) and meta.get("sha256")
    )
    return PublishedRunIndexEntry(
        run_id=str(run["run_id"]),
        repository_relative_path=str(run["repository_relative_path"]).replace("\\", "/"),
        integrity=integrity,
        catalog=dict(run.get("catalog") or {}),
    )


def list_runs(*, repo_root: Path | None = None) -> tuple[PublishedRunIndexEntry, ...]:
    """Return all runs listed in ``PUBLISHED_RUN_INDEX.json``."""
    payload = load_published_run_index(repo_root=_repo_root(repo_root))
    return tuple(_index_entry(r) for r in payload.get("runs", []))


def load_run(run_id: str, *, repo_root: Path | None = None) -> PublishedRunBundle:
    """Load bundle metadata and paths for a governed ``run_id``."""
    root = _repo_root(repo_root)
    for entry in list_runs(repo_root=root):
        if entry.run_id == run_id:
            run_dir = root / entry.repository_relative_path
            if not run_dir.is_dir():
                raise FileNotFoundError(run_dir)
            community = None
            meta_path = run_dir / "COMMUNITY_METADATA.json"
            if meta_path.is_file():
                community = _parse_community(json.loads(meta_path.read_text(encoding="utf-8")))
            gov_path = run_dir / "governance_status.json"
            prov_path = run_dir / "RUN_PROVENANCE.json"
            return PublishedRunBundle(
                run_id=run_id,
                path=run_dir,
                index_entry=entry,
                community=community,
                governance_status=(
                    json.loads(gov_path.read_text(encoding="utf-8")) if gov_path.is_file() else None
                ),
                run_provenance=(
                    json.loads(prov_path.read_text(encoding="utf-8")) if prov_path.is_file() else None
                ),
            )
    raise KeyError(f"run_id not in PUBLISHED_RUN_INDEX: {run_id!r}")


def verify_run(run_id: str, *, repo_root: Path | None = None) -> None:
    """Verify SHA-256 integrity for ``run_id`` (raises ``AssertionError`` on mismatch)."""
    import hashlib

    bundle = load_run(run_id, repo_root=repo_root)
    for entry in bundle.index_entry.integrity:
        fp = bundle.path / entry.path
        if not fp.is_file():
            raise AssertionError(f"missing {fp}")
        h = hashlib.sha256()
        with fp.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != entry.sha256:
            raise AssertionError(f"sha256 mismatch for {fp}")


def current_family_run(family_id: str, *, repo_root: Path | None = None) -> PublishedRunBundle:
    """Return the published bundle for a family's ``current_run_id``."""
    root = _repo_root(repo_root)
    current_path = root / "benchmarks" / "releases" / family_id / "CURRENT.json"
    if not current_path.is_file():
        raise FileNotFoundError(current_path)
    current = json.loads(current_path.read_text(encoding="utf-8"))
    run_id = current.get("current_run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError(f"family {family_id!r} has no current_run_id")
    return load_run(run_id, repo_root=root)


def load_summary(run_id: str, *, repo_root: Path | None = None) -> tuple[SummaryRow, ...]:
    """Load ``summary.json`` arm rows for a published run."""
    bundle = load_run(run_id, repo_root=repo_root)
    raw = json.loads((bundle.path / "summary.json").read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else []
    out: list[SummaryRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label", ""))
        extra = {k: v for k, v in row.items() if k not in ("label", "solve_time_p50_ms")}
        out.append(
            SummaryRow(
                label=label,
                solve_time_p50_ms=(
                    float(row["solve_time_p50_ms"]) if row.get("solve_time_p50_ms") is not None else None
                ),
                extra=extra,
            )
        )
    return tuple(out)


def load_episodes(run_id: str, *, repo_root: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Load ``episodes.jsonl`` records for a published run."""
    bundle = load_run(run_id, repo_root=repo_root)
    path = bundle.path / "episodes.jsonl"
    episodes: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            episodes.append(json.loads(line))
    return tuple(episodes)


def ensure_community_metadata(run_id: str, *, repo_root: Path | None = None) -> CommunityMetadata:
    """Return on-disk metadata or build the canonical payload (does not write)."""
    bundle = load_run(run_id, repo_root=repo_root)
    if bundle.community is not None:
        return bundle.community
    root = _repo_root(repo_root)
    export_prov: dict[str, Any] = {}
    ep = root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if ep.is_file():
        export_prov = json.loads(ep.read_text(encoding="utf-8"))
    current_run_id = None
    cp = root / "benchmarks" / "releases" / "conicshield-transition-bank-v1" / "CURRENT.json"
    if cp.is_file():
        current_run_id = json.loads(cp.read_text(encoding="utf-8")).get("current_run_id")
    payload = build_community_metadata(
        run_dir=bundle.path,
        repo_root=root,
        export_provenance=export_prov,
        current_run_id=str(current_run_id) if current_run_id else None,
    )
    return _parse_community(payload)


def index_path(*, repo_root: Path | None = None) -> Path:
    return published_run_index_path(repo_root=_repo_root(repo_root))
