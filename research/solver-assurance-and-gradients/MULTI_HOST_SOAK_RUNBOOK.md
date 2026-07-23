# Multi-host R4 soak runbook (operator)

Honest evidence collection for the R4 multi-environment gate.
**Synthetic second-host simulation does not satisfy this gate.**
Do not claim R4 / proof-carrying flagship promotion without ≥2 independent
**real** hosts and production governed-hash wiring.

## Artifact schema

Each host produces:

| File | Schema / content |
| ---- | ---------------- |
| `platform_soak.json` | `research.platform_soak_report.v0` |
| `assurance_bundle.json` | AssuranceBundle + sealed digest |
| `provenance.json` | experiment provenance |
| `platform_soak__<host_id>.json` | host-keyed shard (same payload) |

Required `platform` fields: `host_id`, `host_kind` (`real` \| `synthetic`),
`operating_system`, `python_version`, `cpu_info`, `gpu_info`,
`repository_commit`, `dirty_worktree`, `solver_versions`,
`artifact_hashes`, `sealed_corrected_action_digest`, `bundle_sha256`.

Aggregate:

| File | Schema |
| ---- | ------ |
| `platform_soak_aggregate.json` | `research.platform_soak_aggregate.v0` |

Aggregate fields of interest: `n_real_hosts`, `n_synthetic_hosts`,
`digest_mismatches`, `r4_multi_host_gate_ready`, `promotion_claim` (always
`false` from research tooling).

## Exact commands (local / operator machines)

On each **real** host (distinct OS and/or Python environment):

```bash
# from repo root, clean-ish checkout preferred
python -m pip install -r requirements-dev.txt
python -m pip install -e ".[dev]"

python -m conicshield.experimental.assurance.platform_soak \
  --output-dir output/research/multi_host/<host_label> \
  --host-id "<hostname>|<os>|<python>" \
  --host-kind real
```

Copy each host's `platform_soak.json` (or shard) to a merge workstation, then:

```bash
python -m conicshield.experimental.assurance.platform_soak \
  --output-dir output/research/multi_host/aggregate \
  --aggregate \
    output/research/multi_host/host_a/platform_soak.json \
    output/research/multi_host/host_b/platform_soak.json
```

Inspect:

```bash
python -c "import json; d=json.load(open('output/research/multi_host/aggregate/platform_soak_aggregate.json')); print(d['n_real_hosts'], d['n_synthetic_hosts'], d['r4_multi_host_gate_ready'], d['promotion_claim'], d['r4_blockers'])"
```

## CI matrix (≥2 GitHub Actions OS runners)

Workflow: `.github/workflows/research-multi-host-soak.yml` (separate from
`research-public.yml` — does not alter that required path).

- Matrix: `ubuntu-latest` + `windows-latest`
- Each job writes a `host_kind=real` soak shard
- A follow-on job downloads shards and aggregates digests
- Artifacts retained; **promotion_claim remains false**
- Even with 2 CI OS runners, R4 **production** gate still needs governed-hash
  integration with release tooling (see PROMOTION_GATES.md)

Manual dispatch:

```text
Actions → research-multi-host-soak → Run workflow
```

## Simulated multi-host (QA only)

```bash
python -m conicshield.experimental.assurance.multi_host_soak_sim \
  --output-dir output/research/multi_host_soak_sim \
  --digest-mode match
```

Records `is_synthetic: true`, `n_real_hosts: 1`. **Does not** clear R4.

## Same physical machine: Windows + WSL

Distinct OS environments on one machine **may** count as two real hosts when **all** of:

1. Each soak uses `host_kind=real`
2. `host_id` values are distinct (include OS label, e.g. `…|windows|…` vs `…|linux-wsl|…`)
3. Aggregate shows `n_real_hosts >= 2`, `n_synthetic_hosts == 0`
4. Sealed corrected-action digests agree (bundle SHA may differ — host-local provenance)

This matches the runbook rule “distinct OS and/or Python environment” and the CI
ubuntu+windows matrix spirit. It is **evidence-readiness only**, not a production
R4 pass (governed-hash release wiring still required). Physically separate machines
or the GitHub Actions matrix remain preferred for stronger independence claims.

## Pass / fail honesty

| Evidence | Counts for R4 multi-host? |
| -------- | ------------------------- |
| 2+ `host_kind=real` soaks, aggregated, sealed digests agree | Evidence toward gate (still not production claim) |
| Windows + WSL on one machine (distinct `host_id`, both `real`, sealed digests agree) | Evidence toward gate under policy above; still not production claim |
| CI ubuntu+windows matrix aggregate | Real OS diversity evidence; still not production claim |
| `multi_host_soak_sim` synthetic second host | **No** |
| Single-host soak | **No** |
