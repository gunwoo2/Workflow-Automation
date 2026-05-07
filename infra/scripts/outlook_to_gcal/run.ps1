# Outlook → Google Calendar 한 사이클 실행 (extract + register).
# 회사 PC에서 실행. 첫 실행은 register 단계에서 OAuth 브라우저 열림.
#
# 사용:
#   .\run.ps1                           # 향후 14일, events만
#   .\run.ps1 -DaysAhead 30              # 향후 30일
#   .\run.ps1 -IncludeTasks              # tasks 추출까지 (등록은 events만)
#   .\run.ps1 -DryRun                    # Google API 호출 없이 시뮬레이션
#   .\run.ps1 -CalendarId user@gmail.com # primary 외 캘린더 지정

param(
    [int]$DaysAhead = 14,
    [switch]$IncludeTasks,
    [switch]$IncludePastDay,
    [switch]$DryRun,
    [string]$CalendarId = "primary"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jsonPath  = Join-Path $scriptDir "events.json"

Write-Host "=== 1. Extract from Outlook ===" -ForegroundColor Cyan
$extractArgs = @("-DaysAhead", $DaysAhead, "-OutFile", $jsonPath)
if ($IncludeTasks)   { $extractArgs += "-IncludeTasks" }
if ($IncludePastDay) { $extractArgs += "-IncludePastDay" }
& (Join-Path $scriptDir "extract_events.ps1") @extractArgs

Write-Host ""
Write-Host "=== 2. Register to Google Calendar ===" -ForegroundColor Cyan
$env:PYTHONIOENCODING = "utf-8"
$pyArgs = @((Join-Path $scriptDir "register_to_gcal.py"), $jsonPath, "--calendar-id", $CalendarId)
if ($DryRun) { $pyArgs += "--dry-run" }
python @pyArgs
