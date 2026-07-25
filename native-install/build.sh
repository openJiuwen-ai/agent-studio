#!/usr/bin/env bash
# build.sh — openJiuwen AgentStudio 免容器跨平台包构建（Linux 构建机）
# 用法: ./build.sh [-v 版本号] [--platform win|linux] [--skip-apps] [--skip-deps] [--skip-wheels]
#   --platform：只打指定平台 zip（win 或 linux）；不传则两个都打。
#   Phase A/B/C 不受 --platform 影响（仍组装完整跨平台 staging），仅 Phase D 按此决定打几个。
# 产物: dist/AgentStudio-native-<ver>-<windows|linux>.zip
set -euo pipefail
cd "$(dirname "$0")"
NATIVE_ROOT="$(pwd)"
WORKSPACE="$(cd "$NATIVE_ROOT/.." && pwd)"
# shellcheck disable=SC1090
set -a; . "$NATIVE_ROOT/versions.env"; set +a
VER="${BUNDLE_VERSION:-1.0.0}"; NAME="${BUNDLE_NAME:-AgentStudio}"
STAGING="$NATIVE_ROOT/build/${NAME}-native-${VER}"
DIST="$NATIVE_ROOT/dist"

SKIP_APPS=0; SKIP_DEPS=0; SKIP_WHEELS=0; PLATFORM=""
while [ $# -gt 0 ]; do case "$1" in
  -v) VER="$2"; shift 2;;
  --platform) PLATFORM="$2"; shift 2;;
  --skip-apps) SKIP_APPS=1; shift;;
  --skip-deps) SKIP_DEPS=1; shift;;
  --skip-wheels) SKIP_WHEELS=1; shift;;
  *) echo "未知参数: $1"; exit 2;;
esac; done
case "$PLATFORM" in
  "") : ;; # 空=两个都打
  win|linux) : ;;
  *) echo "--platform 仅支持 win 或 linux，得到: $PLATFORM"; exit 2;;
esac

log(){ echo -e "\033[1;36m[build]\033[0m $*"; }
die(){ echo -e "\033[1;31m[build fatal]\033[0m $*"; exit 1; }

log "WORKSPACE=$WORKSPACE  STAGING=$STAGING  VER=$VER"

# ── 0. 初始化 staging（从 bundle_template 复制骨架）───────────────────────
rm -rf "$STAGING"; mkdir -p "$STAGING"
cp -a "$NATIVE_ROOT/lib/bundle_template/." "$STAGING/"
chmod +x "$STAGING/scripts/"*.sh "$STAGING/scripts/runtime_patches.py" 2>/dev/null || true
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
  log "Phase B — 下载并规范化原生依赖（Win+Linux）"
  VERSIONS_FILE="$NATIVE_ROOT/versions.env" STAGING="$STAGING" bash "$NATIVE_ROOT/lib/fetch_deps.sh"
else
  log "Phase B 跳过（--skip-deps）"
fi

# ── C. 离线 Python wheels（供目标机离线安装 runtime 依赖）──────────────────
if [ $SKIP_WHEELS -eq 0 ]; then
  log "Phase C — 下载 runtime Python 依赖离线 wheel（win_amd64 + linux）"
  mkdir -p "$STAGING/deps/wheels"
  # 本机平台（linux manylinux 二进制 + 纯 python）
  pip download -r "$STAGING/app/requirements.txt" -d "$STAGING/deps/wheels/" \
    -i "${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}" --trusted-host "${PIP_TRUSTED_HOST:-mirrors.aliyun.com}" \
    2>/dev/null || log "  [warn] 本机平台 wheel 下载有部分失败"
  # Windows 平台二进制（best-effort；纯 python 包已由上一步覆盖）
  pip download -r "$STAGING/app/requirements.txt" -d "$STAGING/deps/wheels/" \
    --platform win_amd64 --only-binary :all: --no-deps \
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
    echo "  studio-manager.jar  <- backend/studio-manager (profile=manager)"
    echo "  studio-service.jar  <- backend/studio-runtime (profile=runtime, 重命名)"
    echo "  frontend/dist/hws   <- frontend (pnpm build)"
    echo "  agent_runtime/ ...  <- agent-runtime + agent_builder 源码"
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

log "构建完成："
for PLAT in $TARGETS; do
  case "$PLAT" in win) PLATNAME=windows;; linux) PLATNAME=linux;; esac
  ZP="$DIST/${NAME}-native-${VER}-${PLATNAME}.zip"
  if [ -f "$ZP" ]; then log "  $ZP  ($(du -h "$ZP" | cut -f1))"; else log "  $ZP  缺失"; fi
done
log "拷到目标机解压后，Linux 跑 ./scripts/start.sh；Windows 跑 .\\scripts\\start.ps1"
