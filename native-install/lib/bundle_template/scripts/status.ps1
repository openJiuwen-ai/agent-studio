# openJiuwen AgentStudio — 原生模式状态查看（Windows PowerShell）
[CmdletBinding()] param()
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path; Set-Location $BundleRoot
$Run = Join-Path $BundleRoot 'run'
$EnvFile = Join-Path $BundleRoot '.env'
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object { $l=$_.Trim(); if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $kv=$l -split '=',2; Set-Item "Env:$($kv[0].Trim())" $kv[1].Trim() } }
}
if (-not $env:CONSOLE_PORT){$env:CONSOLE_PORT='80'};if(-not $env:DB_PORT){$env:DB_PORT='3306'};if(-not $env:REDIS_EXTERNAL_PORT){$env:REDIS_EXTERNAL_PORT='6379'}
if(-not $env:MINIO_API_PORT){$env:MINIO_API_PORT='9000'};if(-not $env:MANAGER_PORT){$env:MANAGER_PORT='31111'};if(-not $env:SERVICE_PORT){$env:SERVICE_PORT='31113'};if(-not $env:RUNTIME_PORT){$env:RUNTIME_PORT='31014'}

function IsAlive($pf){ if (Test-Path $pf) { $p=[int](Get-Content $pf -Raw); try { Get-Process -Id $p -ErrorAction Stop | Out-Null; return $p } catch { return $null } }; return $null }
function PortOk($port){ try { $c=New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1',[int]$port); $c.Close(); return $true } catch { return $false } }
function HttpOk($url){ try { $r=Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3; return ($r.StatusCode -lt 500) } catch { return $false } }
function Row($n,$proc,$health,$pid){ "{0,-12} {1,-12} {2,-12} {3}" -f $n,$proc,$health,$pid }

Write-Host ("{0,-12} {1,-12} {2,-12} {3}" -f 'SERVICE','PROC','HEALTH','PID')
$services = @(
  @{n='mysql';  pf='mysqld.pid'; kind='port'; tgt=$env:DB_PORT},
  @{n='redis';  pf='redis.pid';  kind='port'; tgt=$env:REDIS_EXTERNAL_PORT},
  @{n='minio';  pf='minio.pid';  kind='http'; tgt="http://127.0.0.1:$($env:MINIO_API_PORT)/minio/health/live"},
  @{n='manager';pf='manager.pid';kind='http'; tgt="http://127.0.0.1:$($env:MANAGER_PORT)/health"},
  @{n='service';pf='service.pid';kind='http'; tgt="http://127.0.0.1:$($env:SERVICE_PORT)/v1/health"},
  @{n='runtime';pf='runtime.pid';kind='http';tgt="http://127.0.0.1:$($env:RUNTIME_PORT)/v1/health"},
  @{n='console';pf='nginx.pid'; kind='http'; tgt="http://127.0.0.1:$($env:CONSOLE_PORT)/openjiuwen/"}
)
foreach ($s in $services) {
  $pf = Join-Path $Run $s.pf
  $p = IsAlive $pf
  $proc  = if ($p) { 'RUNNING' } else { 'DOWN' }
  $hret = if ($s.kind -eq 'http') { HttpOk $s.tgt } else { PortOk $s.tgt }
  $health = if ($hret) { 'RUNNING' } else { 'DOWN' }
  if ($proc -eq 'RUNNING') { $proc = $proc -replace 'RUNNING','RUNNING' }
  $color = if ($proc -eq 'RUNNING' -and $health -eq 'RUNNING') { 'Green' } else { 'Red' }
  Write-Host (Row $s.n $proc $health $(if($p){"pid=$p"}else{'no-pid'})) -ForegroundColor $color
}
Write-Host ""
Write-Host "控制台: http://localhost:$($env:CONSOLE_PORT)/openjiuwen/   登录 agent/agent"
