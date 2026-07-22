#!/usr/bin/env python3
"""Schema compatibility checks for committed governance / community artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


EXPECTED: dict[str, str] = {
    "community_metadata": "conicshield_community_metadata/v1",
    "reference_system_status": "conicshield_reference_system_status/v1",
    "reference_authority_snapshot": "conicshield_reference_authority_snapshot/v1",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=None)
    args = p.parse_args()
    root = args.root or _repo_root()
    failures: list[str] = []

    status_path = root / "benchmarks" / "reports" / "reference_system_status.json"
    if status_path.is_file():
        schema = _load(status_path).get("schema_version")
        if schema != EXPECTED["reference_system_status"]:
            failures.append(
                f"{status_path}: schema_version={schema!r} expected {EXPECTED['reference_system_status']!r}"
            )
    else:
        failures.append(f"missing {status_path}")

    snap_path = root / "benchmarks" / "reports" / "reference_authority_snapshot.json"
    if snap_path.is_file():
        schema = _load(snap_path).get("schema_version")
        if schema != EXPECTED["reference_authority_snapshot"]:
            failures.append(
                f"{snap_path}: schema_version={schema!r} expected {EXPECTED['reference_authority_snapshot']!r}"
            )

    index_path = root / "benchmarks" / "PUBLISHED_RUN_INDEX.json"
    if not index_path.is_file():
        failures.append(f"missing {index_path}")
    else:
        index = _load(index_path)
        runs = index.get("runs") or []
        if not runs:
            failures.append(f"{index_path}: empty runs list")
        for run in runs:
            rel = str(run.get("repository_relative_path") or "").replace("\\", "/")
            if not rel:
                failures.append("index run missing repository_relative_path")
                continue
            meta = root / rel / "COMMUNITY_METADATA.json"
            if not meta.is_file():
                failures.append(f"missing {meta}")
                continue
            schema = _load(meta).get("schema_version")
            if schema != EXPECTED["community_metadata"]:
                failures.append(
                    f"{meta}: schema_version={schema!r} expected {EXPECTED['community_metadata']!r}"
                )

    # Contract module must agree with expected community schema.
    from conicshield.governance.community_metadata_contract import SCHEMA_VERSION

    if EXPECTED["community_metadata"] != SCHEMA_VERSION:
        failures.append(
            f"community_metadata_contract.SCHEMA_VERSION={SCHEMA_VERSION!r} "
            f"expected {EXPECTED['community_metadata']!r}"
        )

    if failures:
        for row in failures:
            print(f"ERROR: {row}", file=sys.stderr)
        return 1
    print("OK: schema compatibility checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
