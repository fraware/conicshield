# Examples

Runnable scripts for the **public product surface**. Run every command from the **repository root**:

```bash
pip install -e ".[dev]"
make onboard                    # recommended first check
python examples/<script>.py
```

Public map: [docs/COMMUNITY_LAYER.md](../docs/COMMUNITY_LAYER.md).

## Researcher (published bundles, no vendor Moreau)

| Script | What you learn | Typical output |
|--------|----------------|----------------|
| [verify_published_run_index.py](verify_published_run_index.py) | Index integrity + verify all indexed runs | `index integrity OK`, `verify_run OK` per run |
| [load_published_runs_api.py](load_published_runs_api.py) | **Canonical** v1 API tour | list/current/verify/summary/provenance + CLI hints |
| [inspect_flagship_bundle.py](inspect_flagship_bundle.py) | Flagship metadata, gates, arms | `vendor_native`, green gates, 4 arms |
| [load_flagship_run.py](load_flagship_run.py) | Shortest verify + episodes sample | `integrity OK`, episode keys |
| [compare_reference_vs_native_metrics.py](compare_reference_vs_native_metrics.py) | Reference vs native p50/p95 | ratio + **disclaimer** (not a speedup claim) |

## Integrator (library projection)

| Script | Requires | Notes |
|--------|----------|--------|
| [minimal_reference_projection.py](minimal_reference_projection.py) | CVXPY + Moreau | `SKIP` if reference stack missing |
| [native_compiled_projection.py](native_compiled_projection.py) | Licensed Moreau | sequential native compiled path |
| [true_batched_compiled_projection.py](true_batched_compiled_projection.py) | Licensed Moreau | `project_batch`; viability_only public narrative |

## Maintainer

| Script | Notes |
|--------|--------|
| [refresh_published_bundle_readmes.py](refresh_published_bundle_readmes.py) | **Mutates** repo (finalize + index). Use `--check-only` to verify without writing. |

## Shared helpers

[_common.py](_common.py) — `repo_root()`, `section()`, `minimal_spec()`, flagship constants.

## Structure (every public example)

Each script documents:

- **Audience** — who should run it  
- **Prerequisites** — install / license  
- **Proves** / **Does not prove** — claim discipline  
- **Expected** — what success looks like  

## Claims

Read [docs/PUBLIC_CLAIMS.md](../docs/PUBLIC_CLAIMS.md) before citing results externally.

## CI

`tests/examples/test_public_examples_smoke.py` runs researcher + reference examples (vendor examples may `SKIP` with exit 0).
