# Reference system (v1)

Single-page map for auditors and external consumers. Machine summary: [`benchmarks/reports/reference_system_status.json`](../benchmarks/reports/reference_system_status.json).

## Flagship

| Field | Value |
|-------|--------|
| Family | `conicshield-transition-bank-v1` |
| `current_run_id` | `host-realistic-20260525` |
| Tier | `vendor_native`, `real_projector` |
| Export | `live_upstream_dump`, graph `host_realistic_fork` |

## Closed loop

```text
capture inter-sim graph → upstream export JSON → transition bank → publish → parity → release → index
```

Licensed command: `make host-realistic-refresh-cycle-licensed`

## Evidence and logs

| Artifact | Role |
|----------|------|
| [`REFERENCE_AUTHORITY_LOG.md`](REFERENCE_AUTHORITY_LOG.md) | Human refresh cadence log |
| [`EXPORT_PROVENANCE.json`](../benchmarks/external_evidence/EXPORT_PROVENANCE.json) | Export + `refresh_history` |
| [`reference_authority_snapshot.json`](../benchmarks/reports/reference_authority_snapshot.json) | CI alignment gate |
| [`PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) | Per-file SHA-256 integrity |
| [`COMMUNITY_METADATA.json`](../benchmarks/published_runs/host-realistic-20260525/COMMUNITY_METADATA.json) | External scope per bundle |

## CI merge gates

`quality`, `conic-trusted-shape`, `governance-audit`, `reference-authority`, `solver-touch` — see [`CI_MERGE_GATES.md`](CI_MERGE_GATES.md). `vendor-ci-moreau` is Policy B attestation, not a required check.

## Public claim boundaries

| Topic | Allowed | Not allowed |
|-------|---------|-------------|
| Batch | True batched solve exists; viability tested | Universal speedup on all scenarios |
| Differentiation | FD / validation (Layer F) | Production autograd product |
| Graph | Fork validated via inter-sim API | Full Maps/session navigation graph |

## Community dataset API

Governed bundles are a **public dataset**, not only maintainer docs.

| Surface | Entry |
|---------|--------|
| Quickstarts | [`QUICKSTART_RESEARCHER.md`](QUICKSTART_RESEARCHER.md), [`QUICKSTART_INTEGRATOR.md`](QUICKSTART_INTEGRATOR.md) |
| Python API | `conicshield.published_runs` — `list_runs`, `load_run`, `verify_run`, `load_summary` |
| CLI | `python -m conicshield.published_runs.cli` or `conicshield-published-runs` after install |
| Scope per bundle | `COMMUNITY_METADATA.json` ([schema](COMMUNITY_METADATA_SCHEMA.md)) |
| Honest claims | [`PUBLIC_CLAIMS.md`](PUBLIC_CLAIMS.md), [`CITING_CONICSHIELD_ARTIFACTS.md`](CITING_CONICSHIELD_ARTIFACTS.md) |
| Examples | [`examples/`](../examples/README.md) |

```bash
make community-verify
python -m conicshield.published_runs.cli verify host-realistic-20260525
```

## Verification

```bash
make verify-reference-system
make community-verify
python scripts/check_flagship_full_refresh_cadence.py --max-days 35
python scripts/generate_reference_system_status.py --check
```

Pre-lock verification: `make verify-v1-lock` ([`V1_LOCK_CHECKLIST.md`](V1_LOCK_CHECKLIST.md))
