#!/usr/bin/env python3
"""Build a transition bank from an offline graph export JSON, then run reference_run (real or passthrough).

Use this for the P0 path: real projector requires a licensed Moreau stack on Linux/WSL2.

Example (in-repo minimal export, real solver):

  python scripts/produce_reference_bundle.py \\
    --export-json tests/fixtures/offline_graph_export_minimal.json \\
    --run-id canonical-from-minimal-export \\
    --no-passthrough

CI / no license:

  python scripts/produce_reference_bundle.py \\
    --export-json tests/fixtures/offline_graph_export_minimal.json \\
    --run-id ci-smoke-bundle \\
    --passthrough
"""

from __future__ import annotations

import argparse
import importlib.metadata as ilm
import json
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from conicshield.bench.offline_graph_export import load_offline_graph_export, transition_bank_from_offline_graph_export
from conicshield.bench.reference_run import run_benchmark_bundle
from conicshield.bench.transition_bank import TransitionBank


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _bank_schema() -> dict[str, Any]:
    path = _repo_root() / "schemas" / "transition_bank_file.schema.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _validate_bank_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator(_bank_schema()).validate(payload)


def _cvxpy_has_moreau() -> tuple[bool, str]:
    try:
        import cvxpy as cp
    except Exception as exc:
        return False, f"cvxpy import failed: {exc}"
    if getattr(cp, "MOREAU", None) is None:
        return False, "cvxpy.MOREAU attribute missing"
    try:
        solvers = {str(s).upper() for s in cp.installed_solvers()}
    except Exception as exc:
        return False, f"cvxpy installed_solvers() failed: {exc}"
    if "MOREAU" not in solvers:
        return False, "MOREAU solver is not registered in cvxpy.installed_solvers()"
    return True, ""


def _collect_solver_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for pkg in ("moreau", "cvxpy", "cvxpylayers"):
        try:
            out[pkg] = ilm.version(pkg)
        except Exception:
            out[pkg] = "not-installed"
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Offline export → bank → reference_run bundle under benchmarks/runs/.")
    p.add_argument("--export-json", type=Path, required=True, help="offline_transition_graph_export/v1 JSON.")
    p.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Output directory name under benchmarks/runs/ (default: random).",
    )
    p.add_argument(
        "--passthrough",
        action="store_true",
        help="Use PassthroughProjector (no Moreau license).",
    )
    p.add_argument("--no-passthrough", action="store_true", help="Real CVXPY/Moreau path (default if neither flag).")
    p.add_argument("--include-native-arm", action="store_true", help="Add native_moreau arm (no passthrough only).")
    p.add_argument(
        "--strict-real-projector",
        action="store_true",
        help="Fail unless the run is produced via the real projector path (non-passthrough).",
    )
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    use_passthrough = bool(args.passthrough)
    if args.no_passthrough:
        use_passthrough = False
    if args.passthrough and args.no_passthrough:
        print("Specify at most one of --passthrough / --no-passthrough", file=sys.stderr)
        return 2
    if args.strict_real_projector and use_passthrough:
        print("--strict-real-projector forbids --passthrough", file=sys.stderr)
        return 2
    if not use_passthrough:
        ok, reason = _cvxpy_has_moreau()
        if not ok:
            print(
                f"Real projector preflight failed: {reason}",
                file=sys.stderr,
            )
            print(
                "Install vendor MOREAU stack, then retry with --no-passthrough.",
                file=sys.stderr,
            )
            return 3

    root = _repo_root()
    runs_root = root / "benchmarks" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or f"run-{uuid.uuid4().hex[:12]}"
    out_dir = runs_root / run_id
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"Refusing to clobber non-empty {out_dir}", file=sys.stderr)
        return 1

    export_payload = load_offline_graph_export(args.export_json)
    bank = transition_bank_from_offline_graph_export(export_payload)
    bank_id = f"bank_{uuid.uuid4().hex[:12]}"
    provenance = {
        "bank_id": bank_id,
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": "scripts.produce_reference_bundle",
        "generator_version": "0.1.0",
        "schema_version": "transition_bank_file/v1",
        "notes": f"from-offline-graph-export source={args.export_json}",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
    try:
        bank.to_json(tmp_path, provenance=provenance)
        _validate_bank_file(tmp_path)
        bank_loaded = TransitionBank.from_json(tmp_path)
        run_benchmark_bundle(
            out_dir=out_dir,
            bank=bank_loaded,
            use_passthrough_projector=use_passthrough,
            seed=args.seed,
            include_native_arm=bool(args.include_native_arm),
            benchmark_name=run_id,
        )
        provenance_payload = {
            "schema_version": "conicshield_reference_run_provenance/v1",
            "run_id": run_id,
            "projector_mode": "passthrough" if use_passthrough else "real_projector",
            "strict_real_projector": bool(args.strict_real_projector),
            "source_export_json": str(args.export_json),
            "generated_by": "scripts/produce_reference_bundle.py",
            "seed": int(args.seed),
        }
        (out_dir / "RUN_PROVENANCE.json").write_text(
            json.dumps(provenance_payload, indent=2),
            encoding="utf-8",
        )
        (out_dir / "solver_versions.json").write_text(
            json.dumps(_collect_solver_versions(), indent=2),
            encoding="utf-8",
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    mode = "passthrough" if use_passthrough else "real_projector"
    print(f"Wrote validated bundle: {out_dir} ({mode})")
    if use_passthrough:
        print("Note: use --no-passthrough on a licensed host for the canonical vendor-backed reference run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
