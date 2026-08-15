# PowerShell Script: One-click Deployment for Agent-Studio (Windows Version)
# Requirements: Windows 10+, PowerShell 5.1+

[CmdletBinding()]
param(
    [ValidateSet("mysql", "sqlite")]
    [string]$DbType = "mysql",
    
    [ValidateNotNullOrEmpty()]
    [string]$Branch = "main",
    
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 8000,

    [string]$AppDbUser = "openjiuwen",
    [string]$AppDbPassword = "openjiuwen",
    
    [switch]$Help,
    [switch]$Status,
    [switch]$Stop,
    [switch]$Start,
    [switch]$Restart
)

# ===================== Basic Configuration =====================
$ErrorActionPreference = "Stop"
$WORK_HOME = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $WORK_HOME "agent-studio\backend"
$FRONTEND_DIR = Join-Path $WORK_HOME "agent-studio\frontend"
$RUNTIME_DIR = Join-Path $WORK_HOME "agent-runtime"
$TARGET_ENV_FILE = Join-Path $WORK_HOME "agent-studio\.env"
$ENV_EXAMPLE_FILE = Join-Path $WORK_HOME "agent-studio\.env.example"
$PROGRESS_FILE = Join-Path $WORK_HOME ".setup_progress"
$global:LOG_FILE = Join-Path $WORK_HOME "setup.log"

# Install steps (in order)
$INSTALL_STEPS = @(
    "check_tools",
    "fetch_code",
    "config_aes",
    "config_env",
    "fetch_runtime_code",
    "config_runtime_env",
    "config_mysql",
    "install_backend_dep",
    "install_frontend_dep",
    "start_services"
)

# ===================== Load Utility Functions =====================
$UtilsScript = Join-Path $WORK_HOME "utils.ps1"
. $UtilsScript
Apply-UserEnvironmentConfig -WorkHome $WORK_HOME

$ManageServiceScript = Join-Path $WORK_HOME "manage_service.ps1"
. $ManageServiceScript

function Show-Help {
    Write-Host @"
Usage: .\setup.ps1 [Options]
Function: One-click deployment of Agent-Studio (Windows version), supports specifying database type

Supported Parameters:
  -DbType type    Specify database type, optional values: mysql (default), sqlite
                  -DbType mysql: Set DB_TYPE to mysql in .env
                  -DbType sqlite: Set DB_TYPE to sqlite in .env
  -Branch branch  Git branch for agent-studio and agent-runtime, default: main
  -FrontendPort port  Frontend service port (default: 3000), written to .env FRONTEND_PORT
  -BackendPort port   Backend service port (default: 8000), written to .env BACKEND_PORT
  -AppDbUser user     MySQL application user (default: openjiuwen)
  -AppDbPassword pwd  MySQL application user password (default: openjiuwen)
  -Status         Show runtime, frontend, and backend service status and access URLs
  -Stop           Gracefully stop runtime, frontend, and backend services
  -Start          Start runtime, frontend, and backend services (without reinstalling dependencies)
  -Restart        Restart runtime, frontend, and backend services (without reinstalling dependencies)
  -Help           Show this help message and exit

Examples:
  .\setup.ps1                    # Default: Set DB_TYPE to mysql, use main branch, ports 3000/8000
  .\setup.ps1 -DbType sqlite      # Set DB_TYPE to sqlite, use main branch
  .\setup.ps1 -Branch develop        # Use develop branch for code download
  .\setup.ps1 -FrontendPort 3001 -BackendPort 8001  # Custom frontend/backend ports
  .\setup.ps1 -DbType sqlite -Branch develop  # Set DB_TYPE to sqlite, use develop branch
  .\setup.ps1 -Status             # Show service status and access URLs
  .\setup.ps1 -Stop                # Gracefully stop runtime, frontend, and backend services
  .\setup.ps1 -Start               # Start runtime, frontend, and backend services
  .\setup.ps1 -Restart             # Restart runtime, frontend, and backend services
  .\setup.ps1 -Help                # View help

Working Directory: $WORK_HOME
"@
    exit 0
}

# ===================== Parameter Parsing =====================
# Parameter validation is done via PowerShell attributes: [ValidateSet] (DbType), [ValidateNotNullOrEmpty] (Branch), [CmdletBinding()] (reject unknown params)

if ($Help) {
    Show-Help
}

if ($Status) {
    Show-Status
}

if ($Stop) {
    Stop-Services
}

if ($Start) {
    Start-Services
    exit 0
}

if ($Restart) {
    Restart-Services
    exit 0
}

# ===================== Resume from Checkpoint =====================
# Check if we should continue from last checkpoint
$LAST_PROGRESS = ""
$LAST_PROGRESS = Read-Progress
if (-not [string]::IsNullOrEmpty($LAST_PROGRESS)) {
    Write-Log "WARN" "Detected previous deployment progress: $LAST_PROGRESS"
    $Continue = Read-Host "Continue from last checkpoint? (y/n, default y)"
    if ($Continue -ne "n" -and $Continue -ne "N") {
        Write-Log "INFO" "Will continue from checkpoint: $LAST_PROGRESS"
    } else {
        Clear-Progress
        $LAST_PROGRESS = ""
        Write-Log "INFO" "Progress cleared, starting fresh deployment"
    }
}

# ===================== Pre-check =====================
Write-Log "INFO" "===== Starting Agent-Studio Deployment (Windows Version) ====="
Write-Log "INFO" "Working Directory: $WORK_HOME"

# Check Windows version
$OSVersion = [System.Environment]::OSVersion.Version
if ($OSVersion.Major -lt 10) {
    Write-Log "ERROR" "This script requires Windows 10 or later, current version: $($OSVersion.Major).$($OSVersion.Minor)"
    exit 1
}

# Check PowerShell version
$PSVersion = $PSVersionTable.PSVersion
if ($PSVersion.Major -lt 5) {
    Write-Log "ERROR" "This script requires PowerShell 5.1 or later, current version: $($PSVersion.Major).$($PSVersion.Minor)"
    exit 1
}

# Check execution policy
$ExecutionPolicy = Get-ExecutionPolicy
if ($ExecutionPolicy -eq "Restricted") {
    Write-Log "WARN" "Current execution policy is Restricted, need to modify execution policy"
    Write-Log "INFO" "Please run as administrator: Set-ExecutionPolicy RemoteSigned"
    exit 1
}

# Unblock all scripts to avoid security warnings
Unblock-AllScripts -WorkHome $WORK_HOME

# ===================== Install Basic Tools =====================
$STEP = "check_tools"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Basic tools check (already completed)"
} else {
    Write-Log "INFO" "===== Checking Basic Tools ===="
    $Scripts = @("check_git.ps1", "check_nodejs.ps1", "check_python.ps1")

    # Add MySQL check if database type is MySQL
    if ($DbType -eq "mysql") {
        $Scripts += "check_mysql.ps1"
    }

    $PythonExePath = $null

    foreach ($Script in $Scripts) {
        $ScriptPath = Join-Path $WORK_HOME $Script
        Test-File $ScriptPath
        Write-Log "INFO" "Executing script: $ScriptPath"
        & $ScriptPath
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR" "Execution of $Script failed"
            exit 1
        }
    }
    Save-Progress -Step $STEP
}

# Get Python executable path from environment variable set by check_python.ps1
if ($env:PYTHON_EXE_PATH) {
    $PythonExePath = $env:PYTHON_EXE_PATH.Trim()
    Write-Log "INFO" "Found Python executable from environment variable: $PythonExePath"
} else {
    Write-Log "ERROR" "PYTHON_EXE_PATH environment variable not found"
    Write-Log "ERROR" "Please ensure Python is installed and check_python.ps1 completed successfully"
    exit 1
}

# Verify Python executable path exists (version already checked in check_python.ps1)
if (-not (Test-Path $PythonExePath)) {
    Write-Log "ERROR" "Python executable path not found or invalid: $PythonExePath"
    Write-Log "ERROR" "Please ensure Python is installed and check_python.ps1 completed successfully"
    exit 1
}

# Refresh PATH environment variable to include newly installed tools
Write-Log "INFO" "Refreshing PATH environment variable..."
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", [System.EnvironmentVariableTarget]::Machine) + ";" + [System.Environment]::GetEnvironmentVariable("PATH", [System.EnvironmentVariableTarget]::User)

# Add Python path to current session PATH
$PythonDir = Split-Path -Parent $PythonExePath
$ScriptsDir = Join-Path $PythonDir "Scripts"
if ($env:PATH -notlike "*$PythonDir*") {
    $env:PATH = "$PythonDir;$ScriptsDir;" + $env:PATH
}

# Check basic commands
Test-Command "git"
Test-Command "node"
Test-Command "npm"

Write-Log "INFO" "Will use Python executable at: $PythonExePath"

# ===================== Fetching Code =====================
$STEP = "fetch_code"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Code fetch (already completed)"
    if (-not (Test-Path (Join-Path $WORK_HOME "agent-studio"))) {
        Write-Log "WARN" "Code directory not found, re-fetching..."
        $LAST_PROGRESS = ""
    }
} else {
    Write-Log "INFO" "===== Fetching Code ====="
    Write-Log "INFO" "Using branch: $Branch"
    $StudioRepoUrl = "https://gitcode.com/openJiuwen/agent-studio.git"
    $StudioDir = Join-Path $WORK_HOME "agent-studio"
    Write-Log "INFO" "Repository: $StudioRepoUrl"
    Write-Log "INFO" "Target directory: $StudioDir"

    if (Test-Path $StudioDir) {
        Write-Log "INFO" "agent-studio directory already exists, updating code..."
        Set-Location $StudioDir
        git fetch origin --prune
        git pull origin $Branch
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR" "Failed to update agent-studio code"
            Write-Log "INFO" "Try manually: cd `"$StudioDir`" && git fetch origin --prune && git pull origin $Branch"
            exit 1
        }
        Write-Log "SUCCESS" "agent-studio updated successfully"
    } else {
        Write-Log "INFO" "Cloning agent-studio repository..."
        Set-Location $WORK_HOME
        git clone -b $Branch $StudioRepoUrl "agent-studio"
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR" "Failed to clone agent-studio repository"
            Write-Log "INFO" "Check network and repository access: $StudioRepoUrl"
            exit 1
        }
        Write-Log "SUCCESS" "agent-studio cloned successfully"
    }

    try {
        Set-Location $WORK_HOME
    } catch {
        Write-Log "WARN" "Could not change directory to work home: $($_.Exception.Message)"
    }

    # Check code directories
    Test-Directory (Join-Path $WORK_HOME "agent-studio")
    Test-Directory $BACKEND_DIR
    Test-Directory $FRONTEND_DIR
    Save-Progress -Step $STEP
}

# ===================== Configure AES Key =====================
$STEP = "config_aes"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: AES key configuration (already completed)"
    if ([string]::IsNullOrEmpty($env:SERVER_AES_MASTER_KEY_ENV) -and (Test-Path $TARGET_ENV_FILE)) {
        Write-Log "WARN" "AES key not set, will read from .env file (if exists)"
    }
} else {
    Write-Log "INFO" "===== Configuring AES Key ======"
    $AESKey = $null

    # Try to use existing build_AES_master_key.ps1 script
    $AESScript = Join-Path $BACKEND_DIR "build_AES_master_key.ps1"
    if (Test-Path $AESScript) {
        Write-Log "INFO" "Executing AES key generation script: $AESScript"
        $AESKey = & $AESScript
        if ([string]::IsNullOrEmpty($AESKey)) {
            Write-Log "WARN" "AES key generation script returned empty result, generating key dynamically"
            $AESKey = $null
        }
    } else {
        Write-Log "INFO" "AES key generation script not found, generating key dynamically"
    }

    # Generate AES key dynamically if script not found or failed
    if ([string]::IsNullOrEmpty($AESKey)) {
        Write-Log "INFO" "Generating AES key dynamically..."
        # Generate a random 32-byte key (256 bits) and convert to base64
        $RandomBytes = New-Object byte[] 32
        $Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $Rng.GetBytes($RandomBytes)
        $Rng.Dispose()
        $AESKey = [Convert]::ToBase64String($RandomBytes)
    }

    $env:SERVER_AES_MASTER_KEY_ENV = $AESKey
    Write-Log "INFO" "AES key set: $($AESKey.Substring(0, [Math]::Min(8, $AESKey.Length)))**** (partially hidden)"
    Save-Progress -Step $STEP
}

# ===================== Configure .env File =====================
$STEP = "config_env"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: .env file configuration (already completed)"
} else {
    Write-Log "INFO" "===== Configuring .env File ====="
    Test-File $ENV_EXAMPLE_FILE
    if (Test-Path $TARGET_ENV_FILE) {
        $BackupEnv = "$TARGET_ENV_FILE.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
        Copy-Item $TARGET_ENV_FILE $BackupEnv
        Write-Log "INFO" "Backed up existing .env file: $BackupEnv"
    }
    # 按字节复制，避免 Copy-Item 在 Windows 上把 LF 转成 CRLF 导致 UTF-8 中文乱码
    [System.IO.File]::WriteAllBytes($TARGET_ENV_FILE, [System.IO.File]::ReadAllBytes($ENV_EXAMPLE_FILE))
    Test-File $TARGET_ENV_FILE

    # Replace DB_TYPE and ports
    Write-Log "INFO" "Setting database type to: $DbType"
    Write-Log "INFO" "Setting FRONTEND_PORT to: $FrontendPort, BACKEND_PORT to: $BackendPort"
    $Content = Get-Content $TARGET_ENV_FILE -Raw -Encoding UTF8
    if ($DbType -eq "sqlite") {
        $Content = $Content -replace "DB_TYPE=mysql", "DB_TYPE=sqlite"
    } else {
        $Content = $Content -replace "DB_TYPE=sqlite", "DB_TYPE=mysql"
    }
    $Content = $Content -replace "FRONTEND_PORT=\d+", "FRONTEND_PORT=$FrontendPort"
    $Content = $Content -replace "BACKEND_PORT=\d+", "BACKEND_PORT=$BackendPort"
    $Content = $Content -replace "VITE_API_PROXY_TARGET=http://localhost:\d+/", "VITE_API_PROXY_TARGET=http://localhost:${BackendPort}/"
    $Content = $Content -replace 'ALLOWED_ORIGINS=\["http://localhost:\d+","http://127\.0\.0\.1:\d+"\]', "ALLOWED_ORIGINS=[`"http://localhost:${FrontendPort}`",`"http://127.0.0.1:${FrontendPort}`"]"
    # MySQL 应用账号
    Write-Log "INFO" "Setting DB_USER / DB_PASSWORD from -AppDbUser / -AppDbPassword"
    if ($Content -match '(?m)^\s*DB_USER=') {
        $Content = $Content -replace '(?m)^\s*DB_USER=.*$', ('DB_USER=' + $AppDbUser)
    } else {
        if (-not $Content.EndsWith("`n")) { $Content += "`n" }
        $Content += 'DB_USER=' + $AppDbUser + "`n"
    }
    if ($Content -match '(?m)^\s*DB_PASSWORD=') {
        $Content = $Content -replace '(?m)^\s*DB_PASSWORD=.*$', ('DB_PASSWORD=' + $AppDbPassword)
    } else {
        if (-not $Content.EndsWith("`n")) { $Content += "`n" }
        $Content += 'DB_PASSWORD=' + $AppDbPassword + "`n"
    }
    $MysqlConnForEnv = Get-DbHostPortFromUserConfig -WorkHome $WORK_HOME -DefaultHost "127.0.0.1" -DefaultPort 3306
    Write-Log "INFO" "Setting DB_HOST / DB_PORT from user_config.ps1 (`$DB_HOST / `$DB_PORT)"
    if ($Content -match '(?m)^\s*DB_HOST=') {
        $Content = $Content -replace '(?m)^\s*DB_HOST=.*$', ('DB_HOST=' + $MysqlConnForEnv.Host)
    } else {
        if (-not $Content.EndsWith("`n")) { $Content += "`n" }
        $Content += 'DB_HOST=' + $MysqlConnForEnv.Host + "`n"
    }
    if ($Content -match '(?m)^\s*DB_PORT=') {
        $Content = $Content -replace '(?m)^\s*DB_PORT=.*$', ('DB_PORT=' + $MysqlConnForEnv.Port)
    } else {
        if (-not $Content.EndsWith("`n")) { $Content += "`n" }
        $Content += 'DB_PORT=' + $MysqlConnForEnv.Port + "`n"
    }
    # 统一为 LF 换行并用 UTF-8 无 BOM 写回，避免 CRLF 导致配置解析/编码错误
    $Content = $Content -replace "`r`n", "`n" -replace "`r", "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($TARGET_ENV_FILE, $Content, $utf8NoBom)

    # Verify replacement result
    $DBTypeActual = (Select-String -Path $TARGET_ENV_FILE -Pattern "^DB_TYPE=").Line -replace "DB_TYPE=", ""
    if ($DBTypeActual -ne $DbType) {
        Write-Log "WARN" "DB_TYPE configuration may not have taken effect, current value: $DBTypeActual (expected: $DbType)"
    } else {
        Write-Log "INFO" "DB_TYPE configured successfully: $DbType"
    }
    $FrontendPortActual = (Select-String -Path $TARGET_ENV_FILE -Pattern "^FRONTEND_PORT=").Line -replace "FRONTEND_PORT=", ""
    $BackendPortActual = (Select-String -Path $TARGET_ENV_FILE -Pattern "^BACKEND_PORT=").Line -replace "BACKEND_PORT=", ""
    Write-Log "INFO" "FRONTEND_PORT configured: $FrontendPortActual, BACKEND_PORT configured: $BackendPortActual"
    Write-Log "SUCCESS" ".env updated: DB_USER=$AppDbUser (DB_PASSWORD set), DB_HOST=$($MysqlConnForEnv.Host), DB_PORT=$($MysqlConnForEnv.Port)"

    Save-Progress -Step $STEP
}

# ===================== Persist AES key into .env =====================
# The AES key generated in the config_aes step is only set in the current
# process environment. If it is not written back to .env, manage_service.ps1
# will generate a *new* random key on every restart, making previously
# encrypted API keys undecryptable (issue #1236). Persist it here so restarts
# reuse the same key.
if (-not [string]::IsNullOrEmpty($env:SERVER_AES_MASTER_KEY_ENV) -and (Test-Path $TARGET_ENV_FILE)) {
    $EnvContent = Get-Content $TARGET_ENV_FILE -Raw -Encoding UTF8
    if ($EnvContent -match '(?m)^\s*SERVER_AES_MASTER_KEY=') {
        $EnvContent = $EnvContent -replace '(?m)^\s*SERVER_AES_MASTER_KEY=.*$', ('SERVER_AES_MASTER_KEY=' + $env:SERVER_AES_MASTER_KEY_ENV)
    } else {
        if (-not $EnvContent.EndsWith("`n")) { $EnvContent += "`n" }
        $EnvContent += 'SERVER_AES_MASTER_KEY=' + $env:SERVER_AES_MASTER_KEY_ENV + "`n"
    }
    $EnvContent = $EnvContent -replace "`r`n", "`n" -replace "`r", "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($TARGET_ENV_FILE, $EnvContent, $utf8NoBom)
    Write-Log "SUCCESS" "AES key persisted to .env (SERVER_AES_MASTER_KEY)"
}



# ===================== Download Runtime Code =====================
$STEP = "fetch_runtime_code"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Runtime code download/update (already completed)"
} else {
    Write-Log "INFO" "===== Downloading Runtime Code ====="
    $RuntimeRepoUrl = "https://gitcode.com/openJiuwen/agent-runtime.git"
    Write-Log "INFO" "Runtime repository: $RuntimeRepoUrl"
    Write-Log "INFO" "Runtime branch: $Branch (same as -Branch for agent-studio)"

    if (Test-Path $RUNTIME_DIR) {
        Write-Log "INFO" "Runtime directory already exists, updating code..."
        Set-Location $RUNTIME_DIR
        git fetch origin --prune
        git pull origin $Branch
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR" "Failed to update runtime code"
            exit 1
        }
    } else {
        Write-Log "INFO" "Cloning runtime repository..."
        Set-Location $WORK_HOME
        git clone -b $Branch $RuntimeRepoUrl "agent-runtime"
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERROR" "Failed to clone runtime repository"
            exit 1
        }
    }
    Save-Progress -Step $STEP
}

# ===================== Configure Runtime .env =====================
$STEP = "config_runtime_env"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Runtime .env configuration (already completed)"
} else {
    Write-Log "INFO" "===== Configuring Runtime .env ====="
    $RuntimeServerDir = Join-Path $RUNTIME_DIR "server"
    $RuntimeEnvExample = Join-Path $RuntimeServerDir ".env.example"
    $RuntimeEnvFile = Join-Path $RuntimeServerDir ".env"
    Test-Directory $RuntimeServerDir
    Test-File $RuntimeEnvExample

    if (-not (Test-Path $RuntimeEnvFile)) {
        Write-Log "INFO" "Runtime .env not found, copying from .env.example"
        Copy-Item -Path $RuntimeEnvExample -Destination $RuntimeEnvFile -Force
        if (-not (Test-Path $RuntimeEnvFile)) {
            Write-Log "ERROR" "Failed to create runtime .env from .env.example"
            exit 1
        }
    }

    Write-Log "INFO" "Setting runtime DB_TYPE to: $DbType"
    $RuntimeEnvContent = Get-Content -Path $RuntimeEnvFile -Raw -Encoding UTF8
    if ($RuntimeEnvContent -match "(?m)^DB_TYPE=") {
        $RuntimeEnvContent = [System.Text.RegularExpressions.Regex]::Replace($RuntimeEnvContent, "(?m)^DB_TYPE=.*$", "DB_TYPE=$DbType")
    } else {
        if (-not $RuntimeEnvContent.EndsWith("`n")) {
            $RuntimeEnvContent += "`n"
        }
        $RuntimeEnvContent += "DB_TYPE=$DbType`n"
    }

    $RtDbCfg = Get-DbHostPortFromUserConfig -WorkHome $WORK_HOME -DefaultHost "127.0.0.1" -DefaultPort 3306
    Write-Log "INFO" "Setting runtime DB_USER / DB_PASSWORD from -AppDbUser / -AppDbPassword"
    Write-Log "INFO" "Setting runtime DB_HOST / DB_PORT from user_config.ps1 (`$DB_HOST / `$DB_PORT)"
    $UserWritten = $false
    $PasswordWritten = $false
    $HostWritten = $false
    $PortWritten = $false
    $RuntimeLines = [System.Collections.ArrayList]@()
    foreach ($Line in [regex]::Split($RuntimeEnvContent, '\r\n|\r|\n')) {
        if ($Line -match "^\s*DB_USER=") {
            [void]$RuntimeLines.Add("DB_USER=$AppDbUser")
            $UserWritten = $true
        } elseif ($Line -match "^\s*DB_PASSWORD=") {
            [void]$RuntimeLines.Add("DB_PASSWORD=$AppDbPassword")
            $PasswordWritten = $true
        } elseif ($Line -match "^\s*DB_HOST=") {
            [void]$RuntimeLines.Add("DB_HOST=$($RtDbCfg.Host)")
            $HostWritten = $true
        } elseif ($Line -match "^\s*DB_PORT=") {
            [void]$RuntimeLines.Add("DB_PORT=$($RtDbCfg.Port)")
            $PortWritten = $true
        } else {
            [void]$RuntimeLines.Add($Line)
        }
    }
    if (-not $UserWritten) { [void]$RuntimeLines.Add("DB_USER=$AppDbUser") }
    if (-not $PasswordWritten) { [void]$RuntimeLines.Add("DB_PASSWORD=$AppDbPassword") }
    if (-not $HostWritten) { [void]$RuntimeLines.Add("DB_HOST=$($RtDbCfg.Host)") }
    if (-not $PortWritten) { [void]$RuntimeLines.Add("DB_PORT=$($RtDbCfg.Port)") }
    $RuntimeEnvContent = ($RuntimeLines -join "`n")
    Write-Log "SUCCESS" "Runtime .env updated: DB_USER=$AppDbUser (DB_PASSWORD set), DB_HOST=$($RtDbCfg.Host), DB_PORT=$($RtDbCfg.Port)"

    $RuntimeEnvContent = $RuntimeEnvContent -replace "`r`n", "`n" -replace "`r", "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($RuntimeEnvFile, $RuntimeEnvContent, $utf8NoBom)

    $RuntimeDbTypeActual = (Select-String -Path $RuntimeEnvFile -Pattern "^DB_TYPE=").Line -replace "DB_TYPE=", ""
    if ($RuntimeDbTypeActual -ne $DbType) {
        Write-Log "WARN" "Runtime DB_TYPE configuration may not have taken effect, current value: $RuntimeDbTypeActual (expected: $DbType)"
    } else {
        Write-Log "INFO" "Runtime DB_TYPE configured successfully: $DbType"
    }

    Save-Progress -Step $STEP
}

# ===================== MySQL Database Configuration =====================
$STEP = "config_mysql"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: MySQL database configuration (already completed)"
} elseif ($DbType -eq "mysql") {
    Write-Log "INFO" "===== MySQL Database Configuration ====="

    # Call config_mysql.ps1 to create databases
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ConfigMySQLPath = Join-Path $ScriptDir "config_mysql.ps1"
    Write-Log "INFO" "Calling config_mysql.ps1 to create MySQL databases..."
    # Set WORK_HOME environment variable so config_mysql.ps1 can find .env file
    $env:WORK_HOME = $WORK_HOME
    & $ConfigMySQLPath -AppDbUser $AppDbUser -AppDbPassword $AppDbPassword
    if ($LASTEXITCODE -eq 0) {
        Write-Log "SUCCESS" "MySQL databases configured successfully"
    } else {
        Write-Log "WARN" "MySQL database configuration may have failed (exit code: $LASTEXITCODE)"
        Write-Log "INFO" "Please verify that databases are created correctly"
    }

    Write-Log "INFO" "Continuing with deployment..."
    Save-Progress -Step $STEP
} else {
    Write-Log "INFO" "Skipping: MySQL database configuration (not applicable, DbType=$DbType)"
    Save-Progress -Step $STEP
}

# ===================== Install Backend Dependencies =====================
$STEP = "install_backend_dep"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Backend dependencies install (already completed)"
    Set-Location $BACKEND_DIR
} else {
    Write-Log "INFO" "===== Installing Backend Dependencies ====="
    Set-Location $BACKEND_DIR
    Write-Log "INFO" "Creating/resetting uv virtual environment"

    # Ensure the virtual environment directory is clean before creating
    $VenvPath = ".venv"

    if (Test-Path $VenvPath) {
        Write-Log "INFO" "Removing existing virtual environment directory: .venv"
        if (Remove-DirectoryRobust -Path $VenvPath) {
            Write-Log "INFO" "Existing virtual environment directory removed successfully"
        } else {
            Write-Log "WARN" "Failed to remove existing virtual environment directory using robust methods"
            Write-Log "INFO" "Attempting to use uv venv --clear to recreate virtual environment..."
        }
    }

    Write-Log "INFO" "Using Python executable at: $PythonExePath for virtual environment"
    uv venv --clear --python $PythonExePath
    if ($LASTEXITCODE -ne 0) {
        # Check if .venv directory still exists (both manual removal and uv --clear failed)
        if (Test-Path $VenvPath) {
            Write-Log "ERROR" "Failed to create virtual environment"
            Write-Log "ERROR" "The .venv directory cannot be removed, likely because it is in use by running processes."
            Write-Host ""
            Write-Host "Solution 1 (Recommended): Stop all services first" -ForegroundColor Yellow
            Write-Host "  Run: .\setup.ps1 -Stop" -ForegroundColor Green
            Write-Host "  Then retry the deployment: .\setup.ps1" -ForegroundColor Green
            Write-Host ""
            Write-Host "Solution 2: Manually delete the directory" -ForegroundColor Yellow
            Write-Host "  1. Close all applications that might be using the .venv directory" -ForegroundColor White
            Write-Host "  2. Stop any running backend services" -ForegroundColor White
            Write-Host "  3. Manually delete the directory:" -ForegroundColor White
            Write-Host "     $BACKEND_DIR\.venv" -ForegroundColor Cyan
            Write-Host "  4. Then retry the deployment: .\setup.ps1" -ForegroundColor Green
            Write-Host ""
            exit 1
        } else {
            Write-Log "ERROR" "Failed to create virtual environment"
            exit 1
        }
    }

    Write-Log "INFO" "Syncing dependencies with uv (editable project + default dependency groups, e.g. dev)"
    $UvDiBackend = Get-UvDefaultIndexArgsFromUserConfig -WorkHome $WORK_HOME
    $UvSyncArgs = @('sync', '--python', $PythonExePath) + $UvDiBackend
    $UvSyncArgsLog = ($UvSyncArgs | ForEach-Object { "$_" }) -join ' '
    $UvSyncArgsLog = $UvSyncArgsLog -replace '(https?://)([^/\s:@]+):([^/\s@]+)@', '$1***:***@'
    Write-Log "INFO" "Running uv command: uv $UvSyncArgsLog"
    uv @UvSyncArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "Failed to sync dependencies with uv"
        exit 1
    }

    # Create log directory
    $LogDir = Join-Path $BACKEND_DIR "logs\run"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    Save-Progress -Step $STEP
}


# ===================== Install Frontend Dependencies =====================
$STEP = "install_frontend_dep"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Frontend dependencies install (already completed)"
    Set-Location $FRONTEND_DIR
} else {
    Write-Log "INFO" "===== Installing Frontend Dependencies ====="
    Set-Location $FRONTEND_DIR

    Write-Log "INFO" "Installing frontend dependencies"
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "Failed to install frontend dependencies"
        exit 1
    }
    Save-Progress -Step $STEP
}


# ===================== Start Services =====================
$STEP = "start_services"
if (Test-SkipStep -CurrentStep $STEP -LastProgress $LAST_PROGRESS) {
    Write-Log "INFO" "Skipping: Service startup (already completed)"
} else {
    Write-Log "INFO" "===== Starting Services ====="
    try {
        Start-Services
        Save-Progress -Step $STEP
    } catch {
        $ErrMsg = $_.Exception.Message
        $ErrType = $_.Exception.GetType().FullName
        $ErrStack = $_.ScriptStackTrace
        Write-Log "WARN" "Service startup reported an error (services may still be running): $ErrMsg"
        Write-Log "WARN" "Service startup error type: $ErrType"
        if (-not [string]::IsNullOrWhiteSpace($ErrStack)) {
            Write-Log "WARN" "Service startup script stack:`n$ErrStack"
        }
        try { Save-Progress -Step $STEP } catch { }
    }
}

# Return to installation directory (failure does not affect completion message)
try {
    Set-Location $WORK_HOME
} catch {
    Write-Log "WARN" "Could not change to working directory: $($_.Exception.Message)"
}

# ===================== Completion =====================
try {
    Write-Log "SUCCESS" "========================================="
    Write-Log "SUCCESS" "========= Deployment Completed ========="
    Write-Log "SUCCESS" "========================================="

    # Clear progress file on successful completion
    Clear-Progress

} catch {
    Write-Log "WARN" "Post-completion step failed: $($_.Exception.Message)"
    Write-Log "SUCCESS" "========= Deployment Completed ========="
    Show-Status
}

exit 0