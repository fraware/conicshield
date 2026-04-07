# State-of-the-art notes

This scaffold is designed around several high-standard engineering principles:

- optional solver dependencies are isolated from governance code
- native execution is parity-gated against a reference path
- run bundles are schema-validated and invariant-checked
- benchmark families are versioned as semantic task objects
- releases are governed artifacts, not ad hoc file edits
- a global audit and dashboard summarize the state of the benchmark tree

The repository is intentionally overbuilt relative to a typical prototype because the goal is not just to run experiments, but to preserve meaning as the system evolves.

## Where this is encoded

- **Trust ladder (commands and artifacts):** [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) and [VERIFICATION_MASTER_SPEC.md](VERIFICATION_MASTER_SPEC.md)
- **CI matrix and pytest markers:** [DEVENV.md](DEVENV.md)
- **Stress-test metric inventory (roadmap):** [METRICS_INVENTORY.md](METRICS_INVENTORY.md)
- **Benchmark governance:** [../BENCHMARK_GOVERNANCE.md](../BENCHMARK_GOVERNANCE.md)
