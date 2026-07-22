# One-command Moreau sidecar starter for native Windows.
# Starts a persistent WSL2 worker (stdio NDJSON). Does NOT install Moreau on Windows.
# Qualification surface — see docs/WINDOWS_OPERATING_MODES.md.

[CmdletBinding()]
param(
    [string]$Distro = $env:CONICSHIELD_WSL_DISTRO,
    [string]$Python = $(if ($env:CONICSHIELD_WSL_PYTHON) { $env:CONICSHIELD_WSL_PYTHON } else { "python3" }),
    [switch]$RequireMoreau,
    [switch]$SmokePing
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function ConvertTo-WslPath([string]$WinPath) {
    $full = (Resolve-Path $WinPath).Path
    if ($full -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = $Matches[2] -replace '\\', '/'
        return "/mnt/$drive/$rest"
    }
    throw "Cannot translate path to WSL: $WinPath"
}

$wsl = Join-Path $env:SystemRoot "System32\wsl.exe"
if (-not (Test-Path $wsl)) {
    Write-Error "wsl.exe not found. Windows Moreau sidecar requires WSL2. Public mode does not need this script — use: pwsh scripts/bootstrap_moreau.ps1 -Profile public"
    exit 2
}

$linuxRoot = ConvertTo-WslPath $Root
$requireFlag = ""
if ($RequireMoreau) { $requireFlag = " --require-moreau" }

$distroArgs = @()
if ($Distro) { $distroArgs = @("-d", $Distro) }

Write-Host "Starting persistent Moreau sidecar worker in WSL (stdio protocol v1)."
Write-Host "Repo (WSL): $linuxRoot"
Write-Host "This does not claim native Moreau-on-Windows support."

$inner = "cd '$linuxRoot' && exec $Python -m conicshield.workers.moreau_worker$requireFlag"

if ($SmokePing) {
    # Handshake smoke: send hello/ping/shutdown via a short Python client.
    $env:CONICSHIELD_REPO_ROOT = $Root
    if ($Distro) { $env:CONICSHIELD_WSL_DISTRO = $Distro }
    $env:CONICSHIELD_WSL_PYTHON = $Python
    if ($RequireMoreau) { $env:CONICSHIELD_SIDECAR_REQUIRE_MOREAU = "1" }
    & python -c @"
from conicshield.platform.windows_sidecar_client import start_sidecar_from_env
c = start_sidecar_from_env()
print({'worker_id': c._worker_id, 'running': c.is_running, 'overhead': c.overhead_report()})
c.close()
print('sidecar smoke ok')
"@
    exit $LASTEXITCODE
}

# Foreground persistent worker (caller may also use WindowsSidecarClient which spawns its own).
& $wsl @distroArgs -e bash -lc $inner
