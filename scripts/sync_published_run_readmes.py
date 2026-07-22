#!/usr/bin/env python3
"""Refresh human README.md files for governed published bundles from catalog metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from conicshield.published_run_index import build_run_catalog_metadata, load_published_run_index


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _export_provenance(repo: Path) -> dict:
    path = repo / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_sentence(*, run_id: str, tier: str, host: bool, current: bool, native: bool) -> str:
    if run_id == "host-realistic-20260525":
        return (
            "Public **host-realistic** benchmark artifact: a governed, hash-indexed run recording "
            f"shielded RL episodes at evidence tier `{tier}` with native Moreau arm and family `current_run_id`."
        )
    if current:
        return (
            f"Governed benchmark artifact `{run_id}` at tier `{tier}` (family current run; native arm={native})."
        )
    return f"Governed benchmark artifact `{run_id}` at evidence tier `{tier}`."


def _render_readme(
    *,
    run_id: str,
    run_rel_path: str,
    run_dir: Path,
    catalog: dict[str, object],
    export_prov: dict,
) -> str:
    tier = catalog.get("evidence_tier", "unknown")
    host = "yes" if catalog.get("host_realistic") else "no"
    native = "yes" if catalog.get("includes_native_arm") else "no"
    fixture = "yes" if catalog.get("parity_fixture_source") else "no"
    current = "yes" if catalog.get("is_family_current_run") else "no"
    mode = catalog.get("projector_mode") or "n/a"
    gov_state = catalog.get("governance_state") or "n/a"
    export_kind = export_prov.get("export_kind", "n/a")
    graph_shape = export_prov.get("graph_shape", "n/a") if catalog.get("host_realistic") else "n/a"
    graph_note = (
        "Host-realistic **fork** via inter-sim `RLEnvironment` (fork topology only; does not prove full upstream navigation export)."
        if catalog.get("host_realistic")
        else "See `RUN_PROVENANCE.json` for export scope."
    )

    parity_status = "n/a"
    if (run_dir / "parity_out" / "parity_summary.json").is_file():
        ps = json.loads((run_dir / "parity_out" / "parity_summary.json").read_text(encoding="utf-8"))
        parity_status = "green" if ps.get("passed") else str(ps.get("status", "present"))

    solver_lines: list[str] = []
    sv_path = run_dir / "solver_versions.json"
    if sv_path.is_file():
        sv = json.loads(sv_path.read_text(encoding="utf-8"))
        for pkg, ver in sorted(sv.items()):
            solver_lines.append(f"- `{pkg}`: `{ver}`")

    lines = [
        f"# Published run `{run_id}`",
        "",
        _artifact_sentence(
            run_id=run_id,
            tier=str(tier),
            host=host == "yes",
            current=current,
            native=native == "yes",
        ),
        "",
        "Read [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) before `summary.json`.",
        "",
        "| Field | Value |",
        "|-------|--------|",
        f"| `evidence_tier` | `{tier}` |",
        f"| `projector_mode` | `{mode}` |",
        f"| Export `export_kind` | `{export_kind}` |",
        f"| Graph shape (qualification) | `{graph_shape}` — {graph_note} |",
        f"| Native arm (`shielded-native-moreau`) | {native} |",
        f"| Parity status | `{parity_status}` |",
        f"| Host-realistic path | {host} |",
        f"| Family `current_run_id` | {current} |",
        f"| Governance state | `{gov_state}` |",
        "",
    ]
    if solver_lines:
        lines.extend(["## Solver stack", ""] + solver_lines + [""])

    lines.extend(
        [
            "## What this run proves",
            "",
            "- Validator-required bundle surface passes `validate_run_bundle`",
            "- `summary.json` arms with governance gates recorded in `governance_status.json`",
        ]
    )
    if catalog.get("host_realistic"):
        lines.append(
            "- Host-realistic export → transition bank → publish path is **closed in-repo**"
        )
    lines.extend(
        [
            "",
            "## What this run does not prove",
            "",
            "- Production differentiable shield / autograd product ([`docs/DIFFERENTIATION_PUBLIC_STANCE.md`](../../docs/DIFFERENTIATION_PUBLIC_STANCE.md))",
            "- Claim of universal batch throughput win ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))",
            "- Full upstream navigation export (fork topology only unless provenance documents more)",
            "",
            "## Verify this artifact",
            "",
            "```bash",
            "python -m conicshield.published_runs.cli verify " + run_id,
            "python -m conicshield.published_runs.cli show " + run_id,
            "python -m conicshield.published_runs.cli summary " + run_id,
            "python -m conicshield.published_runs.cli provenance " + run_id,
            "python -m conicshield.artifacts.validator_cli --run-dir " + run_rel_path,
            "python scripts/validate_published_bundle_profile.py --run-id " + run_id,
            "```",
            "",
            "Canonical API example: [`examples/load_published_runs_api.py`](../../examples/load_published_runs_api.py).",
            "",
            "## Cite this artifact",
            "",
            "Cite **`run_id`**, repository **commit SHA**, and [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json). "
            "Artifact identity is not a scientific conclusion — follow "
            "[`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md) and "
            "[`docs/PUBLIC_CLAIMS.md`](../../docs/PUBLIC_CLAIMS.md).",
            "",
        ]
    )
    if catalog.get("host_realistic"):
        lines.extend(
            [
                "## Source export",
                "",
                "- `benchmarks/external_evidence/offline_graph_export_upstream.json` "
                f"(`{export_kind}`)",
                "- [`benchmarks/external_evidence/EXPORT_PROVENANCE.json`](../../benchmarks/external_evidence/EXPORT_PROVENANCE.json)",
                "- Refresh log: [`benchmarks/reports/reference_refresh_log.md`](../../benchmarks/reports/reference_refresh_log.md)",
                "",
            ]
        )
    lines.extend(
        [
            "## Further reading",
            "",
            "- Public entry: [`docs/COMMUNITY_LAYER.md`](../../docs/COMMUNITY_LAYER.md)",
            "- Index consumers: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)",
            "- Maintainers: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--check",
        action="store_true",
        help="Fail if any published-run README.md differs (read-only; no writes).",
    )
    args = p.parse_args()

    root = _repo_root()
    payload = load_published_run_index(repo_root=root)
    export_prov = _export_provenance(root)
    current_path = root / "benchmarks" / "releases" / "conicshield-transition-bank-v1" / "CURRENT.json"
    current_run_id = None
    if current_path.is_file():
        current_run_id = json.loads(current_path.read_text(encoding="utf-8")).get("current_run_id")

    stale: list[str] = []
    for run in payload.get("runs", []):
        rid = str(run["run_id"])
        rel = str(run["repository_relative_path"]).replace("\\", "/")
        run_dir = root / rel
        catalog = run.get("catalog") or build_run_catalog_metadata(run_dir=run_dir, repo_root=root)
        catalog = dict(catalog)
        catalog["is_family_current_run"] = rid == current_run_id
        text = _render_readme(
            run_id=rid,
            run_rel_path=rel,
            run_dir=run_dir,
            catalog=catalog,
            export_prov=export_prov,
        )
        dest = run_dir / "README.md"
        if args.check:
            if not dest.is_file():
                stale.append(f"missing {dest}")
                continue
            if dest.read_text(encoding="utf-8") != text:
                stale.append(str(dest))
            continue
        dest.write_text(text, encoding="utf-8")
        print(dest, file=sys.stderr)

    if args.check:
        if stale:
            for row in stale:
                print(f"stale: {row}", file=sys.stderr)
            print("Run: python scripts/sync_published_run_readmes.py", file=sys.stderr)
            return 2
        print("OK published-run READMEs")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
