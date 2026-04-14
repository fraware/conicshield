#!/usr/bin/env python3
"""Emit ``benchmarks/PUBLISHED_RUN_INDEX.json`` from committed ``benchmarks/published_runs/<run_id>/`` trees.

Run after adding or updating a canonical published bundle so integrity SHA-256 fields stay in sync.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


def _run_id_from_bundle_path(s: str) -> str | None:
    p = s.strip().replace("\\", "/")
    if "/published_runs/" not in p:
        return None
    tail = p.rstrip("/").split("/")[-1]
    return tail or None


def _governed_run_ids(repo_root: Path) -> set[str]:
    """Run IDs referenced by release metadata (excludes local scratch under ``published_runs/``)."""
    out: set[str] = set()
    registry_path = repo_root / "benchmarks" / "registry.json"
    if registry_path.is_file():
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        for fam in reg.get("benchmark_families", []):
            rid = fam.get("current_run_id")
            if rid:
                out.add(str(rid))
    rel_root = repo_root / "benchmarks" / "releases"
    if rel_root.is_dir():
        for current_path in rel_root.glob("*/CURRENT.json"):
            cur = json.loads(current_path.read_text(encoding="utf-8"))
            cr = cur.get("current_run_id")
            if cr:
                out.add(str(cr))
            for bp in cur.get("benchmark_bundle_paths") or []:
                parsed = _run_id_from_bundle_path(str(bp))
                if parsed:
                    out.add(parsed)
            hist_path = current_path.parent / "HISTORY.json"
            if hist_path.is_file():
                hist = json.loads(hist_path.read_text(encoding="utf-8"))
                for ent in hist.get("entries", []):
                    r = ent.get("run_id")
                    if r:
                        out.add(str(r))
    return out


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_index(*, repo_root: Path, published_root: Path) -> dict[str, Any]:
    allowed = _governed_run_ids(repo_root)
    if not allowed:
        raise SystemExit("no governed run_ids found (registry/releases); refusing to emit an empty index")
    runs_payload: list[dict[str, Any]] = []
    missing: list[str] = []
    for rid in sorted(allowed):
        run_dir = published_root / rid
        if not run_dir.is_dir() or not (run_dir / "summary.json").is_file():
            missing.append(rid)
            continue
        rid = run_dir.name
        rel = run_dir.as_posix()
        if not rel.startswith("benchmarks/"):
            rel = f"benchmarks/published_runs/{rid}"
        integrity: dict[str, Any] = {}
        for name in ("summary.json", "RUN_PROVENANCE.json", "governance_status.json"):
            p = run_dir / name
            if p.is_file():
                integrity[name] = {"sha256": _sha256_file(p)}
        runs_payload.append(
            {
                "run_id": rid,
                "repository_relative_path": rel,
                "integrity": integrity,
            }
        )
    if missing:
        raise SystemExit("governed run_id(s) missing from disk under benchmarks/published_runs: " + ", ".join(missing))
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published_root": "benchmarks/published_runs",
        "governed_run_ids": sorted(allowed),
        "runs": runs_payload,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root (default: parent of scripts/).",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if PUBLISHED_RUN_INDEX.json would change (CI drift check).",
    )
    args = p.parse_args()
    root = args.root or Path(__file__).resolve().parents[1]
    published_root = root / "benchmarks" / "published_runs"
    out_path = root / "benchmarks" / "PUBLISHED_RUN_INDEX.json"
    payload = build_index(repo_root=root, published_root=published_root)
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"

    def _stable(obj: dict[str, Any]) -> dict[str, Any]:
        d = dict(obj)
        d.pop("generated_at_utc", None)
        return d

    if args.check:
        if not out_path.is_file():
            raise SystemExit(f"missing {out_path}")
        existing_obj = cast(dict[str, Any], json.loads(out_path.read_text(encoding="utf-8")))
        if json.dumps(_stable(existing_obj), indent=2, sort_keys=True) != json.dumps(
            _stable(payload), indent=2, sort_keys=True
        ):
            raise SystemExit(f"{out_path} is stale; run: python scripts/refresh_published_run_index.py")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
