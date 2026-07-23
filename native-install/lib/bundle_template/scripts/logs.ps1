# openJiuwen AgentStudio — 查看日志（Windows PowerShell）
# 用法: .\scripts\logs.ps1 [manager|service|runtime|mysql|redis|minio|nginx|access|error]
param([string]$svc = 'manager')
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$Log = Join-Path $BundleRoot 'logs'
$name = if ($svc -in @('nginx','access','error')) { $svc } else { $svc }
$file = Join-Path $Log "$name.log"
if (-not (Test-Path $file)) {
  Write-Host "日志不存在: $file" -ForegroundColor Yellow
  Write-Host "可选: manager service runtime mysql redis minio nginx access error"
  Get-ChildItem $Log -Filter *.log -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
  exit 1
}
Write-Host "→ Get-Content -Wait $file   (Ctrl+C 退出)"
Get-Content $file -Wait -Tail 100
