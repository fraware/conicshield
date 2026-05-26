#!/usr/bin/env python3
"""Refresh human README.md files for governed published bundles from catalog metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conicshield.published_run_index import build_run_catalog_metadata, load_published_run_index


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _render_readme(*, run_id: str, catalog: dict[str, object]) -> str:
    tier = catalog.get("evidence_tier", "unknown")
    host = "yes" if catalog.get("host_realistic") else "no"
    native = "yes" if catalog.get("includes_native_arm") else "no"
    fixture = "yes" if catalog.get("parity_fixture_source") else "no"
    current = "yes" if catalog.get("is_family_current_run") else "no"
    mode = catalog.get("projector_mode") or "n/a"
    gov = catalog.get("governance_state") or "n/a"
    lines = [
        f"# Published run `{run_id}`",
        "",
        "Governed benchmark bundle for `conicshield-transition-bank-v1`.",
        "",
        "| Field | Value |",
        "|-------|--------|",
        f"| `evidence_tier` | `{tier}` |",
        f"| `projector_mode` | `{mode}` |",
        f"| Host-realistic export evidence | {host} |",
        f"| Includes `shielded-native-moreau` | {native} |",
        f"| Parity fixture gold source | {fixture} |",
        f"| Family `current_run_id` | {current} |",
        f"| Governance `state` | `{gov}` |",
        "",
        "## What this run proves",
        "",
        "- Validated artifact surface (`validate_run_bundle`)",
        "- Benchmark arms in `summary.json` with governance gates in `governance_status.json`",
        "",
        "## What this run does not claim",
        "",
        "- Differentiable runtime shield product guarantees (see `docs/DIFFERENTIATION_PUBLIC_STANCE.md`)",
        "- Live upstream simulator export unless `RUN_PROVENANCE.json` says so",
        "",
        "## Ops",
        "",
        "- Refresh procedure: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)",
        "- Catalog spec: [`docs/PUBLISHED_BUNDLE_CATALOG.md`](../../docs/PUBLISHED_BUNDLE_CATALOG.md)",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    root = _repo_root()
    payload = load_published_run_index(repo_root=root)
    current_path = root / "benchmarks" / "releases" / "conicshield-transition-bank-v1" / "CURRENT.json"
    current_run_id = None
    if current_path.is_file():
        current_run_id = json.loads(current_path.read_text(encoding="utf-8")).get("current_run_id")

    for run in payload.get("runs", []):
        rid = str(run["run_id"])
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        run_dir = root / rel
        catalog = run.get("catalog") or build_run_catalog_metadata(run_dir=run_dir, repo_root=root)
        catalog = dict(catalog)
        catalog["is_family_current_run"] = rid == current_run_id
        text = _render_readme(run_id=rid, catalog=catalog)
        dest = run_dir / "README.md"
        dest.write_text(text, encoding="utf-8")
        print(dest, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
