# Tests and logical layers

This mirrors the trust model in [docs/VERIFICATION_AND_STRESS_TEST_PLAN.md](../docs/VERIFICATION_AND_STRESS_TEST_PLAN.md). Physical layout is still evolving; use these subtrees as the target convention:

| Layer | Role | Typical paths |
|-------|------|----------------|
| Environment / smoke | Scripts and minimal health | (repo `scripts/`, not under `tests/`) |
| Reference correctness | Public solvers, no vendor Moreau | `tests/reference/` |
| Native / vendor | Moreau-backed paths | `tests/native/` |
| Parity | Replay vs fixture | `tests/parity/` |
| Performance | Timing harnesses | `tests/performance/` |
| Artifacts | Bundles, schemas | `tests/artifacts/` |
| Governance | Registry, releases, publish | `tests/governance/` |

New tests should prefer the closest matching subtree. Moves of existing files can happen incrementally when touching those areas.
