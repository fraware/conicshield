# Track 1 stabilization (S0 baseline)

Long-lived integration branch: `engineering/stabilization-moreau`.

This directory holds the **reproducible baseline** for production stabilization work packages (S0+). It does not change solver behavior.

## Artifacts

| Path | Purpose |
|------|---------|
| [`starting_commit.json`](starting_commit.json) | Exact SHA / describe / date for the S0 starting tip |
| [`issue_ledger.json`](issue_ledger.json) | Machine-readable P0/P1 issue ledger |
| [`baseline/`](baseline/) | Environment, freeze, check outcomes, parity/published-run status |

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
$env:CONICSHIELD_VENDOR_REQUIRED = "1"   # desired S7 policy; not wired into CI yet
py -3 -m pytest tests/ -q -m "solver or requires_moreau"
```

Regression tests that encode known P0 defects live under `tests/stabilization/` and use `pytest.mark.xfail(strict=True, reason="CS-SOLVER-00N")` so default CI stays green while still failing loudly if a defect is “fixed” incorrectly without updating the test.

## Issue IDs

See [`issue_ledger.json`](issue_ledger.json). Fixes belong in S1+ work packages on short-lived branches off `engineering/stabilization-moreau`.
