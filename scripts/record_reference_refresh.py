#!/usr/bin/env python3
"""Append a flagship refresh row to REFERENCE_AUTHORITY_LOG and EXPORT_PROVENANCE.refresh_history."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git_ref(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout.strip()
    return "unknown"


def _append_provenance_history(
    *,
    prov_path: Path,
    trigger: str,
    workflow: str,
    export_kind: str,
    git_ref: str,
    authority_ok: bool,
    notes: str,
) -> int:
    prov: dict = {}
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    history = list(prov.get("refresh_history") or [])
    next_idx = max((int(h.get("refresh_index", 0)) for h in history), default=0) + 1
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    history.append(
        {
            "refresh_index": next_idx,
            "completed_at_utc": now,
            "trigger": trigger,
            "workflow": workflow,
            "export_kind": export_kind,
            "git_ref": git_ref,
            "authority_ok": authority_ok,
            "notes": notes,
        }
    )
    prov["refresh_history"] = history
    prov["last_flagship_refresh_at_utc"] = now
    prov_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    return next_idx


def _append_log_table_row(
    *,
    log_path: Path,
    index: int,
    completed_at_utc: str,
    trigger: str,
    workflow: str,
    export_kind: str,
    git_ref: str,
    authority_ok: bool,
    notes: str,
) -> None:
    text = log_path.read_text(encoding="utf-8")
    marker = "<!-- Append rows via:"
    row = (
        f"| {index} | {completed_at_utc} | {trigger} | {workflow} | {export_kind} | "
        f"`{git_ref}` | {'yes' if authority_ok else 'no'} | {notes} |"
    )
    if marker in text:
        text = text.replace(marker, f"{row}\n\n{marker}", 1)
    else:
        text = text.rstrip() + "\n" + row + "\n"
    log_path.write_text(text, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trigger", required=True, help="e.g. calendar-cadence, inter-sim-revision")
    p.add_argument(
        "--workflow",
        default="live-export",
        help="live-export | governance-only | manual",
    )
    p.add_argument("--export-kind", default="live_upstream_dump")
    p.add_argument("--authority-ok", action="store_true", help="reference_authority_check passed")
    p.add_argument("--notes", default="")
    args = p.parse_args()

    repo = _repo_root()
    prov_path = repo / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    log_path = repo / "docs" / "REFERENCE_AUTHORITY_LOG.md"
    if not log_path.is_file():
        print(f"Missing {log_path}", file=sys.stderr)
        return 2

    # Remove stale placeholder row 4 if present (pending partial)
    text = log_path.read_text(encoding="utf-8")
    text = re.sub(r"\| 4 \| [^\n]+\n", "", text)
    log_path.write_text(text, encoding="utf-8")

    git_ref = _git_ref(repo)
    idx = _append_provenance_history(
        prov_path=prov_path,
        trigger=args.trigger,
        workflow=args.workflow,
        export_kind=args.export_kind,
        git_ref=git_ref,
        authority_ok=args.authority_ok,
        notes=args.notes,
    )
    history = json.loads(prov_path.read_text(encoding="utf-8"))["refresh_history"]
    completed = history[-1]["completed_at_utc"]
    _append_log_table_row(
        log_path=log_path,
        index=idx,
        completed_at_utc=completed,
        trigger=args.trigger,
        workflow=args.workflow,
        export_kind=args.export_kind,
        git_ref=git_ref,
        authority_ok=args.authority_ok,
        notes=args.notes or "—",
    )
    print(f"Recorded refresh #{idx} at {completed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
