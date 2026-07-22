# Idempotent ConicShield bootstrap for Windows PowerShell.
# Native Windows: public profile only. Vendor Moreau requires WSL2.
# Never prints credentials.

[CmdletBinding()]
param(
    [ValidateSet("public", "moreau-cpu", "moreau-cuda")]
    [string]$Profile = $(if ($env:CONICSHIELD_BOOTSTRAP_PROFILE) { $env:CONICSHIELD_BOOTSTRAP_PROFILE } else { "public" })
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Redacted {
    param([string]$Message)
    $out = $Message
    foreach ($key in @("MOREAU_LICENSE_KEY", "MOREAU_EXTRA_INDEX_URL", "MOREAU_PIP_EXTRA_INDEX_URL", "GEMFURY_TOKEN")) {
        $val = [Environment]::GetEnvironmentVariable($key)
        if ($val -and $val.Length -ge 4) {
            $out = $out.Replace($val, "<${key}_REDACTED>")
        }
    }
    $out = [Regex]::Replace($out, '(https?://)[^/@\s]+@', '$1<REDACTED>@')
    Write-Host $out
}

function Assert-PythonVersion {
    $ver = & python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
    if ($ver -notin @("3.11", "3.12")) {
        throw "Unsupported Python $ver. Governed builds require 3.11 or 3.12. See docs/DEVENV.md."
    }
}

Assert-PythonVersion

if ($Profile -eq "public") {
    & python -m pip install --upgrade pip
    & python -m pip install -e ".[dev,solver-public]" -c packaging/constraints/solver-public.txt
    Write-Host "Public solver profile installed (no CUDA, no vendor Moreau)."
    & python -m conicshield.cli solver-doctor --json | Out-String | ForEach-Object { Write-Redacted $_ }
    Write-Host "Public bootstrap succeeded (idempotent)."
    exit 0
}

Write-Redacted "Profile '$Profile' requires vendor Moreau on Linux/WSL2."
Write-Host "Native Windows cannot install solver-moreau-cpu/cuda wheels."
Write-Host "From WSL2 Ubuntu run:"
Write-Host "  export CONICSHIELD_BOOTSTRAP_PROFILE=$Profile"
Write-Host "  # set MOREAU_EXTRA_INDEX_URL and MOREAU_LICENSE_KEY in the environment (not printed here)"
Write-Host "  bash scripts/bootstrap_moreau.sh"
exit 2
