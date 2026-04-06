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
