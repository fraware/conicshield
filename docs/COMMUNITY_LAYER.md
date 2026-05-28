# Community layer (public front door)

**Start here** if you are new to the repository. This page is the default map for researchers, integrators, and anyone citing published benchmarks.

v1 release summary: [`V1_REFERENCE_RELEASE.md`](V1_REFERENCE_RELEASE.md).  
All public docs: [`README.md`](README.md) in this folder.

```bash
make onboard   # under one minute: community-verify + v1 status snapshot
```

**Day-to-day auditor check:** `make verify-v1-lock-quick`  
**Pre-announcement lock gate:** `make verify-v1-lock`

## Choose your path (< 10 minutes)

| You are | Start here | Then run |
|---------|------------|----------|
| Researcher (cite / inspect bundles) | [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md) | `python examples/verify_published_run_index.py` |
| Integrator (use the library) | [QUICKSTART_INTEGRATOR.md](QUICKSTART_INTEGRATOR.md) | `python examples/minimal_reference_projection.py` |
| Auditor (“is v1 still coherent?”) | below | `make verify-v1-lock-quick` |

Repository changes (publish, refresh, CI): [CONTRIBUTING.md](../CONTRIBUTING.md).

## Published benchmark dataset

Committed bundles: `benchmarks/published_runs/<run_id>/`  
Integrity index: [`benchmarks/PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json)  
Flagship publication artifact: **`host-realistic-20260525`** — family `current_run_id` for `conicshield-transition-bank-v1`

Read the flagship [`README.md`](../benchmarks/published_runs/host-realistic-20260525/README.md) and [`COMMUNITY_METADATA.json`](../benchmarks/published_runs/host-realistic-20260525/COMMUNITY_METADATA.json) before interpreting `summary.json`.

### Why use the API instead of reading raw JSON?

- **Stable interface** — `list_runs`, `verify_run`, `load_summary`, and CLI subcommands are versioned in v1; raw bundle layout can gain files without breaking callers.
- **Easier validation** — `verify_run` checks SHA-256 against `PUBLISHED_RUN_INDEX.json` in one call.
- **Forward-compatible ergonomics** — optional catalog fields and new sidecars can appear; dataclasses and helpers absorb them without your scripts parsing paths by convention.

**Canonical example:** [examples/load_published_runs_api.py](../examples/load_published_runs_api.py) (list → current → verify → summary → provenance).

### Python API (v1 stable)

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

- Reference: [PUBLISHED_RUNS_API.md](PUBLISHED_RUNS_API.md)
- CLI: `python -m conicshield.published_runs.cli` — `list`, `current`, `verify`, `show`, `summary`, `provenance`

## Examples (learn by running)

| Script | Audience |
|--------|----------|
| [verify_published_run_index.py](../examples/verify_published_run_index.py) | Researcher |
| [inspect_flagship_bundle.py](../examples/inspect_flagship_bundle.py) | Researcher |
| [compare_reference_vs_native_metrics.py](../examples/compare_reference_vs_native_metrics.py) | Researcher |
| [load_published_runs_api.py](../examples/load_published_runs_api.py) | Researcher (canonical API) |
| [minimal_reference_projection.py](../examples/minimal_reference_projection.py) | Integrator |
| [true_batched_compiled_projection.py](../examples/true_batched_compiled_projection.py) | Integrator (vendor) |

Table: [examples/README.md](../examples/README.md)

## Claims and citation

- [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md)
- [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md)
- [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md)
- [DIFFERENTIATION_PUBLIC_STANCE.md](DIFFERENTIATION_PUBLIC_STANCE.md)

## Verification

```bash
make community-verify
make verify-v1-lock-quick
make verify-v1-lock
python scripts/verify_v1_lock.py --json
```

| Command | When |
|---------|------|
| `make verify-v1-lock-quick` | Day-to-day: “Is v1 still coherent?” |
| `make verify-v1-lock` | Before external “v1 locked” or release announcements |

Success JSON shape: [`V1_LOCK_AUDITOR_SUCCESS.example.json`](V1_LOCK_AUDITOR_SUCCESS.example.json).  
Entrypoint: [`scripts/verify_v1_lock.py`](../scripts/verify_v1_lock.py).
