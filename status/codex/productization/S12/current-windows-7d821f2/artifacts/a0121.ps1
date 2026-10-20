param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$CandidateRevision,[ValidatePattern('^(first|retry[0-9]{2})$')][string]$QualificationAttempt='first')
$ErrorActionPreference='Stop'
$CheckpointPython='<USER_HOME>\AppData\Local\Python\pythoncore-3.12-64\python.exe'
$Prior=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('qualify-'+$CandidateRevision.Substring(0,7)+'-'+$QualificationAttempt+'/checkpoint.json')) -Raw | ConvertFrom-Json
if ($Prior.passed -ne $true -or $Prior.revision -ne $CandidateRevision) { throw 'Actual complete owning prerequisite required' }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_portable_checkpoint.py') $CandidateRevision
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'run_current_checkpoint.py') headless $CandidateRevision
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_unattended_checkpoint.py') $CandidateRevision $QualificationAttempt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_ordinary_idle_coordinator.py') $CandidateRevision $QualificationAttempt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'verify_qualified_backup_checkpoint.py') $CandidateRevision $QualificationAttempt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'index_current_qualification.py') $CandidateRevision $QualificationAttempt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'bind_current_acceptance_records.py') $CandidateRevision $QualificationAttempt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $CheckpointPython -X utf8 (Join-Path $PSScriptRoot 'write_current_launch_guide.py') $CandidateRevision $QualificationAttempt
exit $LASTEXITCODE
