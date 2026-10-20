$ErrorActionPreference='Stop'
$CheckpointPython='<USER_HOME>\AppData\Local\Python\pythoncore-3.12-64\python.exe'
$CandidateRevision='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
$Prior=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'qualify-aa2d00a-first/checkpoint.json') -Raw | ConvertFrom-Json
$Observer=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'owning-memory-aa2d00a-first/checkpoint.json') -Raw | ConvertFrom-Json
if ($Prior.passed -ne $true -or $Prior.revision -ne $CandidateRevision -or $Observer.owning_passed -ne $true -or $Observer.tree_reaped -ne $true -or $Observer.monitor_stopped -ne $true) {
    throw 'Actual completed qualification and stopped observer required'
}
foreach ($PriorName in @('portable','headless')) {
    $Completed=Get-Content -LiteralPath (Join-Path $PSScriptRoot ($PriorName+'-aa2d00a-first/checkpoint.json')) -Raw | ConvertFrom-Json
    if ($Completed.passed -ne $true -or $Completed.revision -ne $CandidateRevision) { throw 'Already completed exact ancillary prerequisite differs' }
}
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_unattended_checkpoint.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_ordinary_idle_coordinator.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_qualified_backup_checkpoint.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'index_current_qualification.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'bind_current_acceptance_records.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'write_current_launch_guide.py') $CandidateRevision first
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'materialize_current_delivery_aa2d00a.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $PSScriptRoot 'record_power_interval_aa2d00a.ps1')
# Tracked evidence is written only after all clean-source executors are done.
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'retain_current_checkpoint_aa2d00a.py') $CandidateRevision first first COMPLETE_OWNING_TREE_OBSERVER
exit $LASTEXITCODE
