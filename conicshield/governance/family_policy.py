from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from conicshield.governance.family_manifest import validate_family_manifest


@dataclass(slots=True)
class FamilyDecision:
    same_family_allowed: bool
    requires_new_family: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "same_family_allowed": self.same_family_allowed,
            "requires_new_family": self.requires_new_family,
            "reason": self.reason,
        }


def decide_family_compatibility(
    *,
    family_id: str,
    current_config: dict[str, Any],
    candidate_config: dict[str, Any],
) -> FamilyDecision:
    manifest = validate_family_manifest(family_id)
    rules = manifest["same_family_replacement_rules"]

    current_env = current_config["environment"]
    candidate_env = candidate_config["environment"]

    current_bank = current_config["transition_bank"]
    candidate_bank = candidate_config["transition_bank"]

    current_arms = {arm["label"]: arm for arm in current_config["arms"]}
    candidate_arms = {arm["label"]: arm for arm in candidate_config["arms"]}

    required_arms = set(manifest["required_arms"])
    reference_arm = manifest["reference_arm"]

    if rules["action_space_must_match"] and current_env["action_space"] != candidate_env["action_space"]:
        return FamilyDecision(False, True, "Action space changed")

    if rules["state_contract_must_match"] and current_env["state_contract"] != candidate_env["state_contract"]:
        return FamilyDecision(False, True, "State contract changed")

    if rules["rule_choices_must_match"] and current_env["rule_choices"] != candidate_env["rule_choices"]:
        return FamilyDecision(False, True, "Rule-choice task surface changed")

    if rules["transition_bank_semantics_must_match"]:
        keys = ["max_depth", "max_nodes", "radius", "max_candidates_per_node"]
        for key in keys:
            if current_bank.get(key) != candidate_bank.get(key):
                return FamilyDecision(False, True, f"Transition-bank semantic changed: {key}")

    if not required_arms.issubset(current_arms):
        return FamilyDecision(False, True, "Current config missing required arms")
    if not required_arms.issubset(candidate_arms):
        return FamilyDecision(False, True, "Candidate config missing required arms")

    if rules["reference_arm_definition_must_match"]:
        current_ref = current_arms[reference_arm]
        candidate_ref = candidate_arms[reference_arm]
        for field in ["backend", "use_geometry_prior"]:
            if current_ref.get(field) != candidate_ref.get(field):
                return FamilyDecision(False, True, f"Reference arm definition changed: {field}")

    return FamilyDecision(True, False, "Task contract compatible with current family")
