# Live / vendor integration tests

Vendor-heavy tests live under `tests/vendor/` (native + diff). Inter-sim-rl e2e remains `tests/test_inter_sim_rl_e2e.py` until further moves. See `tests/STRUCTURE.md`.

## Windows vs WSL

**Optimal Intellect Moreau is not supported on native Windows.** Pip may install an unrelated tiny PyPI package also named `moreau`; the real solver registers in CVXPY only on **Linux / WSL2**.

- **Full live vendor lane:** use **WSL2** (Ubuntu), same repo (`cd` to the Linux path, e.g. `/mnt/c/Users/<you>/conicshield`), copy `.env`, then `python scripts/run_live_vendor_tests.py --bootstrap` and run without `--skip-preflight`.
- **Windows only:** `python scripts/run_live_vendor_tests.py --skip-preflight` runs pytest but most Moreau-marked tests will still skip or fail at import time.

Run everything that needs Moreau license and optional `INTERSIM_RL_ROOT` from a filled `.env`:

```bash
# First time / new venv: install project + vendor solver into THIS interpreter
python scripts/run_live_vendor_tests.py --bootstrap

python scripts/run_live_vendor_tests.py
# Optional parallelism when pytest-xdist is installed:
#   python scripts/run_live_vendor_tests.py --parallel auto
# Extra pytest flags are forwarded (e.g. --collect-only, -k native).
# If you must run pytest without cvxpy/moreau (not recommended): --skip-preflight
```

With `CONICSHIELD_LOAD_DOTENV=1`, plain `pytest` also loads `.env` (see `tests/conftest.py`).
