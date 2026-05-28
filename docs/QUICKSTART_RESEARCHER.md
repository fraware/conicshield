# Quickstart: researcher

Curated path for **inspecting and citing** committed benchmark bundles without reading the full governance graph.

## What ConicShield proves (in this repo)

ConicShield ships **governed, hash-indexed benchmark bundles** that record shielded RL episodes, per-arm metrics, and release state. The flagship demonstrates a closed **export → transition bank → publish → parity** loop at `vendor_native` tier. See [README.md](../README.md) and [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md).

## Flagship run

| Item | Value |
|------|--------|
| `run_id` | `host-realistic-20260525` |
| Family | `conicshield-transition-bank-v1` (`current_run_id`) |
| Bundle | [`benchmarks/published_runs/host-realistic-20260525/`](../benchmarks/published_runs/host-realistic-20260525/) |
| Scope | [`COMMUNITY_METADATA.json`](../benchmarks/published_runs/host-realistic-20260525/COMMUNITY_METADATA.json) |

## Python API (recommended)

```python
from conicshield.published_runs import load_run, verify_run, load_summary

verify_run("host-realistic-20260525")
bundle = load_run("host-realistic-20260525")
print(bundle.community.known_limitations)
```

Runnable walkthrough: [`examples/load_flagship_run.py`](../examples/load_flagship_run.py). After `pip install -e .`, the same CLI is available as `conicshield-published-runs`.

## Verify the published-run index

```bash
python scripts/refresh_published_run_index.py --check
python -m conicshield.published_runs.cli list
python -m conicshield.published_runs.cli verify host-realistic-20260525
# or: conicshield-published-runs verify host-realistic-20260525
```

Details: [PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md](PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md), [PUBLISHED_RUN_INDEX_SCHEMA.md](PUBLISHED_RUN_INDEX_SCHEMA.md).

## Validate a committed bundle

```bash
python -m conicshield.artifacts.validator_cli \
  --run-dir benchmarks/published_runs/host-realistic-20260525
python scripts/validate_published_bundle_profile.py --run-id host-realistic-20260525
```

## Read key files

| File | Purpose |
|------|---------|
| `summary.json` | Per-arm benchmark metrics (`label`, solve times, etc.) |
| `governance_status.json` | Gate colors and `publishable_arms` at publish time |
| `RUN_PROVENANCE.json` | How the bundle was produced (`projector_mode`, `evidence_tier`, export source) |
| `COMMUNITY_METADATA.json` | **Read first** — recommended uses and explicit limitations |

Example: [examples/inspect_flagship_bundle.py](../examples/inspect_flagship_bundle.py), [examples/load_flagship_run.py](../examples/load_flagship_run.py).

## What this repo does **not** claim

From [CONTRIBUTING.md](../CONTRIBUTING.md) and [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md):

- `progress` / `clearance` constraint kinds
- Production shield autograd
- Other families as reference authority
- Maps/session navigation graphs (flagship uses host-realistic **fork** topology)
- Universal batch speedup

## Next steps

- [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)
- [examples/README.md](../examples/README.md)
- Full index: [docs/README.md](README.md) (maintainer-oriented)
