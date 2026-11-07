# Read-only diagnosis for Switch Console 0.40.1 on Windows.
# This script never restarts services, deletes files, opens ports, or reads secrets.
# Run it in a normal PowerShell session; administrator privileges are not required.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'
Write-Host 'Switch Console - local read-only diagnostics' -ForegroundColor Cyan
Write-Host ('UTC: {0:u}' -f (Get-Date).ToUniversalTime())
Write-Host ('Windows: {0}' -f [Environment]::OSVersion.VersionString)

# The bundled Switch Console process and Codex provider should be detectable.
$processNames = @('Switch Console','switch-console','codex','docker','com.docker.backend','mattermost','node','python')
foreach ($name in $processNames) {
    $processes = @(Get-Process -Name $name -ErrorAction SilentlyContinue)
    Write-Host ('Process {0}: {1}' -f $name, $processes.Count)
}

# Never read the contents of credential files or print absolute paths with usernames.
$agentController = Join-Path $env:APPDATA 'switchdash\agent-controller'
$watcherFiles = @()
if (Test-Path -LiteralPath $agentController) {
    $watcherFiles = @(Get-ChildItem -LiteralPath $agentController -Recurse -Filter 'health.json' -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match '[\\/]watchers[\\/]' })
}
Write-Host ('Switch agent watcher health files: {0}' -f $watcherFiles.Count)
if ($watcherFiles.Count -gt 0) {
    Write-Host 'If logs contain kill EPERM, stale watcher health.json files are a known issue.'
    Write-Host 'Do NOT rename files while Switch Console is running.'
}

# Socket check: no changes to firewall or network adapters.
try {
    $interesting = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {
        $_.LocalPort -in @(8000, 50007, 62226, 8765)
    } | Select-Object -Property LocalAddress,LocalPort,State)
    if ($interesting.Count -gt 0) {
        Write-Host 'Selected listening endpoints:'
        $interesting | Format-Table -AutoSize
    } else {
        Write-Host 'No listeners on selected optional reference ports (not a failure by itself).'
    }
} catch {
    Write-Host 'TCP listener information unavailable; continue with UI checks.'
}

if (Get-Command codex -ErrorAction SilentlyContinue) {
    try {
        # Auth status, not tokens or login secrets.
        Write-Host 'Codex CLI authentication status:'
        & codex login status 2>&1 | Select-Object -First 5
    } catch { Write-Host 'Codex authentication command could not finish.' }
} else {
    Write-Host 'Codex not available on this PowerShell PATH; Switch may use a separate installation path.'
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    try {
        Write-Host 'Docker container names and running state:'
        & docker ps --format '{{.Names}} :: {{.Status}}' 2>&1 | Select-Object -First 20
    } catch { Write-Host 'Docker is not available to this shell.' }
}

Write-Host ''
Write-Host 'Manual checks in Switch (no changes):' -ForegroundColor Yellow
Write-Host '  1) Try a private chat with switch-buddy-admin, not just a room mention.'
Write-Host '  2) Inspect Console -> Admin -> Status and local logs for: kill EPERM, Bridge ... crashed.'
Write-Host '  3) If kill EPERM is present, see the documented guarded recovery in SWITCH_DIAGNOSIS.md.'
Write-Host '  4) If Bridge ... crashed is present, see the Mattermost bridge workaround.'
Write-Host '  5) Do not delete agents, rooms, connectors, auth files, or Docker volumes.'
