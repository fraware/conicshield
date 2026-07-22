# Release gate evaluation (Track 1 → main)

Evaluation date: 2026-07-22. Evaluator host: native Windows (no licensed Moreau).

## Verdict

**FAIL — do not merge `engineering/stabilization-moreau` → `main`.**

S8 artifacts and the S8 → integration PR may proceed. Main release is blocked.

## Checklist

| Gate | Status | Evidence / blocker |
|------|--------|--------------------|
| Every P0 closed | PASS | `docs/stabilization/issue_ledger.json` — 001–007 fixed |
| Every accepted action independently verified | PASS (code) | S2 release pipeline; regressions in `tests/stabilization/` |
| Schema parity tests pass | PASS (public) | Stabilization + public tests; vendor parity NOT attested here |
| Heterogeneous batch parity | BLOCKED | Requires licensed Moreau; documented NOT_RUN — no false green |
| Episode + concurrency isolation | PASS (tests) | S3 tests; S8 concurrent public cell |
| Vendor CI proves real solver execution | FAIL | Vendor workflow fails without Gemfury/license; host cannot attest |
| Windows public mode | PASS | `windows-ci.yml` + local public Clarabel/SCS/AUTO |
| WSL sidecar declared qualification | PASS (narrow) | Declared: scaffolding + protocol/tests + public CI — **not** live Moreau production |
| Verification commands read-only | PASS | S7 `--check` / dirty-worktree fail |
| Worktree clean after full verification | PARTIAL | Unrelated untracked research trees may exist on this host; S8 paths clean when committed alone |
| Governed dependencies recorded | PASS | `packaging/solver_stack_policy.json` + doctor |
| Benchmark claims supported by committed reports | PASS | `benchmarks/reports/s8_qualification/` |
| Public docs install instructions unambiguous | PASS (updated) | Migration guide + PUBLIC_CLAIMS |
| `make verify-v1-lock` green | FAIL / AT RISK | Flagship refresh cadence ~55d may fail until licensed refresh |
| Existing published bundles verifiable | PASS | `host-realistic-20260525` verify OK on this host |

## Blocking items for main

1. **Vendor CI real-solve attestation** with secrets (Gemfury + Moreau license) producing evidence-gate green.
2. **Heterogeneous batch parity** on a vendor-capable host (or keep documented blocked — still blocks a “fully qualified” main merge per directive).
3. **`make verify-v1-lock`** cadence / authority green after flagship refresh if required by lock policy.
4. Confirm sidecar claim language stays at scaffolding (already declared) — do not widen to production.

## Non-blocking but explicit

- Native Windows Moreau remains unsupported (correct).
- CUDA / live sidecar IPC remain NOT_RUN on this host.
- Public latency figures are host-specific.
