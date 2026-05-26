#!/usr/bin/env python3
"""Host-realistic loop: upstream export JSON → bundle → optional published_runs copy.

Follows ``docs/HOST_REALISTIC_RUNBOOK.md``. Rejects the minimal contract fixture unless
``--allow-minimal-fixture`` is set (host-realistic evidence must not use only that path).

Example (licensed host, real projector):

  python scripts/run_host_realistic_publish.py \\
    --export-json /path/from/inter-sim-rl/export.json \\
    --run-id host-realistic-20260525 \\
    --no-passthrough \\
    --include-native-arm \\
    --copy-to-published

Structural rehearsal (committed upstream export, passthrough on unlicensed hosts):

  python scripts/run_host_realistic_publish.py \\
    --export-json benchmarks/external_evidence/offline_graph_export_upstream.json \\
    --run-id host-realistic-20260525 \\
    --passthrough \\
    --copy-to-published
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


_MINIMAL_FIXTURE_REL = "tests/fixtures/offline_graph_export_minimal.json"


def _is_minimal_fixture(export_json: Path, *, repo_root: Path) -> bool:
    try:
        return export_json.resolve() == (repo_root / _MINIMAL_FIXTURE_REL).resolve()
    except OSError:
        return False


def _run_produce_bundle(
    *,
    repo_root: Path,
    export_json: Path,
    run_id: str,
    passthrough: bool,
    include_native_arm: bool,
    seed: int,
) -> int:
    script = repo_root / "scripts" / "produce_reference_bundle.py"
    cmd = [
        sys.executable,
        str(script),
        "--export-json",
        str(export_json),
        "--run-id",
        run_id,
        "--seed",
        str(seed),
    ]
    if passthrough:
        cmd.append("--passthrough")
    else:
        cmd.append("--no-passthrough")
    if include_native_arm:
        cmd.append("--include-native-arm")
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(repo_root))


def _enhance_provenance(*, run_dir: Path, export_json: Path, repo_root: Path) -> None:
    prov_path = run_dir / "RUN_PROVENANCE.json"
    if not prov_path.is_file():
        return
    payload = json.loads(prov_path.read_text(encoding="utf-8"))
    try:
        rel_export = export_json.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel_export = str(export_json)
    payload["source_export_json"] = rel_export
    payload["host_realistic_evidence"] = True
    payload["minimal_fixture_export"] = _is_minimal_fixture(export_json, repo_root=repo_root)
    export_prov = repo_root / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    if export_prov.is_file():
        payload["external_export_provenance"] = "benchmarks/external_evidence/EXPORT_PROVENANCE.json"
    mode = str(payload.get("projector_mode", ""))
    summary_path = run_dir / "summary.json"
    has_native = False
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if isinstance(summary, list):
            has_native = any(row.get("label") == "shielded-native-moreau" for row in summary)
    if has_native and mode == "real_projector":
        payload["evidence_tier"] = "vendor_native"
    elif mode == "real_projector":
        payload["evidence_tier"] = "vendor_reference"
    elif payload.get("host_realistic_evidence"):
        payload["evidence_tier"] = "structural_export"
    else:
        payload["evidence_tier"] = "contract_fixture"
    prov_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _copy_to_published(*, runs_dir: Path, published_dir: Path, force: bool) -> None:
    if published_dir.exists():
        if any(published_dir.iterdir()) and not force:
            raise SystemExit(f"Refusing to clobber non-empty {published_dir} (use --force)")
        if force:
            shutil.rmtree(published_dir)
    published_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(runs_dir, published_dir)
    print(f"Copied bundle to {published_dir}", file=sys.stderr)


def _write_governance_scaffold(*, repo_root: Path, run_dir: Path, run_id: str, family_id: str) -> int:
    finalize = [
        sys.executable,
        "-m",
        "conicshield.governance.finalize_cli",
        "--run-dir",
        str(run_dir),
        "--family-id",
        family_id,
        "--task-contract-version",
        "v1",
        "--fixture-version",
        "fixture-v1",
        "--reference-fixture-dir",
        str(repo_root / "tests" / "fixtures" / "parity_reference"),
        "--current-release-path",
        str(repo_root / "benchmarks" / "releases" / family_id / "CURRENT.json"),
    ]
    print("Running:", " ".join(finalize), file=sys.stderr)
    rc = subprocess.call(finalize, cwd=str(repo_root))
    if rc != 0:
        return rc
    template = repo_root / "benchmarks" / "templates" / "governance_decision.template.md"
    dest = run_dir / "governance_decision.md"
    if template.is_file() and not dest.is_file():
        text = template.read_text(encoding="utf-8")
        text = (
            text.replace("<RUN_ID>", run_id)
            .replace("<FAMILY_ID>", family_id)
            .replace("<TASK_CONTRACT_VERSION>", "v1")
            .replace("<FIXTURE_VERSION>", "fixture-v1")
            .replace("<approve | reject | defer>", "defer")
            .replace("<names or roles>", "maintainer")
            .replace("<ISO-8601>", "pending")
        )
        dest.write_text(text, encoding="utf-8")
    return 0


def _write_published_readme(*, published_dir: Path, run_id: str, export_rel: str) -> None:
    text = (
        f"# Published run `{run_id}` (host-realistic export evidence)\n\n"
        f"Canonical **upstream-shaped** export: `{export_rel}` (not "
        f"`{_MINIMAL_FIXTURE_REL}`).\n\n"
        "Re-run ``scripts/run_host_realistic_publish.py`` with ``--no-passthrough`` "
        "and ``--include-native-arm`` on a licensed host to upgrade ``projector_mode`` "
        "and native arms; refresh ``benchmarks/PUBLISHED_RUN_INDEX.json`` after changes.\n"
    )
    (published_dir / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    repo = _repo_root()
    p = argparse.ArgumentParser(description="Host-realistic export → bundle → optional publish copy.")
    p.add_argument("--export-json", type=Path, required=True)
    p.add_argument("--run-id", type=str, required=True)
    p.add_argument("--passthrough", action="store_true")
    p.add_argument("--no-passthrough", action="store_true")
    p.add_argument("--include-native-arm", action="store_true")
    p.add_argument("--allow-minimal-fixture", action="store_true")
    p.add_argument("--copy-to-published", action="store_true")
    p.add_argument(
        "--force",
        action="store_true",
        help="Remove existing benchmarks/runs/<run_id> before producing a new bundle.",
    )
    p.add_argument(
        "--refresh-index",
        action="store_true",
        help="Run scripts/refresh_published_run_index.py after --copy-to-published.",
    )
    p.add_argument(
        "--governance-scaffold",
        action="store_true",
        help="Run finalize_cli and copy governance_decision template into the run directory.",
    )
    p.add_argument("--family-id", type=str, default="conicshield-transition-bank-v1")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    export_json = args.export_json
    if not export_json.is_file():
        print(f"Export JSON not found: {export_json}", file=sys.stderr)
        return 2

    if _is_minimal_fixture(export_json, repo_root=repo) and not args.allow_minimal_fixture:
        print(
            f"Refusing minimal fixture {_MINIMAL_FIXTURE_REL} for host-realistic publish. "
            "Use a real upstream export or --allow-minimal-fixture for smoke only.",
            file=sys.stderr,
        )
        return 2

    use_passthrough = bool(args.passthrough)
    if args.no_passthrough:
        use_passthrough = False
    if args.passthrough and args.no_passthrough:
        print("Specify at most one of --passthrough / --no-passthrough", file=sys.stderr)
        return 2
    if not args.passthrough and not args.no_passthrough:
        use_passthrough = False

    runs_dir = repo / "benchmarks" / "runs" / args.run_id
    if args.force and runs_dir.exists():
        shutil.rmtree(runs_dir)

    rc = _run_produce_bundle(
        repo_root=repo,
        export_json=export_json,
        run_id=args.run_id,
        passthrough=use_passthrough,
        include_native_arm=bool(args.include_native_arm),
        seed=args.seed,
    )
    if rc != 0:
        return rc

    _enhance_provenance(run_dir=runs_dir, export_json=export_json, repo_root=repo)

    from conicshield.artifacts.validator import validate_run_bundle

    validate_run_bundle(runs_dir)
    print(f"OK validate_run_bundle: {runs_dir}", file=sys.stderr)

    if args.governance_scaffold:
        rc = _write_governance_scaffold(
            repo_root=repo,
            run_dir=runs_dir,
            run_id=args.run_id,
            family_id=args.family_id,
        )
        if rc != 0:
            return rc

    if args.copy_to_published:
        published_dir = repo / "benchmarks" / "published_runs" / args.run_id
        _copy_to_published(runs_dir=runs_dir, published_dir=published_dir, force=bool(args.force))
        try:
            rel_export = export_json.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            rel_export = str(export_json)
        _write_published_readme(published_dir=published_dir, run_id=args.run_id, export_rel=rel_export)
        _enhance_provenance(run_dir=published_dir, export_json=export_json, repo_root=repo)
        if args.governance_scaffold:
            gov = runs_dir / "governance_status.json"
            if gov.is_file():
                shutil.copy2(gov, published_dir / "governance_status.json")
            gdec = runs_dir / "governance_decision.md"
            if gdec.is_file():
                shutil.copy2(gdec, published_dir / "governance_decision.md")
        if args.refresh_index:
            script = repo / "scripts" / "refresh_published_run_index.py"
            rc = subprocess.call([sys.executable, str(script)], cwd=str(repo))
            if rc != 0:
                return rc

    print(
        "\nNext: governed_local_promotion.py validate/parity-sync/index; "
        "finalize_cli / release_cli per docs/MAINTAINER_RUNBOOK.md",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
