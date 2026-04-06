from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from conicshield.artifacts.run_spec import RunSpec


@dataclass(slots=True)
class RunContext:
    run_spec: RunSpec
    output_root: str = "output"

    @property
    def run_id(self) -> str:
        return self.run_spec.run_id()

    @property
    def bank_id(self) -> str:
        return self.run_spec.transition_bank.bank_id()

    @property
    def policy_id(self) -> str:
        return self.run_spec.policy.policy_id()

    @property
    def run_dir(self) -> Path:
        return Path(self.output_root) / self.run_id

    def config_payload(self) -> dict:
        return self.run_spec.to_config()
