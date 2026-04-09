from copy import deepcopy

from conicshield.governance.family_policy import decide_family_compatibility


def base_config():
    return {
        "environment": {
            "action_space": ["turn_left", "turn_right", "go_straight", "turn_back"],
            "rule_choices": ["right", "left", "alternate"],
            "state_contract": {
                "location_dim": 2,
                "direction_dim": 2,
                "nearby_places_feature_size": 20,
            },
        },
        "transition_bank": {
            "max_depth": 4,
            "max_nodes": 300,
            "radius": 500,
            "max_candidates_per_node": 12,
        },
        "arms": [
            {"label": "baseline-unshielded", "backend": "none"},
            {"label": "shielded-rules-only", "backend": "cvxpy_moreau", "use_geometry_prior": False},
            {"label": "shielded-rules-plus-geometry", "backend": "cvxpy_moreau", "use_geometry_prior": True},
        ],
    }


def test_same_family_allowed_when_contract_matches() -> None:
    current = base_config()
    candidate = deepcopy(current)
    decision = decide_family_compatibility(
        family_id="conicshield-transition-bank-v1",
        current_config=current,
        candidate_config=candidate,
    )
    assert decision.same_family_allowed is True
    assert decision.requires_new_family is False


def test_family_bump_required_when_state_contract_changes() -> None:
    current = base_config()
    candidate = deepcopy(current)
    candidate["environment"]["state_contract"]["nearby_places_feature_size"] = 24
    decision = decide_family_compatibility(
        family_id="conicshield-transition-bank-v1",
        current_config=current,
        candidate_config=candidate,
    )
    assert decision.same_family_allowed is False
    assert decision.requires_new_family is True
