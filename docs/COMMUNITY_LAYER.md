# Community layer (public front door)

**Start here** if you are new to the repository. This page is the default map for researchers, integrators, and anyone citing published benchmarks.

Maintainer depth (cadence, governance graph, refresh scripts) lives in [`docs/README.md`](README.md) — not required for consumption.

## Choose your path (< 10 minutes)

| You are | Start here | Then run |
|---------|------------|----------|
| Researcher (cite / inspect bundles) | [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md) | `python examples/verify_published_run_index.py` |
| Integrator (use the library) | [QUICKSTART_INTEGRATOR.md](QUICKSTART_INTEGRATOR.md) | `python examples/minimal_reference_projection.py` |
| Maintainer (publish / refresh) | [QUICKSTART_MAINTAINER.md](QUICKSTART_MAINTAINER.md) | `make verify-v1-lock` |
| Auditor (“is v1 still coherent?”) | below | `make verify-v1-lock-quick` |

## Published benchmark dataset

Committed bundles: `benchmarks/published_runs/<run_id>/`  
Integrity index: [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json)  
Flagship publication artifact: **`host-realistic-20260525`** — family `current_run_id` for `conicshield-transition-bank-v1`

Read the flagship [`README.md`](../benchmarks/published_runs/host-realistic-20260525/README.md) and [`COMMUNITY_METADATA.json`](../benchmarks/published_runs/host-realistic-20260525/COMMUNITY_METADATA.json) before interpreting `summary.json`.

### Python API (v1 stable — do not rely on governance internals)

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

- Reference: [PUBLISHED_RUNS_API.md](PUBLISHED_RUNS_API.md) (stability guarantees)
- CLI: `python -m conicshield.published_runs.cli` — `list`, `current`, `verify`, `show`, `summary`, `provenance`
- Full walkthrough: [examples/load_published_runs_api.py](../examples/load_published_runs_api.py)

## Examples (learn by running)

| Script | Audience |
|--------|----------|
| [verify_published_run_index.py](../examples/verify_published_run_index.py) | Researcher |
| [inspect_flagship_bundle.py](../examples/inspect_flagship_bundle.py) | Researcher |
| [compare_reference_vs_native_metrics.py](../examples/compare_reference_vs_native_metrics.py) | Researcher |
| [load_published_runs_api.py](../examples/load_published_runs_api.py) | Researcher |
| [minimal_reference_projection.py](../examples/minimal_reference_projection.py) | Integrator |
| [true_batched_compiled_projection.py](../examples/true_batched_compiled_projection.py) | Integrator (vendor) |

Table: [examples/README.md](../examples/README.md)

## Claims and citation

- [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md) — what you may and may not say publicly
- [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md) — runs, index commit, family current
- [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md) — batch API vs throughput claims
- [DIFFERENTIATION_PUBLIC_STANCE.md](DIFFERENTIATION_PUBLIC_STANCE.md) — validation only

## Verification

```bash
make community-verify       # API + CLI + public examples (read-only)
make verify-v1-lock-quick    # auditor: index, cadence, bundle profile, community tests
make verify-v1-lock          # full gate before “v1 locked” statements
python scripts/verify_v1_lock.py --json
```

**Canonical auditor question:** “Is the reference system still coherent?” → `make verify-v1-lock-quick` first.
