from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
            fh.write("\n")


def write_run_bundle(
    *,
    run_dir: str | Path,
    config: dict[str, Any],
    config_schema: dict[str, Any],
    summary: list[dict[str, Any]],
    summary_schema: dict[str, Any],
    episodes: list[dict[str, Any]],
    episodes_schema: dict[str, Any],
    transition_bank: dict[str, Any],
    benchmark_card_md: str,
    governance_status: dict[str, Any] | None = None,
    governance_status_schema: dict[str, Any] | None = None,
    conicshield_commit: str | None = None,
    inter_sim_rl_commit: str | None = None,
) -> None:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "config.schema.json", config_schema)
    _write_json(run_dir / "summary.json", summary)
    _write_json(run_dir / "summary.schema.json", summary_schema)
    _write_jsonl(run_dir / "episodes.jsonl", episodes)
    _write_json(run_dir / "episodes.schema.json", episodes_schema)
    _write_json(run_dir / "transition_bank.json", transition_bank)
    _write_text(run_dir / "benchmark_card.md", benchmark_card_md)

    if governance_status is not None:
        _write_json(run_dir / "governance_status.json", governance_status)
    if governance_status_schema is not None:
        _write_json(run_dir / "governance_status.schema.json", governance_status_schema)

    if conicshield_commit is not None:
        _write_text(run_dir / "conicshield_commit.txt", conicshield_commit + "\n")
    if inter_sim_rl_commit is not None:
        _write_text(run_dir / "inter_sim_rl_commit.txt", inter_sim_rl_commit + "\n")
