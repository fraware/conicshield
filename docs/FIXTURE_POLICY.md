# Frozen parity fixture policy

**Related:** [PARITY_FIXTURE_PROMOTION.md](PARITY_FIXTURE_PROMOTION.md), [NATIVE_PARITY_POLICY.md](NATIVE_PARITY_POLICY.md), [BENCHMARK_GOVERNANCE.md](../BENCHMARK_GOVERNANCE.md), [MAINTAINER_RUNBOOK.md](../MAINTAINER_RUNBOOK.md).

The parity fixture is a versioned benchmark artifact.

It must only be regenerated when:
- reference shield semantics change intentionally
- reference compiler semantics change intentionally
- reference input stream semantics change intentionally
- a semantic-preserving refresh is explicitly approved

It must never be regenerated just to make native parity green.

Required files:
- `FIXTURE_MANIFEST.json`
- `REGENERATION_NOTE.md`
- reference bundle artifacts
