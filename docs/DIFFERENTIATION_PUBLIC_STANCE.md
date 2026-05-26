# Differentiation public stance

## What we claim publicly

- **Layer F** is an **internal validation layer**: finite-difference sanity via `scripts/differentiation_check.py`, optional torch/jax micro-probes, and `--shield-inter-sim` on licensed hosts.
- Vendor tests under `tests/vendor/diff/` support engineering discipline, not product marketing.

## What we do not claim

- Production shield **autograd** (`enable_grad` on the real shield QP) as a supported product capability.
- A “fully validated differentiable runtime shield stack” in README, pitch decks, or release notes.

## Promotion criteria (future milestone only)

Do not update external narrative until all of the following exist and pass on licensed hosts:

1. Production-path autograd tests on the shield objective
2. Autograd vs finite-difference agreement within declared tolerances
3. Stability measurements around active-set changes
4. Explicit maintainer approval and roadmap milestone

Until then, keep [`ROADMAP.md`](ROADMAP.md) backlog item #2 in **deferred** state.
