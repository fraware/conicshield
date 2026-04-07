"""Regression: parity CLI must persist outputs before calling parity gates (solver-ci artifacts)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from conicshield.parity.replay import ParityStepResult, ParitySummary


def test_parity_cli_writes_jsonl_before_enforce(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import conicshield.parity.cli as pc

    out = tmp_path / "parity_out"
    out.mkdir()

    def fake_compare(
        *,
        episodes_jsonl: str | Path,
        candidate_shield: Any,
        reference_arm_label: str = "shielded-rules-plus-geometry",
    ) -> tuple[list[ParityStepResult], ParitySummary]:
        sr = ParityStepResult(
            episode_id="e1",
            step=0,
            reference_action="turn_right",
            candidate_action="turn_right",
            action_match=True,
            proposed_linf=0.0,
            corrected_linf=0.0,
            corrected_l2=0.0,
            objective_abs_diff=None,
            intervention_norm_abs_diff=None,
            active_constraints_match=True,
            solver_status_reference=None,
            solver_status_candidate=None,
        )
        summary = ParitySummary(
            total_steps=1,
            action_match_rate=1.0,
            max_corrected_linf=0.0,
            p95_corrected_linf=0.0,
            max_corrected_l2=0.0,
            p95_corrected_l2=0.0,
            active_constraints_match_rate=1.0,
        )
        return [sr], summary

    monkeypatch.setattr(pc, "compare_against_reference", fake_compare)
    monkeypatch.setattr(pc, "build_native_candidate_from_config", lambda _c: object())

    order: list[str] = []

    def track_enforce(summary: ParitySummary) -> None:
        order.append("enforce")
        assert (out / "parity_summary.json").is_file()
        assert (out / "parity_steps.jsonl").is_file()
        from conicshield.parity.gates import enforce_default_parity_gates as real

        real(summary)

    monkeypatch.setattr(pc, "enforce_default_parity_gates", track_enforce)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "parity.cli",
            "--reference-dir",
            "tests/fixtures/parity_reference",
            "--reference-arm-label",
            "shielded-rules-plus-geometry",
            "--out-dir",
            str(out),
        ],
    )
    pc.main()
    assert order == ["enforce"]
    payload = json.loads((out / "parity_summary.json").read_text(encoding="utf-8"))
    assert payload["total_steps"] == 1
