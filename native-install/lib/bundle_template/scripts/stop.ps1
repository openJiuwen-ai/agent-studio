# openJiuwen AgentStudio — 原生模式停止全部服务（Windows PowerShell）
[CmdletBinding()] param()
$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path; Set-Location $BundleRoot
$Run = Join-Path $BundleRoot 'run'
$EnvFile = Join-Path $BundleRoot '.env'
if (Test-Path $EnvFile) {
  Get-Content $EnvFile -Encoding UTF8 | ForEach-Object { $l=$_.Trim(); if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $kv=$l -split '=',2; Set-Item "Env:$($kv[0].Trim())" $kv[1].Trim() } }
}
if (-not $env:CONSOLE_PORT) { $env:CONSOLE_PORT='80' }; if (-not $env:DB_PORT){$env:DB_PORT='3306'}; if(-not $env:REDIS_EXTERNAL_PORT){$env:REDIS_EXTERNAL_PORT='6379'}
$Deps = Join-Path $BundleRoot 'deps\win'
$env:PATH = "$(Join-Path $Deps 'mysql-8.0\bin');$(Join-Path $Deps 'redis-7');$(Join-Path $Deps 'nginx');$env:PATH"

function W-Log($m){ Write-Host "[stop] $m" -ForegroundColor Cyan }
function Stop-PidFile($pf, $name){
  if (Test-Path $pf) {
    $p=[int](Get-Content $pf -Raw)
    try {
      $pr = Get-Process -Id $p -ErrorAction Stop
      # taskkill /T 连带杀子进程（Stop-Process 不杀子）；成功停止后也清 pid 文件，
      # 否则下次 start 的 Is-PidAlive 拿到死 pid 虽能判死，但残留文件不整洁。
      & taskkill.exe /F /T /PID $p 2>$null | Out-Null
      Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
      W-Log "$name (pid $p) 已停止"
    } catch { W-Log "$name 未运行（清理 pid）" }
    Remove-Item $pf -Force -ErrorAction SilentlyContinue
  } else { W-Log "$name 无 pid 文件" }
}
# 杀所有本包 python（路径在 BundleRoot 下）。runtime 用 multiprocessing-fork 起 worker，
# 父进程被杀后 worker 成孤儿仍占 31014（Windows 套接字继承：netstat 报死掉的父 pid）。
# 按路径杀能兜底清掉孤儿 worker，且不波及用户机器上其它 python。
function Stop-BundlePython($label){
  $ps = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$BundleRoot\*" }
  foreach($pr in $ps){ try { Stop-Process -Id $pr.Id -Force -ErrorAction SilentlyContinue } catch {} }
  if($ps.Count -gt 0){ W-Log "  清理 $label 残留 python $($ps.Count) 个（含 multiprocessing worker）" }
}
# 按进程镜像路径杀本包 nginx 的兜底。旧版 start.ps1 前台启动 nginx + stop 失败后
# Remove-Item 了 pid 文件，会留下无 pid 文件的孤儿 nginx（-s stop 与 Stop-PidFile 都
# 读 pid 文件、命中不了）。按 nginx.exe 路径在本包下杀，兜底清孤儿，不波及系统其它 nginx。
function Stop-BundleNginx{
  $ps = Get-Process nginx -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$BundleRoot\*" }
  foreach($pr in $ps){ try { Stop-Process -Id $pr.Id -Force -ErrorAction SilentlyContinue } catch {} }
  if($ps.Count -gt 0){ W-Log "  清理残留 nginx $($ps.Count) 个（无 pid 文件的孤儿 master/worker）" }
}

W-Log "停止 console (nginx)..."
$NginxBin = Join-Path $Deps 'nginx\nginx.exe'
# -c/-p 用正斜杠路径（与 start.ps1 一致；nginx 读 conf 的 pid 指令定位 master pid 发信号）。
# start.ps1 现在用 Start-Process 后台拉 nginx 为独立进程并写 run/nginx.pid，故 -s stop 能命中；
# Stop-PidFile 的 taskkill /T 再兜底杀 master+worker。
$NginxConfFw = (Join-Path $Run 'nginx.conf') -replace '\\','/'
$NginxPrefixFw = "$BundleRoot" -replace '\\','/'
& $NginxBin -s stop -c $NginxConfFw -p "$NginxPrefixFw/" 2>$null
Stop-PidFile (Join-Path $Run 'nginx.pid') 'nginx'
Stop-BundleNginx   # 兜底清无 pid 文件的孤儿 nginx

W-Log "停止 studio-builder..."; Stop-PidFile (Join-Path $Run 'builder.pid') 'builder'
W-Log "停止 studio-runtime..."; Stop-PidFile (Join-Path $Run 'runtime.pid') 'runtime'; Stop-BundlePython 'runtime'
W-Log "停止 studio-manager..."; Stop-PidFile (Join-Path $Run 'manager.pid') 'manager'
W-Log "停止 MinIO...";         Stop-PidFile (Join-Path $Run 'minio.pid') 'minio'

W-Log "停止 Redis..."
& (Join-Path $Deps 'redis-7\redis-cli.exe') -p $env:REDIS_EXTERNAL_PORT shutdown nosave 2>$null
Stop-PidFile (Join-Path $Run 'redis.pid') 'redis'

W-Log "停止 MySQL..."
$pass = if ($env:SPRING_DATASOURCE_PASSWORD) { $env:SPRING_DATASOURCE_PASSWORD } else { '123456' }
& (Join-Path $Deps 'mysql-8.0\bin\mysqladmin.exe') --socket="$(Join-Path $Run 'mysql.sock')" -uroot "-p$pass" shutdown 2>$null
Stop-PidFile (Join-Path $Run 'mysqld.pid') 'mysqld'
W-Log "完成。"
