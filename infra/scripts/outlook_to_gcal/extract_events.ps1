# Outlook 캘린더 + (옵션) Tasks 폴더에서 향후 N일치 데이터를 JSON으로 추출.
# Outlook COM 객체만 사용 — 외부 API 호출 0, OAuth 0, 회사 정책 영향 최소.
#
# 사용:
#   .\extract_events.ps1                       # 향후 14일 events
#   .\extract_events.ps1 -DaysAhead 30          # 향후 30일
#   .\extract_events.ps1 -IncludeTasks          # tasks도 함께 추출
#   .\extract_events.ps1 -OutFile out.json      # 출력 경로 지정

param(
    [int]$DaysAhead = 14,
    [string]$OutFile,
    [switch]$IncludeTasks,
    [switch]$IncludePastDay  # 오늘 시작 이전 회의도 포함 (오늘 0시부터)
)

$ErrorActionPreference = "Stop"

# 한글·UTF-8 출력
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

# 출력 경로 default
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutFile) { $OutFile = Join-Path $scriptDir "events.json" }

Write-Host "Connecting to Outlook (COM)..." -ForegroundColor Cyan
$outlook = New-Object -ComObject Outlook.Application
$ns = $outlook.GetNamespace("MAPI")

# --- Calendar (events) ---
$calendar = $ns.GetDefaultFolder(9)   # olFolderCalendar
$items = $calendar.Items
$items.IncludeRecurrences = $true
$items.Sort("[Start]")

$rangeStart = if ($IncludePastDay) { (Get-Date).Date } else { Get-Date }
$rangeEnd   = $rangeStart.AddDays($DaysAhead)
$ci = [System.Globalization.CultureInfo]::InvariantCulture
$filter = "[Start] >= '$($rangeStart.ToString("g", $ci))' AND [Start] < '$($rangeEnd.ToString("g", $ci))'"
$filtered = $items.Restrict($filter)

# Truncate helper (works on $null and short strings)
function Take([string]$s, [int]$n) {
    if (-not $s) { return "" }
    if ($s.Length -le $n) { return $s }
    return $s.Substring(0, $n)
}

$events = @()
foreach ($item in $filtered) {
    $events += [ordered]@{
        outlook_entry_id   = $item.EntryID
        subject            = $item.Subject
        start              = $item.Start.ToString("yyyy-MM-ddTHH:mm:ss")
        end                = $item.End.ToString("yyyy-MM-ddTHH:mm:ss")
        location           = $item.Location
        body               = Take $item.Body 2000
        organizer          = $item.Organizer
        required_attendees = $item.RequiredAttendees
        optional_attendees = $item.OptionalAttendees
        is_all_day         = [bool]$item.AllDayEvent
        is_recurring       = [bool]$item.IsRecurring
        response_status    = [int]$item.ResponseStatus
        sensitivity        = [int]$item.Sensitivity   # 0=Normal,1=Personal,2=Private,3=Confidential
        importance         = [int]$item.Importance    # 0=Low,1=Normal,2=High
        timezone           = "Asia/Seoul"
    }
}

# --- Tasks (optional) ---
$tasks = @()
if ($IncludeTasks) {
    $tasksFolder = $ns.GetDefaultFolder(13)   # olFolderTasks
    foreach ($t in $tasksFolder.Items) {
        if ($t.Complete) { continue }
        $due = $null
        if ($t.DueDate -and $t.DueDate.Year -gt 2000) {
            $due = $t.DueDate.ToString("yyyy-MM-dd")
        }
        $tasks += [ordered]@{
            outlook_entry_id = $t.EntryID
            subject          = $t.Subject
            due_date         = $due
            importance       = [int]$t.Importance
            percent_complete = [int]$t.PercentComplete
            body             = Take $t.Body 2000
        }
    }
}

# --- Payload ---
$payload = [ordered]@{
    extracted_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    range        = [ordered]@{
        days  = $DaysAhead
        start = $rangeStart.ToString("yyyy-MM-ddTHH:mm:ss")
        end   = $rangeEnd.ToString("yyyy-MM-ddTHH:mm:ss")
    }
    events_count = $events.Count
    tasks_count  = $tasks.Count
    events       = $events
    tasks        = $tasks
}

$json = $payload | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutFile, $json, (New-Object System.Text.UTF8Encoding $false))

Write-Host "Extracted: $($events.Count) events, $($tasks.Count) tasks" -ForegroundColor Green
Write-Host "Saved to:  $OutFile"

# COM 정리
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($filtered) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($items)    | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($calendar) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($ns)       | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($outlook)  | Out-Null
