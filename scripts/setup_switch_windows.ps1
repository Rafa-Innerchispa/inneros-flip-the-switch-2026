# Switch Console 0.40.1 Windows installer, no browser admin panel required.
# No service resets, no firewall changes, no Home Assistant writes.
[CmdletBinding()]
param([string]$SwitchUrl = 'http://127.0.0.1:62226')
$ErrorActionPreference = 'Stop'
if ($SwitchUrl -notmatch '^http://(127[.]0[.]0[.]1|localhost):[0-9]{2,5}$') {
    throw 'Only local Switch HTTP URLs are allowed.'
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $root
try {
    $health = Invoke-RestMethod -Uri ($SwitchUrl + '/health') -TimeoutSec 5
    if ($health.status -ne 'ok') { throw 'Switch /health did not return status=ok.' }
    Write-Host 'PASS: Switch Core is healthy.' -ForegroundColor Green
    $exe = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv .venv
        } else {
            throw 'Python 3.10+ not found. Install Python first.'
        }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    }
    & $exe -m pip install --disable-pip-version-check -e '.[switch]'
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Write-Host 'Registering agent using local admin session (no secrets printed)...' -ForegroundColor Cyan
    & $exe scripts\register_agent_local_admin.py --url $SwitchUrl
    if ($LASTEXITCODE -ne 0) { throw 'Agent registration failed; check the BLOCKED message above.' }
    Write-Host 'READY: InnerOS agent registered. The temporary registration key was revoked.' -ForegroundColor Green
    Write-Host 'NEXT: add inneros-incident-triage to #inneros-live-operations.' -ForegroundColor Cyan
    Write-Host 'NEXT: .\.venv\Scripts\python.exe scripts\discover_rooms.py'
    Write-Host 'Home Assistant remains unconfigured/read-only. No device was changed.'
} finally {
    Pop-Location
}
