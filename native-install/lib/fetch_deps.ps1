# fetch_deps.ps1 — 按 versions.env 下载 Windows+Linux x64 原生依赖到 bundle_template/deps
# Windows 构建机：所有“预编译”依赖（JRE/MySQL/MinIO/mc/Python，两平台）可直接下载；
#   Linux 的 redis 与 nginx 需从源码编译——本脚本优先用 WSL 调用 fetch_deps.sh 完成编译，
#   无 WSL 则跳过并明确告警（请在 Linux 上跑 build.sh 或用 wsl 补齐 deps/linux/redis-7 与 deps/linux/nginx）。
param(
  [string]$VersionsFile,
  [Parameter(Mandatory=$true)][string]$Staging,
  [string]$Cache
)
$ErrorActionPreference = "Stop"
# PS 5.1 的 Invoke-WebRequest 进度条会严重拖慢下载（逐字节渲染），务必关掉。
$ProgressPreference = "SilentlyContinue"
# $PSScriptRoot 在 param() 默认值求值时尚不可靠（实测本文件下为空串，致 Split-Path 报
# "EmptyStringNotAllowed"）。改在体内解析——此时 $PSScriptRoot 必已填充。
if (-not $VersionsFile) { $VersionsFile = Join-Path (Split-Path $PSScriptRoot) 'versions.env' }
if (-not $Cache)         { $Cache = Join-Path (Split-Path $PSScriptRoot) '.cache' }
function D-Log($m){ Write-Host "[deps] $m" -ForegroundColor Cyan }
function D-Warn($m){ Write-Host "[deps] $m" -ForegroundColor Yellow }
function D-Die($m){ Write-Host "[deps fatal] $m" -ForegroundColor Red; exit 1 }

# 读 versions.env（须 -Encoding UTF8：文件无 BOM，PS5.1 默认按 ANSI(GBK) 解码会因全角字符
# 吞换行、错行，导致 GITHUB_MIRROR 等解析不到）
Get-Content $VersionsFile -Encoding UTF8 | ForEach-Object {
  $l=$_.Trim(); if ($l -and -not $l.StartsWith('#') -and $l.Contains('=')) { $kv=$l -split '=',2; Set-Item "Env:$($kv[0].Trim())" $kv[1].Trim() }
}
New-Item -ItemType Directory -Force -Path $Cache | Out-Null
$Win = "$Staging\deps\win"; $Lin = "$Staging\deps\linux"
New-Item -ItemType Directory -Force -Path $Win,$Lin,"$Staging\deps\wheels" | Out-Null

function Download($url, $sha, $out){
  # 可选 GitHub 加速镜像：GITHUB_MIRROR 非空则前缀 github.com 的 URL（如 https://ghfast.top/）
  if ($env:GITHUB_MIRROR -and $url -like 'https://github.com/*') { $url = "$env:GITHUB_MIRROR$url" }
  # 须用嵌套 if 而非 -and：PowerShell 的 -and 不保证短路右侧 cmdlet 调用，
  # Get-Item 在文件不存在时仍会执行，抛 ItemNotFound 叠加 Stop 偏好即致命退出。
  $cached = $false
  if (Test-Path $out -PathType Leaf) { if ((Get-Item $out).Length -gt 0) { $cached = $true } }
  if ($cached) { D-Log "  缓存命中: $(Split-Path $out -Leaf)" }
  else {
    D-Log "  下载: $url"
    # 用 curl.exe（真 curl）。注意 PS5.1 中裸 "curl" 是 Invoke-WebRequest 的别名，须带 .exe。
    # curl 比 IWR 快且对大文件/慢连接更稳；IWR 的 -TimeoutSec 会卡断大文件下载（MySQL 250MB ~25min）。
    $curlExe = Join-Path $env:WINDIR 'System32\curl.exe'
    if (Test-Path $curlExe) {
      & $curlExe -fL --retry 3 --retry-delay 5 --connect-timeout 30 --max-time 2400 -o "$out" "$url"
      if ($LASTEXITCODE -ne 0) { D-Die "下载失败(curl exit=$LASTEXITCODE): $url" }
    } else {
      try { Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing } catch { D-Die "下载失败: $url" }
    }
  }
  if ($sha) {
    $got = (Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
    if ($got -ne $sha.ToLower()) { D-Die "SHA256 校验失败: $(Split-Path $out -Leaf)  期望=$sha  实际=$got" }
    D-Log "  SHA256 OK"
  }
}
function Extract($arc, $dest){
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }; New-Item -ItemType Directory -Force -Path $dest | Out-Null
  # 用 Windows 自带 bsdtar（System32\tar.exe）：GNU tar 会把 "D:\path" 当 rsh 的 host:path。
  $bsdtar = Join-Path $env:WINDIR 'System32\tar.exe'; if (-not (Test-Path $bsdtar)) { $bsdtar = 'tar' }
  switch -Wildcard ($arc) {
    '*.zip'    { Expand-Archive -Path $arc -DestinationPath $dest -Force }
    '*.tar.gz' { & $bsdtar -xzf $arc -C $dest; if ($LASTEXITCODE -ne 0) { D-Die "解压失败: $arc" } }
    '*.tar.xz' { & $bsdtar -xJf $arc -C $dest; if ($LASTEXITCODE -ne 0) { D-Die "解压失败: $arc" } }
    default    { D-Die "未知归档: $arc" }
  }
}
function PlaceBin($root, $name, $destDir){
  New-Item -ItemType Directory -Force -Path $destDir | Out-Null
  $f = Get-ChildItem $root -Recurse -Filter $name -File -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $f) { D-Die "未找到 $name 于 $root" }
  Copy-Item $f.FullName "$destDir\$name" -Force
  Write-Host "    -> $destDir\$name"
}

# ── JRE 17 ───────────────────────────────────────────────────────────────────
D-Log "JRE 17"
Download $env:JRE17_WIN_URL $env:JRE17_WIN_SHA256 "$Cache\jre17-win.zip"
Download $env:JRE17_LINUX_URL $env:JRE17_LINUX_SHA256 "$Cache\jre17-linux.tar.gz"
Extract "$Cache\jre17-win.zip" "$Cache\x-jre17-win"
# JRE 运行需 bin/ + lib/（modules 等），单拷 java.exe 无法启动。整目录拷贝（同 Linux 侧做法）。
$winJdk = Get-ChildItem "$Cache\x-jre17-win" -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$Win\jre-17" | Out-Null
if ($winJdk) { Copy-Item "$($winJdk.FullName)\*" "$Win\jre-17\" -Recurse -Force }
else { D-Die "JRE win 解压后未找到顶层目录" }
Extract "$Cache\jre17-linux.tar.gz" "$Cache\x-jre17-linux"
$linJdk = Get-ChildItem "$Cache\x-jre17-linux" -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$Lin\jre-17" | Out-Null
Copy-Item "$($linJdk.FullName)\*" "$Lin\jre-17\" -Recurse -Force

# ── MySQL 8.0 ────────────────────────────────────────────────────────────────
D-Log "MySQL 8.0"
Download $env:MYSQL_WIN_URL $env:MYSQL_WIN_SHA256 "$Cache\mysql-win.zip"
Download $env:MYSQL_LINUX_URL $env:MYSQL_LINUX_SHA256 "$Cache\mysql-linux.tar.xz"
Extract "$Cache\mysql-win.zip" "$Cache\x-mysql-win"
# mysqld 运行需 share/（errmsg/charset）与 bin/ 下依赖 DLL，整目录拷贝。
$wmb = Get-ChildItem "$Cache\x-mysql-win" -Directory | Where-Object { Test-Path "$($_.FullName)\bin" } | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$Win\mysql-8.0" | Out-Null
if ($wmb) { Copy-Item "$($wmb.FullName)\*" "$Win\mysql-8.0\" -Recurse -Force } else { D-Die "MySQL win 未找到 bin 目录" }
Extract "$Cache\mysql-linux.tar.xz" "$Cache\x-mysql-linux"
$lmb = Get-ChildItem "$Cache\x-mysql-linux" -Directory | Where-Object { Test-Path "$($_.FullName)\bin" } | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$Lin\mysql-8.0" | Out-Null
if ($lmb) { Copy-Item "$($lmb.FullName)\*" "$Lin\mysql-8.0\" -Recurse -Force } else { D-Die "MySQL linux 未找到 bin 目录" }

# ── Redis 7 ──────────────────────────────────────────────────────────────────
D-Log "Redis 7"
Download $env:REDIS_WIN_URL $env:REDIS_WIN_SHA256 "$Cache\redis-win.zip"
Extract "$Cache\redis-win.zip" "$Cache\x-redis-win"
New-Item -ItemType Directory -Force -Path "$Win\redis-7" | Out-Null
# redis-windows 8.x 为 cygwin 构建，redis-server.exe 依赖 cygwin1.dll 等同目录 DLL。
# 定位 redis-server.exe 所在目录，整目录拷到顶层，保证 exe 与依赖 DLL 同级。
$rs = Get-ChildItem "$Cache\x-redis-win" -Recurse -Filter 'redis-server.exe' -File | Select-Object -First 1
if (-not $rs) { D-Die "redis-win.zip 未找到 redis-server.exe" }
Copy-Item "$($rs.DirectoryName)\*" "$Win\redis-7\" -Recurse -Force
if (-not (Test-Path "$Win\redis-7\redis-cli.exe")) {
  $rc = Get-ChildItem "$Cache\x-redis-win" -Recurse -Filter 'redis-cli.exe' -File | Select-Object -First 1
  if ($rc) { Copy-Item $rc.FullName "$Win\redis-7\redis-cli.exe" -Force }
}

# ── MinIO + mc ───────────────────────────────────────────────────────────────
D-Log "MinIO + mc"
New-Item -ItemType Directory -Force -Path "$Win\minio","$Lin\minio" | Out-Null
Download $env:MINIO_WIN_URL $env:MINIO_WIN_SHA256 "$Cache\minio-win.exe";   Copy-Item "$Cache\minio-win.exe" "$Win\minio\minio.exe" -Force
Download $env:MC_WIN_URL $env:MC_WIN_SHA256 "$Cache\mc-win.exe";            Copy-Item "$Cache\mc-win.exe" "$Win\minio\mc.exe" -Force
Download $env:MINIO_LINUX_URL $env:MINIO_LINUX_SHA256 "$Cache\minio-linux"; Copy-Item "$Cache\minio-linux" "$Lin\minio\minio" -Force
Download $env:MC_LINUX_URL $env:MC_LINUX_SHA256 "$Cache\mc-linux";           Copy-Item "$Cache\mc-linux" "$Lin\minio\mc" -Force

# ── Python 3.11 ──────────────────────────────────────────────────────────────
D-Log "Python 3.11"
Download $env:PYTHON_WIN_URL $env:PYTHON_WIN_SHA256 "$Cache\python-win.tar.gz"
Download $env:PYTHON_LINUX_URL $env:PYTHON_LINUX_SHA256 "$Cache\python-linux.tar.gz"
Extract "$Cache\python-win.tar.gz" "$Cache\x-python-win"
New-Item -ItemType Directory -Force -Path "$Win\python-3.11" | Out-Null
$wp = Get-ChildItem "$Cache\x-python-win" -Directory | Where-Object { Test-Path "$($_.FullName)\python.exe" } | Select-Object -First 1
Copy-Item "$($wp.FullName)\*" "$Win\python-3.11\" -Recurse -Force
Extract "$Cache\python-linux.tar.gz" "$Cache\x-python-linux"
$lp = Get-ChildItem "$Cache\x-python-linux" -Directory | Where-Object { Test-Path "$($_.FullName)\bin\python3" } | Select-Object -First 1
New-Item -ItemType Directory -Force -Path "$Lin\python-3.11" | Out-Null
Copy-Item "$($lp.FullName)\*" "$Lin\python-3.11\" -Recurse -Force

# ── nginx（Windows 官方 zip）─────────────────────────────────────────────────
D-Log "nginx"
Download $env:NGINX_WIN_URL $env:NGINX_WIN_SHA256 "$Cache\nginx-win.zip"
Extract "$Cache\nginx-win.zip" "$Cache\x-nginx-win"
New-Item -ItemType Directory -Force -Path "$Win\nginx" | Out-Null
PlaceBin "$Cache\x-nginx-win" "nginx.exe" "$Win\nginx"
$mt = Get-ChildItem "$Cache\x-nginx-win" -Recurse -Filter 'mime.types' | Select-Object -First 1
if ($mt) { Copy-Item $mt.FullName "$Staging\config\mime.types" -Force }

# ── Linux redis/nginx 编译（需 Linux 工具链）──────────────────────────────
# Windows 构建机经 WSL 调 fetch_deps.sh 补 Linux redis/nginx。但很多 Windows 机只有
# docker-desktop 极简 WSL 发行版（无 gcc/make），编译必败——此时告警跳过、不致命，
# 让构建继续产出包（Windows 侧全齐；Linux 侧 redis/nginx 缺，需在 Linux 机跑 build.sh 补）。
D-Log "Linux redis + nginx 编译"
$needRedis = -not (Test-Path "$Lin\redis-7\redis-server")
$needNginx = -not (Test-Path "$Lin\nginx\sbin\nginx")
if ($needRedis -or $needNginx) {
  $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
  $compiled = $false
  if ($wsl) {
    # wsl.exe 会把 localhost NAT 代理警告写 stderr；本脚本 ErrorActionPreference=Stop 下
    # 原生命令写 stderr 即抛 NativeCommandError（连 2>$null 都挡不住），致 gcc 探测与 fetch_deps.sh
    # 调用被 try/catch 误吞 → 误判"无 gcc"。整个 WSL 块临时切 Continue（非终止 stderr 不抛）。
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
      # 枚举已装发行版，挑一个带 gcc 的（避开无工具链的 docker-desktop 极简发行版）。
      # 注意：吃默认 distro 会命中 docker-desktop（无 gcc）→ 必须显式 -d 指定 Ubuntu 等带工具链的发行版。
      $raw = & wsl.exe -l -q 2>$null
      $distros = (($raw | Out-String) -replace "`0","") -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
      # 默认发行版优先（wsl -l -q 首行即默认），其次 Ubuntu*，docker-desktop* 排最后。
      $ordered = $distros | Sort-Object @{ Expression = { if ($_ -like 'docker-desktop*') { 2 } elseif ($_ -like 'Ubuntu*') { 0 } else { 1 } } }
      $wslDistro = $null
      foreach ($d in $ordered) {
        $g = $null
        try { $g = (& wsl.exe -d $d bash -lc 'command -v gcc 2>/dev/null' 2>$null) } catch {}
        if ($g -and $g.ToString().Trim() -ne '') { $wslDistro = $d; break }
      }
      if ($wslDistro) {
        D-Log "  通过 WSL($wslDistro) 调用 fetch_deps.sh 完成 Linux redis/nginx 编译..."
        try {
          # fetch_deps.sh 与本 ps1 同目录（lib/）；versions.env 在 native-install 根。
          $libDir = $PSScriptRoot
          $stagingWin = $Staging -replace '\\','/'
          $wslStaging = (wsl -d $wslDistro wslpath -a "$stagingWin" 2>$null)
          if (-not $wslStaging) { $wslStaging = "/mnt/" + (($stagingWin -replace '^([A-Z]):','/$1'.ToLower()) -replace '\\','/') }
          # drvfs 挂载为小写盘符 /mnt/d（勿 ToUpper）。
          $vf = (wsl -d $wslDistro wslpath -a ($VersionsFile -replace '\\','/'))
          $fs = (wsl -d $wslDistro wslpath -a "$libDir\fetch_deps.sh".Replace('\','/'))
          $bashScript = "VERSIONS_FILE=`"$vf`" STAGING=`"$wslStaging`" LINUX_COMPILE_ONLY=1 bash `"$fs`""
          & wsl.exe -d $wslDistro bash -lc $bashScript
          if ($LASTEXITCODE -eq 0) { $compiled = $true } else { D-Warn "fetch_deps.sh 退出码 $LASTEXITCODE" }
        } catch { D-Warn "WSL 调用异常：$($_.Exception.Message)" }
      } else {
        D-Warn "WSL 各发行版均无 gcc（需在 Ubuntu WSL 内 apt install -y build-essential），跳过 Linux redis/nginx 编译。"
      }
    } finally {
      $ErrorActionPreference = $prevEAP
    }
  } else {
    D-Warn "无 WSL：跳过 Linux redis/nginx 编译。"
  }
  if (-not $compiled) {
    D-Warn "Linux redis/nginx 未就绪。请在 Linux 主机跑 build.sh 补齐 deps/linux/redis-7 与 deps/linux/nginx 后再分发，或装 Ubuntu WSL 发行版后重跑。"
  }
}

D-Log "原生依赖下载完成（Windows 侧全部就绪）。"
