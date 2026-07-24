# Multi-host R12 soak runbook (operator)

Honest evidence collection for the R4 / R12 multi-environment gate.
**Synthetic second-host simulation does not satisfy this gate.**
Do not claim R4 / proof-carrying flagship promotion without ≥2 independent
**real** hosts, matching problem digests, and production governed-hash wiring.

Phase-0 historical soak artifacts remain invalidated
(`annotate_deprecated_soak_artifact`); do not re-interpret them as R12-ready.

## Required matrix roles

| Environment | Role id | Purpose |
| ----------- | ------- | ------- |
| Linux public solver | `linux_public` | deterministic public baseline |
| Windows public solver | `windows_public` | cross-platform public replay |
| Linux/WSL Moreau CPU | `linux_wsl_moreau_cpu` | native exact + batch |
| Linux Moreau CUDA | `linux_moreau_cuda` | GPU when available |
| Windows→WSL sidecar | `windows_wsl_sidecar` | transport + request binding |

Windows + Linux **public** runners alone do **not** establish Moreau
reproducibility. Any Moreau research claim requires ≥1 native Moreau host.
L4 candidates require ≥2 independent environments (distinct
`environment_signature`).

## Artifact schema

Each host produces:

| File | Schema / content |
| ---- | ---------------- |
| `platform_soak.json` | `research.platform_soak_report.v1` |
| `assurance_bundle.json` | AssuranceBundle v1 + digests |
| `provenance.json` | experiment provenance |
| `platform_soak__<host_id>.json` | host-keyed shard (same payload) |

Required `platform` fields:

- identity: `host_id`, `host_kind` (`real` \| `synthetic`), `matrix_role`
- environment: `operating_system`, `python_version`, `cpu_info`, `gpu_info`,
  `environment_signature`
- provenance: `repository_commit`, `dirty_worktree` (must be `false` for gate),
  `package_provenance`, `solver_versions`, `corpus_version`
- digests: `problem_digest`, `forward_solution_digest`,
  `sealed_corrected_action_digest`, `bundle_sha256`
- evidence: `has_shadow`, `has_live_sensitivity`, `claimed_evidence_level`,
  `moreau_native`
- index: `artifact_hashes`, `artifact_index`

Aggregate:

| File | Schema |
| ---- | ------ |
| `platform_soak_aggregate.json` | `research.platform_soak_aggregate.v1` |

Aggregate fields of interest: `n_real_hosts`, `n_synthetic_hosts`,
`n_independent_envs`, `matrix_roles_present`, `problem_digest_mismatches`,
`digest_comparison_policy` (`byte_identity`), `numerical_comparison_policy`
(`tolerance`), `rejection_reasons`, `r4_multi_host_gate_ready`,
`promotion_claim` (always `false` from research tooling).

### Digest vs tolerance

- **Byte identity:** `problem_digest`, sealed corrected-action digest, commit.
- **Tolerance / informational:** forward digests and bundle SHA may differ
  across solvers/hosts; recorded as notes, not equated to problem agreement.

## Exact commands (local / operator machines)

On each **real** host (distinct OS and/or Python environment), pick the matching
`--matrix-role`:

```bash
# from repo root, clean checkout required for R12 gate (dirty_worktree=false)
python -m pip install -r requirements-dev.txt
python -m pip install -e ".[dev]"

python -m conicshield.experimental.assurance.platform_soak \
  --output-dir output/research/multi_host/<host_label> \
  --host-id "<hostname>|<os>|<python>|<matrix_role>" \
  --host-kind real \
  --matrix-role linux_public   # or windows_public / linux_wsl_moreau_cpu / ...
```

Copy each host's `platform_soak.json` (or shard) to a merge workstation, then:

```bash
python -m conicshield.experimental.assurance.platform_soak \
  --output-dir output/research/multi_host/aggregate \
  --aggregate \
    output/research/multi_host/host_a/platform_soak.json \
    output/research/multi_host/host_b/platform_soak.json \
  --expected-commit "$(git rev-parse HEAD)" \
  --require-public-matrix
# add --require-moreau-matrix when claiming Moreau research coverage
```

Inspect:

```bash
python -c "import json; d=json.load(open('output/research/multi_host/aggregate/platform_soak_aggregate.json')); print(d['n_real_hosts'], d['n_synthetic_hosts'], d['matrix_roles_present'], d['r4_multi_host_gate_ready'], d['rejection_reasons'], d['promotion_claim'])"
```

## Aggregate gate (rejects)

The aggregate **rejects** readiness when any of:

- synthetic hosts counted toward the gate
- missing / mismatched `problem_digest` (byte identity)
- sealed digest mismatch
- dirty worktree
- stale or disagreeing `repository_commit` (or vs `--expected-commit`)
- corpus / provenance mismatch
- synthetic sensitivity fields
- L3 claimed without live gradient (`has_live_sensitivity`)
- Moreau claim without ≥1 `moreau_native` host
- L4 candidate with `<2` independent `environment_signature`s

Governed-hash verification (`governed_hash_policy`) recomputes **actual**
on-disk artifact hashes and requires attestation — nonempty digest strings
alone do not pass.

## CI matrix

Workflow: `.github/workflows/research-multi-host-soak.yml` (separate from
`research-public.yml`).

- Always: `linux_public` (`ubuntu-latest`) + `windows_public` (`windows-latest`)
- Optional (disabled until self-hosted labels exist):
  `linux_wsl_moreau_cpu`, `linux_moreau_cuda`, `windows_wsl_sidecar`
- Follow-on job aggregates shards with `--require-public-matrix` and
  `--expected-commit=$GITHUB_SHA`
- Artifacts retained; **promotion_claim remains false**

Manual dispatch:

```text
Actions → research-multi-host-soak → Run workflow
```

Optional input `require_moreau_matrix` fails the aggregate unless a native
Moreau role shard is present.

## Simulated multi-host (QA only)

```bash
python -m conicshield.experimental.assurance.multi_host_soak_sim \
  --output-dir output/research/multi_host_soak_sim \
  --digest-mode match
```

Records `is_synthetic: true`, `n_real_hosts: 1`. **Does not** clear R12.

## Same physical machine: Windows + WSL

Distinct OS environments on one machine **may** count as two real hosts when **all** of:

1. Each soak uses `host_kind=real` with distinct `matrix_role` / `host_id`
2. Aggregate shows `n_real_hosts >= 2`, `n_synthetic_hosts == 0`
3. Problem digests agree (byte identity); sealed digests agree
4. `dirty_worktree=false` and commits match
5. For Moreau claims: WSL host uses `linux_wsl_moreau_cpu` with `moreau_native=true`

This is **evidence-readiness only**, not a production R4 pass.

## Pass / fail honesty

| Evidence | Counts for R12 multi-host? |
| -------- | -------------------------- |
| 2+ `host_kind=real` soaks, matching problem digests, clean trees, R12 fields | Evidence toward gate (still not production claim) |
| linux_public + windows_public CI matrix | Public-matrix evidence; Moreau not established |
| ≥1 native Moreau host in aggregate with Moreau claim | Required for Moreau research claims |
| ≥2 independent envs for L4 candidate | Required for L4 candidates |
| `multi_host_soak_sim` synthetic second host | **No** |
| Historical Phase-0 / v0 soak artifacts | **No** (invalidated) |
| Single-host soak | **No** |

## Remaining operator steps (live Moreau — no fake green)

Until these exist on disk as **real** host shards, R12 / R14 / R15 stay blocked:

1. Install Moreau in WSL (or Linux) and confirm `python -c "import moreau"` succeeds.
2. Run a soak with `--matrix-role linux_wsl_moreau_cpu --host-kind real` (and optionally CUDA).
3. On Windows, enable research sidecar (`CONICSHIELD_RESEARCH_SIDECAR_ENABLE=1`) and complete a live hello against the WSL worker speaking protocol v2 (request binding + provenance).
4. Aggregate real shards only; confirm `rejection_reasons=[]` is earned, not simulated.
5. Regenerate `RESEARCH_STATUS.md` via `python -m conicshield.experimental.assurance.status_report`.

Do **not** clear promotion gates with synthetic sensitivity, mock sidecar, or fabricated Moreau availability.
