# Quickstart: integrator

Curated path for **using ConicShield as a library** on the public/reference stack.

## Install (public / reference)

Matches default CI — no vendor secrets:

```bash
python -m pip install -e ".[dev]"
```

Vendor Moreau (native compiled paths): [README.md](../README.md) and [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md).

## Choose a solver path

| Mode | When | API |
|------|------|-----|
| Reference CVXPY | Parity gold, no vendor license | `Backend.CVXPY_MOREAU` |
| Native sequential | Per-step shield with warm-start | `Backend.NATIVE_MOREAU` |
| Native true batch | Stacked proposals, one batched solve | `Backend.NATIVE_MOREAU_BATCH` |

Full detail: [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md).

## `create_projector` (reference or sequential native)

```python
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.schema import SafetySpec, SimplexConstraint, BoxConstraint, RateConstraint, TurnFeasibilityConstraint

spec = SafetySpec(
    spec_id="demo",
    version="0.1.0",
    action_dim=4,
    constraints=[
        SimplexConstraint(total=1.0),
        TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
        BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
        RateConstraint(max_delta=[0.9] * 4),
    ],
)
projector = create_projector(spec=spec, backend=Backend.CVXPY_MOREAU)
```

Example: [examples/minimal_reference_projection.py](../examples/minimal_reference_projection.py).

## Sequential native vs true batched native

- **Sequential:** `create_projector(..., backend=Backend.NATIVE_MOREAU)` — one `project()` per proposal.
- **Batch:** `create_batch_projector(...)` — `project_batch(proposed_batch, previous_action)` → `(K, n)`.

Do **not** describe batch as universally faster; see [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md).

Examples: [examples/native_compiled_projection.py](../examples/native_compiled_projection.py), [examples/true_batched_compiled_projection.py](../examples/true_batched_compiled_projection.py).

## Supported semantics today

Implemented constraint kinds: `simplex`, `turn_feasibility`, `box`, `rate`.  
Not implemented: `progress`, `clearance` — [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md).

Contributing / PR rules: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Next steps

- [examples/README.md](../examples/README.md)
- [docs/README.md](README.md)
