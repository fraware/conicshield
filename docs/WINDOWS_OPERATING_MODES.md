# Windows operating modes (S6)

ConicShield qualifies **three** Windows-related modes. Native Moreau running
inside Windows Python is **not** supported and is not a qualified mode.

| Mode | Where the app runs | Where Moreau runs | CI |
|------|--------------------|-------------------|----|
| `windows_public` | Native Windows Python | N/A (PUBLIC_CLARABEL / PUBLIC_SCS / AUTO→public) | Required: `.github/workflows/windows-ci.yml` |
| `windows_wsl_native_repo` | WSL2 Python + repo on Linux filesystem | Optional vendor install inside WSL | Local / optional; skip-with-reason when WSL absent |
| `windows_moreau_sidecar` | Native Windows Python | Persistent WSL2 worker (stdio NDJSON) | Local qualification; skip-with-reason without WSL/Moreau |

Machine identifiers: `conicshield.platform.windows_modes.WindowsOperatingMode`.

## Mode 1 — Windows Public

Bootstrap:

```powershell
pwsh scripts/bootstrap_moreau.ps1 -Profile public
conicshield solver-doctor --json
```

Expectations:

- Explicit `PUBLIC_CLARABEL` / `PUBLIC_SCS` / `AUTO` (AUTO never selects vendor Moreau from importability).
- Schema, residual verification, release evidence, CLI doctor, and governance hooks that are publicly testable.
- No vendor credentials. No native Moreau import success.

## Mode 2 — WSL-native repository

Use Linux paths (`/home/...` or `/mnt/c/...` carefully). Prefer cloning/working
inside the WSL filesystem for I/O. Path helpers:

- `conicshield.platform.paths.windows_path_to_wsl`
- `conicshield.platform.paths.wsl_path_to_windows`
- `conicshield.platform.paths.portable_artifact_key`

Vendor Moreau installs belong here (or in the sidecar worker), never on native Windows.

## Mode 3 — Windows Moreau sidecar (qualification)

Architecture:

- Persistent subprocess: Windows client ↔ WSL `python -m conicshield.workers.moreau_worker`
- Transport: versioned NDJSON on stdin/stdout (`PROTOCOL_VERSION = 2`)
- Hello negotiates via `supported_protocol_versions`; empty intersection fails closed
- Solve requests carry cryptographic `request_binding_digest`; workers recompute and reject mismatches
- hello_ack / solve_result carry worker and solver provenance
- **No** localhost networking
- **No** per-solve `wsl.exe` relaunch once the worker is up
- Requests carry structural fingerprint, numerical parameters, row IDs, deadline, trace ID
- Responses carry full solve + S2 verification evidence, or fail closed
- Worker death → declared `FallbackPolicy` (default `public_clarabel`); never release unverified actions
- Bounded worker restart; multiple solves reuse one process

One-command smoke:

```powershell
pwsh scripts/start_moreau_sidecar.ps1 -SmokePing
```

### Readiness caveats

The sidecar is a **qualification surface**, not a production claim. Until
qualification notes record pass/fail for your environment:

- Do not call the sidecar production-ready.
- Do not claim native Moreau-on-Windows support.
- If WSL or Moreau is missing, tests must skip with an explicit reason or
  fail closed — never fake a green Moreau qualification.

## Related

- [DEVENV.md](DEVENV.md)
- [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)
- Ledger: CS-SOLVER-111
