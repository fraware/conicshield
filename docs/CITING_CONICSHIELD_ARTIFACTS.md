# Citing ConicShield artifacts

How to cite bundles, families, and the integrity index without conflating **artifact identity** with **scientific conclusions**.

## Cite a specific run id

Use the governed `run_id` and the **git commit** that contains its bundle bytes and index hashes.

> ConicShield published run `host-realistic-20260525` (family `conicshield-transition-bank-v1`), repository commit `<SHA>`, bundle path `benchmarks/published_runs/host-realistic-20260525/`, scope file `COMMUNITY_METADATA.json`.

Include `evidence_tier` and `export_kind` from that metadata when the claim depends on them.

## Cite a family current run

For “the project’s current reference benchmark,” cite:

- family id: `conicshield-transition-bank-v1`
- `current_run_id` from `benchmarks/releases/conicshield-transition-bank-v1/CURRENT.json` at commit `<SHA>`

Do not cite a historical `run_id` as “current” without checking `CURRENT.json` at that commit.

## Cite the integrity index

When referring to **verification** rather than metrics:

> `benchmarks/PUBLISHED_RUN_INDEX.json` at commit `<SHA>` (schema v2), verified with `python scripts/refresh_published_run_index.py --check`.

The index is an **integrity catalog** (SHA-256 per file), not the scientific claim. See [PUBLISHED_RUN_INDEX_SCHEMA.md](PUBLISHED_RUN_INDEX_SCHEMA.md).

## Bundle citation vs scientific claim

| Citation type | Points to | Does not prove |
|---------------|-----------|----------------|
| Bundle + commit | Exact bytes and governance snapshot | Novel algorithmic superiority |
| `summary.json` row | Recorded arm metrics at publish | Universal batch or autograd claims |
| `COMMUNITY_METADATA.json` | Allowed uses and limitations | More than listed in `known_limitations` |

Read [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md) before drafting paper text.

## Machine-readable helpers

```bash
python -m conicshield.published_runs.cli show host-realistic-20260525
```

```python
from conicshield.published_runs import current_family_run
bundle = current_family_run("conicshield-transition-bank-v1")
```
