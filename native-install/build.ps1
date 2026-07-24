# build.ps1 — openJiuwen AgentStudio 免容器跨平台包构建（Windows 构建机）
# 用法: .\build.ps1 [-Version <ver>] [-SkipApps] [-SkipDeps] [-SkipWheels]
# 产物: dist\AgentStudio-native-<ver>.zip（Windows + Linux 通用单一交付物）
param(
  [string]$Version,
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
$manifest = @"
openJiuwen AgentStudio — 原生（免容器）运行包
name:    $name
version: $ver
git:     $git
built:   $buildTime

组件产物（从源码构建）:
  studio-manager.jar  <- backend/studio-manager (profile=manager)
  studio-service.jar  <- backend/studio-runtime (profile=runtime, 重命名)
  frontend/dist/hws   <- frontend (pnpm build)
  agent_runtime/ ...  <- agent-runtime + agent_builder 源码

原生依赖版本（详见 versions.env）:
  JRE=$($env:JRE17_VERSION)  MySQL=$($env:MYSQL_VERSION)  Redis=$($env:REDIS_VERSION)  Python=$($env:PYTHON_VERSION)  nginx=$($env:NGINX_VERSION)

启动：
  Linux:   ./scripts/start.sh
  Windows: powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
控制台: http://localhost/openjiuwen/  登录 agent/agent
"@
Set-Content -Path (Join-Path $staging 'MANIFEST.txt') -Value $manifest -Encoding UTF8
Copy-Item (Join-Path $NativeRoot 'versions.env') (Join-Path $staging 'versions.env') -Force

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$pkg = "$name-native-$ver"
# 只产 zip（Windows + Linux 通用）：解压后 start.sh 启动前 chmod +x 补 Linux 执行位，
# 故 zip 不保留 Unix 权限位也无妨。Windows/Linux 系统自带 tar/unzip 均可解 zip。
# 必须用 Python zipfile 生成，**不可用 Compress-Archive**：后者写入的 zip 条目用反斜杠
# 作路径分隔（Windows 习惯），Linux unzip 把反斜杠当文件名字面字符 → 解不出目录树、解压失败。
B-Log "  生成 zip（Windows + Linux 通用，Python zipfile 正斜杠路径）"
$zipPath = Join-Path $dist "$pkg.zip"
$py = @"
import zipfile, os
staging = r"$staging"
out = r"$zipPath"
n = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
    for root, dirs, files in os.walk(staging):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.relpath(full, staging).replace(os.sep, '/')
            z.write(full, arc)
            n += 1
print('wrote %d entries' % n)
"@
$py | py -3 -
B-Log "构建完成："
B-Log "  $zipPath"
B-Log "拷到目标机解压后，Linux 跑 ./scripts/start.sh；Windows 跑 .\scripts\start.ps1"
