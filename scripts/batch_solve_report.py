#!/usr/bin/env python3
"""Summarize native_microbatch vs native_compiled_real_batch from performance_benchmark output.

Reads ``output/performance_summary.json`` (or ``--input``) and writes ``batch_solve_report.json``
with per-row speedup (sequential / batched mean_sec).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BATCH_STORY_VIABILITY = "viability_only"
_BATCH_STORY_THROUGHPUT = "throughput_win"
_BATCH_STORY_BELOW = "below_viability"


def _speedup_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = summary.get("rows") or []
    by_key: dict[tuple[Any, ...], dict[str, float]] = {}
    for row in rows:
        path = row.get("path")
        if path not in ("native_microbatch", "native_compiled_real_batch"):
            continue
        key = (
            row.get("scenario_id"),
            row.get("conditioning"),
            row.get("device"),
            row.get("auto_tune"),
            row.get("batch_size"),
        )
        mean_sec = row.get("mean_sec")
        if mean_sec is None:
            continue
        by_key.setdefault(key, {})[str(path)] = float(mean_sec)

    out: list[dict[str, Any]] = []
    for key, paths in sorted(by_key.items()):
        seq = paths.get("native_microbatch")
        bat = paths.get("native_compiled_real_batch")
        if seq is None or bat is None or bat <= 0:
            continue
        out.append(
            {
                "scenario_id": key[0],
                "conditioning": key[1],
                "device": key[2],
                "auto_tune": key[3],
                "batch_size": key[4],
                "mean_sec_sequential": seq,
                "mean_sec_batched": bat,
                "speedup_ratio": seq / bat,
            }
        )
    return out


def _load_acceptance_policy(root: Path) -> dict[str, Any]:
    path = root / "benchmarks" / "reports" / "batch_acceptance_policy.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _interpret_batch_story(*, comparisons: list[dict[str, Any]], policy: dict[str, Any]) -> str:
    if not comparisons:
        return _BATCH_STORY_BELOW
    max_ratio = max(float(c["speedup_ratio"]) for c in comparisons)
    throughput_min = float((policy.get("throughput_advisory") or {}).get("min_speedup_ratio", 1.05))
    viability_min = float((policy.get("viability") or {}).get("min_speedup_ratio", 0.98))
    if max_ratio >= throughput_min:
        return _BATCH_STORY_THROUGHPUT
    if max_ratio >= viability_min:
        return _BATCH_STORY_VIABILITY
    return _BATCH_STORY_BELOW


def build_batch_solve_report_payload(
    *,
    summary: dict[str, Any],
    source: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    comparisons = _speedup_rows(summary)
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[1]
    policy = _load_acceptance_policy(root)
    batch_story = _interpret_batch_story(comparisons=comparisons, policy=policy)
    advisory = (
        "Governed true batch solve path exists; public claims stay at viability unless "
        "throughput_advisory tier is met on representative scenarios."
        if batch_story != _BATCH_STORY_THROUGHPUT
        else "Throughput advisory tier met on at least one row; still not a universal speedup claim."
    )
    return {
        "schema_version": "conicshield_batch_solve_report/v2",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(source),
        "batch_story": batch_story,
        "batch_story_advisory": advisory,
        "comparisons": comparisons,
        "summary": {
            "pairs": len(comparisons),
            "max_speedup_ratio": max((c["speedup_ratio"] for c in comparisons), default=None),
        },
    }


def write_batch_solve_report(*, summary_path: Path, out_path: Path) -> dict[str, Any] | None:
    """Write batch comparison JSON; return payload or None if no batch rows."""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    payload = build_batch_solve_report_payload(summary=summary, source=summary_path)
    if not payload["comparisons"]:
        return None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=None,
        help="performance_summary.json (default: <repo>/output/performance_summary.json).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write report JSON (default: <repo>/output/batch_solve_report.json).",
    )
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    in_path = args.input or (root / "output" / "performance_summary.json")
    if not in_path.is_file():
        print(f"Missing input: {in_path}", flush=True)
        return 2
    out_path = args.out or (root / "output" / "batch_solve_report.json")
    payload = write_batch_solve_report(summary_path=in_path, out_path=out_path)
    if payload is None:
        print("No native_microbatch / native_compiled_real_batch pairs in input.", flush=True)
        return 0
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
