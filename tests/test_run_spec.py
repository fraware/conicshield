from conicshield.artifacts.run_spec import (
    ArmSpec,
    CommitSpec,
    EnvironmentSpec,
    PolicySpec,
    RunSpec,
    TransitionBankSpec,
)


def test_run_spec_ids_are_deterministic() -> None:
    spec1 = RunSpec(
        benchmark_name="bench",
        description="desc",
        policy=PolicySpec(policy_name="p", input_dim=24),
        environment=EnvironmentSpec(),
        transition_bank=TransitionBankSpec(root_addresses=["Root"]),
        arms=[ArmSpec(label="baseline-unshielded", backend="none")],
        seeds=[7],
        commits=CommitSpec(),
        created_at_utc="2026-04-06T00:00:00Z",
    )
    spec2 = RunSpec(
        benchmark_name="bench",
        description="desc",
        policy=PolicySpec(policy_name="p", input_dim=24),
        environment=EnvironmentSpec(),
        transition_bank=TransitionBankSpec(root_addresses=["Root"]),
        arms=[ArmSpec(label="baseline-unshielded", backend="none")],
        seeds=[7],
        commits=CommitSpec(),
        created_at_utc="2026-04-06T00:00:00Z",
    )
    assert spec1.run_id() == spec2.run_id()
    assert spec1.policy.policy_id() == spec2.policy.policy_id()
    assert spec1.transition_bank.bank_id() == spec2.transition_bank.bank_id()
