# Test layout (physical vs logical)

| Directory | Role |
|-----------|------|
| `tests/vendor/native/` | Moreau native projector vs CVXPY reference (licensed host). |
| `tests/vendor/diff/` | Layer F differentiation checks and optional torch/jax micrograd probes. |
| `tests/live/` | Documentation only: how to run the live vendor pytest lane (`run_live_vendor_tests.py`). |
| `tests/governance/` | Registry, finalize, publish, published-run index. |
| `tests/parity/` | Parity CLI / layout smoke. |
| `tests/reference/` | Conic correctness (public + vendor-marked rows). |
| `tests/environment/` | Repo hygiene, tooling smoke. |

**Deferred (ADR 001):** `progress` / `clearance` constraint kinds are not implemented; see `docs/adr/001-progress-clearance-constraints.md`.

**P2-8 (export → published bundle):** operational sequence lives in `benchmarks/published_runs/README.md` and `scripts/governed_local_promotion.py` (validate / parity-sync / index).
