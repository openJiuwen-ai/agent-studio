# build.ps1 — openJiuwen AgentStudio 免容器跨平台包构建（Windows 构建机）
# 用法: .\build.ps1 [-Version <ver>] [-Platform <win|linux>] [-SkipApps] [-SkipDeps] [-SkipWheels]
#   [-SeedDeps <dir>] [-Workspace <repo根>]
#   -Platform：只打指定平台 zip（win 或 linux）；不传则两个都打。
#   Phase A/B/C 不受 -Platform 影响（仍组装完整跨平台 staging），仅 Phase D 按此决定打几个。
#   -SeedDeps <dir>：复用已有包/构建目录的 deps\（跳过下载与 WSL 编译），dir 形如某次 STAGING 或解压后的包根。
#   -Workspace <repo根>：应用源码（backend/frontend/agent-runtime/packages…）所在仓库根。
#       默认是 native-install 的上级目录（worktree 场景需显式指定主仓库，避免打包过期 checkout）。
# 产物: dist\AgentStudio-native-<ver>-<windows|linux>.zip
param(
  [string]$Version,
  [ValidatePattern('^(win|linux)?$')][string]$Platform,
  [switch]$SkipApps, [switch]$SkipDeps, [switch]$SkipWheels,
  [string]$SeedDeps,
  [string]$Workspace
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$NativeRoot = $PSScriptRoot
if (-not $Workspace) { $Workspace = (Resolve-Path (Join-Path $NativeRoot '..')).Path }
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
  if ($SeedDeps) {
    # 复用已有 deps（免重新下载/WSL 编译）：复制 seed 的 deps\ 到 staging，跳过 fetch_deps。
    $seedDeps = Join-Path $SeedDeps 'deps'
    if (-not (Test-Path $seedDeps)) { B-Die "-SeedDeps 目录下无 deps\（给出 STAGING 或解压后的包根）: $SeedDeps" }
    B-Log "Phase B — 复用 -SeedDeps 的 deps\（$SeedDeps）"
    New-Item -ItemType Directory -Force -Path (Join-Path $staging 'deps') | Out-Null
    Copy-Item (Join-Path $seedDeps 'win') (Join-Path $staging 'deps\win') -Recurse -Force
    Copy-Item (Join-Path $seedDeps 'linux') (Join-Path $staging 'deps\linux') -Recurse -Force
    if (Test-Path (Join-Path $seedDeps 'wheels')) { Copy-Item (Join-Path $seedDeps 'wheels') (Join-Path $staging 'deps\wheels') -Recurse -Force }
    # seed 自带 mime.types 时补上（Windows nginx 从 config\mime.types 引用）。多路径兜底：
    # seed/config/mime.types（已打过的包）或 seed 的 nginx 依赖（deps/win/nginx/mime.types /
    # deps/linux/nginx/conf/mime.types，fetch_deps 的放置源）。任一命中即拷到 staging/config。
    $seedMime = @(
      (Join-Path $SeedDeps 'config\mime.types'),
      (Join-Path $SeedDeps 'deps\win\nginx\mime.types'),
      (Join-Path $SeedDeps 'deps\linux\nginx\conf\mime.types')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($seedMime) { Copy-Item $seedMime (Join-Path $staging 'config\mime.types') -Force }
  } else {
    B-Log "Phase B — 下载并规范化原生依赖（Win+Linux；Linux redis/nginx 经 WSL 编译）"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $NativeRoot 'lib\fetch_deps.ps1') -VersionsFile (Join-Path $NativeRoot 'versions.env') -Staging $staging
    if ($LASTEXITCODE -ne 0) { B-Die "Phase B 失败" }
  }
} else { B-Log "Phase B 跳过（-SkipDeps）" }

# ── C. 离线 Python wheels ──────────────────────────────────────────────────
if (-not $SkipWheels) {
  B-Log "Phase C — 下载 runtime Python 依赖离线 wheel（win+linux，均按 python 3.11）"
  $wheelsDir = Join-Path $staging 'deps\wheels'
  New-Item -ItemType Directory -Force -Path $wheelsDir | Out-Null
  # 每次全新下载（requirements 可能跨版本变更；-SeedDeps 复用的 wheel 不保留，避免旧版本混入增大包体）
  if (Test-Path $wheelsDir) { Remove-Item $wheelsDir -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $wheelsDir | Out-Null
  $req = Join-Path $staging 'app\requirements.txt'
  # 关键：必须是 cp311 的二进制 wheel（runtime 用内置 python 3.11）。
  # 早期版本用构建机系统 pip（cp312）下载 → 目标机 3.11 pip 跳过 cp312 wheel → 离线首启仍联网补包。
  # 修法：Windows 侧直接调内置 python-3.11 的 pip；跨平台侧用 --python-version/--implementation/--abi 指定 cp311。
  $py311 = Join-Path $staging 'deps\win\python-3.11\python.exe'
  $pip = if (Test-Path $py311) { $py311 } else { (Get-Command pip -ErrorAction SilentlyContinue).Source }
  if (-not $pip) { B-Log "[warn] 未找到 pip，跳过 wheel 下载（目标机需联网安装）" }
  else {
    # pip 把全部日志写到 stderr，PS5.1 Stop 偏好会把原生命令 stderr 转成 NativeCommandError
    # 致命退出（连 2>$null 都挡不住）。临时改 Continue + 2>&1|Out-Null 丢弃，按 $LASTEXITCODE 判成败。
    $ErrorActionPreference = 'Continue'
    B-Log "  win wheel (内置 python-3.11: $pip)"
    if ($pip.EndsWith('\python.exe')) {
      & $pip -m pip download -r $req -d $wheelsDir -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" 2>&1 | Out-Null
    } else {
      & pip download -r $req -d $wheelsDir -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" 2>&1 | Out-Null
    }
    if ($LASTEXITCODE -ne 0) { B-Log "[warn] win wheel 下载退出码 $LASTEXITCODE（部分包可能缺失，目标机需联网补）" }
    B-Log "  linux wheel (manylinux2014, cp311)"
    & pip download -r $req -d $wheelsDir --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary :all: --no-deps -i "https://mirrors.aliyun.com/pypi/simple/" --trusted-host "mirrors.aliyun.com" 2>&1 | Out-Null
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
  studio-manager.jar  <- backend/studio-manager (profile=manager, 端口 31111)
  frontend/dist/hws   <- frontend (pnpm build, nginx 托管)
  agent_runtime/jiuwen/agent_builder <- Python 源码（runtime 31014 / builder 31015 两服务）
  model_service/storage/common_utils <- packages/ 共享包（PYTHONPATH=app 非 pip 安装）

原生依赖版本（详见 versions.env）:
  JRE=$($env:JRE17_VERSION)  MySQL=$($env:MYSQL_VERSION)  Redis=$($env:REDIS_VERSION)  Python=$($env:PYTHON_VERSION)  nginx=$($env:NGINX_VERSION)

启动：
  Windows: powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
  Linux:   ./scripts/start.sh
控制台: http://localhost/openjiuwen/
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
