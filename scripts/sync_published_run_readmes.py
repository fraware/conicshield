#!/usr/bin/env python3
"""Refresh human README.md files for governed published bundles from catalog metadata."""

from __future__ import annotations

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


def _one_liner(*, run_id: str, tier: str, host: bool, current: bool, native: bool) -> str:
    if run_id == "host-realistic-20260525":
        return (
            "Flagship **host-realistic** governed bundle: closed export→bank→publish loop at "
            f"`{tier}` with native Moreau arm and family `current_run_id`."
        )
    if current == "yes":
        return f"Family **current** published run at `{tier}` with native arm={native}."
    return f"Governed benchmark bundle `{run_id}` at evidence tier `{tier}`."


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
    gov = catalog.get("governance_state") or "n/a"
    export_kind = export_prov.get("export_kind", "n/a")
    blurb = _one_liner(
        run_id=run_id,
        tier=str(tier),
        host=host == "yes",
        current=current,
        native=native == "yes",
    )
    solver_lines: list[str] = []
    sv_path = run_dir / "solver_versions.json"
    if sv_path.is_file():
        sv = json.loads(sv_path.read_text(encoding="utf-8"))
        for pkg, ver in sorted(sv.items()):
            solver_lines.append(f"- `{pkg}`: `{ver}`")
    parity_status = "n/a"
    if (run_dir / "parity_out" / "parity_summary.json").is_file():
        ps = json.loads((run_dir / "parity_out" / "parity_summary.json").read_text(encoding="utf-8"))
        parity_status = "green" if ps.get("passed") else str(ps.get("status", "present"))

    lines = [
        f"# Published run `{run_id}`",
        "",
        blurb,
        "",
        "| Field | Value |",
        "|-------|--------|",
        f"| `evidence_tier` | `{tier}` |",
        f"| `projector_mode` | `{mode}` |",
        f"| Host-realistic | {host} |",
        f"| Native arm (`shielded-native-moreau`) | {native} |",
        f"| Parity fixture gold source | {fixture} |",
        f"| Family `current_run_id` | {current} |",
        f"| Export `export_kind` | `{export_kind}` |",
        f"| Export source | `benchmarks/external_evidence/offline_graph_export_upstream.json` |"
        if catalog.get("host_realistic")
        else f"| Export source | n/a |",
        f"| Parity status | `{parity_status}` |",
        f"| Scope contract | [`COMMUNITY_METADATA.json`](COMMUNITY_METADATA.json) |",
        "",
        "## What this run proves",
        "",
        "- Validator-required bundle surface passes `validate_run_bundle`",
        "- `summary.json` arms with governance gates recorded in `governance_status.json`",
    ]
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
            "- Universal batch speedup ([`docs/SOLVER_PATHS_AND_BATCHING.md`](../../docs/SOLVER_PATHS_AND_BATCHING.md))",
            "- Full Maps/session navigation graph (fork topology unless provenance says otherwise)",
            "",
            "## Validate and inspect",
            "",
            "```bash",
            "python -m conicshield.published_runs.cli verify " + run_id,
            "python -m conicshield.artifacts.validator_cli --run-dir " + run_rel_path,
            "python scripts/validate_published_bundle_profile.py --run-id " + run_id,
            "```",
            "",
            "Python API:",
            "",
            "```python",
            "from conicshield.published_runs import load_run, load_summary, verify_run",
            f"verify_run({run_id!r})",
            f"bundle = load_run({run_id!r})",
            "```",
            "",
        ]
    )
    if solver_lines:
        lines.extend(["## Solver stack", ""] + solver_lines + [""])
    if catalog.get("host_realistic"):
        lines.extend(
            [
                "## Source export",
                "",
                "- `benchmarks/external_evidence/offline_graph_export_upstream.json` "
                f"(`{export_kind}`)",
                "- Authority log: [`docs/REFERENCE_AUTHORITY_LOG.md`](../../docs/REFERENCE_AUTHORITY_LOG.md)",
                "- Export provenance: [`benchmarks/external_evidence/EXPORT_PROVENANCE.json`](../../benchmarks/external_evidence/EXPORT_PROVENANCE.json)",
                "",
            ]
        )
    lines.extend(
        [
            "## Further reading",
            "",
            "- Consumer guide: [`docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md`](../../docs/PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md)",
            "- Citation: [`docs/CITING_CONICSHIELD_ARTIFACTS.md`](../../docs/CITING_CONICSHIELD_ARTIFACTS.md)",
            "- Maintainer refresh: [`docs/HOST_REALISTIC_REFRESH_PROCEDURE.md`](../../docs/HOST_REALISTIC_REFRESH_PROCEDURE.md)",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    root = _repo_root()
    payload = load_published_run_index(repo_root=root)
    export_prov = _export_provenance(root)
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
        text = _render_readme(
            run_id=rid,
            run_rel_path=rel,
            run_dir=run_dir,
            catalog=catalog,
            export_prov=export_prov,
        )
        dest = run_dir / "README.md"
        dest.write_text(text, encoding="utf-8")
        print(dest, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
