# Reference correctness report

Generated: 2026-07-22T22:01:31Z

## Conic suite (Moreau vs trusted public solver)

Deltas are **Moreau vs CLARABEL** when CLARABEL is installed, otherwise **Moreau vs SCS**.

| case_id | trusted | family | n | density | cond | status | primal_linf | obj_abs | obj_rel | iters T/M |
|---------|---------|--------|---|---------|------|--------|-------------|---------|---------|-----------|

### Conic errors

- cvxpy import: No module named 'numpy.lib.array_utils'

## Shield QP minimal (CVXPY Moreau vs native)

**Status:** skipped

```json
[
  {
    "arm": "cvxpy_moreau",
    "error": "Optional dependency 'cvxpy' is required for CVXPY-based reference projector. Install solver extras, for example: pip install -e \".[solver,dev]\" --extra-index-url \"https://<GEMFURY_TOKEN>:@pypi.fury.io/optimalintellect/\". Place your Moreau license in ~/.moreau/key (or set MOREAU_LICENSE_KEY). See https://docs.moreau.so/installation.html"
  }
]
```
