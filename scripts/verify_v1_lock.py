#!/usr/bin/env python3
"""Run v1 reference-system lock checks and print an auditor-facing summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path, label: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    ok = proc.returncode == 0
    detail = (proc.stdout or "") + (proc.stderr or "")
    if not detail.strip():
        detail = f"exit {proc.returncode}"
    return ok, f"{label}: {'OK' if ok else 'FAIL'} — {detail.strip()[:240]}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--full",
        action="store_true",
        help="Also run make verify-reference-system (slow; same as verify-v1-lock).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable summary on stdout after human report.",
    )
    args = p.parse_args()
    root = _repo_root()
    py = sys.executable
    results: list[dict[str, object]] = []

    steps: list[tuple[str, list[str]]] = [
        ("index_integrity", [py, str(root / "scripts" / "refresh_published_run_index.py"), "--check"]),
        ("reference_system_status", [py, str(root / "scripts" / "generate_reference_system_status.py"), "--check"]),
        ("export_cadence", [py, str(root / "scripts" / "check_reference_refresh_cadence.py"), "--max-days", "35"]),
        ("full_refresh_cadence", [py, str(root / "scripts" / "check_flagship_full_refresh_cadence.py"), "--max-days", "35"]),
        ("bundle_profile", [py, str(root / "scripts" / "validate_published_bundle_profile.py")]),
        (
            "community_verify",
            [
                py,
                "-m",
                "pytest",
                "tests/test_published_runs_api.py",
                "tests/test_published_runs_cli.py",
                "tests/examples/test_public_examples_smoke.py",
                "-q",
                "--tb=line",
            ],
        ),
        ("public_claim_phrases", [py, str(root / "scripts" / "check_public_claim_phrases.py")]),
    ]
    for name, cmd in steps:
        ok, msg = _run(cmd, cwd=root, label=name)
        results.append({"check": name, "ok": ok})
        print(msg)

    if args.full:
        ok, msg = _run(["make", "verify-reference-system"], cwd=root, label="verify_reference_system")
        results.append({"check": "verify_reference_system", "ok": ok})
        print(msg)
    else:
        print("skip: verify-reference-system (pass --full or run make verify-v1-lock)")

    status_path = root / "benchmarks" / "reports" / "reference_system_status.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        print("\nflagship:", status.get("flagship_run_id"))
        print("authority_aligned:", status.get("reference_authority_aligned"))
        print("full_refresh_cadence_ok:", status.get("full_refresh_cadence_ok"))
        community = status.get("community_dataset") or {}
        print("onboarding:", community.get("onboarding_doc"))

    all_ok = all(bool(r["ok"]) for r in results)
    if args.json:
        print(json.dumps({"v1_lock_checks": results, "all_ok": all_ok}, indent=2))
    print("\n" + ("v1 lock checks PASSED" if all_ok else "v1 lock checks FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
