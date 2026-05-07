# Outlook → Google Calendar 한 사이클 실행 (extract + register).
# default: Apps Script Web App 패턴 (OAuth/Cloud Console 우회).
# -UseOAuth 플래그를 주면 Python + Cloud Console OAuth 패턴 사용.
#
# 사용:
#   .\run.ps1                           # 향후 14일, Apps Script로 등록
#   .\run.ps1 -DaysAhead 30              # 향후 30일
#   .\run.ps1 -IncludeTasks              # tasks 추출까지 (등록은 events만)
#   .\run.ps1 -DryRun                    # 실제 등록 없이 시뮬레이션
#   .\run.ps1 -UseOAuth                  # Apps Script 대신 Python OAuth 패턴

param(
    [int]$DaysAhead = 14,
    [switch]$IncludeTasks,
    [switch]$IncludePastDay,
    [switch]$DryRun,
    [switch]$UseOAuth,
    [string]$CalendarId = "primary"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jsonPath  = Join-Path $scriptDir "events.json"

Write-Host "=== 1. Extract from Outlook ===" -ForegroundColor Cyan
$extractScript = Join-Path $scriptDir "extract_events.ps1"
# Hashtable splat for named-parameter binding (array splat treats hyphen-prefixed
# strings as positional values on some PowerShell builds → 'DaysAhead' cast error).
$extractParams = @{
    DaysAhead = $DaysAhead
    OutFile   = $jsonPath
}
if ($IncludeTasks)   { $extractParams.IncludeTasks   = $true }
if ($IncludePastDay) { $extractParams.IncludePastDay = $true }
& $extractScript @extractParams

Write-Host ""
Write-Host "=== 2. Register to Google Calendar ===" -ForegroundColor Cyan

if ($UseOAuth) {
    Write-Host "  (mode: Python OAuth Cloud Console)" -ForegroundColor DarkGray
    $env:PYTHONIOENCODING = "utf-8"
    # Python is a native exe — array splat / positional flags are fine.
    $pyArgs = @((Join-Path $scriptDir "register_to_gcal.py"), $jsonPath, "--calendar-id", $CalendarId)
    if ($DryRun) { $pyArgs += "--dry-run" }
    python @pyArgs
} else {
    Write-Host "  (mode: Apps Script Web App)" -ForegroundColor DarkGray
    $registerScript = Join-Path $scriptDir "register_via_appscript.ps1"
    $registerParams = @{ JsonPath = $jsonPath }
    if ($DryRun) { $registerParams.DryRun = $true }
    & $registerScript @registerParams
}
