# Using `PUBLISHED_RUN_INDEX.json`

How external researchers and integrators consume governed bundles without maintainer access.

## What the index is

[`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) (schema v2) lists every **committed** run under `benchmarks/published_runs/<run_id>/` with:

- `repository_relative_path` — bundle root
- `integrity` — SHA-256 per file (validator surface + governance sidecars)
- `catalog` — evidence tier, native arm, host-realistic flags

It is the **integrity catalog**, not the scientific claim. Scope lives in each bundle’s `README.md` and `COMMUNITY_METADATA.json`.

## Recommended workflow

1. **Clone** the repo at a release tag or `main` commit you trust.
2. **Verify integrity:**
   ```bash
   python scripts/refresh_published_run_index.py --check
   ```
3. **Pick a run** — flagship: `host-realistic-20260525` (`current_run_id` in [`benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json`](../benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json)).
4. **Read scope before metrics:**
   - `benchmarks/published_runs/<run_id>/COMMUNITY_METADATA.json` ([schema](COMMUNITY_METADATA_SCHEMA.md))
   - `benchmarks/published_runs/<run_id>/README.md`
5. **Validate bundle shape:**
   ```bash
   python -m conicshield.published_runs.cli verify <run_id>
   python scripts/validate_published_bundle_profile.py --run-id <run_id>
   python -m conicshield.artifacts.validator_cli --run-dir benchmarks/published_runs/<run_id>
   ```

   Python API:
   ```python
   from conicshield.published_runs import (
       list_runs,
       get_current_run,
       load_run,
       verify_run,
       load_summary,
       load_provenance,
   )
   ```
   Examples: [verify_published_run_index.py](../examples/verify_published_run_index.py), [inspect_flagship_bundle.py](../examples/inspect_flagship_bundle.py).

## Files to trust for what

| File | Use |
|------|-----|
| `config.json`, `episodes.jsonl`, `transition_bank.json` | Task contract + data |
| `summary.json` | Arm metrics (read `label` per row) |
| `governance_status.json` | Gate colors at publish time |
| `RUN_PROVENANCE.json` | How the bundle was produced |
| `governance_decision.md` | Human approve/defer |
| `release_decision.json` | Release orchestration record |
| `solver_versions.json` | Vendor stack snapshot (when present) |
| `parity_out/` | Native vs reference replay (when present) |

## What the index does not guarantee

- Universal batch speedup (see [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md))
- Production autograd (see [`DIFFERENTIATION_PUBLIC_STANCE.md`](DIFFERENTIATION_PUBLIC_STANCE.md))
- Full upstream navigation graphs for host-realistic runs (fork topology unless provenance says otherwise)

## Flagship export chain

Host-realistic runs link to [`benchmarks/external_evidence/EXPORT_PROVENANCE.json`](../benchmarks/external_evidence/EXPORT_PROVENANCE.json) and [`docs/REFERENCE_AUTHORITY_LOG.md`](REFERENCE_AUTHORITY_LOG.md).
