param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot 'config.json'),
    [switch]$Once
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line = "[$stamp][$Level] $Message"
    Write-Host $line
    if ($script:LogPath) {
        Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
    }
}

function Get-OptionalProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Default = $null
    )
    if ($null -eq $Object) { return $Default }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) { return $Default }
    return $property.Value
}

function Read-Config {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Config not found: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Load-State {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return [ordered]@{ dispatched = @(); pm_notified = @() }
    }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    return [ordered]@{
        dispatched = @(Get-OptionalProperty -Object $raw -Name 'dispatched' -Default @())
        pm_notified = @(Get-OptionalProperty -Object $raw -Name 'pm_notified' -Default @())
    }
}

function Save-State {
    param([System.Collections.IDictionary]$State, [string]$Path)
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Invoke-Git {
    param(
        [string]$RepoPath,
        [string[]]$Arguments,
        [switch]$AllowFailure
    )
    $output = @(& git -C $RepoPath @Arguments 2>&1)
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git -C `"$RepoPath`" $($Arguments -join ' ') failed ($code): $($output -join [Environment]::NewLine)"
    }
    return [pscustomobject]@{
        ExitCode = $code
        Output = $output
    }
}

function Get-RemoteFileText {
    param(
        [string]$RepoPath,
        [string]$Remote,
        [string]$Branch,
        [string]$Path
    )
    $spec = "${Remote}/${Branch}:${Path}"
    $result = Invoke-Git -RepoPath $RepoPath -Arguments @('show', $spec) -AllowFailure
    if ($result.ExitCode -ne 0) { return $null }
    return ($result.Output -join "`n")
}

function Get-MarkdownField {
    param([string]$Text, [string]$Field)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $escaped = [regex]::Escape($Field)
    $pattern = "(?mi)^\s*[-*]?\s*(?:\*\*)?$escaped(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) { return $null }
    return $match.Groups[1].Value.Trim().Trim('`').Trim()
}

function Expand-Template {
    param([string]$Template, [System.Collections.IDictionary]$Values)
    $result = $Template
    foreach ($key in $Values.Keys) {
        $result = $result.Replace("{$key}", [string]$Values[$key])
    }
    return $result
}

function Send-ChatWakeup {
    param(
        [string]$Url,
        [string]$Message,
        [string]$Mode,
        [bool]$AllowUnsafeUiAutomation,
        [int]$StartupDelaySeconds
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        throw 'Chat URL is empty.'
    }
    if ($Url -notmatch '^https://chatgpt\.com/') {
        throw "Refusing non-ChatGPT URL: $Url"
    }

    Set-Clipboard -Value $Message
    Start-Process $Url

    if ($Mode -eq 'prepare_only') {
        Write-Log 'Opened ChatGPT chat and copied wake prompt to clipboard. Manual paste/send is required.'
        return
    }

    if ($Mode -ne 'auto_send') {
        throw "Unsupported dispatch_mode: $Mode"
    }
    if (-not $AllowUnsafeUiAutomation) {
        throw 'dispatch_mode=auto_send requires allow_unsafe_ui_automation=true.'
    }

    Start-Sleep -Seconds ([Math]::Max(1, $StartupDelaySeconds))
    $shell = New-Object -ComObject WScript.Shell
    $shell.SendKeys('^v')
    Start-Sleep -Milliseconds 200
    $shell.SendKeys('{ENTER}')
    Write-Log 'Wake prompt auto-sent through foreground UI automation.'
}

$config = Read-Config -Path $ConfigPath
$resolvedConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path
$baseDir = Split-Path -Parent $resolvedConfigPath

$stateFileName = [string](Get-OptionalProperty -Object $config -Name 'state_file' -Default '.dispatcher-state.json')
$logFileName = [string](Get-OptionalProperty -Object $config -Name 'log_file' -Default 'dispatcher.log')
$statePath = if ([IO.Path]::IsPathRooted($stateFileName)) { $stateFileName } else { Join-Path $baseDir $stateFileName }
$script:LogPath = if ([IO.Path]::IsPathRooted($logFileName)) { $logFileName } else { Join-Path $baseDir $logFileName }
$state = Load-State -Path $statePath

$pollSeconds = [int](Get-OptionalProperty -Object $config -Name 'poll_seconds' -Default 30)
$dispatchMode = [string](Get-OptionalProperty -Object $config -Name 'dispatch_mode' -Default 'prepare_only')
$allowUnsafe = [bool](Get-OptionalProperty -Object $config -Name 'allow_unsafe_ui_automation' -Default $false)
$startupDelay = [int](Get-OptionalProperty -Object $config -Name 'startup_delay_seconds' -Default 4)
$projects = @(Get-OptionalProperty -Object $config -Name 'projects' -Default @())
if ($projects.Count -eq 0) {
    throw 'Config contains no projects.'
}

$defaultWakeTemplate = '讀取最新 {branch} 上的 {task_path}，只執行該 TASK，不得自行擴張 scope，也不得自行開始下一個任務。完成、HOLD acknowledgement 或遇到 blocker 後，更新 {status_path}，並依 TASK 要求 commit/push。'
$defaultPmTemplate = '{agent_id} 已回報 task {task_id} 為 {status_state}。請讀取最新 {branch} 上的 {status_path} 與 repository evidence，依 PM 權限決定下一步；不要假設 executable verification 已 PASS。'

Write-Log "Dispatcher started. mode=$dispatchMode config=$resolvedConfigPath"

while ($true) {
    foreach ($project in $projects) {
        try {
            $projectId = [string](Get-OptionalProperty -Object $project -Name 'id' -Default '')
            $repoPath = [string](Get-OptionalProperty -Object $project -Name 'repo_path' -Default '')
            $remote = [string](Get-OptionalProperty -Object $project -Name 'remote' -Default 'origin')
            $branch = [string](Get-OptionalProperty -Object $project -Name 'branch' -Default 'main')
            $coordinationRoot = [string](Get-OptionalProperty -Object $project -Name 'coordination_root' -Default 'coordination')
            $dispatchStates = @((Get-OptionalProperty -Object $project -Name 'dispatch_states' -Default @('ACTIVE')) | ForEach-Object { ([string]$_).ToUpperInvariant() })
            $terminalStates = @((Get-OptionalProperty -Object $project -Name 'terminal_status_states' -Default @('DONE','COMPLETED','PARTIAL','BLOCKED')) | ForEach-Object { ([string]$_).ToUpperInvariant() })
            $agents = @(Get-OptionalProperty -Object $project -Name 'agents' -Default @())

            if ([string]::IsNullOrWhiteSpace($projectId)) {
                Write-Log 'Skipping project with empty id.' 'WARN'
                continue
            }
            if (-not (Test-Path -LiteralPath $repoPath)) {
                Write-Log "[$projectId] repo_path missing: $repoPath" 'WARN'
                continue
            }
            if ($agents.Count -eq 0) {
                Write-Log "[$projectId] no agents configured." 'WARN'
                continue
            }

            $fetchResult = Invoke-Git -RepoPath $repoPath -Arguments @('fetch', $remote, $branch, '--quiet')
            if ($fetchResult.ExitCode -ne 0) {
                throw "git fetch failed for $projectId"
            }

            foreach ($agent in $agents) {
                $agentId = [string](Get-OptionalProperty -Object $agent -Name 'id' -Default '')
                $agentUrl = [string](Get-OptionalProperty -Object $agent -Name 'chat_url' -Default '')
                if ([string]::IsNullOrWhiteSpace($agentId)) { continue }

                $taskPath = "$coordinationRoot/$agentId/TASK.md"
                $statusPath = "$coordinationRoot/$agentId/STATUS.md"

                $taskText = Get-RemoteFileText -RepoPath $repoPath -Remote $remote -Branch $branch -Path $taskPath
                if (-not $taskText) { continue }

                $taskId = Get-MarkdownField -Text $taskText -Field 'task_id'
                $taskState = Get-MarkdownField -Text $taskText -Field 'state'
                if (-not $taskId -or -not $taskState) {
                    Write-Log "[$projectId/$agentId] TASK missing task_id/state." 'WARN'
                    continue
                }
                $taskState = $taskState.ToUpperInvariant()
                $dispatchKey = "$projectId|$agentId|$taskId"

                if (($dispatchStates -contains $taskState) -and ($state.dispatched -notcontains $dispatchKey)) {
                    $template = [string](Get-OptionalProperty -Object $project -Name 'wake_prompt_template' -Default $defaultWakeTemplate)
                    $message = Expand-Template -Template $template -Values ([ordered]@{
                        project_id = $projectId
                        agent_id = $agentId
                        task_id = $taskId
                        task_state = $taskState
                        branch = $branch
                        task_path = $taskPath
                        status_path = $statusPath
                    })
                    $extraPrompt = [string](Get-OptionalProperty -Object $project -Name 'extra_prompt' -Default '')
                    if (-not [string]::IsNullOrWhiteSpace($extraPrompt)) {
                        $message = "$message $extraPrompt"
                    }

                    Send-ChatWakeup -Url $agentUrl -Message $message -Mode $dispatchMode -AllowUnsafeUiAutomation $allowUnsafe -StartupDelaySeconds $startupDelay
                    $state.dispatched += $dispatchKey
                    Save-State -State $state -Path $statePath
                    Write-Log "[$projectId/$agentId] dispatched $taskId ($taskState)."
                }

                $statusText = Get-RemoteFileText -RepoPath $repoPath -Remote $remote -Branch $branch -Path $statusPath
                if (-not $statusText) { continue }
                $statusTaskId = Get-MarkdownField -Text $statusText -Field 'task_id'
                $statusState = Get-MarkdownField -Text $statusText -Field 'state'
                if (-not $statusTaskId -or -not $statusState) { continue }
                $statusState = $statusState.ToUpperInvariant()

                if (($statusTaskId -eq $taskId) -and ($terminalStates -contains $statusState)) {
                    $pmKey = "$projectId|$agentId|$taskId|$statusState"
                    if ($state.pm_notified -notcontains $pmKey) {
                        $pm = Get-OptionalProperty -Object $project -Name 'pm' -Default $null
                        $pmUrl = [string](Get-OptionalProperty -Object $pm -Name 'chat_url' -Default '')
                        if (-not [string]::IsNullOrWhiteSpace($pmUrl)) {
                            $pmTemplate = [string](Get-OptionalProperty -Object $project -Name 'pm_prompt_template' -Default $defaultPmTemplate)
                            $pmMessage = Expand-Template -Template $pmTemplate -Values ([ordered]@{
                                project_id = $projectId
                                agent_id = $agentId
                                task_id = $taskId
                                task_state = $taskState
                                status_state = $statusState
                                branch = $branch
                                task_path = $taskPath
                                status_path = $statusPath
                            })
                            Send-ChatWakeup -Url $pmUrl -Message $pmMessage -Mode $dispatchMode -AllowUnsafeUiAutomation $allowUnsafe -StartupDelaySeconds $startupDelay
                        }
                        $state.pm_notified += $pmKey
                        Save-State -State $state -Path $statePath
                        Write-Log "[$projectId/$agentId] PM notified for $taskId ($statusState)."
                    }
                }
            }
        }
        catch {
            Write-Log "Project loop failed: $($_.Exception.Message)" 'ERROR'
        }
    }

    if ($Once) { break }
    Start-Sleep -Seconds ([Math]::Max(5, $pollSeconds))
}
