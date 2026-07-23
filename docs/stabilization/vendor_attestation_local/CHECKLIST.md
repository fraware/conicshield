# Local vendor attestation checklist

Mirrors `.github/workflows/solver-ci.yml` evidence path. Do **not** claim the
vendor CI gate cleared without green evidence below.

## Prerequisites (WSL2 / Linux)

1. `GEMFURY_TOKEN` or `MOREAU_EXTRA_INDEX_URL` / `MOREAU_PIP_EXTRA_INDEX_URL` in `.env`
2. `MOREAU_LICENSE_KEY` in `.env` (or `~/.moreau/key`)
3. Bootstrap: `CONICSHIELD_BOOTSTRAP_PROFILE=moreau-cpu bash scripts/bootstrap_moreau.sh`
4. Verify: `python -m moreau check`

## Commands

```bash
export CONICSHIELD_VENDOR_REQUIRED=1
python scripts/run_local_vendor_attestation.py --out-dir docs/stabilization/vendor_attestation_local
```

## Success criteria (all required)

- `attestation_status.json` → `status` is `PASS`
- `mandatory_native_solves.json` → `known_feasible_ok` and failure-policy OK; `native_solve_count` ≥ 1
- `vendor_pytest.junit.xml` present with executed vendor tests
- `assert_vendor_ci_evidence` exit 0 (recorded in status)

## Failure modes that must remain red

- Native Windows host
- PyPI stub `moreau` without `CompiledSolver`
- Missing license / GemFury install
- Empty or all-skipped pytest suites
