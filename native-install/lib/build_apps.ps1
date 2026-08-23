# build_apps.ps1 — 构建应用产物并填入 bundle_template（Windows 构建机，复刻 docker/package.sh）
# 环境变量/参数：WORKSPACE=仓库根  STAGING=bundle_template 目录
param(
  [Parameter(Mandatory=$true)][string]$Workspace,
  [Parameter(Mandatory=$true)][string]$Staging
)
$ErrorActionPreference = "Stop"
function A-Log($m){ Write-Host "[apps] $m" -ForegroundColor Cyan }
function A-Die($m){ Write-Host "[apps fatal] $m" -ForegroundColor Red; exit 1 }

New-Item -ItemType Directory -Force -Path "$Staging\app","$Staging\app\frontend","$Staging\config" | Out-Null

# ── [1] 后端 Maven 打包 ─────────────────────────────────────────────────────
A-Log "[1/4] 后端 Maven 打包 (backend)"
Set-Location "$Workspace\backend"
$mvn = Get-Command mvn -ErrorAction SilentlyContinue
if (-not $mvn) { A-Die "未找到 mvn，请安装 Maven 并加入 PATH" }
# PS 5.1 脚本模式调原生 exe 时，-Dprop=val 形式的参数会被拆成 -Dprop + =val（-Dprop 被 PS 参数绑定
# 吞掉，=val 作为 lifecycle phase 报 "Unknown lifecycle phase"）。必须用数组 splat 让每个元素作为
# 独立参数原样下发；--% 在 -File 模式有坑（实测失败），不可用。
$mvnArgs = @('clean','package','-Dmaven.test.skip=true','-U')
& mvn @mvnArgs
if ($LASTEXITCODE -ne 0) { A-Die "Maven 打包失败" }

A-Log "  复制 studio-manager 产物"
New-Item -ItemType Directory -Force -Path "$Staging\app\manager" | Out-Null
$mgrJar = Get-ChildItem "$Workspace\backend\studio-manager\target\studio-manager-*.jar" | Select-Object -First 1
Copy-Item $mgrJar.FullName "$Staging\app\manager\studio-manager.jar" -Force
# jar 是 thin jar（Main-Class=PropertiesLauncher，依赖在 manifest Class-Path 列为同级 bare 名），
# 必须把 target/lib/*.jar 一并拷到 jar 同级目录，否则 NoClassDefFoundError: org/slf4j/LoggerFactory。
$mgrLib = "$Workspace\backend\studio-manager\target\lib"
if (Test-Path $mgrLib) { Copy-Item "$mgrLib\*" "$Staging\app\manager\" -Force }
else { A-Log "  [warn] studio-manager/target/lib 不存在，依赖缺失将致 NoClassDefFoundError" }
Copy-Item "$Workspace\backend\studio-manager-service\src\main\resources\application-manager.yml" "$Staging\config\" -Force
Copy-Item "$Workspace\backend\studio-manager-service\src\main\resources\log4j2.xml" "$Staging\config\log4j2-manager.xml" -Force

# 注：Java「agent-service」（studio-runtime 模块，端口 31113）已随 commit 51a88020 从代码库删除，
# 新版架构由 Python「studio-builder」（agent_builder/EIBuilder，端口 31015）替代，故不再产出 studio-service.jar。

# ── [2] 前端构建 (pnpm) ──────────────────────────────────────────────────────
A-Log "[2/4] 前端构建 (frontend → dist/hws)"
Set-Location "$Workspace\frontend"
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { A-Log "  安装 pnpm..."; npm install -g pnpm }
& pnpm install --ignore-scripts
if ($LASTEXITCODE -ne 0) { A-Die "pnpm install 失败" }
& pnpm run build
if ($LASTEXITCODE -ne 0) { A-Die "前端构建失败" }
New-Item -ItemType Directory -Force -Path "$Staging\app\frontend\dist" | Out-Null
if (Test-Path "$Staging\app\frontend\dist\hws") { Remove-Item "$Staging\app\frontend\dist\hws" -Recurse -Force }
Copy-Item "$Workspace\frontend\dist\hws" "$Staging\app\frontend\dist\hws" -Recurse -Force

# ── [3] runtime 源码复制 ─────────────────────────────────────────────────────
A-Log "[3/4] runtime(Python) 源码复制"
foreach ($d in 'agent_runtime','jiuwen','agent_builder','tests') {
  if (Test-Path "$Staging\app\$d") { Remove-Item "$Staging\app\$d" -Recurse -Force }
}
Copy-Item "$Workspace\agent-runtime\agent_runtime" "$Staging\app\agent_runtime" -Recurse -Force
Copy-Item "$Workspace\agent-runtime\jiuwen"        "$Staging\app\jiuwen"        -Recurse -Force
Copy-Item "$Workspace\agent_builder"              "$Staging\app\agent_builder" -Recurse -Force
Copy-Item "$Workspace\agent-runtime\tests"        "$Staging\app\tests"        -Recurse -Force

# 共享包：model_service/storage/common_utils 是裸顶级导入（from model_service.../from storage...），
# 靠 PYTHONPATH=app 解析（非 pip 安装）——与 docker/package.sh runtime_copy 对齐，缺失则运行时 ModuleNotFoundError。
A-Log "  共享包 (model_service/storage/common_utils)"
foreach ($d in 'model_service','storage','common_utils') {
  if (Test-Path "$Staging\app\$d") { Remove-Item "$Staging\app\$d" -Recurse -Force }
}
Copy-Item "$Workspace\packages\model_service\model_service" "$Staging\app\model_service" -Recurse -Force
Copy-Item "$Workspace\packages\storage\storage"             "$Staging\app\storage"             -Recurse -Force
Copy-Item "$Workspace\packages\common_utils\common_utils"   "$Staging\app\common_utils"       -Recurse -Force

# 合并 runtime + builder 依赖为单一 requirements.txt（同一 venv 供 EIStart 与 EIBuilder 两服务，
# 按包名去重、runtime 优先；psycopg2 与 psycopg2-binary 是不同包均保留）。
# 无 BOM 写（PS5.1 Set-Content -Encoding UTF8 加 BOM 会破坏 pip 解析首个包名）。
A-Log "  合并 requirements.txt (agent-runtime + agent_builder)"
$mergedReqs = New-Object System.Collections.Generic.List[string]
$seenPkg = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($l in @((Get-Content "$Workspace\agent-runtime\requirements.txt") + (Get-Content "$Workspace\agent_builder\requirements.txt"))) {
  $t = $l.Trim()
  if (-not $t) { continue }
  $pkg = (($t -split '[<>=!~]', 2)[0]).Trim()
  if ($seenPkg.Add($pkg)) { $mergedReqs.Add($t) }
}
[System.IO.File]::WriteAllLines("$Staging\app\requirements.txt", $mergedReqs, (New-Object System.Text.UTF8Encoding $false))

# ── [4] 生成 nginx.conf.tmpl + 复制 init.sql ────────────────────────────────
A-Log "[4/4] 生成 nginx.conf.tmpl + 复制 init.sql"
$srcNginx = "$Workspace\deploy\config\nginx.conf"
if (-not (Test-Path $srcNginx)) { A-Die "未找到 $srcNginx" }
$t = Get-Content $srcNginx -Raw
$t = $t -replace 'server studio-manager:31111','server 127.0.0.1:31111'
$t = $t -replace 'server studio-builder:31015','server 127.0.0.1:31015'
$t = $t -replace '/opt/cloud/wiseagent-nginx/nginx/dist/hws','@@BUNDLE_ROOT@@/app/frontend/dist/hws'
$t = $t -replace '/opt/cloud/wiseagent-nginx/logs','@@BUNDLE_ROOT@@/logs'
$t = $t -replace 'include       mime.types;','include @@BUNDLE_ROOT@@/config/mime.types;'
$t = $t -replace 'listen 80;','listen @@CONSOLE_PORT@@;'
$t = $t -replace 'worker_processes auto;','worker_processes 1;'
$t = $t -replace '(?m)^\s*use epoll;\s*$',''
$t = $t -replace '(?m)^\s*multi_accept on;\s*$',''
# 无 BOM 写：nginx.conf.tmpl 是数据文件，BOM 会被 start 脚本读进 conf 致 nginx "unknown directive ﻿"。
# PS5.1 Set-Content -Encoding UTF8 加 BOM，改用 .NET WriteAllText(UTF8Encoding $false)。
[System.IO.File]::WriteAllText("$Staging\config\nginx.conf.tmpl", $t, (New-Object System.Text.UTF8Encoding $false))
Copy-Item "$Workspace\deploy\init.sql" "$Staging\config\init.sql" -Force
A-Log "应用产物构建完成。"
