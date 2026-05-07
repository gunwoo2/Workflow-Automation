# POST events.json to the Apps Script Web App which upserts to Google Calendar.
# Bypasses Cloud Console / OAuth — only a shared secret + URL needed.
#
# Setup:    apps_script/README.md
# Required env vars (or pass as -WebAppUrl / -Token):
#   GCAL_APPSCRIPT_URL    deployed URL  (https://script.google.com/macros/s/.../exec)
#   GCAL_APPSCRIPT_TOKEN  same value as SHARED_SECRET in Code.gs

param(
    [string]$JsonPath,
    [string]$WebAppUrl,
    [string]$Token,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# UTF-8 console output (events / errors may contain Korean / non-ASCII).
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

# Minimal .env loader. Falls back to process env vars if the file is absent.
function Import-DotEnv($path) {
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
Import-DotEnv (Join-Path $repoRoot ".env")

if (-not $WebAppUrl) { $WebAppUrl = $env:GCAL_APPSCRIPT_URL }
if (-not $Token)     { $Token     = $env:GCAL_APPSCRIPT_TOKEN }
if (-not $JsonPath)  { $JsonPath  = Join-Path $scriptDir "events.json" }

if (-not $WebAppUrl -or -not $Token) {
    Write-Host "[error] GCAL_APPSCRIPT_URL / GCAL_APPSCRIPT_TOKEN missing." -ForegroundColor Red
    Write-Host "        Set them in .env or as env vars. See apps_script/README.md." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $JsonPath)) {
    Write-Host "[error] $JsonPath not found. Run extract_events.ps1 first." -ForegroundColor Red
    exit 1
}

# Read JSON as UTF-8 (preserves Korean characters in payload).
$body = [System.IO.File]::ReadAllText($JsonPath, [System.Text.Encoding]::UTF8)

$payload = $body | ConvertFrom-Json

# --- Merge Outlook tasks into the events array as [Task] all-day events ---
# Apps Script Code.gs only knows how to upsert calendar events; tasks with a
# due_date become single all-day events titled "[Task] <subject>" so they
# show up alongside meetings on the same calendar grid.
$taskList = if ($payload.tasks) { @($payload.tasks) } else { @() }
$taskEvents = @()
foreach ($t in $taskList) {
    if (-not $t.due_date) { continue }   # tasks without a due date can't be placed
    $taskEvents += [ordered]@{
        outlook_entry_id = "task:" + $t.outlook_entry_id
        subject          = "[Task] " + $t.subject
        start            = $t.due_date
        end              = $t.due_date
        location         = ""
        body             = "Outlook Task. importance=$($t.importance) percent_complete=$($t.percent_complete)`n`n$($t.body)"
        is_all_day       = $true
        timezone         = "Asia/Seoul"
    }
}

# Append converted tasks to the events array, then re-serialize.
$mergedEvents = @($payload.events) + @($taskEvents)
$mergedPayload = [ordered]@{
    extracted_at = $payload.extracted_at
    range        = $payload.range
    events_count = $mergedEvents.Count
    tasks_count  = 0
    events       = $mergedEvents
    tasks        = @()
}
$body = $mergedPayload | ConvertTo-Json -Depth 8

$evCount   = $mergedEvents.Count
$taskCount = $taskEvents.Count
Write-Host "Posting $evCount events to Apps Script Web App..." -ForegroundColor Cyan
Write-Host "  url:    $WebAppUrl"
Write-Host "  events: $evCount  (incl. $taskCount task -> all-day)"

if ($DryRun) {
    Write-Host "  (dry run - skipping POST)" -ForegroundColor Yellow
    $mergedEvents | Select-Object -First 8 | ForEach-Object {
        Write-Host ("    [dry] {0}  {1} -> {2}" -f $_.subject, $_.start, $_.end)
    }
    return
}

# Apps Script issues a 302 to script.googleusercontent.com. Invoke-RestMethod
# loses the POST body across that redirect on some PowerShell builds, so use
# Invoke-WebRequest with explicit MaximumRedirection and parse manually.
try {
    $rawResp = Invoke-WebRequest -Method Post -Uri "$WebAppUrl`?token=$Token" `
        -Body $body -ContentType "application/json; charset=utf-8" `
        -MaximumRedirection 5
} catch {
    Write-Host "[error] HTTP request failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

try {
    $resp = $rawResp.Content | ConvertFrom-Json
} catch {
    Write-Host "[error] Response is not JSON. Verify the deployment's 'Who has access' is set to 'Anyone'." -ForegroundColor Red
    Write-Host $rawResp.Content.Substring(0, [Math]::Min(300, $rawResp.Content.Length))
    exit 1
}

if (-not $resp.ok) {
    Write-Host "[error] Apps Script: $($resp.error)" -ForegroundColor Red
    exit 1
}

$c = $resp.counters
Write-Host ""
Write-Host ("Done: new={0} updated={1} skipped={2} errors={3}" -f $c.newCount, $c.updCount, $c.skipCount, $c.errCount) -ForegroundColor Green

if ($resp.errors -and @($resp.errors).Count -gt 0) {
    Write-Host "Errors:" -ForegroundColor Yellow
    $resp.errors | ForEach-Object { Write-Host ("  {0}: {1}" -f $_.subject, $_.error) }
}
