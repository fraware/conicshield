# Native parity reference fixture

**Policy:** [`docs/PARITY_AND_FIXTURES.md`](../../docs/PARITY_AND_FIXTURES.md).

This fixture is a frozen reference bundle for native-Moreau parity checks.

Source of truth:
- reference arm: `shielded-rules-plus-geometry`
- backend: CVXPY + Moreau
- environment: precomputed transition-bank replay only
- purpose: replay the exact recorded shield inputs through the native compiled path

This fixture must only be regenerated intentionally. Promotion source and index alignment are recorded in [`REGENERATION_NOTE.md`](REGENERATION_NOTE.md) and checked against [`benchmarks/PUBLISHED_RUN_INDEX.json`](../../../benchmarks/PUBLISHED_RUN_INDEX.json) in CI.
