#!/usr/bin/env python3
"""Validate every governed published bundle matches the tier file profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from conicshield.governance.community_metadata_contract import validate_community_metadata
from conicshield.published_run_index import (
    build_run_catalog_metadata,
    classify_evidence_tier,
    load_published_run_index,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_profile(root: Path) -> dict:
    path = root / "benchmarks" / "reports" / "published_bundle_profile.json"
    return json.loads(path.read_text(encoding="utf-8"))


def check_bundle(
    *,
    run_dir: Path,
    profile: dict,
    catalog: dict,
    is_current_run: bool,
) -> list[str]:
    failures: list[str] = []
    tier = classify_evidence_tier(run_dir=run_dir)
    required = list(profile.get("common_required", []))
    tier_extra = (profile.get("tier_required") or {}).get(tier, [])
    required.extend(tier_extra)
    if is_current_run:
        required.extend(profile.get("when_family_current_run", []))
    if catalog.get("host_realistic") and catalog.get("includes_native_arm"):
        required.extend(profile.get("when_host_realistic_and_native_arm", []))
    seen: set[str] = set()
    ordered: list[str] = []
    for rel in required:
        if rel not in seen:
            seen.add(rel)
            ordered.append(rel)
    for rel in ordered:
        if not (run_dir / rel).is_file() and not (run_dir / rel).is_dir():
            failures.append(f"missing {rel} (tier={tier})")
    meta_path = run_dir / "COMMUNITY_METADATA.json"
    if meta_path.is_file():
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        for msg in validate_community_metadata(payload, expected_run_id=run_dir.name):
            failures.append(f"COMMUNITY_METADATA.json: {msg}")
    return failures


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", type=str, default=None, help="Check one run only.")
    args = p.parse_args()
    root = _repo_root()
    profile = _load_profile(root)
    index = load_published_run_index(repo_root=root)
    current_path = root / "benchmarks" / "releases" / "conicshield-transition-bank-v1" / "CURRENT.json"
    current_run_id: str | None = None
    if current_path.is_file():
        current_run_id = json.loads(current_path.read_text(encoding="utf-8")).get("current_run_id")
    failures: list[str] = []
    for run in index.get("runs", []):
        rid = str(run["run_id"])
        if args.run_id is not None and rid != args.run_id:
            continue
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        run_dir = root / rel
        catalog = run.get("catalog") or build_run_catalog_metadata(run_dir=run_dir, repo_root=root)
        for msg in check_bundle(
            run_dir=run_dir,
            profile=profile,
            catalog=dict(catalog),
            is_current_run=rid == current_run_id,
        ):
            failures.append(f"{rid}: {msg}")
    if failures:
        print("published bundle profile FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    n = 1 if args.run_id else len(index.get("runs", []))
    print(f"published bundle profile OK ({n} run(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
