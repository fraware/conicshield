# Published run `wsl-real-20260409-132450`

`CURRENT.json` for family `conicshield-transition-bank-v1` points at this `run_id`. **Strict governance audit** expects a validate-passing bundle at this path (see `conicshield.benchmark_paths.resolve_run_directory`).

## Maintainer: commit the real bundle here

1. On the licensed host where this run was produced, confirm:

   `python -m conicshield.artifacts.validator_cli --run-dir <path-to-bundle>`

2. Copy the **entire** directory contents into this folder so it matches the published run (same `config.json`, `summary.json`, `episodes.jsonl`, `transition_bank.json`, `governance_status.json` when present, schema sidecars, etc.).

3. Re-run locally from the repo root:

   `python -m conicshield.governance.audit_cli --strict`

Until the files are present, clones of the repository cannot reproduce or audit the published bytes alongside registry metadata. Keeping this directory in sync with each publish is the chosen **in-repo immutable bundle** policy; see [`../README.md`](../README.md).
