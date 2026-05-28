# Differentiation public stance

`differentiation_check.py` writes `layer_f_note` into every report:

> Layer F validates local sensitivity and FD consistency; it is not a public autograd guarantee.

## Public claims (allowed)

- Layer F is **internal validation**: `scripts/differentiation_check.py`, optional torch/jax toy probes, `--shield-inter-sim` on licensed hosts.
- `tests/vendor/diff/` — engineering only, not product marketing.

## Public claims (forbidden)

- Production shield **autograd** (`enable_grad` on the real shield QP).
- “Fully validated differentiable runtime shield stack” in README, decks, or release notes.

## Promotion gate (future)

Do not change public narrative until **all** pass on licensed hosts:

1. Production-path autograd tests on shield objective
2. Autograd vs FD within declared tolerances
3. Stability around active-set changes
4. Maintainer milestone + explicit doc update

Until then: [`ROADMAP.md`](ROADMAP.md) item 2 stays deferred.
