"""Load corpus SafetySpec dicts, including intentional infeasible regimes.

Production ``SafetySpec`` rejects structurally contradictory specs. The research
corpus intentionally includes such regimes (``infeasible`` family). Research
harnesses soft-load those cases with ``model_construct`` and record the bypass.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from conicshield.specs.schema import SafetySpec

# Expected regimes that may fail production SafetySpec consistency checks.
STRUCTURALLY_INFEASIBLE_REGIMES: frozenset[str] = frozenset(
    {
        "infeasible",
        "near_infeasible",
    }
)


def load_research_safety_spec(
    scenario: dict[str, Any],
) -> tuple[SafetySpec, dict[str, Any]]:
    """Return ``(spec, load_meta)`` for a corpus scenario dict."""

    raw = scenario["spec"]
    regime = str(scenario.get("expected_regime") or "")
    meta: dict[str, Any] = {
        "validation": "strict",
        "expected_regime": regime,
        "soft_load": False,
    }
    try:
        return SafetySpec.model_validate(raw), meta
    except (ValidationError, ValueError) as exc:
        if regime not in STRUCTURALLY_INFEASIBLE_REGIMES and "infeasible" not in regime:
            raise
        # Soft-load: skip production consistency validators for intentional failure regimes.
        spec = SafetySpec.model_construct(**_coerce_construct_kwargs(raw))
        meta.update(
            {
                "validation": "soft_model_construct",
                "soft_load": True,
                "validation_error": str(exc),
                "note": (
                    "Intentionally contradictory research scenario soft-loaded; not a production SafetySpec acceptance."
                ),
            }
        )
        return spec, meta


def _coerce_construct_kwargs(raw: dict[str, Any]) -> dict[str, Any]:
    """Best-effort kwargs for ``SafetySpec.model_construct`` from corpus JSON."""

    from conicshield.specs.schema import (
        BoxConstraint,
        RateConstraint,
        SimplexConstraint,
        TurnFeasibilityConstraint,
    )

    kind_map = {
        "simplex": SimplexConstraint,
        "box": BoxConstraint,
        "rate": RateConstraint,
        "turn_feasibility": TurnFeasibilityConstraint,
    }
    constraints = []
    for c in raw.get("constraints") or []:
        kind = str(c.get("kind"))
        cls = kind_map.get(kind)
        if cls is None:
            continue
        constraints.append(cls.model_validate(c))  # type: ignore[attr-defined]
    return {
        "spec_id": raw.get("spec_id", "research/unknown"),
        "version": raw.get("version", "0.1.0"),
        "action_dim": int(raw["action_dim"]),
        "slack_weight": float(raw.get("slack_weight", 10.0)),
        "constraints": constraints,
        "fail_safe_policy": raw.get("fail_safe_policy"),
    }
