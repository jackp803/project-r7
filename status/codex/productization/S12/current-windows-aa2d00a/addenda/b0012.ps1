$EvidenceRoot=Split-Path -Parent $PSScriptRoot
$ErrorActionPreference='Stop'
$Candidate='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
$Checkpoint=Get-Content -LiteralPath (Join-Path $EvidenceRoot 'qualify-aa2d00a-first/checkpoint.json') -Raw | ConvertFrom-Json -DateKind String
$Observer=Get-Content -LiteralPath (Join-Path $EvidenceRoot 'owning-memory-aa2d00a-first/checkpoint.json') -Raw | ConvertFrom-Json -DateKind String
if ($Checkpoint.revision -ne $Candidate -or $Checkpoint.passed -ne $true -or $Observer.owning_passed -ne $true -or $Observer.tree_reaped -ne $true) {
    throw 'Actual completed owning/observer subject required'
}
$WindowStart=[DateTimeOffset]::Parse($Checkpoint.started_at).UtcDateTime
$WindowEnd=[DateTimeOffset]::Parse($Checkpoint.finished_at).UtcDateTime
if ($WindowEnd -lt $WindowStart) { throw 'Actual ordered owning window required' }
$Destination=Join-Path $PSScriptRoot 'retry-observation.json'
if (Test-Path -LiteralPath $Destination) { throw 'Preserve existing power observation' }
$Record=[ordered]@{
    revision=$Candidate
    source='WindowsSystem/Kernel-Power+Power-Troubleshooter'
    scope='SANITIZED_EVENT_IDS_AND_POWER_TIMES_ONLY;NO_HOST_SETTING_CHANGE'
    qualification_credit='NONE;OBSERVATIONAL_SUPPORT_ONLY'
    owning_start_utc=$WindowStart.ToString('o')
    owning_end_utc=$WindowEnd.ToString('o')
    query_started_at_utc=[DateTime]::UtcNow.ToString('o')
    query_status='PENDING'
    events=@()
    limitations=@('No absence of unmatched events, hard power interruptions or complete power continuity is inferred.','Actual awake-request lifetime and process sampling are separate evidence.')
}
try {
    $PowerStartText=$WindowStart.ToString('o')
    $PowerEndText=$WindowEnd.ToString('o')
    $PowerXPath="*[System[TimeCreated[@SystemTime>='$PowerStartText' and @SystemTime<='$PowerEndText'] and ((Provider[@Name='Microsoft-Windows-Kernel-Power'] and (EventID=42 or EventID=107 or EventID=506 or EventID=507)) or (Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1))]]"
    $Record['query_time_semantics']='UTC_XML_SYSTEMTIME_EXACT_INTERVAL'
    $PowerRows=@(Get-WinEvent -LogName 'System' -FilterXPath $PowerXPath -MaxEvents 201 -ErrorAction Stop)
    if ($PowerRows.Count -gt 200) { throw 'Bounded power observation limit exceeded' }
    foreach ($PowerRow in $PowerRows) {
        $Allowed=($PowerRow.ProviderName -eq 'Microsoft-Windows-Kernel-Power' -and $PowerRow.Id -in @(42,107,506,507)) -or ($PowerRow.ProviderName -eq 'Microsoft-Windows-Power-Troubleshooter' -and $PowerRow.Id -eq 1)
        if (-not $Allowed) { continue }
        [xml]$PowerXml=$PowerRow.ToXml()
        $EventUtc=[DateTimeOffset]::Parse($PowerXml.Event.System.TimeCreated.SystemTime).UtcDateTime
        if ($EventUtc -lt $WindowStart -or $EventUtc -gt $WindowEnd) { throw 'Returned event outside exact owning UTC window' }
        $Safe=[ordered]@{ provider=$PowerRow.ProviderName; event_id=$PowerRow.Id; recorded_utc=$EventUtc.ToString('o') }
        if ($PowerRow.ProviderName -eq 'Microsoft-Windows-Power-Troubleshooter') {
            [xml]$PowerXml=$PowerRow.ToXml()
            foreach ($Datum in $PowerXml.Event.EventData.Data) {
                if ($Datum.Name -in @('SleepTime','WakeTime')) {
                    $Safe[$Datum.Name]=[DateTimeOffset]::Parse($Datum.InnerText).ToUniversalTime().ToString('o')
                }
            }
        }
        $Record.events+=,$Safe
    }
    $Record.query_status='COMPLETE'
} catch {
    if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') {
        $Record.query_status='COMPLETE_NO_MATCHING_EVENTS'
    } else {
        $Record.query_status='UNAVAILABLE'
        $Record['error_type']=$_.Exception.GetType().Name
    }
}
$Record['query_finished_at_utc']=[DateTime]::UtcNow.ToString('o')
$Record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Destination -Encoding utf8NoBOM -NoNewline
Write-Output ([pscustomobject]$Record | Select-Object revision,query_status,query_started_at_utc,query_finished_at_utc | ConvertTo-Json -Compress)
