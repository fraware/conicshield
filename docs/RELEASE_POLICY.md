# Release policy

**Related:** [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md), [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md), [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md), [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md).

Releases have exactly two legal modes:
- same-family publication
- new-family fork and publication

A same-family release is allowed only if the task contract is unchanged.

A new-family release is required when the task contract changes materially.

Publication must consume only `governance_status.json`. Manual editing of release pointers is forbidden.
