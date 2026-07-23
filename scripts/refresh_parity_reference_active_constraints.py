#!/usr/bin/env python3
"""Refresh parity-reference active_constraints to S2 stable IDs (WSL/Moreau)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from conicshield.adapters.inter_sim_rl.shield import InterSimConicShield
from conicshield.backends.base import Backend
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "tests" / "fixtures" / "parity_reference" / "episodes.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    shield = InterSimConicShield(
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(device="cpu", max_iter=800, verbose=False),
    )
    updated = 0
    for ep in rows:
        arm = ep.get("arm_label")
        if arm == "baseline-unshielded":
            continue
        if arm not in {"shielded-rules-only", "shielded-rules-plus-geometry"}:
            continue
        shield.reset_episode()
        for step in ep["steps"]:
            meta = dict(step.get("metadata", {}))
            ctx = meta.get("shield_context_snapshot")
            action_space = meta.get("canonical_action_space")
            if ctx is None or action_space is None:
                raise SystemExit(f"missing context/action_space for {arm}")
            decision = shield.choose_action(
                q_values=np.asarray(step["raw_q_values"], dtype=float),
                action_space=list(action_space),
                context=ctx,
            )
            old = list(step.get("active_constraints") or [])
            new = list(decision.projection.active_constraints)
            step["active_constraints"] = new
            if step.get("solver_status") in (None, "1"):
                step["solver_status"] = str(decision.projection.solver_status)
            print(arm, "step", step.get("step"), "old", old, "->", new)
            updated += 1

    path.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    print(f"updated_steps={updated} wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
