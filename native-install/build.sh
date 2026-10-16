#!/usr/bin/env bash
# build.sh — openJiuwen AgentStudio 免容器包构建（Linux 构建机；x86_64 与 aarch64 单入口）
# 用法: ./build.sh [-v 版本] [--arch x86|arm64|all] [--platform win|linux] [--skip-apps]
#         [--skip-deps] [--skip-wheels] [--seed-deps <dir>] [--seed-apps <dir>] [--workspace <repo根>]
#   --arch x86（默认）：产出 Windows x64 + Linux x64 双平台包（推荐主路径）。
#   --arch arm64：产出 Linux arm64 单平台包。应用产物（jar/前端/源码/requirements，架构
#       无关）复用同版本 x86 staging——没有则现场构建；仅重建 aarch64 侧 deps/linux 与
#       deps/wheels。前置：Docker 且支持 linux/arm64（`docker buildx ls` 应含 linux/arm64；
#       Docker Desktop 自带 QEMU/binfmt，Windows 构建机用 Git Bash 运行本脚本）。
#   --arch all：先产 x86 双平台包，再产 arm64 包（应用产物只构建一次）。
#   --platform：仅对 x86 包生效（win 或 linux）；不传则两个都打。arm64 恒为 linux 单包。
#   --skip-apps / --skip-deps / --skip-wheels：跳过对应阶段（两架构各自生效）。
#   --seed-deps <dir>：x86 复用已有 deps/（跳过下载/编译），dir 形如某次 STAGING 或解压后的包根。
#   --seed-apps <dir>：arm64 复用指定目录的应用产物与模板（默认同版本 x86 staging），须含 app/ 与 scripts/。
#   --workspace <repo根>：应用源码（backend/frontend/agent-runtime/packages…）所在仓库根。
#       默认是 native-install 的上级目录（worktree 场景需显式指定主仓库，避免打包过期 checkout）。
# 产物: dist/AgentStudio-native-<ver>-<windows|linux|linux-arm64>.zip
# arm64 与 x86 路径的差异（MySQL 全量包裁剪、Redis/nginx 源码编译、glibc 2.28 基线等）
# 详见 versions.arm64.env 头部注释。
set -euo pipefail
cd "$(dirname "$0")"
NATIVE_ROOT="$(pwd)"
WORKSPACE="$(cd "$NATIVE_ROOT/.." && pwd)"
# 注意：MSYS_NO_PATHCONV/MSYS2_ARG_CONV_EXCL 不能全局 export——那会禁用 MSYS 对原生工具
# （curl/tar 等）的 POSIX→Windows 路径转换，curl -o /d/... 将写到不存在的 "\d\..."。
# 故仅在 docker 调用处按命令前缀注入（防容器挂载参数与脚本参数被改写）。
# shellcheck disable=SC1090
set -a; . "$NATIVE_ROOT/versions.env"; set +a

ARCH="x86"; VER=""; PLATFORM=""; SKIP_APPS=0; SKIP_DEPS=0; SKIP_WHEELS=0; SEED_DEPS=""; SEED_APPS=""
while [ $# -gt 0 ]; do case "$1" in
  -v) VER="$2"; shift 2;;
  --arch) ARCH="$2"; shift 2;;
  --platform) PLATFORM="$2"; shift 2;;
  --skip-apps) SKIP_APPS=1; shift;;
  --skip-deps) SKIP_DEPS=1; shift;;
  --skip-wheels) SKIP_WHEELS=1; shift;;
  --seed-deps) SEED_DEPS="$2"; shift 2;;
  --seed-apps) SEED_APPS="$2"; shift 2;;
  --workspace) WORKSPACE="$2"; shift 2;;
  *) echo "未知参数: $1"; exit 2;;
esac; done
case "$ARCH" in
  x86|arm64|all) : ;;
  *) echo "--arch 仅支持 x86|arm64|all，得到: $ARCH"; exit 2;;
esac
case "$PLATFORM" in
  "") : ;; # 空=两个都打
  win|linux) : ;;
  *) echo "--platform 仅支持 win 或 linux，得到: $PLATFORM"; exit 2;;
esac

VER="${VER:-${BUNDLE_VERSION:-1.0.0}}"; NAME="${BUNDLE_NAME:-AgentStudio}"
STAGING="$NATIVE_ROOT/build/${NAME}-native-${VER}"            # x86 跨平台 staging（win+linux x64）
STAGING_ARM="$NATIVE_ROOT/build/${NAME}-native-${VER}-arm64"  # arm64 staging
CACHE_ARM="$NATIVE_ROOT/.cache-arm64"
LIN="$STAGING_ARM/deps/linux"
DIST="$NATIVE_ROOT/dist"

LOG_TAG="build"
log(){ echo -e "\033[1;36m[${LOG_TAG}]\033[0m $*"; }
die(){ echo -e "\033[1;31m[${LOG_TAG} fatal]\033[0m $*" >&2; exit 1; }

# ════════════════ arm64 专用工具（x86 阶段不使用）════════════════
# MSYS(Git Bash) → Docker Desktop 挂载路径：/d/foo → D:/foo（docker -v 接受正斜杠盘符风格）
to_docker_vol(){
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      local p="$1"
      if [[ "$p" =~ ^/([a-zA-Z])/(.*)$ ]]; then echo "${BASH_REMATCH[1]^}:/${BASH_REMATCH[2]}"; else echo "$p"; fi ;;
    *) echo "$1" ;;
  esac
}
# 解档工具（tar.gz/tar.xz）：MSYS 用 System32 bsdtar；Linux 用 GNU tar 即可。
# RPM 是 cpio 归档、GNU tar 不认——其提取走 extract_rpm 的 bsdtar/rpm2cpio 回退链。
TAR_BIN="tar"
if [ -x /c/Windows/System32/tar.exe ]; then TAR_BIN=/c/Windows/System32/tar.exe; fi

# 下载（GitHub 自动走 GITHUB_MIRROR；大文件多并发分块——MySQL 官方 CDN 单连接限速 ~80KB/s）
# 用法: dl <url> <out> [并发数，默认8] [sha256，可选——非空则强校验]
# --ssl-no-revoke：Windows Schannel curl 查不到 CRL/OCSP 吊销服务器时 exit 35（同
# fetch_deps.sh）；Linux OpenSSL 下为 no-op（默认不查吊销，仍校验证书链）。
dl(){
  local url="$1" out="$2" conns="${3:-8}" sha="${4:-}"
  case "$url" in https://github.com/*) [ -n "${GITHUB_MIRROR:-}" ] && url="${GITHUB_MIRROR}${url}" ;; esac
  # 探测 Content-Length（字节）；失败或无长度输出 0
  probe_size(){
    local v
    v=$(curl -sIL --ssl-no-revoke --connect-timeout 20 "$url" 2>/dev/null | tr -d '\r' \
        | awk 'tolower($1)=="content-length:"{v=$2} END{print v+0}') || v=0
    echo "$v"
  }
  # 缓存命中校验大小与可选 SHA256：单连接中断留下的半成品不能误判命中——否则错误
  # 推迟到解压阶段才暴露，只能手删 .cache-arm64。探测不到大小时仅校验 SHA256。
  local size=0 att
  if [ -s "$out" ]; then
    size=$(probe_size)
    if { [ "$size" -eq 0 ] || [ "$(wc -c < "$out")" -eq "$size" ]; } && sha256_ok "$out" "$sha"; then
      log "  缓存命中: $(basename "$out")"; return 0
    fi
    log "  缓存大小/校验不符，删除重下: $(basename "$out")"
    rm -f "$out"
  fi
  # 大小探测带重试：DNS/网络瞬时抖动（curl exit 6 等）在 pipefail 下会直接杀脚本
  for att in 1 2 3; do
    size=$(probe_size)
    [ "$size" -gt 0 ] && break
    sleep 3
  done
  [ "$size" -gt 0 ] || die "无法获取文件大小（网络/DNS 波动，可重跑续传）: $url"
  log "  下载: $url"
  if [ "$size" -lt 33554432 ] || [ "$conns" -le 1 ]; then
    curl -fL --ssl-no-revoke --retry 3 --retry-delay 5 --connect-timeout 30 -o "$out" "$url" || die "下载失败: $url"
  else
    # Range 支持探测：代理类镜像（如 ghfast.top）常不支持分段 → 自动回退单连接。
    # 注意 curl 传输出错时 -w 仍会打印 http_code，不能再用 `|| echo 000`（会拼成 "206000"）。
    rc=$(curl -s --ssl-no-revoke -o /dev/null -w '%{http_code}' --connect-timeout 30 -r 0-1023 "$url" 2>/dev/null || true)
    if [ "$rc" != "206" ]; then
      log "  [hint] 该源不支持 Range(HTTP $rc)，回退单连接"
      curl -fL --ssl-no-revoke --retry 3 --retry-delay 5 --connect-timeout 30 -o "$out" "$url" || die "下载失败: $url"
    else
      local chunk=$(( (size + conns - 1) / conns )) i s e pids=()
      rm -f "$out".part*
      for ((i=0; i<conns; i++)); do
        s=$((i*chunk)); e=$((s+chunk-1)); [ "$e" -ge "$size" ] && e=$((size-1)); [ "$s" -ge "$size" ] && break
        curl -fs --ssl-no-revoke --retry 3 --retry-delay 2 --connect-timeout 30 -r "$s-$e" -o "$out.part$i" "$url" &
        pids+=($!)
      done
      for p in "${pids[@]}"; do wait "$p" || die "分块下载失败: $url（重跑续传）"; done
      : > "$out"
      for ((i=0; i<conns; i++)); do [ -f "$out.part$i" ] && cat "$out.part$i" >> "$out"; done
      rm -f "$out".part*
    fi
  fi
  [ "$(wc -c < "$out")" -eq "$size" ] || die "大小校验失败: $(basename "$out") 期望=$size 实际=$(wc -c < "$out")"
  sha256_ok "$out" "$sha" || die "SHA256 校验失败: $(basename "$out")"
}

# 可选 SHA256 校验：期望值为空则跳过（versions.arm64.env 各 *_SHA256 默认留空，填上即强校验）
sha256_ok(){
  [ -n "$2" ] || return 0
  local got; got=$(sha256sum "$1" | cut -d' ' -f1)
  [ "$got" = "$2" ]
}

log "WORKSPACE=$WORKSPACE  STAGING=$STAGING  ARCH=$ARCH  VER=$VER"

# ════════════════ x86 流水线（Windows x64 + Linux x64 双平台包）════════════════
if [ "$ARCH" != "arm64" ]; then
  [ -z "$PLATFORM" ] || log "--platform=$PLATFORM 仅影响 x86 包的打包目标"
  [ -z "$SEED_APPS" ] || log "--seed-apps 仅对 --arch arm64 有效，已忽略"

  # ── 0. 初始化 staging（从 bundle_template 复制骨架）───────────────────────
  # --skip-apps 且已有应用产物时保留 staging（复用 app/，--arch all 免二次构建应用）；
  # 否则全新初始化。注：旧版无条件 rm -rf，--skip-apps 的复用场景会被清掉应用产物。
  if [ $SKIP_APPS -eq 1 ] && [ -f "$STAGING/app/requirements.txt" ]; then
    log "Phase 0 — 保留已有 staging（--skip-apps 复用应用产物）：$STAGING"
  else
    rm -rf "$STAGING"; mkdir -p "$STAGING"
    cp -a "$NATIVE_ROOT/lib/bundle_template/." "$STAGING/"
    chmod +x "$STAGING/scripts/"*.sh "$STAGING/scripts/runtime_patches.py" 2>/dev/null || true
  fi
  export WORKSPACE STAGING

  # ── A. 应用产物 ──────────────────────────────────────────────────────────────
  if [ $SKIP_APPS -eq 0 ]; then
    log "Phase A — 构建应用产物（Maven + pnpm + 复制 runtime 源码）"
    bash "$NATIVE_ROOT/lib/build_apps.sh"
  else
    log "Phase A 跳过（--skip-apps）"
  fi

  # ── B. 原生依赖 ──────────────────────────────────────────────────────────────
  if [ $SKIP_DEPS -eq 0 ]; then
    if [ -n "$SEED_DEPS" ]; then
      # 复用已有 deps（免重新下载/编译）：复制 seed 的 deps/ 到 staging，跳过 fetch_deps。
      if [ ! -d "$SEED_DEPS/deps" ]; then die "--seed-deps 目录下无 deps/（给出 STAGING 或解压后的包根）: $SEED_DEPS"; fi
      log "Phase B — 复用 --seed-deps 的 deps/（$SEED_DEPS）"
      mkdir -p "$STAGING/deps"
      cp -a "$SEED_DEPS/deps/win" "$STAGING/deps/win"
      cp -a "$SEED_DEPS/deps/linux" "$STAGING/deps/linux"
      [ -d "$SEED_DEPS/deps/wheels" ] && cp -a "$SEED_DEPS/deps/wheels" "$STAGING/deps/wheels"
      # seed 自带 mime.types 时补上（Windows nginx 从 STAGING/config/mime.types 引用）。多路径兜底：
      # seed/config/mime.types（已打过的包）或 seed 的 nginx 依赖（deps/win/nginx/mime.types /
      # deps/linux/nginx/conf/mime.types，fetch_deps 的放置源）。任一命中即拷到 staging/config。
      seed_mime=""
      for m in "$SEED_DEPS/config/mime.types" "$SEED_DEPS/deps/win/nginx/mime.types" "$SEED_DEPS/deps/linux/nginx/conf/mime.types"; do
        [ -f "$m" ] && { seed_mime="$m"; break; }
      done
      if [ -n "$seed_mime" ]; then cp -f "$seed_mime" "$STAGING/config/mime.types"; fi
      if [ -d "$STAGING/deps/wheels" ] && [ $SKIP_WHEELS -eq 0 ]; then
        log "  [hint] deps/wheels 已由 seed 提供；如需按新 requirements 重下，用 --skip-wheels 会保留旧 wheel——"
        log "  [hint] 或删掉 seed 的 wheels 再跑（Phase C 会重新下载）。"
      fi
    else
      log "Phase B — 下载并规范化原生依赖（Win+Linux）"
      VERSIONS_FILE="$NATIVE_ROOT/versions.env" STAGING="$STAGING" bash "$NATIVE_ROOT/lib/fetch_deps.sh"
    fi
  else
    log "Phase B 跳过（--skip-deps）"
  fi

  # ── C. 离线 Python wheels（供目标机离线安装 runtime 依赖）──────────────────
  if [ $SKIP_WHEELS -eq 0 ]; then
    log "Phase C — 下载 runtime Python 依赖离线 wheel（win_amd64 + linux，均按 python 3.11）"
    # 每次全新下载（requirements 可能跨版本变更；seed 复用只共享依赖，不保留旧 wheel）。
    rm -rf "$STAGING/deps/wheels"; mkdir -p "$STAGING/deps/wheels"
    # 关键：必须是 cp311 的二进制 wheel（runtime 用内置 python 3.11）。
    # 早期版本用构建机系统 pip（cp312）下载 → 目标机 3.11 pip 跳过 cp312 wheel → 离线首启仍联网补包。
    # 修法：本机平台用内置 python-3.11 的 pip；跨平台用 --python-version/--implementation/--abi 指定 cp311。
    LIN_PY311="$STAGING/deps/linux/python-3.11/bin/python3"
    if [ -x "$LIN_PY311" ]; then
      # Linux 本机二进制（manylinux/linux，cp311 原生 wheel）
      "$LIN_PY311" -m pip download -r "$STAGING/app/requirements.txt" -d "$STAGING/deps/wheels/" \
        -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
        2>/dev/null || log "  [warn] Linux cp311 wheel 下载有部分失败"
      # sdist（如 py-opengauss 仅发 .tar.gz）转 wheel：离线目标机 pip 构建 sdist 需联网拉
      # setuptools，转 wheel 后 --find-links 可离线装。失败（C 扩展需编译）仅告警不致命。
      for sd in "$STAGING/deps/wheels/"*.tar.gz; do
        [ -f "$sd" ] || continue
        "$LIN_PY311" -m pip wheel --no-deps "$sd" -w "$STAGING/deps/wheels/" \
          -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
          2>/dev/null || log "  [warn] sdist 转 wheel 失败: $(basename "$sd")"
      done
    else
      pip download -r "$STAGING/app/requirements.txt" -d "$STAGING/deps/wheels/" \
        -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
        2>/dev/null || log "  [warn] 本机平台 wheel 下载有部分失败（未找到内置 python-3.11）"
    fi
    # Windows 平台二进制（best-effort；纯 python 包已由上一步覆盖）
    pip download -r "$STAGING/app/requirements.txt" -d "$STAGING/deps/wheels/" \
      --platform win_amd64 --python-version 3.11 --implementation cp --abi cp311 --only-binary :all: --no-deps \
      -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
      2>/dev/null || log "  [warn] Windows 平台 wheel 下载有部分失败（纯 python 包已覆盖即可）"
  else
    log "Phase C 跳过（--skip-wheels）"
  fi

  # ── D. 组装 + 写 MANIFEST + 打包 ───────────────────────────────────────────
  log "Phase D — 写 MANIFEST + 打包"
  GIT_COMMIT="$(cd "$WORKSPACE" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cp -f "$NATIVE_ROOT/versions.env" "$STAGING/versions.env"
  # 决定打哪些平台：PLATFORM 空=两个；否则仅指定平台
  if [ -n "$PLATFORM" ]; then TARGETS="$PLATFORM"; else TARGETS="win linux"; fi
  ZIPPER="$NATIVE_ROOT/lib/zip_platform.py"
  PY=python3
  command -v python3 >/dev/null 2>&1 || PY=python
  for PLAT in $TARGETS; do
    case "$PLAT" in
      win) PLATNAME=windows; PLATLABEL="Windows x64" ;;
      linux) PLATNAME=linux; PLATLABEL="Linux x64 (glibc 2.17+)" ;;
    esac
    {
      echo "openJiuwen AgentStudio — 原生（免容器）运行包 [$PLATNAME 专用]"
      echo "name:    $NAME"
      echo "version: $VER"
      echo "git:     $GIT_COMMIT"
      echo "built:   $BUILD_TIME"
      echo "平台:    $PLATLABEL"
      echo "本包仅含本平台原生依赖（对端平台依赖已剔除；MySQL 调试符号 .pdb/.lib 与"
      echo "mecab 遗留日文编码字典已剔除以瘦身；deps/wheels 仅含本平台 wheel）。"
      echo
      echo "组件产物（从源码构建）:"
      echo "  studio-manager.jar  <- backend/studio-manager (profile=manager, 端口 31111)"
      echo "  frontend/dist/hws   <- frontend (pnpm build, nginx 托管)"
      echo "  agent_runtime/jiuwen/agent_builder <- Python 源码（runtime 31014 / builder 31015 两服务）"
      echo "  model_service/storage/common_utils <- packages/ 共享包（PYTHONPATH=app 非 pip 安装）"
      echo
      echo "原生依赖版本（详见 versions.env）:"
      echo "  JRE=${JRE17_VERSION}  MySQL=${MYSQL_VERSION}  Redis=${REDIS_VERSION}  Python=${PYTHON_VERSION}  nginx=${NGINX_VERSION}"
      echo
      echo "启动："
      echo "  Windows: powershell -ExecutionPolicy Bypass -File .\\scripts\\start.ps1"
      echo "  Linux:   ./scripts/start.sh"
      echo "控制台: http://localhost/openjiuwen/"
    } > "$STAGING/MANIFEST.txt"
    log "  生成 $PLATNAME zip（选择性排除对端依赖 + MySQL 冗余 + 对端 wheel）"
    mkdir -p "$DIST"
    "$PY" "$ZIPPER" "$STAGING" "$DIST/${NAME}-native-${VER}-${PLATNAME}.zip" "$PLAT"
  done
fi

# ════════════════ arm64 流水线（Linux aarch64 单平台包）════════════════
if [ "$ARCH" != "x86" ]; then
  LOG_TAG="arm-build"
  [ "$ARCH" != "arm64" ] || [ -z "$PLATFORM" ] || log "--platform 对 arm64 无效（恒为 linux 单包），已忽略"
  [ "$ARCH" != "arm64" ] || [ -z "$SEED_DEPS" ] || log "--seed-deps 对 arm64 无效，已忽略"
  # shellcheck disable=SC1090
  set -a; . "$NATIVE_ROOT/versions.arm64.env"; set +a
  [ "${BUNDLE_VERSION:-$VER}" = "$VER" ] || log "  [hint] versions.arm64.env BUNDLE_VERSION=${BUNDLE_VERSION} 与构建版本 ${VER} 不同，以 ${VER} 为准"

  # ── 0. 前置校验 + 组装 staging（复用 x86 侧架构无关产物）──────────────────
  command -v docker >/dev/null 2>&1 || die "未找到 docker（编译 redis/nginx 与 aarch64 wheel 解析都依赖 linux/arm64 容器）"
  # 应用产物来源：--seed-apps 指定，或同版本 x86 staging；缺失则现场构建（Phase A）
  SEED="${SEED_APPS:-$STAGING}"
  if [ -f "$SEED/app/requirements.txt" ] && [ -f "$SEED/scripts/start.sh" ]; then
    log "复用应用产物: $SEED（如需重建：删除该目录或先跑 --arch x86）"
  else
    [ "$SEED" = "$STAGING" ] || die "--seed-apps 目录缺 app/requirements.txt 或 scripts/start.sh: $SEED"
    [ $SKIP_APPS -eq 0 ] || die "缺应用产物且 --skip-apps：去掉 --skip-apps 现场构建，或先跑 ./build.sh --arch x86"
    log "Phase A — 构建应用产物（Maven + pnpm + 复制 runtime 源码，架构无关）"
    rm -rf "$STAGING"; mkdir -p "$STAGING"
    cp -a "$NATIVE_ROOT/lib/bundle_template/." "$STAGING/"
    chmod +x "$STAGING/scripts/"*.sh "$STAGING/scripts/runtime_patches.py" 2>/dev/null || true
    export WORKSPACE STAGING
    bash "$NATIVE_ROOT/lib/build_apps.sh"
  fi

  log "SEED=$SEED  STAGING=$STAGING_ARM  VER=$VER"
  log "Phase 0 — 组装 staging（复用 $SEED 的应用产物与模板）"
  if [ -d "$STAGING_ARM" ] && [ $SKIP_DEPS -eq 1 ]; then
    log "  保留已有 staging 的 deps/（--skip-deps）"
  else
    rm -rf "$STAGING_ARM"; mkdir -p "$STAGING_ARM"
  fi
  mkdir -p "$STAGING_ARM" "$CACHE_ARM"
  # 应用产物/模板总是从 seed 刷新（架构无关）；deps/ 不动
  rm -rf "$STAGING_ARM/app" "$STAGING_ARM/config" "$STAGING_ARM/scripts"
  cp -a "$SEED/app"     "$STAGING_ARM/app"
  cp -a "$SEED/config"  "$STAGING_ARM/config"
  cp -a "$SEED/scripts" "$STAGING_ARM/scripts"
  cp -a "$SEED/.env.template" "$STAGING_ARM/" 2>/dev/null || cp -a "$NATIVE_ROOT/lib/bundle_template/.env.template" "$STAGING_ARM/"
  { [ -f "$SEED/README.txt" ] && cp -a "$SEED/README.txt" "$STAGING_ARM/"; } || true
  cp -f "$NATIVE_ROOT/versions.arm64.env" "$STAGING_ARM/versions.env"
  mkdir -p "$LIN" "$STAGING_ARM/deps/wheels"

  # ── B. aarch64 原生依赖 ──────────────────────────────────────────────────────
  if [ $SKIP_DEPS -eq 0 ]; then
    log "Phase B — 下载/规范化 aarch64 原生依赖"

    # JRE 17
    log "  JRE 17 (aarch64)"
    dl "$JRE17_LINUX_URL" "$CACHE_ARM/jre17-linux.tar.gz" 8 "$JRE17_LINUX_SHA256"
    rm -rf "$CACHE_ARM/x-jre17-linux"; mkdir -p "$CACHE_ARM/x-jre17-linux" "$LIN/jre-17"
    "$TAR_BIN" -xzf "$CACHE_ARM/jre17-linux.tar.gz" -C "$CACHE_ARM/x-jre17-linux" || die "解压 jre17 失败"
    jdkdir=$(find "$CACHE_ARM/x-jre17-linux" -maxdepth 1 -mindepth 1 -type d | head -1)
    [ -n "$jdkdir" ] || die "jre17 解压后未找到顶层目录"
    # cp -rL 解引用符号链接（legal/ 等全是相对 symlink，MSYS 无 symlink 权限建不了；物化内容运行时无影响）
    cp -rL "$jdkdir/." "$LIN/jre-17/"

    # MySQL 8.0（全量包 → 裁剪逼近 minimal）
    log "  MySQL ${MYSQL_VERSION} (aarch64, glibc2.28 全量包→裁剪，16 并发下载约 10-20 分钟)"
    dl "$MYSQL_LINUX_URL" "$CACHE_ARM/mysql-linux.tar.xz" 16 "$MYSQL_LINUX_SHA256"
    rm -rf "$CACHE_ARM/x-mysql-linux"; mkdir -p "$CACHE_ARM/x-mysql-linux" "$LIN/mysql-8.0"
    "$TAR_BIN" -xf "$CACHE_ARM/mysql-linux.tar.xz" -C "$CACHE_ARM/x-mysql-linux" || die "解压 mysql 失败"
    mysqldir=$(find "$CACHE_ARM/x-mysql-linux" -maxdepth 1 -mindepth 1 -type d -name 'mysql-*' | head -1)
    [ -n "$mysqldir" ] || die "mysql 解压后未找到顶层目录"
    cp -rL "$mysqldir/." "$LIN/mysql-8.0/"
    # 裁剪：测试套件/文档/手册/头文件/静态库/debug 二进制（运行时均不需要，占全量包大半）
    rm -rf "$LIN/mysql-8.0/mysql-test" "$LIN/mysql-8.0/docs" "$LIN/mysql-8.0/man" "$LIN/mysql-8.0/include"
    rm -f  "$LIN/mysql-8.0/bin/mysqld-debug" "$LIN/mysql-8.0/bin/mysqltest" "$LIN/mysql-8.0/bin/mysql_client_test"
    find "$LIN/mysql-8.0/lib" -name '*.a' -delete 2>/dev/null || true
    [ -f "$LIN/mysql-8.0/bin/mysqld" ] || die "mysql-8.0/bin/mysqld 缺失"

    # MinIO + mc
    log "  MinIO + mc (linux-arm64)"
    mkdir -p "$LIN/minio"
    dl "$MINIO_LINUX_URL" "$CACHE_ARM/minio-linux" 8 "$MINIO_LINUX_SHA256"; cp -f "$CACHE_ARM/minio-linux" "$LIN/minio/minio"
    dl "$MC_LINUX_URL"     "$CACHE_ARM/mc-linux"     8 "$MC_LINUX_SHA256";     cp -f "$CACHE_ARM/mc-linux"     "$LIN/minio/mc"

    # Python 3.11
    log "  Python 3.11 (aarch64)"
    dl "$PYTHON_LINUX_URL" "$CACHE_ARM/python-linux.tar.gz" 8 "$PYTHON_LINUX_SHA256"
    rm -rf "$CACHE_ARM/x-python-linux"; mkdir -p "$CACHE_ARM/x-python-linux" "$LIN/python-3.11"
    "$TAR_BIN" -xzf "$CACHE_ARM/python-linux.tar.gz" -C "$CACHE_ARM/x-python-linux" || die "解压 python 失败"
    # 不限 -type f：bin/python3 可能是 symlink（bsdtar 在 Windows 上可能物化为文件或链接）
    pybin=$(find "$CACHE_ARM/x-python-linux" -name python3 | head -1)
    [ -n "$pybin" ] || die "python 解压后未找到 bin/python3"
    # -rL 物化 bin/python3→python3.11 等 symlink（MSYS 无法建链接）
    cp -rL "$(dirname "$(dirname "$pybin")")/." "$LIN/python-3.11/"
    [ -f "$LIN/python-3.11/bin/python3" ] || die "python-3.11/bin/python3 缺失"

    # Linux 兼容库（el7 aarch64，bundle 进 deps/linux/lib，同 x86 侧 soname 做法）
    log "  兼容库 (ncurses/libaio/numa, el7 aarch64)"
    mkdir -p "$LIN/lib"
    extract_rpm(){ # extract_rpm <url> <name> [sha256]  → 展开到 $CACHE_ARM/x-<name>
      dl "$1" "$CACHE_ARM/$2.rpm" 8 "${3:-}"
      rm -rf "$CACHE_ARM/x-$2"; mkdir -p "$CACHE_ARM/x-$2"
      # RPM 是 cpio 归档，GNU tar 不认（同 fetch_deps.sh）：bsdtar 优先；Windows 用
      # System32 bsdtar（MSYS 自带的是 GNU tar）；再回退 rpm2cpio|cpio。
      local ok=0
      if command -v bsdtar >/dev/null 2>&1; then
        bsdtar -xf "$CACHE_ARM/$2.rpm" -C "$CACHE_ARM/x-$2" 2>/dev/null && ok=1
      elif [ -x /c/Windows/System32/tar.exe ]; then
        /c/Windows/System32/tar.exe -xf "$CACHE_ARM/$2.rpm" -C "$CACHE_ARM/x-$2" && ok=1
      elif command -v rpm2cpio >/dev/null 2>&1 && command -v cpio >/dev/null 2>&1; then
        (cd "$CACHE_ARM/x-$2" && rpm2cpio "$CACHE_ARM/$2.rpm" | cpio -idm 2>/dev/null) && ok=1
      else
        die "解 RPM 需 bsdtar（apt install libarchive-tools / yum install bsdtar）或 rpm2cpio+cpio: $2"
      fi
      [ "$ok" -eq 1 ] || die "解 RPM 失败: $2"
    }
    copy_so(){ # copy_so <dir> <real> <soname>（RPM 内真实文件改名拷为 soname）
      local f; f=$(find "$1" -type f -name "$2" | head -1)
      if [ -n "$f" ]; then cp -f "$f" "$LIN/lib/$3"; else log "  [warn] 未找到 $2（跳过）"; fi
    }
    extract_rpm "$NCURSES_LIBS_URL" ncurses-libs "$NCURSES_LIBS_SHA256"
    copy_so "$CACHE_ARM/x-ncurses-libs" "libncurses.so.5.9" "libncurses.so.5"
    copy_so "$CACHE_ARM/x-ncurses-libs" "libtinfo.so.5.9"  "libtinfo.so.5"
    extract_rpm "$LIBAIO_URL" libaio "$LIBAIO_SHA256"
    copy_so "$CACHE_ARM/x-libaio" "libaio.so.1.0.1" "libaio.so.1"
    extract_rpm "$NUMACTL_LIBS_URL" numactl-libs "$NUMACTL_LIBS_SHA256"
    copy_so "$CACHE_ARM/x-numactl-libs" "libnuma.so.1.0.0" "libnuma.so.1"

    # 源码包（编译在容器内做，此处仅下载缓存）
    log "  源码包 (redis/nginx/pcre2/zlib)"
    dl "$REDIS_LINUX_URL" "$CACHE_ARM/redis-linux.tar.gz" 8 "$REDIS_LINUX_SHA256"
    dl "$NGINX_LINUX_URL" "$CACHE_ARM/nginx-linux.tar.gz" 8 "$NGINX_LINUX_SHA256"
    dl "$PCRE2_URL" "$CACHE_ARM/pcre2.tar.gz" 8 "$PCRE2_SHA256"
    dl "$ZLIB_URL" "$CACHE_ARM/zlib.tar.gz" 8 "$ZLIB_SHA256"

    # ── B2. docker(linux/arm64, debian:10=glibc2.28) 编译 redis + nginx ─────────
    # 注：宿主侧检查一律用 -f 不用 -x——MSYS(Git Bash) 下非 .exe 文件 stat 无执行位，
    # -x 必假；真正执行位由 zip_platform.py 打包时按 bin/sbin 目录统一置 755。
    if [ ! -f "$LIN/redis-7/redis-server" ] || [ ! -f "$LIN/nginx/sbin/nginx" ]; then
      log "Phase B2 — ${COMPILE_IMAGE} arm64 容器内编译 redis ${REDIS_VERSION} + nginx ${NGINX_VERSION}（QEMU 模拟，约 10-30 分钟）"
      V_STAGING=$(to_docker_vol "$STAGING_ARM"); V_CACHE=$(to_docker_vol "$CACHE_ARM")
      MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm --platform linux/arm64 \
        -v "$V_STAGING:/staging" -v "$V_CACHE:/cache" \
        "$COMPILE_IMAGE" bash -c '
          set -eu
          # debian:10 已 EOL：apt 源指归档仓库，且关闭有效期校验（归档 Release 已过期）
          sed -i "s|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org|g" /etc/apt/sources.list
          apt-get -o Acquire::Check-Valid-Until=false update -qq >/dev/null 2>&1 || true
          DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends gcc make libc6-dev ca-certificates binutils >/dev/null
          n=$(nproc)
          # MySQL 全量包二进制未剥离符号（mysqld ~494MB）→ strip 对齐官方 minimal（~70MB）。
          # 脚本类文件 strip 会报错，逐一容忍；strip 只去符号不影响运行时。
          if [ -d /staging/deps/linux/mysql-8.0/bin ]; then
            echo "[arm-compile] strip mysql binaries ..."
            for f in /staging/deps/linux/mysql-8.0/bin/*; do strip --strip-unneeded "$f" 2>/dev/null || true; done
            find /staging/deps/linux/mysql-8.0/lib -name "*.so*" -exec strip --strip-unneeded {} + 2>/dev/null || true
          fi
          if [ ! -x /staging/deps/linux/redis-7/redis-server ]; then
            echo "[arm-compile] redis ..."
            mkdir -p /staging/deps/linux/redis-7 /tmp/b
            tar xzf /cache/redis-linux.tar.gz -C /tmp/b
            cd /tmp/b/redis-*
            if ! make -j"$n" >/tmp/make-redis.log 2>&1; then
              echo "[arm-compile] redis make FAILED（尾部日志）:"; tail -40 /tmp/make-redis.log; exit 1
            fi
            cp src/redis-server src/redis-cli /staging/deps/linux/redis-7/
          fi
          if [ ! -x /staging/deps/linux/nginx/sbin/nginx ]; then
            echo "[arm-compile] nginx (pcre2+zlib static) ..."
            mkdir -p /tmp/b && cd /tmp/b
            tar xzf /cache/nginx-linux.tar.gz; tar xzf /cache/pcre2.tar.gz; tar xzf /cache/zlib.tar.gz
            cd nginx-*
            if ! ./configure --prefix=/staging/deps/linux/nginx \
                --with-pcre=/tmp/b/pcre2-* --with-zlib=/tmp/b/zlib-* --with-cc-opt=-O2 >/tmp/conf-nginx.log 2>&1; then
              echo "[arm-compile] nginx configure FAILED（尾部日志）:"; tail -40 /tmp/conf-nginx.log; exit 1
            fi
            if ! make -j"$n" >/tmp/make-nginx.log 2>&1; then
              echo "[arm-compile] nginx make FAILED（尾部日志）:"; tail -40 /tmp/make-nginx.log; exit 1
            fi
            make install >/dev/null 2>&1
          fi
          echo "[arm-compile] done"
        ' || die "容器内编译失败"
      [ -f "$LIN/redis-7/redis-server" ] || die "redis 编译产物缺失"
      [ -f "$LIN/redis-7/redis-cli" ]    || die "redis-cli 编译产物缺失"
      [ -f "$LIN/nginx/sbin/nginx" ]     || die "nginx 编译产物缺失"
    fi
    # mime.types 兜底（优先用 seed 里 x86 侧已放的）
    { [ -f "$STAGING_ARM/config/mime.types" ] || cp -f "$LIN/nginx/conf/mime.types" "$STAGING_ARM/config/mime.types"; } || true
  else
    log "Phase B 跳过（--skip-deps）"
  fi

  # ── C. aarch64 离线 wheels（容器内 aarch64 python 原生解析）───────────────────
  if [ $SKIP_WHEELS -eq 0 ]; then
    log "Phase C — aarch64 wheels（arm64 容器 + 内置 python-3.11，完整依赖闭包 + sdist 转 wheel）"
    [ -f "$LIN/python-3.11/bin/python3" ] || die "内置 python 缺失（先跑 Phase B）"
    rm -rf "$STAGING_ARM/deps/wheels"; mkdir -p "$STAGING_ARM/deps/wheels"
    V_STAGING=$(to_docker_vol "$STAGING_ARM")
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm --platform linux/arm64 -v "$V_STAGING:/staging" \
      "$COMPILE_IMAGE" bash -c '
        set -eu
        PY=/staging/deps/linux/python-3.11/bin/python3
        "$PY" -m pip download -r /staging/app/requirements.txt -d /staging/deps/wheels/ \
          -i '"${PIP_INDEX_URL}"' --trusted-host '"${PIP_TRUSTED_HOST}"'
        for sd in /staging/deps/wheels/*.tar.gz; do
          [ -f "$sd" ] || continue
          echo "[arm-wheels] sdist→wheel: $(basename "$sd")"
          "$PY" -m pip wheel --no-deps "$sd" -w /staging/deps/wheels/ \
            -i '"${PIP_INDEX_URL}"' --trusted-host '"${PIP_TRUSTED_HOST}"' \
            || echo "[arm-wheels][warn] sdist 转 wheel 失败: $sd"
        done
        echo "[arm-wheels] done"
      ' || die "aarch64 wheel 下载失败"
    n_whl=$(ls "$STAGING_ARM/deps/wheels" | grep -c '\.whl$' || true)
    n_arma=$(ls "$STAGING_ARM/deps/wheels" | grep -c 'aarch64' || true)
    log "  wheels: ${n_whl} 个（含 aarch64 二进制 ${n_arma} 个）"
    [ "$n_arma" -gt 20 ] || die "aarch64 二进制 wheel 异常偏少（${n_arma} 个），检查容器网络或 pip 输出"
  else
    log "Phase C 跳过（--skip-wheels）"
  fi

  # ── D. MANIFEST + 打包（zip_platform 规则架构无关：deps/linux 保留、执行位 755）──
  log "Phase D — 写 MANIFEST + 打包"
  GIT_COMMIT="$(cd "$WORKSPACE" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    echo "openJiuwen AgentStudio — 原生（免容器）运行包 [linux-arm64 专用]"
    echo "name:    $NAME"
    echo "version: $VER"
    echo "git:     $GIT_COMMIT"
    echo "built:   $BUILD_TIME"
    echo "平台:    Linux arm64 (glibc 2.28+)"
    echo "本包仅含 ARM64 原生依赖（无 Windows 侧依赖）；目录结构与启动方式见 README.txt。"
    echo "与 x86 包的差异：MySQL 为官方 aarch64 全量包裁剪（glibc2.28，官方无 minimal 变体）；"
    echo "Redis/nginx 为 debian:10 arm64 容器内源码编译（仅链 glibc，基线 2.28）。"
    echo
    echo "原生依赖版本（详见 versions.env）:"
    echo "  JRE=${JRE17_VERSION}  MySQL=${MYSQL_VERSION}  Redis=${REDIS_VERSION}  Python=${PYTHON_VERSION}  nginx=${NGINX_VERSION}"
  } > "$STAGING_ARM/MANIFEST.txt"

  # 模板 README.txt 为 Win+Linux x64 双平台措辞，按 ARM64 包改写平台标识与 deps 说明
  if [ -f "$STAGING_ARM/README.txt" ]; then
    sed -i -e 's#跨平台（Windows x64 / Linux x64）#ARM64 Linux 专用（glibc 2.28+）#' \
           -e '/^    win\/  jre-17/d' \
           -e 's#^    linux/ .*Linux 原生依赖#    linux/ jre-17 mysql-8.0 redis-7 minio mc python-3.11 nginx   ARM64 原生依赖#' \
           -e '/^  Windows:  powershell/d' \
           -e '/^  - Windows 非管理员/d' \
           -e '/^  - Windows 不含 cron/d' \
      "$STAGING_ARM/README.txt"
  fi

  mkdir -p "$DIST"
  PY=python3; command -v "$PY" >/dev/null 2>&1 || PY=python; command -v "$PY" >/dev/null 2>&1 || PY="py -3"
  ZIP="$DIST/${NAME}-native-${VER}-linux-arm64.zip"
  $PY "$NATIVE_ROOT/lib/zip_platform.py" "$STAGING_ARM" "$ZIP" linux

  log "构建完成：$ZIP  ($(du -h "$ZIP" | cut -f1))"
  log "目标机解压后运行 ./scripts/start.sh（须 arm64 Linux，glibc ≥ 2.28）"
  LOG_TAG="build"
fi

# ════════════════ 产物汇总 ════════════════
log "构建完成："
for Z in windows linux linux-arm64; do
  ZP="$DIST/${NAME}-native-${VER}-${Z}.zip"
  [ -f "$ZP" ] && log "  $ZP  ($(du -h "$ZP" | cut -f1))"
done
log "拷到目标机解压后：Linux 跑 ./scripts/start.sh；Windows 跑 .\\scripts\\start.ps1；ARM64 包须 arm64 Linux（glibc ≥ 2.28）"
