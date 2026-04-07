# Governance Audit Policy

The governance audit CLI verifies the integrity of the benchmark governance tree.

It checks consistency across:
- `benchmarks/registry.json`
- family release directories
- family manifests
- current published runs
- historical run references
- current run bundles
- current run governance status

Strict mode should be used in CI for release and publication workflows.

Canonical policy copy and cross-links: [`docs/BENCHMARK_GOVERNANCE.md`](../../docs/BENCHMARK_GOVERNANCE.md), [`docs/MAINTAINER_RUNBOOK.md`](../../docs/MAINTAINER_RUNBOOK.md), and the governance sections of [`docs/VERIFICATION_AND_STRESS_TEST_PLAN.md`](../../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md).
