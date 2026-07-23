# Release gate evaluation (Track 1 → main)

Evaluation date: 2026-07-23. Evaluator host: native Windows + WSL2 Ubuntu (Moreau CPU 0.3.3 licensed).

## Verdict

**FAIL — do not merge `engineering/stabilization-moreau` → `main` yet.**

Blocker #1 (`verify-v1-lock` cadence) is cleared locally. Heterogeneous batch parity and
local vendor attestation are green on WSL. Main merge still waits on committed evidence
review and CI confirmation on the integration branch (no push performed in this session).

## Checklist

| Gate | Status | Evidence / blocker |
|------|--------|--------------------|
| Every P0 closed | PASS | `docs/stabilization/issue_ledger.json` — 001–007 fixed |
| Every accepted action independently verified | PASS (code) | S2 release pipeline; regressions in `tests/stabilization/` |
| Schema parity tests pass | PASS | Stabilization + public tests; native/reference parity fixture labels refreshed |
| Heterogeneous batch parity | PASS (WSL) | `docs/stabilization/heterogeneous_batch_parity.json` — max_abs_error `0.0` |
| Episode + concurrency isolation | PASS (tests) | S3 tests; S8 concurrent public cell |
| Vendor CI proves real solver execution | PASS (local WSL) | `docs/stabilization/vendor_attestation_local/` — mandatory solves + 37 vendor tests + evidence gate |
| Windows public mode | PASS | `windows-ci.yml` + local public Clarabel/SCS/AUTO |
| WSL sidecar declared qualification | PASS (narrow) | Declared: scaffolding + protocol/tests + public CI — **not** live Moreau production |
| Verification commands read-only | PASS | S7 `--check` / dirty-worktree fail |
| Worktree clean after full verification | PARTIAL | Unrelated untracked research trees may exist on this host |
| Governed dependencies recorded | PASS | `packaging/solver_stack_policy.json` + doctor |
| Benchmark claims supported by committed reports | PASS | `benchmarks/reports/s8_qualification/` |
| Public docs install instructions unambiguous | PASS (updated) | Migration guide + PUBLIC_CLAIMS |
| `make verify-v1-lock` green | PASS (local) | Flagship full refresh #5 recorded `2026-07-23T07:14:18Z`; cadence OK |
| Existing published bundles verifiable | PASS | `host-realistic-20260525` verify OK |

## Blocking items for main (remaining)

1. **Commit + CI confirmation** of this clearance on `engineering/stabilization-moreau` (session did not push).
2. Confirm GitHub Actions `vendor-ci-moreau` stays green with repo secrets (local WSL attestation is necessary but not a substitute for canonical CI until that run is visible).
3. Confirm sidecar claim language stays at scaffolding (already declared) — do not widen to production.

## Cleared in this session

1. **`make verify-v1-lock` cadence** — ran `make host-realistic-refresh-cycle-licensed` on WSL Moreau CPU; recorded refresh history entry #5 (`live-export-full`, `authority_ok`).
2. **Heterogeneous batch parity** — real sequential-vs-batch Moreau solves; evidence artifact PASS.
3. **Local vendor attestation** — mandatory known-feasible + failure-policy + vendor pytest + `assert_vendor_ci_evidence` PASS.

## Defects fixed while clearing gates

- Moreau integer `SolverStatus` (`1` = Solved) mapped to `UNKNOWN` → fixed in `normalize_moreau_status`.
- Objective residual compared `pw||x-p||^2` against Moreau `0.5 x'Px+q'x` → dual-convention check.
- `create_batch_projector(..., metrics=...)` TypeError from inter-sim shield path.
- `performance_benchmark.py` missing `--sweep-auto-tune` argparse flag.
- Eager `backends/__init__.py` imports caused circular import during publish refresh.
- Parity fixture still used coarse `turn_feasibility` label vs S2 `turn_feasibility[i]`.
- Licensed Makefile target used `--amend-last-refresh` (rewrote history #4); now appends.

## Non-blocking but explicit

- Native Windows Moreau remains unsupported (correct).
- CUDA / live sidecar IPC remain NOT_RUN on this host.
- Public latency figures are host-specific.
- GemFury token may appear in local pip progress lines; do not commit `.env` or echo secrets.
