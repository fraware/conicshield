# S0 baseline check report (Windows host)

Captured on branch `engineering/s0-reproducible-baseline` from starting commit `180bed7411f3146205b65b4258e6711c786c9f6f`.

Machine-readable twin: [`checks_summary.json`](checks_summary.json).

## Blockers (visible, not hidden)

1. **Moreau is not supported on native Windows** — package may be present on `sys.path`, but `import moreau` raises an upstream `ImportError` directing users to WSL. Vendor solve / parity / perf are **not runnable** in this public Windows mode.
2. **cvxpy import broken on this host** — `No module named 'numpy.lib.array_utils'` (numpy/cvxpy skew). Breaks environment_check, smoke public QP, solver smoke reference arm, and some CLI preflights.
3. **Vendor CI skip policy** — `pytest -m "solver or requires_moreau"` exited 0 with **4 skips / 1 pass**. `CONICSHIELD_VENDOR_REQUIRED` is not wired into `.github/workflows/solver-ci.yml` yet (CS-SOLVER-003 / S7). S0 adds `tests/stabilization/vendor_required.py` scaffolding only.
4. **Concurrent Track-2 untracked tree** — `tests/research/` existed untracked during capture. Default `pytest tests/` collected those files. Track-1 baseline re-ran with `--ignore=tests/research`. Track-2 paths are **not** part of this S0 commit.

## Check outcomes

| Check | Outcome | Notes |
|-------|---------|-------|
| environment_check | **fail** | See `environment_check.json` |
| filtered package freeze | **pass** | `pip_freeze_filtered.txt` |
| pytest public (default) | **fail** | Contaminated by Track-2 research; see log |
| pytest public Track-1 (`--ignore=tests/research`) | **fail** | 6 failures listed below |
| pytest stabilization | **pass** | xfails encode P0s |
| smoke_check | **fail** | public CVXPY QP |
| differentiation_check | **pass** | |
| published-run verify `host-realistic-20260525` | **pass** | |
| community verify pytest subset | **pass** | |
| pytest vendor-capable | **pass_with_skips** | `ssss.` (4 skip / 1 pass) |
| solver_smoke_cli | **fail** | missing/broken solver stack |
| parity native | **not_runnable** | Windows Moreau |
| performance_benchmark | **not_runnable** | Windows Moreau |
| reference_correctness | **not_runnable** | cvxpy/Moreau |
| `python -m moreau check` | **fail** | Windows unsupported |
| Windows public-mode status | **pass** | `windows_public_mode_status.json` |

### Track-1 public pytest failures (host)

- `test_parity_fixture_source_is_wsl_real` — `parity_fixture_source_run_id` returned `None`
- `test_parity_regeneration_note_run_ids_are_indexed` — no run ids parsed from `REGENERATION_NOTE.md`
- `test_reference_system_status_builds` / `test_committed_reference_system_status_check` — `full_refresh_cadence_ok` false
- `test_verify_v1_lock_quick_exits_zero` — cascade from status/cadence
- `test_produce_reference_bundle_real_projector_preflight_error_without_moreau` — returncode 3 (cvxpy import failure path)

## Production behavior

**Unchanged.** S0 adds documentation, ledger, baseline artifacts, pytest marker metadata, and failing/`xfail(strict=True)` regressions only.

## Reproduce

See [`../README.md`](../README.md).
