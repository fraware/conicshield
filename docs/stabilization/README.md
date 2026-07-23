# Track 1 stabilization

Long-lived integration branch: `engineering/stabilization-moreau`.

This directory holds the reproducible baseline (S0), issue ledger, and Track 1
completion / qualification reports (S8).

## Artifacts

| Path | Purpose |
|------|---------|
| [`starting_commit.json`](starting_commit.json) | Exact SHA / describe / date for the S0 starting tip |
| [`issue_ledger.json`](issue_ledger.json) | Machine-readable P0/P1 issue ledger |
| [`TRACK1_COMPLETION_REPORT.md`](TRACK1_COMPLETION_REPORT.md) | 15-section Track 1 completion report |
| [`PRODUCTION_QUALIFICATION_REPORT.md`](PRODUCTION_QUALIFICATION_REPORT.md) | S8 runtime qualification (separate from v1 bundles) |
| [`RELEASE_GATE_EVALUATION.md`](RELEASE_GATE_EVALUATION.md) | Honest main-merge gate evaluation |
| [`baseline/`](baseline/) | Environment, freeze, check outcomes, parity/published-run status |
| [`../MIGRATION_STABILIZATION_TRACK1.md`](../MIGRATION_STABILIZATION_TRACK1.md) | Consumer migration guide |

## Reproduce baseline (clean checkout)

```powershell
git fetch origin
git checkout engineering/s0-reproducible-baseline   # or merge base of the S0 PR
py -3 -m pip install -r requirements-dev.txt
py -3 -m pip install -e ".[dev]"

# Public checks (no vendor credentials required for default marker set)
py -3 scripts/environment_check.py --out-dir docs/stabilization/baseline
py -3 -m pytest tests/ -q
py -3 scripts/smoke_check.py --out-dir docs/stabilization/baseline
py -3 -m conicshield.published_runs.cli verify host-realistic-20260525

# Optional vendor lane (requires Moreau install + license)
$env:CONICSHIELD_VENDOR_REQUIRED = "1"   # S7: vendor CI sets this; skips become failures
py -3 -m pytest tests/ -q -m "solver or requires_moreau"
```

S7 closed CS-SOLVER-003 (vendor skip false confidence) and CS-SOLVER-007 (read-only verify). See `docs/DEVENV.md` for check meanings and generate vs verify command distinction.

Regression tests that encode known P0 defects live under `tests/stabilization/`. Remaining open ledger items use `pytest.mark.xfail(strict=True)` until their work package lands.

## Issue IDs

See [`issue_ledger.json`](issue_ledger.json). Fixes belong in S1+ work packages on short-lived branches off `engineering/stabilization-moreau`.
