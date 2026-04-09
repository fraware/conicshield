# Release policy

**Related:** [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md), [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md), [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md), [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md).

Releases have exactly two legal modes:
- same-family publication
- new-family fork and publication

A same-family release is allowed only if the task contract is unchanged.

A new-family release is required when the task contract changes materially.

Publication must be driven from `governance_status.json` via **`release_cli`** (which updates `CURRENT.json`, `HISTORY.json`, and `benchmarks/registry.json`). Refreshing gate columns on an **already published** `CURRENT.json` for the same `current_run_id` is allowed only through **`finalize_cli --sync-current-release`** together with `--parity-summary-path` as documented in [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md). Ad-hoc hand edits to release JSON are forbidden.
