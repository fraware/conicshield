#!/usr/bin/env python3
"""Layer G: validate a governed run bundle and write artifact_validation_report.{json,md}."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conicshield.artifacts.validator import ArtifactValidationError, validate_run_bundle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Artifact validation report",
        "",
        f"**Generated:** {payload.get('generated_at_utc', '')}",
        f"**Run directory:** `{payload.get('run_dir', '')}`",
        f"**Status:** **{payload.get('status', '')}**",
        "",
    ]
    if payload.get("error"):
        lines.extend(["## Error", "", "```", str(payload["error"]), "```", ""])
    else:
        lines.extend(["Bundle passed `validate_run_bundle` (schemas, invariants, cross-field checks).", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a benchmark run directory and write Layer G report.")
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Directory containing config.json, summary.json, episodes.jsonl, etc.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_repo_root() / "output"),
        help="Directory for artifact_validation_report.json and .md (default: output/)",
    )
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    ts = datetime.now(tz=UTC).isoformat()
    payload: dict[str, Any] = {
        "generated_at_utc": ts,
        "run_dir": str(run_dir),
        "status": "ok",
    }
    try:
        validate_run_bundle(run_dir)
    except ArtifactValidationError as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
    except OSError as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)

    _write_json(out_dir / "artifact_validation_report.json", payload)
    _write_md(out_dir / "artifact_validation_report.md", payload)
    print(out_dir / "artifact_validation_report.json")
    print(out_dir / "artifact_validation_report.md")
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
