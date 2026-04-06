import numpy as np

from conicshield.adapters.inter_sim_rl.shield import CANONICAL_ACTION_SPACE, InterSimConicShield
from conicshield.core.result import ProjectionResult
from conicshield.core.solver_factory import Backend


class FakeProjector:
    def __init__(self, allowed_index: int):
        self.allowed_index = allowed_index

    def project(self, proposed_action, previous_action=None, *, reference_action=None, policy_weight=1.0, reference_weight=0.0, metadata=None):
        corrected = np.zeros_like(proposed_action)
        corrected[self.allowed_index] = 1.0
        return ProjectionResult(
            proposed_action=np.asarray(proposed_action, dtype=float),
            corrected_action=corrected,
            intervened=not np.allclose(proposed_action, corrected),
            intervention_norm=float(np.linalg.norm(corrected - proposed_action)),
            solver_status="fake",
            active_constraints=["turn_feasibility"],
            warm_started=previous_action is not None,
            metadata=metadata or {},
        )


def projector_factory(spec, backend, cvxpy_options, native_options):
    allowed = None
    for c in spec.constraints:
        if getattr(c, "kind", None) == "turn_feasibility":
            allowed = c.allowed_actions[0]
    return FakeProjector(allowed_index=allowed if allowed is not None else 0)


def test_rule_mask_forces_turn_right() -> None:
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        projector_factory=projector_factory,
    )

    q_values = np.array([5.0, 1.0, 0.2, -3.0], dtype=float)
    context = {
        "rule_choice": "right",
        "previous_instruction": "turn_right",
        "allowed_actions": ["turn_right"],
        "blocked_actions": ["turn_left", "go_straight", "turn_back"],
        "action_upper_bounds": {
            "turn_left": 0.0,
            "turn_right": 1.0,
            "go_straight": 0.0,
            "turn_back": 0.0,
        },
        "hazard_score": 0.25,
    }

    decision = shield.choose_action(
        q_values=q_values,
        action_space=list(CANONICAL_ACTION_SPACE),
        context=context,
    )

    assert decision.action_name == "turn_right"
    assert decision.projection.intervened


def test_action_space_permutation_is_supported() -> None:
    shield = InterSimConicShield(
        backend=Backend.CVXPY_MOREAU,
        projector_factory=projector_factory,
    )
    permuted = ["go_straight", "turn_left", "turn_back", "turn_right"]
    q_values = np.array([0.2, 4.0, -1.0, 0.1], dtype=float)
    context = {
        "allowed_actions": ["turn_left"],
        "blocked_actions": ["turn_right", "go_straight", "turn_back"],
        "action_upper_bounds": {
            "turn_left": 1.0,
            "turn_right": 0.0,
            "go_straight": 0.0,
            "turn_back": 0.0,
        },
        "hazard_score": 0.4,
    }
    decision = shield.choose_action(q_values=q_values, action_space=permuted, context=context)
    assert decision.action_name == "turn_left"
