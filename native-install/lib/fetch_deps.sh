#!/usr/bin/env bash
# fetch_deps.sh — 按 versions.env 下载 Windows+Linux x64 原生依赖，规范化布局到 bundle_template/deps
# 环境变量：VERSIONS_FILE=versions.env 路径  STAGING=bundle_template 目录  CACHE=下载缓存目录
set -euo pipefail

VERSIONS_FILE="${VERSIONS_FILE:-$(cd "$(dirname "$0")/.." && pwd)/versions.env}"
STAGING="${STAGING:?需设置 STAGING}"
CACHE="${CACHE:-$(cd "$(dirname "$0")/.." && pwd)/.cache}"
mkdir -p "$CACHE"
# shellcheck disable=SC1090
set -a; . "$VERSIONS_FILE"; set +a

log(){ echo -e "\033[1;36m[deps]\033[0m $*"; }
die(){ echo -e "\033[1;31m[deps fatal]\033[0m $*"; exit 1; }

# 下载（带缓存 + 可选 SHA256 校验）
# 用法: dl <url> <sha_var_or_empty> <out_file>
dl(){
  local url="$1" sha="$2" out="$3"
  # GitHub 加速镜像（可选）：GITHUB_MIRROR 非空则前缀 github.com 的 URL（如 https://ghfast.top/）
  if [ -n "${GITHUB_MIRROR:-}" ] && [[ "$url" == https://github.com/* ]]; then
    url="${GITHUB_MIRROR}${url}"
  fi
  if [ -f "$out" ] && [ -s "$out" ]; then
    log "  缓存命中: $(basename "$out")"
  else
    log "  下载: $url"
    # --ssl-no-revoke：Windows schannel curl 默认查 CRL/OCSP，连不上吊销服务器抛 CRYPT_E_REVOCATION_OFFLINE (exit 35)。
    # Linux OpenSSL 下为 no-op（默认不查吊销）。跳过吊销仍校验证书链。
    curl -fSL --ssl-no-revoke --retry 3 --retry-delay 5 --connect-timeout 30 --max-time 2400 -o "$out" "$url" || die "下载失败: $url"
  fi
  if [ -n "$sha" ]; then
    local got; got=$(sha256sum "$out" | awk '{print $1}')
    [ "$got" = "$sha" ] || die "SHA256 校验失败: $(basename "$out")  期望=$sha  实际=$got"
    log "  SHA256 OK"
  else
    warn_once "  SHA256 未配置，跳过校验（$(basename "$out")）"
  fi
}
_WARNED=0; warn_once(){ [ $_WARNED -eq 0 ] && echo -e "\033[1;33m[deps]\033[0m $*" && _WARNED=1 || true; }

extract(){ # <archive> <dest>  —— 自动识别 zip/tar.gz/tar.xz
  local arc="$1" dest="$2"; mkdir -p "$dest"; rm -rf "$dest"/* "$dest"/.[!.]* 2>/dev/null || true
  case "$arc" in
    *.zip)     unzip -q -o "$arc" -d "$dest" ;;
    *.tar.gz)  tar -xzf "$arc" -C "$dest" ;;
    *.tar.xz)  tar -xJf "$arc" -C "$dest" ;;
    *) die "未知归档类型: $arc" ;;
  esac
}
# 在解压目录中定位单个文件并放入目标目录（文件名保留）
place_bin(){ # <extracted_root> <binary_name> <dest_dir>
  local root="$1" name="$2" dest="$3"; mkdir -p "$dest"
  local f; f=$(find "$root" -name "$name" -type f 2>/dev/null | head -1)
  [ -n "$f" ] || die "未找到 $name 于 $root"
  cp -f "$f" "$dest/"; chmod +x "$dest/$name" 2>/dev/null || true
  echo "    → $dest/$name"
}

WIN="$STAGING/deps/win"; LIN="$STAGING/deps/linux"
mkdir -p "$WIN" "$LIN" "$STAGING/deps/wheels"

# LINUX_COMPILE_ONLY=1 时仅编译 Linux 侧 redis/nginx（Windows 构建机经 WSL 调本脚本补这两件，
# 其余 win+linux 预编译依赖 fetch_deps.ps1 已就位）。跳过 JRE/MySQL/MinIO/Python 与 win redis/nginx
# 的冗余重处理——既免 unzip/xz 依赖，又避开 /mnt drvfs 上 250MB zip 的慢速重解压。
# build.sh（Linux 构建机）不设此变量，跑全量。
LCO="${LINUX_COMPILE_ONLY:-0}"

###############################################################################
# JRE 17
###############################################################################
if [ "$LCO" -eq 0 ]; then
log "JRE 17"
dl "$JRE17_WIN_URL"   "$JRE17_WIN_SHA256"   "$CACHE/jre17-win.zip"
dl "$JRE17_LINUX_URL" "$JRE17_LINUX_SHA256" "$CACHE/jre17-linux.tar.gz"
extract "$CACHE/jre17-win.zip"   "$CACHE/x-jre17-win"
extract "$CACHE/jre17-linux.tar.gz" "$CACHE/x-jre17-linux"
# JRE 运行需 bin/ + lib/（modules 等），单拷 java.exe 无法启动。整目录拷贝（同 Linux 侧做法）。
rm -rf "$WIN/jre-17"; mkdir -p "$WIN/jre-17"
winJdk=$(find "$CACHE/x-jre17-win" -mindepth 1 -maxdepth 1 -type d | head -1)
[ -n "$winJdk" ] || die "JRE win 解压后未找到顶层目录"
cp -rf "$winJdk"/. "$WIN/jre-17/"
[ -x "$WIN/jre-17/bin/java.exe" ] || die "Windows JRE 缺 java.exe"
# Linux：整个 jdk 目录有用（tools 等），直接整体迁移
rm -rf "$LIN/jre-17"; mkdir -p "$LIN/jre-17"
linJdk=$(find "$CACHE/x-jre17-linux" -mindepth 1 -maxdepth 1 -type d | head -1)
[ -n "$linJdk" ] || die "JRE linux 解压后未找到顶层目录"
cp -rf "$linJdk"/. "$LIN/jre-17/"
[ -x "$LIN/jre-17/bin/java" ] || die "Linux JRE 缺 java"
fi

###############################################################################
# MySQL 8.0
###############################################################################
if [ "$LCO" -eq 0 ]; then
log "MySQL 8.0"
dl "$MYSQL_WIN_URL"   "$MYSQL_WIN_SHA256"   "$CACHE/mysql-win.zip"
dl "$MYSQL_LINUX_URL" "$MYSQL_LINUX_SHA256" "$CACHE/mysql-linux.tar.xz"
extract "$CACHE/mysql-win.zip"   "$CACHE/x-mysql-win"
extract "$CACHE/mysql-linux.tar.xz" "$CACHE/x-mysql-linux"
# mysqld 运行需 share/（errmsg/charset）与 bin/ 下依赖库，整目录拷贝（定位含 bin/ 的目录）。
rm -rf "$WIN/mysql-8.0"; mkdir -p "$WIN/mysql-8.0"
wmb=$(find "$CACHE/x-mysql-win" -mindepth 2 -maxdepth 2 -type d -name bin | head -1)
[ -n "$wmb" ] || die "MySQL win 未找到 bin 目录"
wmb="${wmb%/bin}"; cp -rf "$wmb"/. "$WIN/mysql-8.0/"
[ -x "$WIN/mysql-8.0/bin/mysqld.exe" ] || die "Windows MySQL 缺 mysqld.exe"
rm -rf "$LIN/mysql-8.0"; mkdir -p "$LIN/mysql-8.0"
lmb=$(find "$CACHE/x-mysql-linux" -mindepth 2 -maxdepth 2 -type d -name bin | head -1)
[ -n "$lmb" ] || die "MySQL linux 未找到 bin 目录"
lmb="${lmb%/bin}"; cp -rf "$lmb"/. "$LIN/mysql-8.0/"
[ -x "$LIN/mysql-8.0/bin/mysqld" ] || die "Linux MySQL 缺 mysqld"
fi

###############################################################################
# Redis 7
###############################################################################
log "Redis 7"
# Windows：社区移植版 zip
if [ "$LCO" -eq 0 ]; then
dl "$REDIS_WIN_URL" "$REDIS_WIN_SHA256" "$CACHE/redis-win.zip"
extract "$CACHE/redis-win.zip" "$CACHE/x-redis-win"
# redis-windows 8.x 为 cygwin 构建，redis-server.exe 依赖 cygwin1.dll 等同目录 DLL。
# 定位 redis-server.exe 所在目录，整目录拷到顶层，保证 exe 与依赖 DLL 同级。
rm -rf "$WIN/redis-7"; mkdir -p "$WIN/redis-7"
rsf=$(find "$CACHE/x-redis-win" -name redis-server.exe -type f | head -1)
[ -n "$rsf" ] || die "redis-win.zip 未找到 redis-server.exe"
cp -rf "$(dirname "$rsf")"/. "$WIN/redis-7/"
[ -x "$WIN/redis-7/redis-server.exe" ] || die "Windows Redis 缺 redis-server.exe"
fi
# Linux：Remi el7 预编译 RPM（glibc 2.17，目标 RHEL 系开箱即用）——不再源码编译。
# Windows 构建机由 fetch_deps.ps1 用 bsdtar 直接提取此 RPM，故 WSL（LCO=1）路径跳过；
# Linux 构建机（build.sh 全量，LCO=0）才走此块。
if [ "$LCO" -eq 0 ]; then
dl "$REDIS_LINUX_URL" "$REDIS_LINUX_SHA256" "$CACHE/redis-linux.rpm"
if [ ! -x "$LIN/redis-7/redis-server" ]; then
  rm -rf "$CACHE/x-redis-linux"; mkdir -p "$CACHE/x-redis-linux"
  # RPM 是 cpio 归档：bsdtar（libarchive）可直接解，否则 rpm2cpio|cpio。
  if command -v bsdtar >/dev/null 2>&1; then
    bsdtar -xf "$CACHE/redis-linux.rpm" -C "$CACHE/x-redis-linux" 2>/dev/null
  elif command -v rpm2cpio >/dev/null 2>&1 && command -v cpio >/dev/null 2>&1; then
    (cd "$CACHE/x-redis-linux" && rpm2cpio "$CACHE/redis-linux.rpm" | cpio -idm 2>/dev/null)
  else
    die "解 Redis RPM 需 bsdtar（apt install libarchive-tools）或 rpm2cpio+cpio"
  fi
  mkdir -p "$LIN/redis-7"
  rs=$(find "$CACHE/x-redis-linux" -name redis-server -type f | head -1)
  rc=$(find "$CACHE/x-redis-linux" -name redis-cli -type f | head -1)
  [ -n "$rs" ] || die "Redis RPM 未找到 redis-server"
  cp -f "$rs" "$LIN/redis-7/redis-server"; [ -n "$rc" ] && cp -f "$rc" "$LIN/redis-7/redis-cli"
  chmod +x "$LIN/redis-7"/* 2>/dev/null || true
fi
[ -x "$LIN/redis-7/redis-server" ] || die "Linux Redis 缺 redis-server"
fi

###############################################################################
# Linux 兼容库（centos7 vault，glibc 2.17）—— MySQL/Redis 缺库兜底
###############################################################################
# bundle 进 deps/linux/lib/，start/stop 脚本设 LD_LIBRARY_PATH 指向。目标 RHEL 系自带
# 这些库时 LD_LIBRARY_PATH 优先用 bundle 版也无害（同 glibc2.17 ABI）。
if [ "$LCO" -eq 0 ]; then
log "Linux 兼容库 (ncurses/libaio/numa)"
mkdir -p "$LIN/lib"
# 解 RPM：bsdtar（libarchive）可直接解 cpio，否则 rpm2cpio|cpio。
extract_rpm(){ # <name> <url> <sha> <so_real>...  —— 把 RPM 内 <so_real> 拷成 soname 到 $LIN/lib
  local name="$1" url="$2" sha="$3"; shift 3
  dl "$url" "$sha" "$CACHE/$name.rpm"
  rm -rf "$CACHE/x-$name"; mkdir -p "$CACHE/x-$name"
  if command -v bsdtar >/dev/null 2>&1; then
    bsdtar -xf "$CACHE/$name.rpm" -C "$CACHE/x-$name" 2>/dev/null
  elif command -v rpm2cpio >/dev/null 2>&1 && command -v cpio >/dev/null 2>&1; then
    (cd "$CACHE/x-$name" && rpm2cpio "$CACHE/$name.rpm" | cpio -idm 2>/dev/null)
  else
    die "解 $name RPM 需 bsdtar（apt install libarchive-tools）或 rpm2cpio+cpio"
  fi
  # 拷真实文件改名为 soname（ldd 按 soname 查 libncurses.so.5，而非带版本号的 .5.9）。
  # 入参 "<real>:<soname>"，real 为 RPM 内相对路径基名（find 定位），soname 为目标名。
  local pair real soname f
  for pair in "$@"; do
    real="${pair%%:*}"; soname="${pair##*:}"
    f=$(find "$CACHE/x-$name" -type f -name "$real" | head -1)
    [ -n "$f" ] || { warn_once "  $name 未找到 $real（跳过）"; continue; }
    cp -f "$f" "$LIN/lib/$soname"
  done
}
extract_rpm "ncurses-libs" "$NCURSES_LIBS_URL" "$NCURSES_LIBS_SHA256" \
  "libncurses.so.5.9:libncurses.so.5" "libtinfo.so.5.9:libtinfo.so.5"
extract_rpm "libaio" "$LIBAIO_URL" "$LIBAIO_SHA256" \
  "libaio.so.1.0.1:libaio.so.1"
extract_rpm "numactl-libs" "$NUMACTL_LIBS_URL" "$NUMACTL_LIBS_SHA256" \
  "libnuma.so.1.0.0:libnuma.so.1"
# Remi redis 链 libssl.so.10/libcrypto.so.10（OpenSSL 1.0），EulerOS 2.0 缺，从 centos7 updates 补。
extract_rpm "openssl-libs" "$OPENSSL_LIBS_URL" "$OPENSSL_LIBS_SHA256" \
  "libssl.so.1.0.2k:libssl.so.10" "libcrypto.so.1.0.2k:libcrypto.so.10"
log "  → $(ls "$LIN/lib" 2>/dev/null | tr '\n' ' ')"
fi

###############################################################################
# MinIO + mc
###############################################################################
if [ "$LCO" -eq 0 ]; then
log "MinIO + mc"
mkdir -p "$WIN/minio" "$LIN/minio"
dl "$MINIO_WIN_URL"   "$MINIO_WIN_SHA256"   "$CACHE/minio-win.exe";   cp -f "$CACHE/minio-win.exe"   "$WIN/minio/minio.exe";  chmod +x "$WIN/minio/minio.exe" 2>/dev/null || true
dl "$MC_WIN_URL"      "$MC_WIN_SHA256"      "$CACHE/mc-win.exe";      cp -f "$CACHE/mc-win.exe"      "$WIN/minio/mc.exe";     chmod +x "$WIN/minio/mc.exe"     2>/dev/null || true
dl "$MINIO_LINUX_URL" "$MINIO_LINUX_SHA256" "$CACHE/minio-linux";     cp -f "$CACHE/minio-linux"     "$LIN/minio/minio";      chmod +x "$LIN/minio/minio"
dl "$MC_LINUX_URL"    "$MC_LINUX_SHA256"    "$CACHE/mc-linux";        cp -f "$CACHE/mc-linux"        "$LIN/minio/mc";         chmod +x "$LIN/minio/mc"
fi

###############################################################################
# Python 3.11 (python-build-standalone，自带 pip)
###############################################################################
if [ "$LCO" -eq 0 ]; then
log "Python 3.11"
dl "$PYTHON_WIN_URL"   "$PYTHON_WIN_SHA256"   "$CACHE/python-win.tar.gz"
dl "$PYTHON_LINUX_URL" "$PYTHON_LINUX_SHA256" "$CACHE/python-linux.tar.gz"
extract "$CACHE/python-win.tar.gz"   "$CACHE/x-python-win"
extract "$CACHE/python-linux.tar.gz" "$CACHE/x-python-linux"
# python-build-standalone install_only 解压即 python/ 或 python/python.exe
mkdir -p "$WIN/python-3.11"; rm -rf "$WIN/python-3.11"/*; cp -rf "$CACHE/x-python-win"/python/. "$WIN/python-3.11/" 2>/dev/null || cp -rf "$CACHE/x-python-win"/* "$WIN/python-3.11/"
mkdir -p "$LIN/python-3.11"; rm -rf "$LIN/python-3.11"/*; cp -rf "$CACHE/x-python-linux"/python/. "$LIN/python-3.11/" 2>/dev/null || cp -rf "$CACHE/x-python-linux"/* "$LIN/python-3.11/"
[ -x "$WIN/python-3.11/python.exe" ] || die "Windows Python 缺 python.exe"
[ -x "$LIN/python-3.11/bin/python3" ] || die "Linux Python 缺 python3"
# 验证 pip 可用（python-build-standalone 自带）。Windows .exe 无法在 Linux 构建机运行，
# 仅验 Linux 侧；Windows 侧留待目标机 start.ps1 首启时验证。
"$LIN/python-3.11/bin/python3" -m pip --version >/dev/null 2>&1 || die "Linux Python pip 不可用"
if [ "$(uname -s 2>/dev/null)" != "Linux" ]; then
  "$WIN/python-3.11/python.exe" -m pip --version >/dev/null 2>&1 || die "Windows Python pip 不可用"
fi
fi

###############################################################################
# nginx（Win 官方 zip；Linux 源码编译免 pcre/zlib）
###############################################################################
log "nginx"
if [ "$LCO" -eq 0 ]; then
dl "$NGINX_WIN_URL"   "$NGINX_WIN_SHA256"   "$CACHE/nginx-win.zip"
extract "$CACHE/nginx-win.zip" "$CACHE/x-nginx-win"
mkdir -p "$WIN/nginx"; cp -f "$CACHE/x-nginx-win"/*/nginx.exe "$WIN/nginx/" 2>/dev/null || place_bin "$CACHE/x-nginx-win" nginx.exe "$WIN/nginx"
# mime.types（Windows nginx 自带）
mt=$(find "$CACHE/x-nginx-win" -name mime.types -type f | head -1); [ -n "$mt" ] && cp -f "$mt" "$STAGING/config/mime.types"
fi
# Linux：源码编译（带 gzip+rewrite 模块，静态捆绑 pcre2+zlib）
dl "$NGINX_LINUX_URL" "$NGINX_LINUX_SHA256" "$CACHE/nginx-linux.tar.gz"
if [ ! -x "$LIN/nginx/sbin/nginx" ]; then
  extract "$CACHE/nginx-linux.tar.gz" "$CACHE/x-nginx-linux"
  src=$(find "$CACHE/x-nginx-linux" -maxdepth 1 -name 'nginx-*' -type d | head -1)
  [ -n "$src" ] || die "nginx 源码目录未找到"
  # nginx.conf 用了 gzip 与 if/rewrite 指令（gzip 模块 + rewrite 模块），须带这两模块编译；
  # --with-pcre/--with-zlib 把 pcre2/zlib 源码静态编进 nginx，目标机无需 libpcre/libz 运行时依赖。
  dl "$PCRE2_URL" "$PCRE2_SHA256" "$CACHE/pcre2.tar.gz"
  dl "$ZLIB_URL"  "$ZLIB_SHA256"  "$CACHE/zlib.tar.gz"
  extract "$CACHE/pcre2.tar.gz" "$CACHE/x-pcre2"
  extract "$CACHE/zlib.tar.gz"  "$CACHE/x-zlib"
  pcre2src=$(find "$CACHE/x-pcre2" -maxdepth 1 -name 'pcre2-*' -type d | head -1)
  zlibsrc=$(find "$CACHE/x-zlib"  -maxdepth 1 -name 'zlib-*'  -type d | head -1)
  [ -n "$pcre2src" ] || die "pcre2 源码目录未找到"
  [ -n "$zlibsrc" ] || die "zlib 源码目录未找到"
  log "  编译 nginx（带 gzip+rewrite，静态捆绑 pcre2+zlib，需 gcc/make）..."
  ( cd "$src" && ./configure --prefix="$LIN/nginx" --with-pcre="$pcre2src" --with-zlib="$zlibsrc" --with-cc-opt=-O2 >/dev/null 2>&1 && make -j"$(nproc)" >/dev/null 2>&1 && make install >/dev/null 2>&1 ) || die "nginx 编译失败（确保已装 gcc make）"
fi
[ -x "$LIN/nginx/sbin/nginx" ] || die "Linux nginx 缺 nginx"
# mime.types 回填（Linux 源码版 conf/mime.types）
[ -f "$STAGING/config/mime.types" ] || cp -f "$LIN/nginx/conf/mime.types" "$STAGING/config/mime.types" 2>/dev/null || echo "# mime.types missing" > "$STAGING/config/mime.types"

log "原生依赖下载与规范化完成。"
