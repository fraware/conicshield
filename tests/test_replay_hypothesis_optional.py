from __future__ import annotations

import importlib.util

import pytest

if importlib.util.find_spec("hypothesis") is None:
    pytest.skip("hypothesis not installed", allow_module_level=True)

from hypothesis import given
from hypothesis import strategies as st

from conicshield.adapters.inter_sim_rl.context_validate import validate_shield_context_dict

_CANONICAL = ("turn_left", "turn_right", "go_straight", "turn_back")


@given(st.lists(st.sampled_from(_CANONICAL), unique=True, min_size=1, max_size=4))
def test_shield_context_schema_accepts_random_allowed_sets(allowed: list[str]) -> None:
    allowed_set = set(allowed)
    blocked = [a for a in _CANONICAL if a not in allowed_set]
    bounds = {a: (1.0 if a in allowed_set else 0.0) for a in _CANONICAL}
    ctx = {
        "allowed_actions": allowed,
        "blocked_actions": blocked,
        "action_upper_bounds": bounds,
        "rule_choice": "right",
        "previous_instruction": None,
        "hazard_score": 0.0,
    }
    validate_shield_context_dict(ctx)
