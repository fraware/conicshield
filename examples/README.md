# Examples

Runnable entry points for researchers and integrators. Run from the **repository root**:

```bash
python examples/<script>.py
```

| Example | Audience | Vendor Moreau | Published artifacts | Proves |
|---------|----------|---------------|---------------------|--------|
| [minimal_reference_projection.py](minimal_reference_projection.py) | Integrator | No | No | Reference CVXPY path on minimal spec |
| [native_compiled_projection.py](native_compiled_projection.py) | Integrator | **Yes** | No | Sequential native compiled `project()` |
| [true_batched_compiled_projection.py](true_batched_compiled_projection.py) | Integrator | **Yes** | No | True batch `project_batch()` / `CompiledSolver` |
| [inspect_flagship_bundle.py](inspect_flagship_bundle.py) | Researcher | No | **Yes** | Index verify + governance + summary arms |
| [load_flagship_run.py](load_flagship_run.py) | Researcher | No | **Yes** | `published_runs` API load paths |
| [compare_reference_vs_native_metrics.py](compare_reference_vs_native_metrics.py) | Researcher | No | **Yes** | Arm metrics from flagship `summary.json` |
| [refresh_published_bundle_readmes.py](refresh_published_bundle_readmes.py) | Maintainer | No | **Yes** | Metadata + README + index sync |

## Quickstarts

- Researchers: [docs/QUICKSTART_RESEARCHER.md](../docs/QUICKSTART_RESEARCHER.md)
- Integrators: [docs/QUICKSTART_INTEGRATOR.md](../docs/QUICKSTART_INTEGRATOR.md)
- Maintainers: [docs/QUICKSTART_MAINTAINER.md](../docs/QUICKSTART_MAINTAINER.md)

## Claims

See [docs/PUBLIC_CLAIMS.md](../docs/PUBLIC_CLAIMS.md) before citing results externally.
