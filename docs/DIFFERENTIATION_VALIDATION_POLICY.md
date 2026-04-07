# Differentiation validation policy

## Status

**Layer F (differentiation verification) is optional** until the repository ships a maintained differentiable path validated against finite differences and framework integration tests.

`NativeMoreauCompiledOptions.enable_grad` exists for forward configuration, but **gradient correctness is not yet a governed gate** in public CI.

## Intended scope (future)

When implemented, validation should cover:

1. Core implicit differentiation (native backward where vendor supports it).
2. PyTorch autograd via cvxpylayers (optional dependency).
3. JAX (optional dependency), if in scope.

Each path should report: forward success, finite gradients vs analytic where feasible, NaN/inf incidence, backward timing.

## Artifacts

When enabled, runs should emit `output/differentiation_summary.json` and `output/differentiation_report.md` (produced by `scripts/differentiation_check.py`).

## Related

- [MOREAU_API_NOTES.md](MOREAU_API_NOTES.md)
- [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) Layer F
