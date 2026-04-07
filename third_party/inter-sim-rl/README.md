# inter-sim-rl (external upstream)

ConicShield integrates through a thin adapter; navigation RL code lives in the canonical upstream repository:

- **Repository:** [https://github.com/fraware/inter-sim-rl](https://github.com/fraware/inter-sim-rl)

## Engineering control (pin and fork policy)

- **Single source of truth:** the `repository=` and `sha=` lines in [`REVISION`](REVISION). ConicShield docs and CI resolve the clone URL from `repository=` unless overridden.
- **Fork as canonical:** if your team maintains a fork with the M2 patch merged, set `repository=https://github.com/<org>/inter-sim-rl.git` in `REVISION` to that fork and bump `sha=` to the validated commit. Keep `PATCHES.md` in sync (patch apply should become a no-op once upstream matches).
- **CI override (optional):** GitHub Actions repository variable `INTERSIM_RL_REPO_URL` overrides `repository=` for `inter-sim-rl-ci` only (useful for temporary forks without editing `REVISION` on every experiment).
- **Submodule path:** optional checkout under `third_party/inter-sim-rl/checkout` still works; the workflow attempts `git apply` of the M2 patch there (no-op if already merged).

## Upstream patch (until merged)

See [PATCHES.md](PATCHES.md) and `patches/conicshield-m2-shield-context-and-transitions.patch`. GitHub Actions `inter-sim-rl-ci` applies this patch after cloning upstream.

## Revision pin

The commit validated for integration work with this tree is recorded in `REVISION` (same SHA is summarized in `docs/INTER_SIM_RL_INTEGRATION.md`).

Clone at that revision:

```bash
git clone https://github.com/fraware/inter-sim-rl.git
cd inter-sim-rl
git checkout f1f04ee11d064262f5ee2810abfcb01715260182
```

Optional submodule (reproducible clone inside this repo):

```bash
git submodule add https://github.com/fraware/inter-sim-rl.git third_party/inter-sim-rl/checkout
cd third_party/inter-sim-rl/checkout && git checkout f1f04ee11d064262f5ee2810abfcb01715260182
```

Set `INTERSIM_RL_ROOT` to the clone root for `pytest -m inter_sim_rl`.

## Upstream patches (not in ConicShield)

Implement in [inter-sim-rl](https://github.com/fraware/inter-sim-rl), not in this package:

1. `get_shield_context()` returning the contract validated by `schemas/shield_context.schema.json`.
2. Action-conditioned transitions with deterministic fallback when a branch is missing.
3. Stable observation / DQN `predict` input shape (see ConicShield adapter policy tests).

See `EXTERNAL_PATCH_CHECKLIST.md` for a concise checklist.

## Related Fraware environment

Hospital lab automation benchmarks (separate from intersection navigation):

- [https://github.com/fraware/LabTrust-Gym](https://github.com/fraware/LabTrust-Gym) — see `REVISION_LABTRUST_GYM` in this directory for a pinned `main` reference.
