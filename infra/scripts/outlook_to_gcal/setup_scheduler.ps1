# Register a Windows scheduled task that runs run.ps1 every N minutes.
# No admin rights required - the task runs under the current user account
# (Outlook COM objects work in user context).
#
# Usage:
#   .\setup_scheduler.ps1                    # default: every 30 min, 7 days ahead
#   .\setup_scheduler.ps1 -IntervalMinutes 15 -DaysAhead 14
#   .\setup_scheduler.ps1 -Unregister        # remove the task
#
# Inspect the registered task:
#   Get-ScheduledTask -TaskName 'LifeOS-OutlookToGCal'
#   Get-ScheduledTaskInfo -TaskName 'LifeOS-OutlookToGCal'   # last/next run

param(
    [int]$IntervalMinutes = 30,
    [int]$DaysAhead       = 7,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$taskName  = "LifeOS-OutlookToGCal"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runPath   = Join-Path $scriptDir "run.ps1"

# --- Unregister path ---
if ($Unregister) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "[ok] Unregistered scheduled task: $taskName"
    } else {
        Write-Host "[skip] No scheduled task named '$taskName' found"
    }
    return
}

# --- Validate ---
if (-not (Test-Path $runPath)) {
    Write-Host "[error] run.ps1 not found at: $runPath" -ForegroundColor Red
    exit 1
}

# --- Build action: powershell.exe -File run.ps1 -DaysAhead N (silent window) ---
$pwshArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runPath`" -DaysAhead $DaysAhead"
$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $pwshArgs

# --- Build trigger: start at next minute boundary, repeat every N min for ~10y ---
$startAt  = (Get-Date).AddMinutes(1)
$interval = New-TimeSpan -Minutes $IntervalMinutes
$duration = New-TimeSpan -Days (365 * 10)
$trigger  = New-ScheduledTaskTrigger -Once -At $startAt `
    -RepetitionInterval $interval -RepetitionDuration $duration

# --- Settings: start when machine wakes, OK on battery, kill if >5 min ---
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

# --- Replace existing task if present, then register ---
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "[info] Replacing existing task: $taskName"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName    $taskName `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -Description "Life OS - sync Outlook events + tasks to Google Calendar every $IntervalMinutes min." `
    -RunLevel    Limited | Out-Null

Write-Host ""
Write-Host "[ok] Registered scheduled task: $taskName" -ForegroundColor Green
Write-Host "  Script:    $runPath"
Write-Host "  Interval:  every $IntervalMinutes minute(s)"
Write-Host "  Range:     -DaysAhead $DaysAhead"
Write-Host "  First run: $startAt"
Write-Host ""
Write-Host "Inspect:   Get-ScheduledTaskInfo -TaskName '$taskName'"
Write-Host "Disable:   .\setup_scheduler.ps1 -Unregister"
