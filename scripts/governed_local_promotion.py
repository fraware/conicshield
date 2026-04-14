#!/usr/bin/env python3
"""Chained local steps for governed bundles: validate, parity fixture sync, published-run index.

Run on a licensed host after ``produce_reference_bundle`` / ``reference_run`` (non-passthrough).

**P2-8 export loop (conceptual):** upstream ``offline_transition_graph_export/v1`` JSON to
``scripts/produce_reference_bundle.py --export-json ... --no-passthrough``, then this tool's
``validate`` / ``parity-sync``, then ``finalize_cli`` / copy to ``benchmarks/published_runs/<run_id>/``,
then ``index write`` (see ``benchmarks/published_runs/README.md``).

Does not read ``.env`` itself; load secrets in the shell or use ``python-dotenv`` / ``run_live_vendor_tests.py``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_validate(run_dir: Path) -> int:
    from conicshield.artifacts.validator import validate_run_bundle

    validate_run_bundle(run_dir)
    print(f"OK validate_run_bundle: {run_dir}", file=sys.stderr)
    return 0


def _run_parity_sync(*, source: Path, dest: Path | None) -> int:
    repo = _repo_root()
    script = repo / "scripts" / "regenerate_parity_fixture.py"
    cmd = [sys.executable, str(script), "--source", str(source)]
    if dest is not None:
        cmd.extend(["--dest", str(dest)])
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(repo))


def _run_index(*, check: bool) -> int:
    repo = _repo_root()
    script = repo / "scripts" / "refresh_published_run_index.py"
    cmd = [sys.executable, str(script)]
    if check:
        cmd.append("--check")
    print("Running:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=str(repo))


def _print_next_steps(*, run_dir: Path, family_id: str) -> None:
    print(
        "\nNext (human-governed):\n"
        f"  1. Parity replay: python -m conicshield.parity.cli "
        f"--reference-dir tests/fixtures/parity_reference --out-dir output/parity_out\n"
        f"  2. finalize_cli --run-dir {run_dir} --family-id {family_id} ... "
        f"(see docs/MAINTAINER_RUNBOOK.md)\n"
        f"  3. Copy validated bundle to benchmarks/published_runs/<run_id>/ if not already there.\n"
        f"  4. python scripts/refresh_published_run_index.py\n",
        file=sys.stderr,
    )


def main() -> int:
    repo = _repo_root()
    p = argparse.ArgumentParser(description="Governed local promotion helpers (validate / parity / index).")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate_run_bundle on a run directory")
    v.add_argument("--run-dir", type=Path, required=True)

    s = sub.add_parser(
        "parity-sync",
        help="Run scripts/regenerate_parity_fixture.py --source <validated bundle>",
    )
    s.add_argument("--source", type=Path, required=True, help="Validated benchmarks/runs/<id> or published_runs/<id>.")
    s.add_argument(
        "--dest",
        type=Path,
        default=_repo_root() / "tests" / "fixtures" / "parity_reference",
        help="Parity fixture directory to overwrite (default: tests/fixtures/parity_reference).",
    )

    i = sub.add_parser("index", help="Refresh or check benchmarks/PUBLISHED_RUN_INDEX.json")
    i.add_argument("--check", action="store_true", help="Fail if index is stale (default: regenerate file).")

    a = sub.add_parser(
        "all",
        help="validate, parity-sync (default dest), index --check",
    )
    a.add_argument("--source", type=Path, required=True, help="Validated bundle directory.")
    a.add_argument(
        "--parity-dest",
        type=Path,
        default=repo / "tests" / "fixtures" / "parity_reference",
        help="Parity fixture directory to overwrite.",
    )
    a.add_argument("--family-id", type=str, default="conicshield-transition-bank-v1")
    a.add_argument("--skip-index-check", action="store_true")

    args = p.parse_args()

    if args.cmd == "validate":
        return _run_validate(args.run_dir.resolve())

    if args.cmd == "parity-sync":
        return _run_parity_sync(source=args.source.resolve(), dest=args.dest.resolve())

    if args.cmd == "index":
        if args.check:
            return _run_index(check=True)
        return _run_index(check=False)

    if args.cmd == "all":
        src = args.source.resolve()
        rc = _run_validate(src)
        if rc != 0:
            return rc
        rc = _run_parity_sync(source=src, dest=args.parity_dest.resolve())
        if rc != 0:
            return rc
        if not args.skip_index_check:
            rc = _run_index(check=True)
            if rc != 0:
                print(
                    "Index check failed (expected after bundle changes). "
                    "Run: python scripts/refresh_published_run_index.py",
                    file=sys.stderr,
                )
        _print_next_steps(run_dir=src, family_id=args.family_id)
        return rc

    raise AssertionError("unhandled subcommand")


if __name__ == "__main__":
    raise SystemExit(main())
