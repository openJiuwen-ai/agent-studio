# openJiuwen AgentStudio — 查看日志（Windows PowerShell）
# 用法: .\scripts\logs.ps1 [manager|runtime|builder|mysql|redis|minio|nginx|access|error]
param([string]$svc = 'manager')
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BundleRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$Log = Join-Path $BundleRoot 'logs'
$name = if ($svc -in @('nginx','access','error')) { $svc } else { $svc }
$file = Join-Path $Log "$name.log"
if (-not (Test-Path $file)) {
  Write-Host "日志不存在: $file" -ForegroundColor Yellow
  Write-Host "可选: manager runtime builder mysql redis minio nginx access error"
  Get-ChildItem $Log -Filter *.log -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
  exit 1
}
Write-Host "→ Get-Content -Wait $file   (Ctrl+C 退出)"
# 日志是 UTF-8（含中文），PS5.1 默认 ANSI 解码会乱码，显式 UTF8。
Get-Content $file -Wait -Tail 100 -Encoding UTF8
