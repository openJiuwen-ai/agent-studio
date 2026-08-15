# Service/port helpers for Agent-Studio Windows setup.
# Caller must set $WORK_HOME, $TARGET_ENV_FILE, $BACKEND_DIR, $FRONTEND_DIR, and $RUNTIME_DIR before dot-sourcing (e.g. from setup.ps1 after utils.ps1).

# Single state file: lines like "runtime_port:8100", "backend_pid:1234" (keys: runtime_port, runtime_pid, backend_port, backend_pid, frontend_port, frontend_pid).
function Get-ServiceProcessStateFile {
    if (-not $WORK_HOME) {
        return $null
    }
    return (Join-Path $WORK_HOME "services.state")
}

function Get-ServiceProcessState {
    $path = Get-ServiceProcessStateFile
    $ht = @{}
    if ($path -and (Test-Path $path)) {
        try {
            foreach ($line in Get-Content $path -ErrorAction SilentlyContinue) {
                if ([string]::IsNullOrWhiteSpace($line)) {
                    continue
                }
                if ($line -match '^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(\S+)\s*$') {
                    $ht[$Matches[1]] = $Matches[2].Trim()
                }
            }
        } catch {
            # Ignore errors
        }
        return $ht
    }
    if (-not $WORK_HOME) {
        return $ht
    }
    $legacy = @(
        @{ File = 'runtime.pid'; Key = 'runtime_pid' }
        @{ File = 'runtime.port'; Key = 'runtime_port' }
        @{ File = 'backend.pid'; Key = 'backend_pid' }
        @{ File = 'backend.port'; Key = 'backend_port' }
        @{ File = 'frontend.pid'; Key = 'frontend_pid' }
        @{ File = 'frontend.port'; Key = 'frontend_port' }
    )
    foreach ($item in $legacy) {
        $fp = Join-Path $WORK_HOME $item.File
        if (-not (Test-Path $fp)) {
            continue
        }
        try {
            $Line = Get-Content $fp -ErrorAction SilentlyContinue | Where-Object { $_ -match "^\d+$" } | Select-Object -First 1
            if ($Line) {
                $ht[$item.Key] = $Line.Trim()
            }
        } catch {
            # Ignore errors
        }
    }
    return $ht
}

function Set-ServiceProcessState {
    param(
        [hashtable]$Values = @{},
        [string[]]$RemoveKeys = @()
    )
    if (-not $WORK_HOME) {
        return
    }
    $path = Get-ServiceProcessStateFile
    if (-not $path) {
        return
    }
    $merged = @{}
    $current = Get-ServiceProcessState
    foreach ($k in $current.Keys) {
        $merged[$k] = $current[$k]
    }
    foreach ($k in $RemoveKeys) {
        $null = $merged.Remove($k)
    }
    foreach ($k in $Values.Keys) {
        $val = $Values[$k]
        if ($null -eq $val -or (($val -is [string]) -and [string]::IsNullOrWhiteSpace($val))) {
            $null = $merged.Remove($k)
        } else {
            $merged[$k] = "$val".Trim()
        }
    }
    $order = @('runtime_port', 'runtime_pid', 'backend_port', 'backend_pid', 'frontend_port', 'frontend_pid')
    $lines = [System.Collections.Generic.List[string]]::new()
    $seen = @{}
    foreach ($key in $order) {
        if ($merged.ContainsKey($key)) {
            $lines.Add("${key}:$($merged[$key])")
            $seen[$key] = $true
        }
    }
    foreach ($key in ($merged.Keys | Sort-Object)) {
        if (-not $seen.ContainsKey($key)) {
            $lines.Add("${key}:$($merged[$key])")
        }
    }
    if ($lines.Count -eq 0) {
        if (Test-Path $path) {
            Remove-Item $path -Force -ErrorAction SilentlyContinue
        }
    } else {
        $parent = Split-Path $path -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Set-Content -Path $path -Value $lines -Encoding utf8 -Force
    }
    foreach ($name in @('runtime.pid', 'runtime.port', 'backend.pid', 'backend.port', 'frontend.pid', 'frontend.port')) {
        $leg = Join-Path $WORK_HOME $name
        if (Test-Path $leg) {
            Remove-Item $leg -Force -ErrorAction SilentlyContinue
        }
    }
}

# Written by Start-* services; falls back to .env then default when missing (e.g. old installs).
function Get-BackendServicePort {
    param([int]$DefaultPort = 8000)
    $st = Get-ServiceProcessState
    if ($st.ContainsKey('backend_port') -and $st['backend_port'] -match '^\d+$') {
        return [int]$st['backend_port']
    }
    if (Test-Path $TARGET_ENV_FILE) {
        try {
            $PortLine = Select-String -Path $TARGET_ENV_FILE -Pattern "^(BACKEND_PORT|SERVER_PORT|PORT)=" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($PortLine) {
                $PortValue = ($PortLine.Line -replace "^(BACKEND_PORT|SERVER_PORT|PORT)=", "").Trim() -replace '"', "" -replace "'", ""
                if (-not [string]::IsNullOrEmpty($PortValue) -and $PortValue -match "^\d+$") {
                    return [int]$PortValue
                }
            }
        } catch {
            # Ignore errors
        }
    }
    return $DefaultPort
}

function Get-FrontendServicePort {
    param([int]$DefaultPort = 3000)
    $st = Get-ServiceProcessState
    if ($st.ContainsKey('frontend_port') -and $st['frontend_port'] -match '^\d+$') {
        return [int]$st['frontend_port']
    }
    if (Test-Path $TARGET_ENV_FILE) {
        try {
            $FrontendPortLine = Select-String -Path $TARGET_ENV_FILE -Pattern "^FRONTEND_PORT=" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($FrontendPortLine) {
                $PortValue = ($FrontendPortLine.Line -replace "FRONTEND_PORT=", "").Trim() -replace '"', "" -replace "'", ""
                if (-not [string]::IsNullOrEmpty($PortValue) -and $PortValue -match "^\d+$") {
                    return [int]$PortValue
                }
            }
        } catch {
            # Ignore errors
        }
    }
    return $DefaultPort
}

function Get-LocalIP {
    try {
        # Try to get local IP address
        $LocalIP = $null
        $Interfaces = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue
        foreach ($Interface in $Interfaces) {
            if ($Interface.IPAddress -notlike "127.*" -and $Interface.IPAddress -notlike "169.254.*") {
                $LocalIP = $Interface.IPAddress
                break
            }
        }

        if ([string]::IsNullOrEmpty($LocalIP)) {
            $LocalIP = "localhost"
        }
    } catch {
        $LocalIP = "localhost"
    }

    return $LocalIP
}

function Stop-ProcessTree {
    param(
        [int]$ProcessId,
        [int]$MaxWait = 10
    )

    $Stopped = $false
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $Process) {
        return $false
    }

    try {
        # Get all child processes
        $ChildProcesses = @()
        $AllProcesses = Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $ProcessId }
        foreach ($ChildProc in $AllProcesses) {
            $ChildProcesses += $ChildProc.ProcessId
            # Recursively get grandchildren
            $GrandChildren = Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $ChildProc.ProcessId }
            foreach ($GrandChild in $GrandChildren) {
                $ChildProcesses += $GrandChild.ProcessId
            }
        }

        # Stop child processes first
        foreach ($ChildPid in $ChildProcesses) {
            try {
                $ChildProcess = Get-Process -Id $ChildPid -ErrorAction SilentlyContinue
                if ($ChildProcess) {
                    Stop-Process -Id $ChildPid -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Ignore errors for child processes
            }
        }

        # Wait a bit for child processes to exit
        Start-Sleep -Milliseconds 500

        # Stop the main process gracefully first
        Stop-Process -Id $ProcessId -ErrorAction Stop
        $WaitCount = 0
        while ($WaitCount -lt $MaxWait) {
            Start-Sleep -Seconds 1
            $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
            if (-not $Process) {
                $Stopped = $true
                break
            }
            $WaitCount++
        }

        # If still running, force stop
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($Process) {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
            $Stopped = $true
        }
    } catch {
        # If graceful stop failed, try force stop
        try {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
            $Stopped = $true
        } catch {
            # Process may have already exited
        }
    }

    return $Stopped
}

function Stop-ProcessesByPort {
    param(
        [int]$Port
    )

    $Stopped = $false
    try {
        $NetStat = netstat -ano | Select-String ":$Port\s" -ErrorAction SilentlyContinue
        if ($NetStat) {
            $Pids = @()
            foreach ($Line in $NetStat) {
                $PortPid = ($Line -split '\s+')[-1]
                if ($PortPid -match "^\d+$") {
                    $PidValue = [int]$PortPid
                    if ($Pids -notcontains $PidValue) {
                        $Pids += $PidValue
                    }
                }
            }

            foreach ($ProcessId in $Pids) {
                $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
                if ($Process) {
                    Write-Host "  Stopping process on port $Port (PID: $ProcessId)..." -ForegroundColor Yellow
                    $null = Stop-ProcessTree -ProcessId $ProcessId
                    $Stopped = $true
                }
            }
        }
    } catch {
        # Ignore errors
    }

    return $Stopped
}

function Show-Status {
    param(
        [switch]$NoExit  # When called from Start-Services/Restart/completion block do not exit; exit only when -Status is used alone
    )
    $ServiceStatePath = Get-ServiceProcessStateFile
    $State = Get-ServiceProcessState
    $RuntimeLog = Join-Path $WORK_HOME "runtime.log"
    $BackendLog = Join-Path $WORK_HOME "backend.log"
    $FrontendLog = Join-Path $WORK_HOME "frontend.log"

    $LocalIP = Get-LocalIP

    Write-Host "Frontend Service:" -ForegroundColor Yellow
    $FrontendPid = $null
    $FrontendPort = Get-FrontendServicePort -DefaultPort 3000

    $FrontendPidFromState = $null
    if ($State.ContainsKey('frontend_pid') -and $State['frontend_pid'] -match '^\d+$') {
        $FrontendPidFromState = [int]$State['frontend_pid']
    }
    if ($FrontendPidFromState) {
        $PidValue = $FrontendPidFromState
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $ProcessName = $Process.ProcessName
            $CommandLine = ""
            $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
            if ($WmiProcess) {
                $CommandLine = $WmiProcess.CommandLine
            }
            if ($ProcessName -eq "node" -or $CommandLine -like "*vite*" -or $CommandLine -like "*npm*dev*") {
                $FrontendPid = $PidValue
                Write-Host "  Status: Running" -ForegroundColor Green
                Write-Host "  PID: $FrontendPid"
            }
        }
    }

    if (-not $FrontendPid) {
        $NetStat = netstat -ano | Select-String ":$FrontendPort\s" -ErrorAction SilentlyContinue
        if ($NetStat) {
            $PortPid = ($NetStat -split '\s+')[-1]
            if ($PortPid -match "^\d+$") {
                $PidValue = [int]$PortPid
                $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
                if ($Process -and $Process.ProcessName -eq "node") {
                    $FrontendPid = $PidValue
                    Write-Host "  Status: Running (detected by port)" -ForegroundColor Green
                    Write-Host "  PID: $FrontendPid"
                    Write-Host "  Warning: PID file not found or expired" -ForegroundColor Yellow
                }
            }
        }
    }

    if ($FrontendPid) {
        Write-Host "  Local: http://localhost:${FrontendPort}" -ForegroundColor Blue
        Write-Host "  Network: http://${LocalIP}:${FrontendPort}" -ForegroundColor Blue
    }
    else {
        Write-Host "  Status: Not Running" -ForegroundColor Red
        if ($State.ContainsKey('frontend_pid')) {
            Write-Host "  Note: services.state has frontend_pid but process not found (frontend_pid: $($State['frontend_pid']))"
        } else {
            Write-Host "  Note: frontend_pid not recorded in services.state"
        }
    }

    Write-Host "  Log File: $FrontendLog" -ForegroundColor Green

    Write-Host ""

    Write-Host "Backend Service:" -ForegroundColor Yellow
    $BackendPid = $null
    $BackendPort = Get-BackendServicePort -DefaultPort 8000

    $BackendPidFromState = $null
    if ($State.ContainsKey('backend_pid') -and $State['backend_pid'] -match '^\d+$') {
        $BackendPidFromState = [int]$State['backend_pid']
    }
    if ($BackendPidFromState) {
        $PidValue = $BackendPidFromState
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $ProcessPath = $Process.Path
            $CommandLine = ""
            $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
            if ($WmiProcess) {
                $CommandLine = $WmiProcess.CommandLine
            }
            if ($ProcessPath -like "*python*" -or $CommandLine -like "*main.py*") {
                $BackendPid = $PidValue
                Write-Host "  Status: Running" -ForegroundColor Green
                Write-Host "  PID: $BackendPid"
            }
        }
    }

    if (-not $BackendPid) {
        $NetStat = netstat -ano | Select-String ":$BackendPort\s" -ErrorAction SilentlyContinue
        if ($NetStat) {
            $PortPid = ($NetStat -split '\s+')[-1]
            if ($PortPid -match "^\d+$") {
                $PidValue = [int]$PortPid
                $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
                if ($Process) {
                    $ProcessPath = $Process.Path
                    $CommandLine = ""
                    $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
                    if ($WmiProcess) {
                        $CommandLine = $WmiProcess.CommandLine
                    }
                    if ($ProcessPath -like "*python*" -or $CommandLine -like "*main.py*") {
                        $BackendPid = $PidValue
                        Write-Host "  Status: Running (detected by port)" -ForegroundColor Green
                        Write-Host "  PID: $BackendPid"
                        Write-Host "  Warning: PID file not found or expired" -ForegroundColor Yellow
                    }
                }
            }
        }
    }

    if ($BackendPid) {
        Write-Host "  Local: http://localhost:${BackendPort}" -ForegroundColor Green
        Write-Host "  Network: http://${LocalIP}:${BackendPort}" -ForegroundColor Green
        Write-Host "  API Docs: http://localhost:${BackendPort}/api/docs" -ForegroundColor Green
        Write-Host "  Health: http://localhost:${BackendPort}/api/health" -ForegroundColor Green
    }
    else {
        Write-Host "  Status: Not Running" -ForegroundColor Red
        if ($State.ContainsKey('backend_pid')) {
            Write-Host "  Note: services.state has backend_pid but process not found (backend_pid: $($State['backend_pid']))"
        } else {
            Write-Host "  Note: backend_pid not recorded in services.state"
        }
    }

    Write-Host "  Log File: $BackendLog" -ForegroundColor Green

    Write-Host ""

    Write-Host "Runtime Service:" -ForegroundColor Yellow
    $RuntimePid = $null
    $RuntimePort = $null
    if ($State.ContainsKey('runtime_port') -and $State['runtime_port'] -match '^\d+$') {
        $RuntimePort = [int]$State['runtime_port']
    }

    if ($State.ContainsKey('runtime_pid') -and $State['runtime_pid'] -match '^\d+$') {
        $PidValue = [int]$State['runtime_pid']
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $RuntimePid = $PidValue
        }
    }

    if (-not $RuntimePid -and $RuntimePort) {
        try {
            $ListenConn = Get-NetTCPConnection -LocalPort $RuntimePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($ListenConn -and $ListenConn.OwningProcess -gt 0) {
                $Process = Get-Process -Id $ListenConn.OwningProcess -ErrorAction SilentlyContinue
                if ($Process) {
                    $RuntimePid = [int]$ListenConn.OwningProcess
                }
            }
        } catch {
            # Ignore runtime port detection errors
        }
    }

    if ($RuntimePid) {
        Write-Host "  Status: Running" -ForegroundColor Green
        Write-Host "  PID: $RuntimePid"
        if ($RuntimePort) {
            Write-Host "  Local: http://localhost:${RuntimePort}" -ForegroundColor Cyan
            Write-Host "  Docs: http://localhost:${RuntimePort}/docs" -ForegroundColor Cyan
        } else {
            Write-Host "  Note: runtime_port not in services.state" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Status: Not Running" -ForegroundColor Red
        if ($State.ContainsKey('runtime_pid')) {
            Write-Host "  Note: services.state has runtime_pid but process not found (runtime_pid: $($State['runtime_pid']))"
        } else {
            Write-Host "  Note: runtime_pid not recorded in services.state"
        }
    }
    Write-Host "  Log File: $RuntimeLog" -ForegroundColor Green

    Write-Host ""
    Write-Host "Services state file:" -ForegroundColor Yellow
    Write-Host "  $ServiceStatePath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Manage Service:" -ForegroundColor Yellow
    Write-Host "  Stop Services: .\setup.ps1 -Stop" -ForegroundColor Green
    Write-Host "  Start Services: .\setup.ps1 -Start" -ForegroundColor Green
    Write-Host "  Restart Services: .\setup.ps1 -Restart" -ForegroundColor Green
    Write-Host "  Check Status: .\setup.ps1 -Status" -ForegroundColor Green

    if (-not $NoExit) {
        exit 0
    }
}

function Stop-Services {
    param(
        [switch]$NoExit
    )

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Stopping Services" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    $StoppedBackend = $false
    $StoppedFrontend = $false
    $StoppedRuntime = $false

    # Stop Backend Service
    Write-Host "Backend Service:" -ForegroundColor Yellow
    $BackendPid = $null
    $BackendPort = Get-BackendServicePort -DefaultPort 8000
    $SvcState = Get-ServiceProcessState

    if ($SvcState.ContainsKey('backend_pid') -and $SvcState['backend_pid'] -match '^\d+$') {
        $PidValue = [int]$SvcState['backend_pid']
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $ProcessPath = $Process.Path
            $CommandLine = ""
            $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
            if ($WmiProcess) {
                $CommandLine = $WmiProcess.CommandLine
            }
            if ($ProcessPath -like "*python*" -or $CommandLine -like "*main.py*") {
                $BackendPid = $PidValue
            }
        }
    }

    # If not found in PID file, try to find by port
    if (-not $BackendPid) {
        $NetStat = netstat -ano | Select-String ":$BackendPort\s" -ErrorAction SilentlyContinue
        if ($NetStat) {
            $PortPid = ($NetStat -split '\s+')[-1]
            if ($PortPid -match "^\d+$") {
                $PidValue = [int]$PortPid
                $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
                if ($Process) {
                    $ProcessPath = $Process.Path
                    $CommandLine = ""
                    $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
                    if ($WmiProcess) {
                        $CommandLine = $WmiProcess.CommandLine
                    }
                    if ($ProcessPath -like "*python*" -or $CommandLine -like "*main.py*") {
                        $BackendPid = $PidValue
                    }
                }
            }
        }
    }

    if ($BackendPid) {
        Write-Host "  Found backend process (PID: $BackendPid)" -ForegroundColor Green
        Write-Host "  Stopping gracefully..." -ForegroundColor Yellow
        try {
            $Stopped = Stop-ProcessTree -ProcessId $BackendPid -MaxWait 10
            if ($Stopped) {
                $StoppedBackend = $true
                Write-Host "  Backend service stopped successfully" -ForegroundColor Green
            } else {
                Write-Host "  Backend service may not have stopped completely" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  Error stopping backend service: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  Backend service is not running" -ForegroundColor Yellow
    }

    # Also check and stop any processes on backend port
    $PortStopped = Stop-ProcessesByPort -Port $BackendPort
    if ($PortStopped -and -not $StoppedBackend) {
        $StoppedBackend = $true
    }

    Set-ServiceProcessState -RemoveKeys @('backend_pid', 'backend_port')
    Write-Host "  Cleared backend_pid / backend_port in services.state" -ForegroundColor Green

    Write-Host ""

    # Stop Frontend Service
    Write-Host "Frontend Service:" -ForegroundColor Yellow
    $FrontendPort = Get-FrontendServicePort -DefaultPort 3000
    $SvcState = Get-ServiceProcessState

    # Collect all frontend-related PIDs
    $FrontendPids = @()

    if ($SvcState.ContainsKey('frontend_pid') -and $SvcState['frontend_pid'] -match '^\d+$') {
        $PidValue = [int]$SvcState['frontend_pid']
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $ProcessName = $Process.ProcessName
            $CommandLine = ""
            $WmiProcess = Get-WmiObject Win32_Process -Filter "ProcessId = $PidValue" -ErrorAction SilentlyContinue
            if ($WmiProcess) {
                $CommandLine = $WmiProcess.CommandLine
            }
            if ($ProcessName -eq "node" -or $ProcessName -eq "cmd" -or $CommandLine -like "*vite*" -or $CommandLine -like "*npm*dev*") {
                $FrontendPids += $PidValue
            }
        }
    }

    # Find all node processes that might be related to frontend
    $AllNodeProcesses = Get-WmiObject Win32_Process -Filter "Name = 'node.exe'" | Where-Object {
        $Proc = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
        if ($Proc) {
            $CommandLine = $_.CommandLine
            # Check if it's a vite or npm dev process
            if ($CommandLine -like "*vite*" -or $CommandLine -like "*npm*dev*" -or $CommandLine -like "*frontend*") {
                return $true
            }
            # Check if parent is cmd.exe (likely started by npm)
            $Parent = Get-WmiObject Win32_Process -Filter "ProcessId = $($_.ParentProcessId)" -ErrorAction SilentlyContinue
            if ($Parent -and $Parent.Name -eq "cmd.exe") {
                return $true
            }
        }
        return $false
    }

    foreach ($NodeProc in $AllNodeProcesses) {
        if ($FrontendPids -notcontains $NodeProc.ProcessId) {
            $FrontendPids += $NodeProc.ProcessId
        }
    }

    # Find cmd.exe processes that might be running npm
    $AllCmdProcesses = Get-WmiObject Win32_Process -Filter "Name = 'cmd.exe'" | Where-Object {
        $CommandLine = $_.CommandLine
        if ($CommandLine -like "*npm*dev*" -or $CommandLine -like "*vite*") {
            return $true
        }
        return $false
    }

    foreach ($CmdProc in $AllCmdProcesses) {
        if ($FrontendPids -notcontains $CmdProc.ProcessId) {
            $FrontendPids += $CmdProc.ProcessId
        }
    }

    # Also find processes by port
    $NetStat = netstat -ano | Select-String ":$FrontendPort\s" -ErrorAction SilentlyContinue
    if ($NetStat) {
        foreach ($Line in $NetStat) {
            $PortPid = ($Line -split '\s+')[-1]
            if ($PortPid -match "^\d+$") {
                $PidValue = [int]$PortPid
                $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
                if ($Process -and ($Process.ProcessName -eq "node" -or $Process.ProcessName -eq "cmd")) {
                    if ($FrontendPids -notcontains $PidValue) {
                        $FrontendPids += $PidValue
                    }
                }
            }
        }
    }

    if ($FrontendPids.Count -gt 0) {
        Write-Host "  Found $($FrontendPids.Count) frontend-related process(es)" -ForegroundColor Green
        Write-Host "  Stopping all frontend processes and their children..." -ForegroundColor Yellow

        # Stop all processes, starting with the main one
        foreach ($ProcessId in $FrontendPids) {
            try {
                $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
                if ($Process) {
                    Write-Host "    Stopping process (PID: $ProcessId, Name: $($Process.ProcessName))..." -ForegroundColor Yellow
                    $null = Stop-ProcessTree -ProcessId $ProcessId -MaxWait 5
                }
            } catch {
                # Process may have already been stopped
            }
        }

        # Wait a bit for all processes to exit
        Start-Sleep -Seconds 2

        # Also stop any processes still on the port
        $PortStopped = Stop-ProcessesByPort -Port $FrontendPort

        $StoppedFrontend = $true
        Write-Host "  Frontend service stopped successfully" -ForegroundColor Green
    } else {
        Write-Host "  Frontend service is not running" -ForegroundColor Yellow
    }

    # Final check: stop any remaining processes on frontend port
    $PortStopped = Stop-ProcessesByPort -Port $FrontendPort
    if ($PortStopped -and -not $StoppedFrontend) {
        $StoppedFrontend = $true
    }

    Set-ServiceProcessState -RemoveKeys @('frontend_pid', 'frontend_port')
    Write-Host "  Cleared frontend_pid / frontend_port in services.state" -ForegroundColor Green

    Write-Host ""

    # Stop Runtime Service
    Write-Host "Runtime Service:" -ForegroundColor Yellow
    $RuntimePid = $null
    $RuntimePort = $null
    $SvcState = Get-ServiceProcessState
    if ($SvcState.ContainsKey('runtime_port') -and $SvcState['runtime_port'] -match '^\d+$') {
        $RuntimePort = [int]$SvcState['runtime_port']
    }

    if ($SvcState.ContainsKey('runtime_pid') -and $SvcState['runtime_pid'] -match '^\d+$') {
        $PidValue = [int]$SvcState['runtime_pid']
        $Process = Get-Process -Id $PidValue -ErrorAction SilentlyContinue
        if ($Process) {
            $RuntimePid = $PidValue
        }
    }

    if ($RuntimePid) {
        Write-Host "  Found runtime process (PID: $RuntimePid)" -ForegroundColor Green
        $Stopped = Stop-ProcessTree -ProcessId $RuntimePid -MaxWait 10
        if ($Stopped) {
            $StoppedRuntime = $true
            Write-Host "  Runtime service stopped successfully" -ForegroundColor Green
        } else {
            Write-Host "  Runtime service may not have stopped completely" -ForegroundColor Yellow
        }
    } elseif ($RuntimePort) {
        Write-Host "  Runtime PID not found, trying port-based stop on $RuntimePort" -ForegroundColor Yellow
        $PortStopped = Stop-ProcessesByPort -Port $RuntimePort
        if ($PortStopped) {
            $StoppedRuntime = $true
            Write-Host "  Runtime service stopped by port" -ForegroundColor Green
        } else {
            Write-Host "  Runtime service is not running" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Runtime service is not running" -ForegroundColor Yellow
    }

    Set-ServiceProcessState -RemoveKeys @('runtime_pid', 'runtime_port')
    Write-Host "  Cleared runtime_pid / runtime_port in services.state" -ForegroundColor Green

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    if ($StoppedBackend -or $StoppedFrontend -or $StoppedRuntime) {
        Write-Host "Services stopped successfully" -ForegroundColor Green
    } else {
        Write-Host "No running services found" -ForegroundColor Yellow
    }
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    if (-not $NoExit) {
        exit 0
    }
}

function Start-BackendService {
    # Check if backend directory and .env exist
    if (-not (Test-Path $BACKEND_DIR)) {
        Write-Log "ERROR" "Backend directory not found: $BACKEND_DIR"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }
    if (-not (Test-Path $TARGET_ENV_FILE)) {
        Write-Log "ERROR" ".env file not found: $TARGET_ENV_FILE"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    # Read AES key from .env file if exists
    $AESKey = $null
    if (Test-Path $TARGET_ENV_FILE) {
        try {
            $AESKeyLine = Select-String -Path $TARGET_ENV_FILE -Pattern "^SERVER_AES_MASTER_KEY=" -ErrorAction SilentlyContinue
            if ($AESKeyLine) {
                $AESKey = ($AESKeyLine.Line -replace "SERVER_AES_MASTER_KEY=", "").Trim() -replace '"', "" -replace "'", ""
            }
        } catch {
            # Ignore errors
        }
    }

    # If AES key not found in .env, try to generate or use existing environment variable
    if ([string]::IsNullOrEmpty($AESKey)) {
        if ($env:SERVER_AES_MASTER_KEY_ENV) {
            $AESKey = $env:SERVER_AES_MASTER_KEY_ENV
            Write-Log "INFO" "Using existing AES key from environment variable"
        } else {
            Write-Log "WARN" "AES key not found in .env file or environment, generating new one"
            $RandomBytes = New-Object byte[] 32
            $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            $Rng.GetBytes($RandomBytes)
            $Rng.Dispose()
            $AESKey = [Convert]::ToBase64String($RandomBytes)
            # Persist the generated key back to .env so restarts reuse the same key.
            # Without this, every restart generates a new random key and previously
            # encrypted API keys can no longer be decrypted (issue #1236).
            try {
                $EnvContent = Get-Content $TARGET_ENV_FILE -Raw -Encoding UTF8
                if ($EnvContent -match '(?m)^\s*SERVER_AES_MASTER_KEY=') {
                    $EnvContent = $EnvContent -replace '(?m)^\s*SERVER_AES_MASTER_KEY=.*$', ('SERVER_AES_MASTER_KEY=' + $AESKey)
                } else {
                    if (-not $EnvContent.EndsWith("`n")) { $EnvContent += "`n" }
                    $EnvContent += 'SERVER_AES_MASTER_KEY=' + $AESKey + "`n"
                }
                $EnvContent = $EnvContent -replace "`r`n", "`n" -replace "`r", "`n"
                $utf8NoBom = New-Object System.Text.UTF8Encoding $false
                [System.IO.File]::WriteAllText($TARGET_ENV_FILE, $EnvContent, $utf8NoBom)
                Write-Log "INFO" "Generated and persisted AES key to .env"
            } catch {
                Write-Log "WARN" "Failed to persist AES key to .env: $($_.Exception.Message)"
            }
        }
    }

    $env:SERVER_AES_MASTER_KEY_ENV = $AESKey
    Write-Log "INFO" "AES key set: $($AESKey.Substring(0, [Math]::Min(8, $AESKey.Length)))**** (partially hidden)"

    # ===================== Start Backend =====================
    Write-Log "INFO" "===== Starting Backend Service ====="
    $PrevLocation = Get-Location
    Set-Location $BACKEND_DIR

    # Check if virtual environment exists
    $BackendVenv = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
    if (-not (Test-Path $BackendVenv)) {
        Write-Log "ERROR" "Backend virtual environment not found: $BackendVenv"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    # Create log directory
    $LogDir = Join-Path $BACKEND_DIR "logs\run"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }

    # Start backend (background)
    $BackendLog = Join-Path $WORK_HOME "backend.log"

    # Check if backend is already running
    $BackendStarted = $true
    $BackendState = Get-ServiceProcessState
    $ExistingPid = $null
    if ($BackendState.ContainsKey('backend_pid') -and $BackendState['backend_pid'] -match '^\d+$') {
        $ExistingPid = [int]$BackendState['backend_pid']
    }
    if ($ExistingPid) {
        $Process = Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue
        if ($Process) {
            Write-Log "WARN" "Backend service is already running (PID: $ExistingPid)"
            Write-Log "INFO" "Skipping backend start"
            $BackendStarted = $false
        } else {
            Write-Log "INFO" "Removing stale backend_pid / backend_port from services.state"
            Set-ServiceProcessState -RemoveKeys @('backend_pid', 'backend_port')
        }
    }

    if ($BackendStarted) {
        Write-Log "INFO" "Starting backend service, log file: $BackendLog"

        # Clear existing log file to ensure UTF-8 encoding
        if (Test-Path $BackendLog) {
            Remove-Item $BackendLog -Force -ErrorAction SilentlyContinue
        }
        "" | Out-File -FilePath $BackendLog -Encoding utf8 -NoNewline

        $BackendExe = $BackendVenv
        Write-Log "INFO" "Using backend executable: $BackendExe"
        $BackendArgs = "$BACKEND_DIR\main.py"

        $null = Start-Job -ScriptBlock {
            param($ExePath, $Arguments, $WorkDir, $LogFile)
            Set-Location $WorkDir
            $OutputEncoding = [System.Text.Encoding]::UTF8
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            & $ExePath $Arguments 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
        } -ArgumentList $BackendExe, $BackendArgs, $BACKEND_DIR, $BackendLog

        Start-Sleep -Seconds 2
        $BackendProcesses = Get-WmiObject Win32_Process | Where-Object {
            $_.CommandLine -like "*$BackendArgs*" -and $_.ProcessName -eq "python.exe"
        } | Sort-Object CreationDate -Descending | Select-Object -First 1

        if ($BackendProcesses) {
            $BackendPid = $BackendProcesses.ProcessId
            Write-Log "INFO" "Backend service started (PID: $BackendPid)"
            $BackendProcess = @{ Id = $BackendPid }
        } else {
            Write-Log "ERROR" "Failed to find backend process"
            exit 1
        }

        Start-Sleep -Seconds 5
        if ($BackendProcess -and $BackendProcess.Id -and (Get-Process -Id $BackendProcess.Id -ErrorAction SilentlyContinue)) {
            $ResolvedBackendPort = $null
            try {
                $NetStatLines = netstat -ano | Where-Object { $_ -match "LISTENING" -and $_ -match "\s+$BackendPid\s*$" }
                foreach ($Line in $NetStatLines) {
                    if ($Line -match "^\s*(?:TCP|UDP)\s+(?:0\.0\.0\.0|\[::\]|\*|127\.0\.0\.1|localhost):(\d+)\s+") {
                        $fp = [int]$Matches[1]
                        if ($fp -ge 1000 -and $fp -le 65535) {
                            $ResolvedBackendPort = $fp
                            break
                        }
                    }
                }
            } catch {
                # Ignore errors
            }
            if (-not $ResolvedBackendPort -and (Test-Path $TARGET_ENV_FILE)) {
                try {
                    $PortLine = Select-String -Path $TARGET_ENV_FILE -Pattern "^(BACKEND_PORT|SERVER_PORT|PORT)=" -ErrorAction SilentlyContinue | Select-Object -First 1
                    if ($PortLine) {
                        $PortValue = ($PortLine.Line -replace "^(BACKEND_PORT|SERVER_PORT|PORT)=", "").Trim() -replace '"', "" -replace "'", ""
                        if (-not [string]::IsNullOrEmpty($PortValue) -and $PortValue -match "^\d+$") {
                            $ResolvedBackendPort = [int]$PortValue
                        }
                    }
                } catch {
                    # Ignore errors
                }
            }
            if (-not $ResolvedBackendPort) {
                $ResolvedBackendPort = 8000
            }
            Set-ServiceProcessState -Values @{
                backend_pid  = $BackendPid
                backend_port = $ResolvedBackendPort
            }
            Write-Log "INFO" "Saved backend_pid / backend_port to services.state (port: $ResolvedBackendPort)"

            Write-Log "SUCCESS" "Backend service is running successfully"
            Get-Content $BackendLog -Tail 10 -ErrorAction SilentlyContinue
        } else {
            Write-Log "ERROR" "Backend service failed to start. Check log for details: $BackendLog"
            Get-Content $BackendLog -Tail 30 -ErrorAction SilentlyContinue
            exit 1
        }
    }

    Set-Location $PrevLocation
}

function Start-FrontendService {
    if (-not (Test-Path $FRONTEND_DIR)) {
        Write-Log "ERROR" "Frontend directory not found: $FRONTEND_DIR"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    Write-Log "INFO" "===== Starting Frontend Service ====="
    $PrevLocation = Get-Location
    Set-Location $FRONTEND_DIR

    $NodeModules = Join-Path $FRONTEND_DIR "node_modules"
    if (-not (Test-Path $NodeModules)) {
        Write-Log "ERROR" "Frontend dependencies not found: $NodeModules"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        Set-Location $PrevLocation
        exit 1
    }

    $FrontendLog = Join-Path $WORK_HOME "frontend.log"

    $FrontendStarted = $true
    $FrontendState = Get-ServiceProcessState
    $ExistingFrontendPid = $null
    if ($FrontendState.ContainsKey('frontend_pid') -and $FrontendState['frontend_pid'] -match '^\d+$') {
        $ExistingFrontendPid = [int]$FrontendState['frontend_pid']
    }
    if ($ExistingFrontendPid) {
        $Process = Get-Process -Id $ExistingFrontendPid -ErrorAction SilentlyContinue
        if ($Process) {
            Write-Log "WARN" "Frontend service is already running (PID: $ExistingFrontendPid)"
            Write-Log "INFO" "Skipping frontend start"
            $FrontendStarted = $false
        } else {
            Write-Log "INFO" "Removing stale frontend_pid / frontend_port from services.state"
            Set-ServiceProcessState -RemoveKeys @('frontend_pid', 'frontend_port')
        }
    }

    if ($FrontendStarted) {
        Write-Log "INFO" "Starting frontend service, log file: $FrontendLog"

        if (Test-Path $FrontendLog) {
            Remove-Item $FrontendLog -Force -ErrorAction SilentlyContinue
        }
        "" | Out-File -FilePath $FrontendLog -Encoding utf8 -NoNewline

        $FrontendJob = Start-Job -ScriptBlock {
            param($WorkDir, $LogFile)
            Set-Location $WorkDir
            $OutputEncoding = [System.Text.Encoding]::UTF8
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            # Use 2>&1 in cmd to merge stderr so npm/vite warnings don't trigger NativeCommandError and exit under ErrorActionPreference=Stop
            cmd /c "chcp 65001 >nul && npm run dev 2>&1" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        } -ArgumentList $FRONTEND_DIR, $FrontendLog

        Start-Sleep -Seconds 5
        $NodeProcesses = Get-WmiObject Win32_Process | Where-Object {
            $_.ProcessName -eq "node.exe" -and $_.CommandLine -like "*vite*"
        } | Sort-Object CreationDate -Descending | Select-Object -First 1

        $ActualFrontendPid = $null
        if ($NodeProcesses) {
            $ActualFrontendPid = $NodeProcesses.ProcessId
            Write-Log "INFO" "Frontend service started (Node PID: $ActualFrontendPid)"
        } else {
            Write-Log "WARN" "Could not find Node.js process, frontend may still be starting"
            $ActualFrontendPid = $FrontendJob.Id
            Write-Log "INFO" "Frontend job started (Job ID: $($FrontendJob.Id))"
        }

        Start-Sleep -Seconds 5
        Write-Log "INFO" "Latest frontend logs:"
        if (Test-Path $FrontendLog) {
            try {
                $logLines = Get-Content $FrontendLog -Tail 20 -ErrorAction SilentlyContinue
                if ($logLines) {
                    $logLines | ForEach-Object { Write-Host $_ }
                }
            } catch {
                Write-Log "WARN" "Could not read frontend log: $_"
            }
        }

        $ResolvedFrontendPort = $null
        if (Test-Path $FrontendLog) {
            try {
                $LogContent = Get-Content $FrontendLog -Tail 50 -ErrorAction SilentlyContinue
                foreach ($Line in $LogContent) {
                    if ($Line -match "(?:Local|Network).*?http://[^:]+:(\d+)/?") {
                        $LogPort = [int]$Matches[1]
                        if ($LogPort -ge 1000 -and $LogPort -le 65535) {
                            $ResolvedFrontendPort = $LogPort
                            break
                        }
                    } elseif ($Line -match ":(\d{4,5})/") {
                        $LogPort = [int]$Matches[1]
                        if ($LogPort -ge 1000 -and $LogPort -le 65535) {
                            $ResolvedFrontendPort = $LogPort
                            break
                        }
                    }
                }
            } catch {
                # Ignore errors
            }
        }
        if (-not $ResolvedFrontendPort -and (Test-Path $TARGET_ENV_FILE)) {
            try {
                $FrontendPortLine = Select-String -Path $TARGET_ENV_FILE -Pattern "^FRONTEND_PORT=" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($FrontendPortLine) {
                    $PortValue = ($FrontendPortLine.Line -replace "FRONTEND_PORT=", "").Trim() -replace '"', "" -replace "'", ""
                    if (-not [string]::IsNullOrEmpty($PortValue) -and $PortValue -match "^\d+$") {
                        $ResolvedFrontendPort = [int]$PortValue
                    }
                }
            } catch {
                # Ignore errors
            }
        }
        if (-not $ResolvedFrontendPort) {
            $ResolvedFrontendPort = 3000
        }
        Set-ServiceProcessState -Values @{
            frontend_pid  = $ActualFrontendPid
            frontend_port = $ResolvedFrontendPort
        }
        Write-Log "INFO" "Saved frontend_pid / frontend_port to services.state (port: $ResolvedFrontendPort)"
    }

    Set-Location $PrevLocation
}

function Start-RuntimeService {
    Write-Log "INFO" "===== Starting Runtime Service ====="
    $RuntimeServerDir = Join-Path $RUNTIME_DIR "server"
    $RuntimeEnvFile = Join-Path $RuntimeServerDir ".env"
    $RuntimeLog = Join-Path $WORK_HOME "runtime.log"
    $RuntimeRunScript = Join-Path $RUNTIME_DIR "scripts\run-server.ps1"
    Test-Directory $RuntimeServerDir
    Test-File $RuntimeEnvFile
    Test-File $RuntimeRunScript
    $PwshCmd = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if (-not $PwshCmd) {
        Write-Log "ERROR" "powershell.exe not found in PATH"
        exit 1
    }

    Push-Location $RUNTIME_DIR
    try {
        if (Test-Path $RuntimeLog) {
            Remove-Item $RuntimeLog -Force -ErrorAction SilentlyContinue
        }
        "" | Out-File -FilePath $RuntimeLog -Encoding utf8 -NoNewline

        Write-Log "INFO" "Starting runtime server by run-server.ps1 in background, log file: $RuntimeLog"
        Write-Log "INFO" "Running command: powershell.exe -ExecutionPolicy Bypass -File .\scripts\run-server.ps1"
        $RuntimeCmd = "chcp 65001 >nul && powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-server.ps1 >> `"$RuntimeLog`" 2>&1"
        $RuntimeProcess = Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c", $RuntimeCmd `
            -WorkingDirectory $RUNTIME_DIR `
            -WindowStyle Hidden `
            -PassThru
        if (-not $RuntimeProcess) {
            Write-Log "ERROR" "Failed to start runtime server process"
            exit 1
        }
        Write-Log "INFO" "Runtime server process started (pid: $($RuntimeProcess.Id))"
    } finally {
        Pop-Location
    }

    $RuntimePort = $null
    $RuntimePid = $RuntimeProcess.Id
    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if ($RuntimeProcess.HasExited -and $RuntimeProcess.ExitCode -ne 0) {
            Write-Log "ERROR" "Runtime service process exited unexpectedly (exit code: $($RuntimeProcess.ExitCode))"
            if (Test-Path $RuntimeLog) {
                $RuntimeLogTail = Get-Content $RuntimeLog -Tail 30 -ErrorAction SilentlyContinue | Out-String
                if (-not [string]::IsNullOrWhiteSpace($RuntimeLogTail)) {
                    Write-Log "ERROR" "Runtime log tail:`n$RuntimeLogTail"
                }
            }
            exit 1
        }

        if (-not $RuntimeProcess.HasExited) {
            break
        }
    }

    if (-not $RuntimeProcess.HasExited) {
        if ($TARGET_ENV_FILE -and (Test-Path $TARGET_ENV_FILE)) {
            try {
                $EnvContent = Get-Content $TARGET_ENV_FILE -ErrorAction Stop
                $RuntimePortLine = $EnvContent | Where-Object { $_ -match '^RUNTIME_PORT=' } | Select-Object -First 1
                if ($RuntimePortLine -match '^RUNTIME_PORT=(\d+)$') {
                    $RuntimePort = [int]$Matches[1]
                }
            } catch {
                Write-Log "WARN" "Failed to read RUNTIME_PORT from .env: $TARGET_ENV_FILE"
            }
        }

        Set-ServiceProcessState -Values @{
            runtime_pid = $RuntimePid
        } -RemoveKeys @('runtime_port')
        if ($RuntimePort) {
            Set-ServiceProcessState -Values @{ runtime_port = $RuntimePort }
            Write-Log "INFO" "Saved runtime_pid / runtime_port to services.state (pid: $RuntimePid, port: $RuntimePort)"
            Write-Log "SUCCESS" "Runtime service started in background: http://localhost:$RuntimePort"
        } else {
            Write-Log "INFO" "Saved runtime_pid to services.state (pid: $RuntimePid)"
            Write-Log "SUCCESS" "Runtime service started in background"
        }
    } else {
        Set-ServiceProcessState -Values @{ runtime_pid = $RuntimeProcess.Id } -RemoveKeys @('runtime_port')
        Write-Log "WARN" "Saved runtime_pid (launcher only) to services.state (pid: $($RuntimeProcess.Id))"
        Write-Log "WARN" "Runtime launcher process exited quickly. Check runtime log: $RuntimeLog"
    }
}

function Start-Services {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Starting Services" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Check if directories exist
    if (-not (Test-Path $BACKEND_DIR)) {
        Write-Log "ERROR" "Backend directory not found: $BACKEND_DIR"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    if (-not (Test-Path $FRONTEND_DIR)) {
        Write-Log "ERROR" "Frontend directory not found: $FRONTEND_DIR"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    # Check if .env file exists
    if (-not (Test-Path $TARGET_ENV_FILE)) {
        Write-Log "ERROR" ".env file not found: $TARGET_ENV_FILE"
        Write-Log "ERROR" "Please run full installation first: .\setup.ps1"
        exit 1
    }

    $RuntimeServerDirForStart = Join-Path $RUNTIME_DIR "server"
    if (
        (Test-Path $RuntimeServerDirForStart) -and
        (Test-Path (Join-Path $RuntimeServerDirForStart ".env"))
    ) {
        Start-RuntimeService
    } else {
        Write-Log "WARN" "Runtime not installed or incomplete (need server\.env), skipping runtime start"
    }

    Start-BackendService
    Start-FrontendService

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Services Started Successfully" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    Show-Status -NoExit
    return
}

function Restart-Services {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Restarting Services" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # First, stop services
    Write-Log "INFO" "Stopping services..."
    Stop-Services -NoExit

    # Wait a bit before restarting
    Write-Log "INFO" "Waiting 2 seconds before restarting services..."
    Start-Sleep -Seconds 2

    # Now start services
    Write-Log "INFO" "Starting services..."
    Start-Services

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Services Restarted Successfully" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    return
}
