# Examples

Run from the **repository root**:

```bash
python examples/<script>.py
```

Public front door: [docs/COMMUNITY_LAYER.md](../docs/COMMUNITY_LAYER.md).

| Example | Audience | Vendor Moreau? | Proves | Does not prove |
|---------|----------|----------------|--------|----------------|
| [verify_published_run_index.py](verify_published_run_index.py) | Researcher | No | Index `--check`, `list_runs`, `verify_run` | Scientific superiority |
| [inspect_flagship_bundle.py](inspect_flagship_bundle.py) | Researcher | No | Flagship tier, host-realistic, native arm, gates | Navigation graph, autograd |
| [compare_reference_vs_native_metrics.py](compare_reference_vs_native_metrics.py) | Researcher | No | Published p50 metrics per arm | Universal speedup; overrides governance |
| [load_published_runs_api.py](load_published_runs_api.py) | Researcher | No | Full v1 `published_runs` API walkthrough | Publish pipeline |
| [load_flagship_run.py](load_flagship_run.py) | Researcher | No | Short API load path | Deep governance tour |
| [minimal_reference_projection.py](minimal_reference_projection.py) | Integrator | No | CVXPY reference `project()` | Native batch throughput |
| [native_compiled_projection.py](native_compiled_projection.py) | Integrator | **Yes** | Sequential native compiled path | Batch semantics |
| [true_batched_compiled_projection.py](true_batched_compiled_projection.py) | Integrator | **Yes** | True `project_batch` API | Universal throughput claim |
| [refresh_published_bundle_readmes.py](refresh_published_bundle_readmes.py) | Maintainer | No | `finalize_community_dataset` flow | — |

## Quickstarts

- [QUICKSTART_RESEARCHER.md](../docs/QUICKSTART_RESEARCHER.md)
- [QUICKSTART_INTEGRATOR.md](../docs/QUICKSTART_INTEGRATOR.md)
- [QUICKSTART_MAINTAINER.md](../docs/QUICKSTART_MAINTAINER.md)

## Claims

Read [docs/PUBLIC_CLAIMS.md](../docs/PUBLIC_CLAIMS.md) before citing results externally.
