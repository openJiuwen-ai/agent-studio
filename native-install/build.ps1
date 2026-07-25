# build.ps1 — openJiuwen AgentStudio 免容器跨平台包构建（Windows 构建机）
# 用法: .\build.ps1 [-Version <ver>] [-Platform <win|linux>] [-SkipApps] [-SkipDeps] [-SkipWheels]
#   -Platform：只打指定平台 zip（win 或 linux）；不传则两个都打。
#   Phase A/B/C 不受 -Platform 影响（仍组装完整跨平台 staging），仅 Phase D 按此决定打几个。
# 产物: dist\AgentStudio-native-<ver>-<windows|linux>.zip
param(
  [string]$Version,
  [ValidatePattern('^(win|linux)?$')][string]$Platform,
  [switch]$SkipApps, [switch]$SkipDeps, [switch]$SkipWheels
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$NativeRoot = $PSScriptRoot
$Workspace = (Resolve-Path (Join-Path $NativeRoot '..')).Path
# 读 versions.env（须 -Encoding UTF8：无 BOM，否则 PS5.1 按 GBK 误读全角字符致错行）
Get-Content (Join-Path $NativeRoot 'versions.env') -Encoding UTF8 | ForEach-Object {
  $l=$_.Trim(); if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $kv=$l -split '=',2; Set-Item "Env:$($kv[0].Trim())" $kv[1].Trim() }
}
$ver = if ($Version) { $Version } else { if ($env:BUNDLE_VERSION) { $env:BUNDLE_VERSION } else { '1.0.0' } }
$name = if ($env:BUNDLE_NAME) { $env:BUNDLE_NAME } else { 'AgentStudio' }
$staging = Join-Path $NativeRoot "build\$name-native-$ver"
$dist = Join-Path $NativeRoot 'dist'

function B-Log($m){ Write-Host "[build] $m" -ForegroundColor Cyan }
function B-Die($m){ Write-Host "[build fatal] $m" -ForegroundColor Red; exit 1 }

B-Log "WORKSPACE=$Workspace  STAGING=$staging  VER=$ver"

# ── 0. 初始化 staging ──────────────────────────────────────────────────────
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item (Join-Path $NativeRoot 'lib\bundle_template') $staging -Recurse -Force
# bundle_template 内容应直接位于 $staging 下（复制的是目录，需展平）
$tmpTpl = Join-Path $staging 'bundle_template'
if (Test-Path $tmpTpl) { Copy-Item "$tmpTpl\*" $staging -Recurse -Force; Remove-Item $tmpTpl -Recurse -Force }

# ── A. 应用产物 ──────────────────────────────────────────────────────────────
if (-not $SkipApps) {
  B-Log "Phase A — 构建应用产物（Maven + pnpm + 复制 runtime 源码）"
  & powershell -ExecutionPolicy Bypass -File (Join-Path $NativeRoot 'lib\build_apps.ps1') -Workspace $Workspace -Staging $staging
  if ($LASTEXITCODE -ne 0) { B-Die "Phase A 失败" }
} else { B-Log "Phase A 跳过（-SkipApps）" }

# ── B. 原生依赖 ──────────────────────────────────────────────────────────────
if (-not $SkipDeps) {
  B-Log "Phase B — 下载并规范化原生依赖（Win+Linux；Linux redis/nginx 经 WSL 编译）"
  & powershell -ExecutionPolicy Bypass -File (Join-Path $NativeRoot 'lib\fetch_deps.ps1') -VersionsFile (Join-Path $NativeRoot 'versions.env') -Staging $staging
  if ($LASTEXITCODE -ne 0) { B-Die "Phase B 失败" }
} else { B-Log "Phase B 跳过（-SkipDeps）" }

# ── C. 离线 Python wheels ──────────────────────────────────────────────────
if (-not $SkipWheels) {
  B-Log "Phase C — 下载 runtime Python 依赖离线 wheel（win + linux）"
  $wheelsDir = Join-Path $staging 'deps\wheels'
  New-Item -ItemType Directory -Force -Path $wheelsDir | Out-Null
  $req = Join-Path $staging 'app\requirements.txt'
  $pip = Get-Command pip -ErrorAction SilentlyContinue
  if (-not $pip) { B-Log "[warn] 未找到 pip，跳过 wheel 下载（目标机需联网安装）" }
  else {
    # pip 把全部日志写到 stderr，PS5.1 Stop 偏好会把原生命令 stderr 转成 NativeCommandError
    # 致命退出（连 2>$null 都挡不住）。临时改 Continue + 2>&1|Out-Null 丢弃，按 $LASTEXITCODE 判成败。
    $ErrorActionPreference = 'Continue'
    B-Log "  win wheel"
    & pip download -r $req -d $wheelsDir -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { B-Log "[warn] win wheel 下载退出码 $LASTEXITCODE（部分包可能缺失，目标机需联网补）" }
    B-Log "  linux wheel"
    & pip download -r $req -d $wheelsDir --platform manylinux2014_x86_64 --only-binary :all: --no-deps -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { B-Log "[warn] linux wheel 下载退出码 $LASTEXITCODE（部分包可能缺失，目标机需联网补）" }
    $ErrorActionPreference = 'Stop'
  }
} else { B-Log "Phase C 跳过（-SkipWheels）" }

# ── D. 组装 + 写 MANIFEST + 打包 ───────────────────────────────────────────
B-Log "Phase D — 写 MANIFEST + 打包"
$git = "unknown"; try { $git = (git -C $Workspace rev-parse --short HEAD 2>$null) } catch {}
$buildTime = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
$platLabel = @{ win = 'Windows x64'; linux = 'Linux x64 (glibc 2.17+)' }
# 决定打哪些平台：$Platform 为空=两个；否则仅指定平台
if ($Platform) { $targets = @($Platform) } else { $targets = @('win','linux') }
# MANIFEST 按平台写一份临时模板（每个包用自己的）；versions.env 两包都要
$manifestBase = @"
openJiuwen AgentStudio — 原生（免容器）运行包 [@PLAT@ 专用]
name:    $name
version: $ver
git:     $git
built:   $buildTime
平台:    @PLATLABEL@
本包仅含本平台原生依赖（对端平台依赖已剔除；MySQL 调试符号 .pdb/.lib 与 mecab
遗留日文编码字典已剔除以瘦身；deps/wheels 仅含本平台 wheel）。

组件产物（从源码构建）:
  studio-manager.jar  <- backend/studio-manager (profile=manager)
  studio-service.jar  <- backend/studio-runtime (profile=runtime, 重命名)
  frontend/dist/hws   <- frontend (pnpm build)
  agent_runtime/ ...  <- agent-runtime + agent_builder 源码

原生依赖版本（详见 versions.env）:
  JRE=$($env:JRE17_VERSION)  MySQL=$($env:MYSQL_VERSION)  Redis=$($env:REDIS_VERSION)  Python=$($env:PYTHON_VERSION)  nginx=$($env:NGINX_VERSION)

启动：
  Windows: powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
  Linux:   ./scripts/start.sh
控制台: http://localhost/openjiuwen/  登录 agent/agent
"@
Copy-Item (Join-Path $NativeRoot 'versions.env') (Join-Path $staging 'versions.env') -Force

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$zipper = Join-Path $NativeRoot 'lib\zip_platform.py'
# 必须用 Python zipfile（不可用 Compress-Archive）：后者写的 zip 条目用反斜杠作路径
# 分隔，Linux unzip 把反斜杠当文件名字面字符 → 解不出目录树。助手用正斜杠 arcname
# + ZIP_DEFLATED，并按平台排除对端依赖/MySQL 冗余/对端 wheel。
foreach ($plat in $targets) {
  $platName = if ($plat -eq 'win') { 'windows' } else { 'linux' }
  # 该包的 MANIFEST（占位替换）
  $m = $manifestBase -replace '@PLAT@', $platName -replace '@PLATLABEL@', $platLabel[$plat]
  Set-Content -Path (Join-Path $staging 'MANIFEST.txt') -Value $m -Encoding UTF8
  $zipPath = Join-Path $dist "$name-native-$ver-$platName.zip"
  B-Log "  生成 $platName zip（选择性排除对端依赖 + MySQL 冗余 + 对端 wheel）"
  & py -3 $zipper "$staging" "$zipPath" $plat
  if ($LASTEXITCODE -ne 0) { B-Die "生成 $platName zip 失败" }
}
B-Log "构建完成："
foreach ($plat in $targets) {
  $platName = if ($plat -eq 'win') { 'windows' } else { 'linux' }
  $zp = Join-Path $dist "$name-native-$ver-$platName.zip"
  $sz = if (Test-Path $zp) { "{0:N1} MB" -f ((Get-Item $zp).Length/1MB) } else { '缺失' }
  B-Log "  $zp  ($sz)"
}
B-Log "拷到目标机解压后，Linux 跑 ./scripts/start.sh；Windows 跑 .\scripts\start.ps1"
