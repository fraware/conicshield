#!/usr/bin/env python3
"""Local vendor attestation runner (mirrors vendor-ci-moreau evidence gate).

Runs the mandatory known-feasible + failure-policy native solves, vendor-marked
pytest with JUnit, then ``assert_vendor_ci_evidence.py``.

This script **cannot** false-pass:
  - Missing Moreau / license / CompiledSolver → exit 2 (NOT_RUN / blocked).
  - Evidence gate failures → exit 1.
  - Success requires real native solves and non-skipped vendor tests.

Secrets are never printed. Prefer WSL/Linux with a licensed Moreau install.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_dotenv(repo: Path) -> None:
    env_path = repo / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        # Minimal parser — never prints values.
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, _, val = s.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'")
            if key and key not in os.environ and val:
                os.environ[key] = val
        return
    load_dotenv(env_path, override=False)


def _write_moreau_key_if_requested() -> None:
    if os.environ.get("CONICSHIELD_WRITE_MOREAU_KEY", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return
    key = os.environ.get("MOREAU_LICENSE_KEY", "").strip()
    if not key:
        return
    d = Path.home() / ".moreau"
    d.mkdir(parents=True, exist_ok=True)
    (d / "key").write_text(key, encoding="utf-8")


def _preflight() -> dict:
    info: dict = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
    }
    if sys.platform == "win32":
        info["blocked_reason"] = (
            "Native Windows cannot run licensed Optimal Intellect Moreau. "
            "Use WSL2 Ubuntu with solver-moreau-cpu."
        )
        return info
    try:
        import moreau  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        info["blocked_reason"] = f"moreau import failed: {type(exc).__name__}"
        return info
    if not hasattr(moreau, "CompiledSolver"):
        info["blocked_reason"] = "installed moreau lacks CompiledSolver (likely PyPI stub)"
        return info
    try:
        import cvxpy as cp
    except Exception as exc:  # noqa: BLE001
        info["blocked_reason"] = f"cvxpy import failed: {type(exc).__name__}"
        return info
    if not hasattr(cp, "MOREAU"):
        info["blocked_reason"] = "cp.MOREAU not registered"
        return info
    info["moreau_ok"] = True
    info["compiled_solver"] = True
    info["cvxpy_moreau"] = True
    return info


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Evidence directory (default: docs/stabilization/vendor_attestation_local/).",
    )
    p.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Only run mandatory solves + evidence schema check (no JUnit).",
    )
    p.add_argument(
        "--write-moreau-key",
        action="store_true",
        help="Write MOREAU_LICENSE_KEY from env/.env to ~/.moreau/key.",
    )
    args = p.parse_args()

    repo = _repo_root()
    _load_dotenv(repo)
    if args.write_moreau_key:
        os.environ["CONICSHIELD_WRITE_MOREAU_KEY"] = "1"
    _write_moreau_key_if_requested()

    out_dir = args.out_dir or (repo / "docs" / "stabilization" / "vendor_attestation_local")
    out_dir.mkdir(parents=True, exist_ok=True)

    preflight = _preflight()
    status_path = out_dir / "attestation_status.json"
    checklist_path = out_dir / "CHECKLIST.md"

    checklist = """# Local vendor attestation checklist

Mirrors `.github/workflows/solver-ci.yml` evidence path. Do **not** claim the
vendor CI gate cleared without green evidence below.

## Prerequisites (WSL2 / Linux)

1. `GEMFURY_TOKEN` or `MOREAU_EXTRA_INDEX_URL` / `MOREAU_PIP_EXTRA_INDEX_URL` in `.env`
2. `MOREAU_LICENSE_KEY` in `.env` (or `~/.moreau/key`)
3. Bootstrap: `CONICSHIELD_BOOTSTRAP_PROFILE=moreau-cpu bash scripts/bootstrap_moreau.sh`
4. Verify: `python -m moreau check`

## Commands

```bash
export CONICSHIELD_VENDOR_REQUIRED=1
python scripts/run_local_vendor_attestation.py --out-dir docs/stabilization/vendor_attestation_local
```

## Success criteria (all required)

- `attestation_status.json` → `status` is `PASS`
- `mandatory_native_solves.json` → `known_feasible_ok` and failure-policy OK; `native_solve_count` ≥ 1
- `vendor_pytest.junit.xml` present with executed vendor tests
- `assert_vendor_ci_evidence` exit 0 (recorded in status)

## Failure modes that must remain red

- Native Windows host
- PyPI stub `moreau` without `CompiledSolver`
- Missing license / GemFury install
- Empty or all-skipped pytest suites
"""
    checklist_path.write_text(checklist, encoding="utf-8")

    if preflight.get("blocked_reason"):
        payload = {
            "schema_version": "conicshield_local_vendor_attestation/v1",
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "NOT_RUN",
            "blocked_reason": preflight["blocked_reason"],
            "preflight": preflight,
            "gate_claim": "Vendor CI real-solve attestation remains BLOCKED",
        }
        status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 2

    os.environ["CONICSHIELD_VENDOR_REQUIRED"] = "1"
    mandatory = out_dir / "mandatory_native_solves.json"
    junit = out_dir / "vendor_pytest.junit.xml"

    rc_mand = subprocess.call(
        [
            sys.executable,
            str(repo / "scripts" / "vendor_mandatory_native_solves.py"),
            "--out",
            str(mandatory),
        ],
        cwd=str(repo),
    )
    if rc_mand != 0:
        payload = {
            "schema_version": "conicshield_local_vendor_attestation/v1",
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "FAIL",
            "stage": "mandatory_native_solves",
            "exit_code": rc_mand,
            "preflight": preflight,
            "gate_claim": "Vendor CI real-solve attestation remains BLOCKED",
        }
        status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 1

    if not args.skip_pytest:
        rc_py = subprocess.call(
            [
                sys.executable,
                "-m",
                "pytest",
                str(repo / "tests"),
                "-q",
                "-m",
                "solver or requires_moreau",
                f"--junitxml={junit}",
                "--tb=short",
            ],
            cwd=str(repo),
        )
    else:
        # Minimal JUnit so the evidence gate can still evaluate mandatory solves
        # when the caller explicitly skips pytest (debug only).
        junit.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<testsuite name="skipped-by-flag" tests="0" skipped="0" failures="0" errors="0"/>\n',
            encoding="utf-8",
        )
        rc_py = 0

    rc_gate = subprocess.call(
        [
            sys.executable,
            str(repo / "scripts" / "assert_vendor_ci_evidence.py"),
            "--junit",
            str(junit),
            "--native-evidence",
            str(mandatory),
            "--min-executed",
            "1",
        ],
        cwd=str(repo),
    )

    ok = rc_mand == 0 and rc_py == 0 and rc_gate == 0 and not args.skip_pytest
    payload = {
        "schema_version": "conicshield_local_vendor_attestation/v1",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "PASS" if ok else ("INCOMPLETE" if args.skip_pytest else "FAIL"),
        "exit_codes": {
            "mandatory_native_solves": rc_mand,
            "pytest_vendor": rc_py,
            "assert_vendor_ci_evidence": rc_gate,
        },
        "artifacts": {
            "mandatory_native_solves": _relpath(mandatory, repo),
            "junit": _relpath(junit, repo),
            "checklist": _relpath(checklist_path, repo),
        },
        "preflight": preflight,
        "skip_pytest": bool(args.skip_pytest),
        "gate_claim": (
            "Vendor CI real-solve attestation PASS (local)"
            if ok
            else "Vendor CI real-solve attestation remains BLOCKED"
        ),
    }
    status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status", "gate_claim", "exit_codes")}, indent=2))
    return 0 if ok else (2 if args.skip_pytest else 1)


if __name__ == "__main__":
    raise SystemExit(main())
