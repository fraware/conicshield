# Migration guide — Track 1 stabilization

How to move from pre-stabilization ConicShield usage to the Track 1 contracts
(S0–S8) without breaking published v1 bundles.

## What changed

1. **Backends are explicit.** Prefer `Backend.PUBLIC_CLARABEL`, `PUBLIC_SCS`, or
   `AUTO` for credential-free installs. `AUTO` never selects vendor Moreau merely
   because a package is importable.
2. **Release is gated.** Corrected actions ship only through the verification /
   release pipeline (status + residuals + policy). Catch `VerificationReleaseError`
   instead of assuming every solve yields a usable action.
3. **Episode reset clears warm starts.** Call `reset_episode()` / `reset_state()`
   between episodes; first-solve must match a fresh projector.
4. **Batching is first-class** via `NATIVE_MOREAU_BATCH` / `create_batch_projector`
   on vendor hosts. Public narrative for batch speedup remains **viability_only**
   unless governed reports say otherwise.
5. **Windows:** use public mode on native Windows; vendor Moreau belongs in WSL
   or the Moreau sidecar worker — never claim native Windows Moreau.
6. **CI:** vendor jobs set `CONICSHIELD_VENDOR_REQUIRED=1`; skips are failures.
   Verify scripts are read-only (`--check` / dirty-worktree fail).

## Install profiles

```bash
# Public / Windows-safe
pip install -e ".[dev]"

# Vendor (Linux/WSL + license + approved index) — see MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md
pip install -e ".[solver,dev]" --extra-index-url "<approved Moreau index>"
```

Run `conicshield solver-doctor --json` after install.

## Preserving v1 bundles

- Published runs under `benchmarks/published_runs/` and the integrity catalog remain
  the reference authority.
- Track 1 **runtime qualification** lives under
  `benchmarks/reports/s8_qualification/` and
  `docs/stabilization/PRODUCTION_QUALIFICATION_REPORT.md`.
- Do not rewrite historical bundle hashes to “pass” new runtime gates.

## Public claims

Update consumer-facing text against [`PUBLIC_CLAIMS.md`](PUBLIC_CLAIMS.md) only.
Do not cite smoke microbenchmarks as production latency without the S8 report
and NOT_RUN labels.

## Rollback / coexistence

Old call sites that ignored verification may now raise on inadmissible or
numerically failed solves — this is intentional fail-closed behavior. Prefer
handling release errors over silencing the verifier.
