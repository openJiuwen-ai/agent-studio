# openJiuwen AgentStudio — 原生（免容器）一键启动（Windows PowerShell）
# 按序拉起：MySQL → Redis → MinIO(+mc) → manager → service → runtime → console(nginx)
[CmdletBinding()] param()
$ErrorActionPreference = "Continue"
$ErrorView = "NormalView"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
Set-Location $BundleRoot
$Run = Join-Path $BundleRoot 'run'; $Log = Join-Path $BundleRoot 'logs'; $Data = Join-Path $BundleRoot 'data'
New-Item -ItemType Directory -Force -Path $Run,$Log,$Data,(Join-Path $Data 'mysql'),(Join-Path $Data 'redis'),(Join-Path $Data 'minio') | Out-Null

function W-Log($m){ Write-Host "[start] $m" -ForegroundColor Cyan }
function W-Warn($m){ Write-Host "[warn] $m" -ForegroundColor Yellow }
function W-Die($m){ Write-Host "[fatal] $m" -ForegroundColor Red; exit 1 }

# ── 加载 .env ────────────────────────────────────────────────────────────────
$EnvFile = Join-Path $BundleRoot '.env'
if (-not (Test-Path $EnvFile)) { Copy-Item (Join-Path $BundleRoot '.env.template') $EnvFile; W-Log "已从 .env.template 创建 .env" }
# .env 是无 BOM 的 UTF-8 文件且含中文注释。PS5.1 的 Get-Content 默认按 ANSI/GBK 解码，
# 中文多字节序列里若有字节撞上 0x0A 会被当换行 → 错行/吞行（实测 SPRING_DATASOURCE_URL
# 整行被吞进注释 → 变量丢失 → manager 报 ${spring_datasource_url} 占位符未解析而崩）。
# 必须显式 -Encoding UTF8。同 [[native-install-container-free]] versions.env 那条坑。
Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
    $kv = $line -split '=',2
    $v = $kv[1].Trim()
    # .env 值可能被双引号包裹（如 SPRING_DATASOURCE_URL 含 &，bash 侧需引号）。
    # PS 侧剥掉首尾一对双引号，否则引号会进环境变量值。
    if ($v -match '^"(.*)"$') { $v = $matches[1] }
    Set-Item -Path "Env:$($kv[0].Trim())" -Value $v
  }
}
# 默认端口
if (-not $env:CONSOLE_PORT)        { $env:CONSOLE_PORT = '80' }
if (-not $env:DB_PORT)             { $env:DB_PORT = '3306' }
if (-not $env:REDIS_EXTERNAL_PORT) { $env:REDIS_EXTERNAL_PORT = '6379' }
if (-not $env:MINIO_API_PORT)     { $env:MINIO_API_PORT = '9000' }
if (-not $env:MINIO_CONSOLE_PORT) { $env:MINIO_CONSOLE_PORT = '9001' }
if (-not $env:MANAGER_PORT)       { $env:MANAGER_PORT = '31111' }
if (-not $env:SERVICE_PORT)       { $env:SERVICE_PORT = '31113' }
if (-not $env:RUNTIME_PORT)       { $env:RUNTIME_PORT = '31014' }

# ── 依赖路径 ────────────────────────────────────────────────────────────────
$Deps = Join-Path $BundleRoot 'deps\win'
$env:JAVA_HOME = Join-Path $Deps 'jre-17'
$env:PATH = "$(Join-Path $env:JAVA_HOME 'bin');$(Join-Path $Deps 'mysql-8.0\bin');$(Join-Path $Deps 'redis-7');$(Join-Path $Deps 'minio');$(Join-Path $Deps 'nginx');$env:PATH"
$PythonBin = Join-Path $Deps 'python-3.11\python.exe'
$Mysqld = Join-Path $Deps 'mysql-8.0\bin\mysqld.exe'
$MysqlCli = Join-Path $Deps 'mysql-8.0\bin\mysql.exe'
$RedisSrv = Join-Path $Deps 'redis-7\redis-server.exe'
$MinioBin = Join-Path $Deps 'minio\minio.exe'
$McBin = Join-Path $Deps 'minio\mc.exe'
$NginxBin = Join-Path $Deps 'nginx\nginx.exe'

function Test-Port($port, $maxSec=60){
  $t=0
  while ($t -lt $maxSec) {
    try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1', [int]$port); $c.Close(); return $true }
    catch { Start-Sleep -Seconds 2; $t+=2 }
  }
  return $false
}
function Wait-Http($url, $name, $maxSec=180){
  $t=0
  while ($t -lt $maxSec) {
    try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -lt 500) { W-Log "$name 就绪 ($url)"; return $true } }
    catch { Start-Sleep -Seconds 3; $t+=3 }
  }
  W-Warn "$name 健康检查超时：$url"; return $false
}
function Start-Bg($exe, $argList, $outLog){
  $p = Start-Process -FilePath $exe -ArgumentList $argList -RedirectStandardOutput $outLog -RedirectStandardError "$outLog.err" -WindowStyle Hidden -PassThru
  return $p
}
function Is-PidAlive($pidfile){
  if (Test-Path $pidfile) { $p=[int](Get-Content $pidfile -Raw); try { $pr = Get-Process -Id $p -ErrorAction Stop; return $pr.Id } catch { return $null } }
  return $null
}

# ── 端口 80 需管理员；非 admin 降级 8080 ────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($env:CONSOLE_PORT -eq '80' -and -not $isAdmin) {
  $env:CONSOLE_PORT = '8080'
  W-Warn "非管理员无法绑 80 端口，控制台改用 8080。以管理员重跑可恢复 80。"
}

# ════════════════════════════════════════════════════════════════════════════
# [1/7] MySQL
# ════════════════════════════════════════════════════════════════════════════
W-Log "[1/7] MySQL"
$MysqlData = Join-Path $Data 'mysql'; $MysqlSock = Join-Path $Run 'mysql.sock'; $MysqlPid = Join-Path $Run 'mysqld.pid'
$initFlag = Join-Path $Run '.mysql_initialized'
if (-not (Test-Path $initFlag)) {
  W-Log "  首次初始化 MySQL 数据目录..."
  if (Test-Path $MysqlData) { Remove-Item $MysqlData -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $MysqlData | Out-Null
  & $Mysqld --initialize-insecure --datadir="$MysqlData" --console *> $null
  if ($LASTEXITCODE -ne 0) { W-Die "MySQL 初始化失败" }
}
if (-not (Is-PidAlive $MysqlPid)) {
  Start-Bg $Mysqld @("--datadir=$MysqlData","--port=$($env:DB_PORT)","--pid-file=$MysqlPid","--character-set-server=utf8mb4","--collation-server=utf8mb4_general_ci","--local-infile=1","--default-authentication-plugin=mysql_native_password","--socket=$MysqlSock") (Join-Path $Log 'mysql.log') | Out-Null
}
if (-not (Test-Port $env:DB_PORT 60)) { W-Die "MySQL 启动失败，见 $Log\mysql.log" }
if (-not (Test-Path $initFlag)) {
  W-Log "  设置 root 口令并导入 init.sql..."
  $pass = if ($env:SPRING_DATASOURCE_PASSWORD) { $env:SPRING_DATASOURCE_PASSWORD } else { '123456' }
  $sql = @"
ALTER USER 'root'@'localhost' IDENTIFIED BY '$pass';
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '$pass';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
"@
  $sql | & $MysqlCli --socket=$MysqlSock -uroot 2>$null
  Get-Content (Join-Path $BundleRoot 'config\init.sql') -Encoding UTF8 | & $MysqlCli --socket=$MysqlSock -uroot "-p$pass" 2>$null
  New-Item -ItemType File -Path $initFlag | Out-Null
}
W-Log "MySQL 就绪"

# ════════════════════════════════════════════════════════════════════════════
# [2/7] Redis
# ════════════════════════════════════════════════════════════════════════════
W-Log "[2/7] Redis"
$RedisPid = Join-Path $Run 'redis.pid'
if (-not (Is-PidAlive $RedisPid)) {
  Start-Bg $RedisSrv @("--port","$($env:REDIS_EXTERNAL_PORT)","--dir","$Data\redis","--pidfile","$RedisPid","--logfile","$(Join-Path $Log 'redis.log')") (Join-Path $Log 'redis.out') | Out-Null
}
if (-not (Test-Port $env:REDIS_EXTERNAL_PORT 30)) { W-Die "Redis 启动失败" }
W-Log "Redis 就绪"

# ════════════════════════════════════════════════════════════════════════════
# [3/7] MinIO + bucket
# ════════════════════════════════════════════════════════════════════════════
W-Log "[3/7] MinIO"
$MinioPid = Join-Path $Run 'minio.pid'
$ak = if ($env:OBS_AK) { $env:OBS_AK } else { 'minioadmin' }
$sk = if ($env:OBS_SK) { $env:OBS_SK } else { 'minioadmin' }
if (-not (Is-PidAlive $MinioPid)) {
  $env:MINIO_ROOT_USER = $ak; $env:MINIO_ROOT_PASSWORD = $sk
  $p = Start-Bg $MinioBin @('server',"$Data\minio","--address",":$($env:MINIO_API_PORT)","--console-address",":$($env:MINIO_CONSOLE_PORT)") (Join-Path $Log 'minio.log')
  $p.Id | Set-Content $MinioPid
}
if (-not (Wait-Http "http://127.0.0.1:$($env:MINIO_API_PORT)/minio/health/live" 'MinIO' 60)) { W-Die "MinIO 启动失败，见 $Log\minio.log" }
& $McBin alias set local "http://127.0.0.1:$($env:MINIO_API_PORT)" $ak $sk 2>$null
$bucket = if ($env:OBS_BUCKET) { $env:OBS_BUCKET } else { 'agent-builder' }
& $McBin mb -p "local/$bucket" 2>$null
W-Log "MinIO bucket $bucket 就绪"

# ════════════════════════════════════════════════════════════════════════════
# [4/7] studio-manager (Java)
# ════════════════════════════════════════════════════════════════════════════
W-Log "[4/7] studio-manager"
$totalMB = [Math]::Round((Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize/1024)
# 堆计算：Xmx=min(物理内存×0.35, 4096m) 且 Xms 用小初值(512m)让堆按需增长。
# 旧式 -Xms=-Xmx=物理内存×0.6 会一次性 commit 全堆，Windows 提交额度(物理+页面文件)不够时
# 报 errno 1455（页面文件太小）启动即崩；两个 JVM 各 60% 合计更超 31GB 物理内存。
$heapMax = [Math]::Min([Math]::Round($totalMB * 0.35), 4096); $heapMin = 512
$direct = [Math]::Min([Math]::Round($totalMB*0.1), 512)
$MgrPid = Join-Path $Run 'manager.pid'
if (-not (Is-PidAlive $MgrPid)) {
  $ja = @("-Xms${heapMin}m","-Xmx${heapMax}m","-XX:MaxDirectMemorySize=${direct}m","-Dfile.encoding=UTF-8","-jar","$(Join-Path $BundleRoot 'app\manager\studio-manager.jar')","--spring.config.additional-location=file:$BundleRoot\config\","--spring.profiles.active=manager","--logging.config=file:$BundleRoot\config\log4j2-manager.xml")
  $p = Start-Bg (Join-Path $env:JAVA_HOME 'bin\java.exe') $ja (Join-Path $Log 'manager.log'); $p.Id | Set-Content $MgrPid
}
Wait-Http "http://127.0.0.1:$($env:MANAGER_PORT)/health" 'studio-manager' 180 | Out-Null

# ════════════════════════════════════════════════════════════════════════════
# [5/7] studio-service (Java)
# ════════════════════════════════════════════════════════════════════════════
W-Log "[5/7] studio-service"
$SvcPid = Join-Path $Run 'service.pid'
if (-not (Is-PidAlive $SvcPid)) {
  $ja = @("-Xms${heapMin}m","-Xmx${heapMax}m","-XX:MaxDirectMemorySize=${direct}m","-Dfile.encoding=UTF-8","-jar","$(Join-Path $BundleRoot 'app\service\studio-service.jar')","--spring.config.additional-location=file:$BundleRoot\config\","--spring.profiles.active=runtime","--logging.config=file:$BundleRoot\config\log4j2-runtime.xml")
  $p = Start-Bg (Join-Path $env:JAVA_HOME 'bin\java.exe') $ja (Join-Path $Log 'service.log'); $p.Id | Set-Content $SvcPid
}
Wait-Http "http://127.0.0.1:$($env:SERVICE_PORT)/v1/health" 'studio-service' 180 | Out-Null

# ════════════════════════════════════════════════════════════════════════════
# [6/7] studio-runtime (Python)
# ════════════════════════════════════════════════════════════════════════════
W-Log "[6/7] studio-runtime"
$RtPid = Join-Path $Run 'runtime.pid'
$Venv = Join-Path $Run 'venv'; $VenvPy = Join-Path $Venv 'Scripts\python.exe'; $VenvPip = Join-Path $Venv 'Scripts\pip.exe'
$venvFlag = Join-Path $Run '.venv_ready'
if (-not (Test-Path $venvFlag)) {
  W-Log "  首次创建 venv 并安装依赖（约 1-2 分钟）..."
  & $PythonBin -m venv "$Venv" 2>$null
  $wheelsDir = Join-Path $BundleRoot 'deps\wheels'
  # 不用 --no-index：离线 wheel 不全（Phase C best-effort 有缺），--no-index 下任一缺失即整体失败、
  # 一个包都装不上。改为 --find-links（优先本地 wheel）+ aliyun index 兜底补缺；本地命中的走本地（快且离线友好）。
  # 仅当装成功（openjiuwen 可导入）才写 .venv_ready，否则下次启动重试。
  $req = Join-Path $BundleRoot 'app\requirements.txt'
  if (Test-Path $wheelsDir) {
    & $VenvPip install --find-links "$wheelsDir" -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" -r $req 2>&1 | Out-Host
  } else {
    & $VenvPip install -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" -r $req 2>&1 | Out-Host
  }
  $ok = $false
  try { & $VenvPy -c "import openjiuwen" 2>$null; if ($LASTEXITCODE -eq 0) { $ok = $true } } catch {}
  if ($ok) {
    & $VenvPy (Join-Path $BundleRoot 'scripts\runtime_patches.py') 2>&1 | Out-Host
    New-Item -ItemType File -Path $venvFlag | Out-Null
  } else {
    W-Warn "  依赖安装不完整（openjiuwen 不可导入）。不写 .venv_ready，下次启动重试。请检查网络或 deps/wheels 完整性。"
  }
}
if (-not (Is-PidAlive $RtPid)) {
  $pp = "$(Join-Path $Venv 'Lib\site-packages');$(Join-Path $BundleRoot 'app');$(Join-Path $BundleRoot 'app\agent_runtime')"
  if ($env:PYTHONPATH) { $pp = $pp + ';' + $env:PYTHONPATH }
  $env:PYTHONPATH = $pp
  $env:JIUWEN_EXTENSION_PATH = Join-Path $BundleRoot 'app\agent_runtime\extension'
  $env:LOGGING_LOG_PATH = $Log; $env:TGF_LOG_DIR = $Log
  $env:host = '127.0.0.1'; $env:PORT = $env:RUNTIME_PORT
  $p = Start-Bg $VenvPy @('-u',"$(Join-Path $BundleRoot 'app\agent_runtime\EIStart.py')",'--host','0.0.0.0','--port',"$($env:RUNTIME_PORT)") (Join-Path $Log 'runtime.log'); $p.Id | Set-Content $RtPid
}
Wait-Http "http://127.0.0.1:$($env:RUNTIME_PORT)/v1/health" 'studio-runtime' 180 | Out-Null

# ════════════════════════════════════════════════════════════════════════════
# [7/7] console (nginx)
# ════════════════════════════════════════════════════════════════════════════
W-Log "[7/7] console (nginx)"
$NginxPid = Join-Path $Run 'nginx.pid'
New-Item -ItemType Directory -Force -Path (Join-Path $BundleRoot 'temp') | Out-Null
# 用 .NET 读写：ReadAllText 自动剥模板 BOM；WriteAllText(UTF8Encoding $false) 写无 BOM。
#   PS5.1 Set-Content -Encoding UTF8 会加 BOM，nginx 报 "unknown directive ﻿..." 致启动失败。
# 路径必须正斜杠：nginx 把 \t \n 当转义符，会毁掉 D:\task\... 这类 Windows 反斜杠路径。
$tmpl = [System.IO.File]::ReadAllText((Join-Path $BundleRoot 'config\nginx.conf.tmpl'))
$rootFw = $BundleRoot -replace '\\','/'
$conf = "pid $($NginxPid -replace '\\','/');`n" + ($tmpl -replace '@@BUNDLE_ROOT@@', $rootFw -replace '@@CONSOLE_PORT@@', $env:CONSOLE_PORT)
[System.IO.File]::WriteAllText((Join-Path $Run 'nginx.conf'), $conf, (New-Object System.Text.UTF8Encoding $false))
$NginxConfFw = (Join-Path $Run 'nginx.conf') -replace '\\','/'
$NginxPrefixFw = "$rootFw/"
if (Is-PidAlive $NginxPid) {
  W-Log "  nginx 已在运行，重载配置"
  & $NginxBin -s reload -c $NginxConfFw -p $NginxPrefixFw 2>$null
} else {
  # Windows 的 nginx.exe 默认前台运行（不像 Linux 会 daemonize），不能用同步 & 启动：
  # 会阻塞 start.ps1 致后续访问 URL 不显示，且 nginx 成本控制台子进程、窗口关闭即死、
  # stop.ps1 查不到（报"未运行"）。改用 Start-Process 后台拉起为独立进程，nginx 自己
  # 按 conf 的 pid 指令写 run/nginx.pid 供 stop.ps1 读取与停止。路径用正斜杠（-c/-p
  # 命令行参数虽 Windows fopen 接受反斜杠，但统一正斜杠避免 nginx 内部解析歧义）。
  Start-Process -FilePath $NginxBin -ArgumentList @('-c',$NginxConfFw,'-p',$NginxPrefixFw) -WindowStyle Hidden -PassThru | Out-Null
  Start-Sleep -Seconds 1
}
Wait-Http "http://127.0.0.1:$($env:CONSOLE_PORT)/openjiuwen/" 'console' 60 | Out-Null

# ── 完成 ──────────────────────────────────────────────────────────────────────
$consoleUrl = "http://localhost:$($env:CONSOLE_PORT)/openjiuwen/"
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  openJiuwen AgentStudio 已启动" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  控制台 :  $consoleUrl"
Write-Host "  状态   :  .\scripts\status.ps1"
Write-Host "  停止   :  .\scripts\stop.ps1"
Write-Host "  日志   :  .\scripts\logs.ps1 [manager|service|runtime|mysql|redis|minio|nginx]"
Write-Host "================================================================" -ForegroundColor Green
Start-Process $consoleUrl
# URL 作为脚本最后一行输出，确保执行结束时它就在光标正上方
Write-Host ""
Write-Host ">>> 控制台地址: $consoleUrl <<<" -ForegroundColor Cyan
