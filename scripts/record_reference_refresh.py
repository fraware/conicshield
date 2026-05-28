#!/usr/bin/env python3
"""Append or amend flagship refresh rows in REFERENCE_AUTHORITY_LOG and EXPORT_PROVENANCE."""

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


def _format_log_row(
    *,
    index: int,
    completed_at_utc: str,
    trigger: str,
    workflow: str,
    export_kind: str,
    git_ref: str,
    authority_ok: bool,
    notes: str,
) -> str:
    return (
        f"| {index} | {completed_at_utc} | {trigger} | {workflow} | {export_kind} | "
        f"`{git_ref}` | {'yes' if authority_ok else 'no'} | {notes or '—'} |"
    )


def _upsert_log_row(*, log_path: Path, index: int, row: str) -> None:
    text = log_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\| {index} \| [^\n]+\n", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(row + "\n", text, count=1)
    else:
        marker = "<!-- Append rows via:"
        if marker in text:
            text = text.replace(marker, f"{row}\n\n{marker}", 1)
        else:
            text = text.rstrip() + "\n" + row + "\n"
    log_path.write_text(text, encoding="utf-8")


def _inter_sim_revision_sha(repo: Path) -> str | None:
    rev = repo / "third_party" / "inter-sim-rl" / "REVISION"
    if not rev.is_file():
        return None
    for line in rev.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha="):
            return line.split("=", 1)[1].strip()
    text = rev.read_text(encoding="utf-8").strip()
    return text if text and "=" not in text else None


def _record_entry(
    *,
    prov_path: Path,
    log_path: Path,
    trigger: str,
    workflow: str,
    export_kind: str,
    git_ref: str,
    authority_ok: bool,
    notes: str,
    amend_last: bool,
) -> int:
    prov: dict = {}
    if prov_path.is_file():
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    history = list(prov.get("refresh_history") or [])
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if amend_last and history:
        entry = dict(history[-1])
        idx = int(entry.get("refresh_index", len(history)))
        entry.update(
            {
                "completed_at_utc": now,
                "trigger": trigger,
                "workflow": workflow,
                "export_kind": export_kind,
                "git_ref": git_ref,
                "authority_ok": authority_ok,
                "notes": notes,
            }
        )
        history[-1] = entry
    else:
        idx = max((int(h.get("refresh_index", 0)) for h in history), default=0) + 1
        history.append(
            {
                "refresh_index": idx,
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
    repo = prov_path.resolve().parents[2]
    sha = _inter_sim_revision_sha(repo)
    if sha:
        prov["inter_sim_revision_sha"] = sha
    prov_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")

    row = _format_log_row(
        index=idx,
        completed_at_utc=now,
        trigger=trigger,
        workflow=workflow,
        export_kind=export_kind,
        git_ref=git_ref,
        authority_ok=authority_ok,
        notes=notes,
    )
    _upsert_log_row(log_path=log_path, index=idx, row=row)
    return idx


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trigger", required=True, help="e.g. calendar-cadence, inter-sim-revision")
    p.add_argument(
        "--workflow",
        default="live-export",
        help="live-export | live-export-full | governance-only | manual",
    )
    p.add_argument("--export-kind", default="live_upstream_dump")
    p.add_argument("--authority-ok", action="store_true", help="reference_authority_check passed")
    p.add_argument("--notes", default="")
    p.add_argument(
        "--amend-last",
        action="store_true",
        help="Update the latest refresh_history entry instead of appending.",
    )
    args = p.parse_args()

    repo = _repo_root()
    prov_path = repo / "benchmarks" / "external_evidence" / "EXPORT_PROVENANCE.json"
    log_path = repo / "docs" / "REFERENCE_AUTHORITY_LOG.md"
    if not log_path.is_file():
        print(f"Missing {log_path}", file=sys.stderr)
        return 2

    idx = _record_entry(
        prov_path=prov_path,
        log_path=log_path,
        trigger=args.trigger,
        workflow=args.workflow,
        export_kind=args.export_kind,
        git_ref=_git_ref(repo),
        authority_ok=args.authority_ok,
        notes=args.notes,
        amend_last=args.amend_last,
    )
    verb = "Amended" if args.amend_last else "Recorded"
    print(f"{verb} refresh #{idx}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
