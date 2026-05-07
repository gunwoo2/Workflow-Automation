# events.json을 Apps Script Web App에 POST해서 본인 Google Calendar에 등록.
# OAuth / Cloud Console 우회 패턴. shared secret으로 endpoint 보호.
#
# 사전 셋업: apps_script/README.md
# 환경 변수 (둘 다 필수):
#   GCAL_APPSCRIPT_URL    배포 URL  (https://script.google.com/macros/s/.../exec)
#   GCAL_APPSCRIPT_TOKEN  Code.gs의 SHARED_SECRET과 동일 값

param(
    [string]$JsonPath,
    [string]$WebAppUrl,
    [string]$Token,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# UTF-8 출력
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

# .env 파일에서 변수 로드 (없으면 시스템 env 사용)
function Load-DotEnv($path) {
    if (-not (Test-Path $path)) { return }
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $kv = $line.Split("=", 2)
        $k = $kv[0].Trim()
        $v = $kv[1].Trim().Trim('"').Trim("'")
        if (-not [Environment]::GetEnvironmentVariable($k)) {
            [Environment]::SetEnvironmentVariable($k, $v)
        }
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Resolve-Path (Join-Path $scriptDir "..\..\..") | Select-Object -ExpandProperty Path
Load-DotEnv (Join-Path $repoRoot ".env")

if (-not $WebAppUrl) { $WebAppUrl = $env:GCAL_APPSCRIPT_URL }
if (-not $Token)     { $Token     = $env:GCAL_APPSCRIPT_TOKEN }
if (-not $JsonPath)  { $JsonPath  = Join-Path $scriptDir "events.json" }

if (-not $WebAppUrl -or -not $Token) {
    Write-Host "[error] GCAL_APPSCRIPT_URL / GCAL_APPSCRIPT_TOKEN 미설정." -ForegroundColor Red
    Write-Host "        .env 또는 환경변수에 설정. apps_script/README.md §3 참조." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $JsonPath)) {
    Write-Host "[error] $JsonPath 없음. extract_events.ps1 먼저 실행." -ForegroundColor Red
    exit 1
}

# Read JSON (UTF-8)
$body = [System.IO.File]::ReadAllText($JsonPath, [System.Text.Encoding]::UTF8)

# Sanity preview
$payload = $body | ConvertFrom-Json
$evCount = if ($payload.events) { @($payload.events).Count } else { 0 }
Write-Host "Posting $evCount events to Apps Script Web App..." -ForegroundColor Cyan
Write-Host "  url:     $WebAppUrl"
Write-Host "  events:  $evCount"

if ($DryRun) {
    Write-Host "  (dry run — POST 안 함)" -ForegroundColor Yellow
    $payload.events | Select-Object -First 5 | ForEach-Object {
        Write-Host "    [dry] $($_.subject) $($_.start) → $($_.end)"
    }
    return
}

# Apps Script issues a 302 to script.googleusercontent.com; Invoke-RestMethod
# loses the POST body across the redirect on some PowerShell builds, so we
# use Invoke-WebRequest with explicit MaximumRedirection and parse manually.
try {
    $rawResp = Invoke-WebRequest -Method Post -Uri "$WebAppUrl`?token=$Token" `
        -Body $body -ContentType "application/json; charset=utf-8" `
        -MaximumRedirection 5
} catch {
    Write-Host "[error] HTTP 요청 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

try {
    $resp = $rawResp.Content | ConvertFrom-Json
} catch {
    Write-Host "[error] 응답이 JSON이 아님 (배포 액세스 권한이 'Anyone'인지 확인):" -ForegroundColor Red
    Write-Host $rawResp.Content.Substring(0, [Math]::Min(300, $rawResp.Content.Length))
    exit 1
}

if (-not $resp.ok) {
    Write-Host "[error] Apps Script: $($resp.error)" -ForegroundColor Red
    exit 1
}

$c = $resp.counters
Write-Host ""
Write-Host "Done: new=$($c.newCount) updated=$($c.updCount) skipped=$($c.skipCount) errors=$($c.errCount)" -ForegroundColor Green

if ($resp.errors -and @($resp.errors).Count -gt 0) {
    Write-Host "Errors:" -ForegroundColor Yellow
    $resp.errors | ForEach-Object { Write-Host "  $($_.subject): $($_.error)" }
}
