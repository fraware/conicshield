# Community layer

One-page map for **external** users. Maintainer depth stays in [`README.md`](README.md) and [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## Choose your path (< 10 minutes)

| You are | Start here | Then run |
|---------|------------|----------|
| Researcher (cite / inspect bundles) | [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md) | `python examples/verify_published_run_index.py` |
| Integrator (use the library) | [QUICKSTART_INTEGRATOR.md](QUICKSTART_INTEGRATOR.md) | `python examples/minimal_reference_projection.py` |
| Maintainer (publish / refresh) | [QUICKSTART_MAINTAINER.md](QUICKSTART_MAINTAINER.md) | `make verify-v1-lock` |

## Published benchmark dataset

Committed bundles: `benchmarks/published_runs/<run_id>/`  
Integrity index: [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json)  
Flagship: **`host-realistic-20260525`** (`conicshield-transition-bank-v1` current run)

### Python API

```python
from conicshield.published_runs import (
    list_runs,
    get_current_run,
    load_run,
    verify_run,
    load_summary,
    load_provenance,
)

verify_run("host-realistic-20260525")
bundle = get_current_run("conicshield-transition-bank-v1")
```

Reference: [PUBLISHED_RUNS_API.md](PUBLISHED_RUNS_API.md) · CLI: `python -m conicshield.published_runs.cli` · `conicshield-published-runs` after install

Each bundle ships **`COMMUNITY_METADATA.json`** (scope, uses, limitations) — read before `summary.json`.

## Examples (no policy docs required)

| Script | Audience |
|--------|----------|
| [verify_published_run_index.py](../examples/verify_published_run_index.py) | Researcher |
| [inspect_flagship_bundle.py](../examples/inspect_flagship_bundle.py) | Researcher |
| [minimal_reference_projection.py](../examples/minimal_reference_projection.py) | Integrator |
| [true_batched_compiled_projection.py](../examples/true_batched_compiled_projection.py) | Integrator (vendor) |

Full table: [examples/README.md](../examples/README.md)

## Claims and citation

- Honest boundaries: [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md)
- Citing runs / index / family: [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)
- Batch narrative: [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md) (viability, not universal speedup)
- Differentiation: [DIFFERENTIATION_PUBLIC_STANCE.md](DIFFERENTIATION_PUBLIC_STANCE.md) (validation only)

## Verification

```bash
make community-verify    # API, CLI, public examples (read-only)
make verify-v1-lock      # full reference-system gate (maintainers)
```
