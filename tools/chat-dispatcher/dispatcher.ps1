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
        dispatched = @($raw.dispatched)
        pm_notified = @($raw.pm_notified)
    }
}

function Save-State {
    param([hashtable]$State, [string]$Path)
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
    $output = & git -C $RepoPath @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git -C `"$RepoPath`" $($Arguments -join ' ') failed ($code): $($output -join [Environment]::NewLine)"
    }
    return ,$output
}

function Get-RemoteFileText {
    param(
        [string]$RepoPath,
        [string]$Remote,
        [string]$Branch,
        [string]$Path
    )
    $spec = "${Remote}/${Branch}:${Path}"
    $output = Invoke-Git -RepoPath $RepoPath -Arguments @('show', $spec) -AllowFailure
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($output -join "`n")
}

function Get-MarkdownField {
    param([string]$Text, [string]$Field)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $escaped = [regex]::Escape($Field)
    $pattern = "(?mi)^\s*[-*]?\s*(?:\*\*)?$escaped(?:\*\*)?\s*[:：]\s*`?([^`\r\n]+?)`?\s*$"
    $m = [regex]::Match($Text, $pattern)
    if (-not $m.Success) { return $null }
    return $m.Groups[1].Value.Trim().Trim('`').Trim()
}

function Expand-Template {
    param([string]$Template, [hashtable]$Values)
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
        Write-Log "Opened ChatGPT chat and copied wake prompt to clipboard. Manual paste/send is required."
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
    Write-Log "Wake prompt auto-sent through foreground UI automation."
}

$config = Read-Config -Path $ConfigPath
$baseDir = Split-Path -Parent (Resolve-Path -LiteralPath $ConfigPath)
$stateFileName = if ($config.state_file) { [string]$config.state_file } else { '.dispatcher-state.json' }
$logFileName = if ($config.log_file) { [string]$config.log_file } else { 'dispatcher.log' }
$statePath = if ([IO.Path]::IsPathRooted($stateFileName)) { $stateFileName } else { Join-Path $baseDir $stateFileName }
$script:LogPath = if ([IO.Path]::IsPathRooted($logFileName)) { $logFileName } else { Join-Path $baseDir $logFileName }
$state = Load-State -Path $statePath

$pollSeconds = if ($config.poll_seconds) { [int]$config.poll_seconds } else { 30 }
$dispatchMode = if ($config.dispatch_mode) { [string]$config.dispatch_mode } else { 'prepare_only' }
$allowUnsafe = if ($null -ne $config.allow_unsafe_ui_automation) { [bool]$config.allow_unsafe_ui_automation } else { $false }
$startupDelay = if ($config.startup_delay_seconds) { [int]$config.startup_delay_seconds } else { 4 }

$defaultWakeTemplate = '讀取最新 {branch} 上的 {task_path}，只執行該 TASK，不得自行擴張 scope，也不得自行開始下一個任務。完成、HOLD acknowledgement 或遇到 blocker 後，更新 {status_path}，並依 TASK 要求 commit/push。'
$defaultPmTemplate = '{agent_id} 已回報 task {task_id} 為 {status_state}。請讀取最新 {branch} 上的 {status_path} 與 repository evidence，依 PM 權限決定下一步；不要假設 executable verification 已 PASS。'

Write-Log "Dispatcher started. mode=$dispatchMode config=$ConfigPath"

while ($true) {
    foreach ($project in @($config.projects)) {
        try {
            $projectId = [string]$project.id
            $repoPath = [string]$project.repo_path
            $remote = if ($project.remote) { [string]$project.remote } else { 'origin' }
            $branch = if ($project.branch) { [string]$project.branch } else { 'main' }
            $coordinationRoot = if ($project.coordination_root) { [string]$project.coordination_root } else { 'coordination' }
            $dispatchStates = if ($project.dispatch_states) { @($project.dispatch_states | ForEach-Object { ([string]$_).ToUpperInvariant() }) } else { @('ACTIVE') }
            $terminalStates = if ($project.terminal_status_states) { @($project.terminal_status_states | ForEach-Object { ([string]$_).ToUpperInvariant() }) } else { @('DONE','COMPLETED','PARTIAL','BLOCKED') }

            if (-not (Test-Path -LiteralPath $repoPath)) {
                Write-Log "[$projectId] repo_path missing: $repoPath" 'WARN'
                continue
            }

            Invoke-Git -RepoPath $repoPath -Arguments @('fetch', $remote, $branch, '--quiet') | Out-Null

            foreach ($agent in @($project.agents)) {
                $agentId = [string]$agent.id
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
                    $template = if ($project.wake_prompt_template) { [string]$project.wake_prompt_template } else { $defaultWakeTemplate }
                    $message = Expand-Template -Template $template -Values @{
                        project_id = $projectId
                        agent_id = $agentId
                        task_id = $taskId
                        task_state = $taskState
                        branch = $branch
                        task_path = $taskPath
                        status_path = $statusPath
                    }
                    if ($project.extra_prompt) {
                        $message = $message + ' ' + [string]$project.extra_prompt
                    }
                    Send-ChatWakeup -Url ([string]$agent.chat_url) -Message $message -Mode $dispatchMode -AllowUnsafeUiAutomation $allowUnsafe -StartupDelaySeconds $startupDelay
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
                        if ($project.pm -and $project.pm.chat_url) {
                            $pmTemplate = if ($project.pm_prompt_template) { [string]$project.pm_prompt_template } else { $defaultPmTemplate }
                            $pmMessage = Expand-Template -Template $pmTemplate -Values @{
                                project_id = $projectId
                                agent_id = $agentId
                                task_id = $taskId
                                task_state = $taskState
                                status_state = $statusState
                                branch = $branch
                                task_path = $taskPath
                                status_path = $statusPath
                            }
                            Send-ChatWakeup -Url ([string]$project.pm.chat_url) -Message $pmMessage -Mode $dispatchMode -AllowUnsafeUiAutomation $allowUnsafe -StartupDelaySeconds $startupDelay
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
