#!/usr/bin/env bash
set -xe

# 兼容 Docker Daemon API 版本（当 client 版本高于 daemon 时需要设置）
# 可通过 docker version 查看 daemon 的 API version，按需修改
# 注释掉：让 docker 自动协商 API 版本。原 1.43 在新 daemon（要求 ≥1.44）上会报
# "client version 1.43 is too old"。如需显式指定，改成 daemon 支持的版本（如 1.44）。
# export DOCKER_API_VERSION=1.43

# java基础镜像 (Debian-based, for manager)
BASE_IMAGE_JAVA="eclipse-temurin:17-jre"
# java基础镜像 (公共标准镜像，yum-based，for runtime)
# nginx基础镜像
BASE_IMAGE_NGINX="nginx:1.27"
# python基础镜像 (预编译Python 3.11)
BASE_IMAGE_PYTHON="python:3.11-slim"
# 镜像名
IMAGE_NAME=studio-console
# 版本号
VERSION=1.0.0
# 构建架构：自动获取
BUILD_PLATFORM=$(uname -m)
# 构建时间
BUILD_TIME=$(date +"%Y%m%d%H%M%S")

WORKSPACE=${WORKSPACE:-$(
  cd $(dirname $0/)/..
  pwd
)}

DOCKER_DIR=${WORKSPACE}/docker

function log() {
  echo "========================================"
  echo "[BUILD] $(date '+%Y-%m-%d %H:%M:%S') $1"
  echo "========================================"
}

function main() {
  parse_targets "$@"
  rm -f "${DOCKER_DIR}/.last-build.env"
  log "开始构建 Docker 镜像，DOCKER_DIR=${DOCKER_DIR}"
  log "VERSION=${VERSION}, BUILD_PLATFORM=${BUILD_PLATFORM}, BUILD_TIME=${BUILD_TIME}"

  if [ "${TARGET_SERVICES[0]}" != "all" ]; then
    log "仅构建以下镜像: ${TARGET_SERVICES[*]}"
    for TARGET_SERVICE in "${TARGET_SERVICES[@]}"; do
      build_single_service
    done
    write_build_info
    log "指定镜像构建完成；选择性构建不生成 AgentBuilder.tar.gz"
    return
  fi

  log "[1/6] 构建 studio-manager 镜像"
  docker_build_manager
  log "[1/6] studio-manager 镜像构建完成"

  log "[2/6] 构建 studio-console 镜像"
  docker_build_console
  log "[2/6] studio-console 镜像构建完成"

  log "[3/6] 构建 studio-runtime 镜像"
  docker_build_runtime
  log "[3/6] studio-runtime 镜像构建完成"

  log "[4/6] 构建 studio-builder 镜像"
  build_builder_image
  log "[4/6] studio-builder 镜像构建完成"

  log "[5/6] 构建内置 VictoriaLogs 数据源的 Grafana 镜像"
  docker_build_grafana
  log "[5/6] Grafana 镜像构建完成"

  log "[6/6] 打包所有镜像（含 builder + Grafana）为 AgentBuilder.tar.gz"
  docker_save_package
  log "[6/6] 打包完成"

  write_build_info

  log "Docker 镜像构建全部完成"
}

function usage() {
  echo "用法: bash docker/build.sh [all|manager|console|runtime|builder|grafana ...]"
}

function parse_targets() {
  TARGET_SERVICES=()
  [ "$#" -gt 0 ] || set -- all
  local target normalized existing duplicate
  for target in "$@"; do
    case "${target}" in
      all) normalized=all ;;
      manager|studio-manager) normalized=studio-manager ;;
      console|studio-console) normalized=studio-console ;;
      runtime|studio-runtime) normalized=studio-runtime ;;
      builder|studio-builder) normalized=studio-builder ;;
      grafana|grafana-victorialogs) normalized=grafana-victorialogs ;;
      *) echo "[BUILD] 不支持的服务: ${target}" >&2; usage; exit 1 ;;
    esac
    if [ "${normalized}" = all ] && [ "$#" -gt 1 ]; then
      echo "[BUILD] all 不能与其他服务同时使用" >&2
      exit 1
    fi
    duplicate=false
    for existing in "${TARGET_SERVICES[@]}"; do
      [ "${existing}" = "${normalized}" ] && duplicate=true
    done
    [ "${duplicate}" = true ] || TARGET_SERVICES+=("${normalized}")
  done
}

function build_single_service() {
  case "${TARGET_SERVICE}" in
    studio-manager) docker_build_manager ;;
    studio-console) docker_build_console ;;
    studio-runtime) docker_build_runtime ;;
    studio-builder) build_builder_image ;;
    grafana-victorialogs) docker_build_grafana ;;
  esac
}

function write_build_info() {
  if [ "${TARGET_SERVICES[0]}" = "all" ]; then
    cat > "${DOCKER_DIR}/.last-build.env" <<EOF
STUDIO_MANAGER_IMAGE=studio-manager:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}
STUDIO_RUNTIME_IMAGE=studio-runtime:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}
STUDIO_BUILDER_IMAGE=studio-builder:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}
STUDIO_CONSOLE_IMAGE=studio-console:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}
GRAFANA_IMAGE=openjiuwen/grafana-victorialogs:11.3.0-0.29.0
BUILD_PLATFORM=${BUILD_PLATFORM}
EOF
    return
  fi

  echo "BUILD_PLATFORM=${BUILD_PLATFORM}" > "${DOCKER_DIR}/.last-build.env"
  for TARGET_SERVICE in "${TARGET_SERVICES[@]}"; do
    case "${TARGET_SERVICE}" in
      studio-manager) echo "STUDIO_MANAGER_IMAGE=studio-manager:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}" ;;
      studio-console) echo "STUDIO_CONSOLE_IMAGE=studio-console:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}" ;;
      studio-runtime) echo "STUDIO_RUNTIME_IMAGE=studio-runtime:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}" ;;
      studio-builder) echo "STUDIO_BUILDER_IMAGE=studio-builder:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}" ;;
      grafana-victorialogs) echo "GRAFANA_IMAGE=openjiuwen/grafana-victorialogs:11.3.0-0.29.0" ;;
    esac
  done >> "${DOCKER_DIR}/.last-build.env"
}

# 打studio-manager的docker镜像
function docker_build_manager() {
  IMAGE_NAME=studio-manager
  cd ${DOCKER_DIR}/studio-manager
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
  --build-arg BASE_IMAGE=${BASE_IMAGE_JAVA} \
  -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

function docker_build_runtime() {
  IMAGE_NAME=studio-runtime
  cd ${DOCKER_DIR}/studio-runtime/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

# 将 builder 构建上下文（agent_builder）复制到 studio-builder 目录
# 构建完成后由 cleanup_builder_sources 清理
function copy_builder_sources() {
  local STAGE_BUILDER=${DOCKER_DIR}/studio-builder
  mkdir -p "${STAGE_BUILDER}"
  if [ ! -d "${WORKSPACE}/agent_builder" ]; then
    echo "[ERROR] agent_builder 目录不存在: ${WORKSPACE}/agent_builder"
    exit 1
  fi
  echo "[BUILD] 复制 agent_builder 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/agent_builder "${STAGE_BUILDER}/"
  # 共享包 model_service / storage / common_utils（agent_builder 运行时 import）：与 runtime 一致，靠
  # PYTHONPATH=app（builder CMD `cd app`）导入，非 pip 安装。
  echo "[BUILD] 复制 model_service 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/packages/model_service/model_service "${STAGE_BUILDER}/model_service"
  echo "[BUILD] 复制 storage 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/packages/storage/storage "${STAGE_BUILDER}/storage"
  echo "[BUILD] 复制 common_utils 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/packages/common_utils/common_utils "${STAGE_BUILDER}/common_utils"
  # 清理不需要的文件以减小构建上下文
  rm -rf ${STAGE_BUILDER}/agent_builder/.git ${STAGE_BUILDER}/agent_builder/tests \
         ${STAGE_BUILDER}/agent_builder/docs ${STAGE_BUILDER}/agent_builder/.venv \
         ${STAGE_BUILDER}/agent_builder/__pycache__ ${STAGE_BUILDER}/agent_builder/.pytest_cache \
         ${STAGE_BUILDER}/agent_builder/report
  # 注：agent_builder 已用本地 adapter（adapter.jiuwen_bridge 等）替代 jiuwen 包，不再拷入 jiuwen。
  # 注：openjiuwen 不再从本地 agent-core 拷贝安装，改由 requirements.txt 从 PyPI(aliyun) 装 openjiuwen==0.1.16。
}

# 构建完成后清理 builder 构建上下文中的临时源码（保留已提交的 Dockerfile）
function cleanup_builder_sources() {
  local STAGE_BUILDER=${DOCKER_DIR}/studio-builder
  for sub in agent_builder model_service storage common_utils; do
    if [ -d "${STAGE_BUILDER}/${sub}" ]; then
      echo "[BUILD] 清理构建上下文中的 ${sub}: ${STAGE_BUILDER}/${sub}"
      rm -rf "${STAGE_BUILDER}/${sub}"
    fi
  done
}

# 打studio-builder的docker镜像（agent_builder 独立微服务镜像）
function docker_build_builder() {
  IMAGE_NAME=studio-builder
  cd ${DOCKER_DIR}/studio-builder/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

function build_builder_image() {
  copy_builder_sources
  if ! docker_build_builder; then
    cleanup_builder_sources
    return 1
  fi
  cleanup_builder_sources
}

# studio-builder 不再单独保存为 StudioBuilder.tar.gz —— 已并入 docker_save()，
# 与 manager/runtime/console 一起进 docker/image/ + AgentBuilder.tar.gz。

# 打studio-console的docker镜像
function docker_build_console() {
  IMAGE_NAME=studio-console
  cd ${DOCKER_DIR}/studio-console/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_NGINX} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

function docker_build_grafana() {
  GRAFANA_IMAGE=openjiuwen/grafana-victorialogs:11.3.0-0.29.0
  if docker image inspect "${GRAFANA_IMAGE}" > /dev/null 2>&1; then
    echo "[BUILD] ${GRAFANA_IMAGE} 已存在，跳过构建"
    return
  fi
  cd ${DOCKER_DIR}/grafana/
  docker build \
    --build-arg GRAFANA_VERSION=11.3.0 \
    --build-arg VICTORIA_LOGS_DATASOURCE_VERSION=0.29.0 \
    -t "${GRAFANA_IMAGE}" .
}

function docker_save_package() {
  docker_save
  package
}

# docker tag and save
function docker_save() {
  if [ -d "${DOCKER_DIR}/image" ]; then
      rm -rf ${DOCKER_DIR}/image
    fi
  mkdir -p ${DOCKER_DIR}/image
  cd ${DOCKER_DIR}/image
  docker save studio-manager:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-manager_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save studio-runtime:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-runtime_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save studio-console:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-console_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save studio-builder:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-builder_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save openjiuwen/grafana-victorialogs:11.3.0-0.29.0 > grafana-victorialogs_11.3.0-0.29.0.${BUILD_PLATFORM}.tar
}

# docker镜像打成压缩包
function package() {
  cd ${DOCKER_DIR}
  if [ -f "AgentBuilder.tar.gz" ]; then
      rm -f "AgentBuilder.tar.gz"
  fi
  tar -czvf AgentBuilder.tar.gz ./image ./compose ./k8s
}

main "$@"
