from __future__ import annotations

from dataclasses import dataclass


class GovernanceError(RuntimeError):
    pass


@dataclass(slots=True)
class RunGovernanceState:
    family_id: str
    task_contract_version: str
    fixture_version: str
    artifact_gate: str
    parity_gate: str
    promotion_gate: str
    review_locked: bool


def assert_same_family_replacement(
    *,
    current_family_id: str,
    candidate_family_id: str,
    current_task_contract_version: str,
    candidate_task_contract_version: str,
) -> None:
    if candidate_family_id != current_family_id:
        raise GovernanceError(
            "Candidate run belongs to a different benchmark family. "
            "Publish as a new family, not as a replacement."
        )

    if candidate_task_contract_version != current_task_contract_version:
        raise GovernanceError(
            "Candidate run changes the semantic task contract. "
            "Create a new benchmark family version."
        )


def assert_publishable(state: RunGovernanceState) -> None:
    if state.artifact_gate != "green":
        raise GovernanceError("Run is not publishable: artifact gate is not green")
    if state.review_locked is not True:
        raise GovernanceError("Run is not publishable: run is not review-locked")
    if state.promotion_gate != "green":
        raise GovernanceError("Run is not publishable: promotion gate is not green")


def assert_native_arm_publishable(state: RunGovernanceState) -> None:
    assert_publishable(state)
    if state.parity_gate != "green":
        raise GovernanceError("Native arm is not publishable: parity gate is not green")
