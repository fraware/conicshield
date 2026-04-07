# Roadmap

What still depends on **external** work, licenses, or product decisions — as opposed to what already lives in the repository and tests.

## External integration

- **inter-sim-rl:** Production benchmarks assume a real offline graph export and transition bank from the patched host environment, not only the minimal JSON fixtures used in CI. Pin and checkout policy: `third_party/inter-sim-rl/` and [`INTER_SIM_RL_INTEGRATION.md`](INTER_SIM_RL_INTEGRATION.md).

## Solver and parity

- **Validated solver versions** belong in [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) after a green manual **Vendor CI** run (`vendor-ci-moreau`) or local licensed run.
- **Parity fixture:** The checked-in fixture may remain synthetic until you promote a real `reference_run`; procedure: [`PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md) and [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## Deferred product semantics

- **`progress` and `clearance` constraint kinds** in `SafetySpec` are not implemented for projection yet. See [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md).

## After first governed publish

Possible follow-ons (not blocking core development): retraining comparisons under a frozen family, richer proof metadata in artifacts, a second benchmark host — each needs its own family manifest and governance review.

## Where to run commands

Step-by-step publish, audit, and dashboard commands: [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md). Verification layers and artifacts: [`VERIFICATION_AND_STRESS_TEST_PLAN.md`](VERIFICATION_AND_STRESS_TEST_PLAN.md).
