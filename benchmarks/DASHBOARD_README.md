# Governance Dashboard

The governance dashboard is the top-level status view for the benchmark system.

It summarizes:
- active benchmark families
- current published runs
- task contract versions
- fixture versions
- publication gates
- whether the native compiled arm is endorsed
- current audit health

## How to generate

- **Registry-aware dashboard:** `python -m conicshield.governance.dashboard_cli` (see [README.md](../README.md) and [MAINTAINER_RUNBOOK.md](../MAINTAINER_RUNBOOK.md)).
- **Unified verification view (env, smoke, reference, parity, perf, governance):** `python scripts/generate_trust_dashboard.py` after producing artifacts under `output/` — described in [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md).

## Related

- [BENCHMARK_GOVERNANCE.md](../BENCHMARK_GOVERNANCE.md)
- [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md) (metrics dashboard §14)
