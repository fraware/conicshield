"""ConicShield console CLI.

Commands:
  solver-doctor   Emit packaging / provenance / capability evidence (JSON or text).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence


def _cmd_solver_doctor(args: argparse.Namespace) -> int:
    from conicshield.platform.doctor import run_solver_doctor

    report = run_solver_doctor(run_license_check=bool(args.license_check))
    payload = report.as_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(f"python: {payload['python_version']}  os: {payload['os_name']}/{payload['arch']}")
        print(f"executable: {payload['executable_path']}")
        print(f"env: {payload['environment_type']}  commit: {payload['conicshield_commit']}")
        auto = payload["selected_solver_settings"]["auto_policy"]
        print(f"AUTO -> {auto['auto_resolves_to']} (never vendor-from-import)")
        for note in payload.get("platform_notes") or []:
            print(f"note: {note}")
        for warn in payload.get("migration_warnings") or []:
            print(f"migration: {warn}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="conicshield", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser(
        "solver-doctor",
        help="Record Python/OS/package/Moreau/CVXPY/device/commit/solver settings evidence",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (secrets redacted)",
    )
    doctor.add_argument(
        "--license-check",
        action="store_true",
        help="Attempt Moreau license/entitlement probe when the vendor API is present",
    )
    doctor.set_defaults(func=_cmd_solver_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
