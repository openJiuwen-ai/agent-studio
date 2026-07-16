#!/usr/bin/env bash
set -xe

# 兼容 Docker Daemon API 版本（当 client 版本高于 daemon 时需要设置）
# 可通过 docker version 查看 daemon 的 API version，按需修改
export DOCKER_API_VERSION=1.43

# java基础镜像 (Debian-based, for manager/service)
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
  log "开始构建 Docker 镜像，DOCKER_DIR=${DOCKER_DIR}"
  log "VERSION=${VERSION}, BUILD_PLATFORM=${BUILD_PLATFORM}, BUILD_TIME=${BUILD_TIME}"

  log "[1/6] 构建 studio-manager 镜像"
  docker_build_manager
  log "[1/6] studio-manager 镜像构建完成"

  log "[2/6] 构建 studio-service 镜像"
  docker_build_service
  log "[2/6] studio-service 镜像构建完成"

  log "[3/6] 构建 studio-console 镜像"
  docker_build_console
  log "[3/6] studio-console 镜像构建完成"

  log "[4/6] 构建 studio-runtime 镜像"
  copy_agent_core
  docker_build_runtime
  cleanup_agent_core
  log "[4/6] studio-runtime 镜像构建完成"

  log "[5/6] 构建 studio-builder 镜像"
  copy_builder_sources
  docker_build_builder
  cleanup_builder_sources
  docker_save_builder
  log "[5/6] studio-builder 镜像构建完成"

  log "[6/6] 打包所有镜像为 AgentBuilder.tar.gz"
  docker_save_package
  log "[6/6] 打包完成"

  log "Docker 镜像构建全部完成"
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

# 打studio-service的docker镜像
function docker_build_service() {
  IMAGE_NAME=studio-service
  cd ${DOCKER_DIR}/studio-service/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_JAVA} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}
# 将 agent-core（openjiuwen 本地源码）复制到 studio-runtime 构建上下文
# 构建完成后由 cleanup_agent_core 清理
function copy_agent_core() {
  local AGENT_CORE_SRC=${WORKSPACE}/agent-core
  local AGENT_CORE_DST=${DOCKER_DIR}/studio-runtime/agent-core
  if [ ! -d "${AGENT_CORE_SRC}" ]; then
    echo "[ERROR] agent-core 目录不存在: ${AGENT_CORE_SRC}"
    echo "[ERROR] 请先 git clone agent-core 到项目根目录"
    exit 1
  fi
  echo "[BUILD] 复制 agent-core 到构建上下文: ${AGENT_CORE_DST}"
  cp -r ${AGENT_CORE_SRC} ${AGENT_CORE_DST}
  # 清理不需要的文件以减小构建上下文
  rm -rf ${AGENT_CORE_DST}/.git ${AGENT_CORE_DST}/tests ${AGENT_CORE_DST}/docs \
         ${AGENT_CORE_DST}/.venv ${AGENT_CORE_DST}/__pycache__ \
         ${AGENT_CORE_DST}/.pytest_cache ${AGENT_CORE_DST}/report
}

# 构建完成后清理 agent-core 临时目录
function cleanup_agent_core() {
  local AGENT_CORE_DST=${DOCKER_DIR}/studio-runtime/agent-core
  if [ -d "${AGENT_CORE_DST}" ]; then
    echo "[BUILD] 清理构建上下文中的 agent-core: ${AGENT_CORE_DST}"
    rm -rf ${AGENT_CORE_DST}
  fi
}

function docker_build_runtime() {
  IMAGE_NAME=studio-runtime
  cd ${DOCKER_DIR}/studio-runtime/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

# 将 builder 构建上下文（agent_builder、jiuwen、agent-core）复制到 studio-builder 目录
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
  echo "[BUILD] 复制 jiuwen 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/jiuwen "${STAGE_BUILDER}/"
  # 清理不需要的文件以减小构建上下文
  rm -rf ${STAGE_BUILDER}/agent_builder/.git ${STAGE_BUILDER}/agent_builder/tests \
         ${STAGE_BUILDER}/agent_builder/docs ${STAGE_BUILDER}/agent_builder/.venv \
         ${STAGE_BUILDER}/agent_builder/__pycache__ ${STAGE_BUILDER}/agent_builder/.pytest_cache \
         ${STAGE_BUILDER}/agent_builder/report
  rm -rf ${STAGE_BUILDER}/jiuwen/.git ${STAGE_BUILDER}/jiuwen/tests \
         ${STAGE_BUILDER}/jiuwen/docs ${STAGE_BUILDER}/jiuwen/.venv \
         ${STAGE_BUILDER}/jiuwen/__pycache__ ${STAGE_BUILDER}/jiuwen/.pytest_cache \
         ${STAGE_BUILDER}/jiuwen/report
  # agent-core（openjiuwen 本地源码），构建完成后清理
  local AGENT_CORE_SRC=${WORKSPACE}/agent-core
  local AGENT_CORE_DST=${STAGE_BUILDER}/agent-core
  if [ ! -d "${AGENT_CORE_SRC}" ]; then
    echo "[ERROR] agent-core 目录不存在: ${AGENT_CORE_SRC}"
    echo "[ERROR] 请先 git clone agent-core 到项目根目录"
    exit 1
  fi
  echo "[BUILD] 复制 agent-core 到构建上下文: ${AGENT_CORE_DST}"
  cp -r ${AGENT_CORE_SRC} ${AGENT_CORE_DST}
  # 清理不需要的文件以减小构建上下文
  rm -rf ${AGENT_CORE_DST}/.git ${AGENT_CORE_DST}/tests ${AGENT_CORE_DST}/docs \
         ${AGENT_CORE_DST}/.venv ${AGENT_CORE_DST}/__pycache__ \
         ${AGENT_CORE_DST}/.pytest_cache ${AGENT_CORE_DST}/report
}

# 构建完成后清理 builder 构建上下文中的临时源码（保留已提交的 Dockerfile）
function cleanup_builder_sources() {
  local STAGE_BUILDER=${DOCKER_DIR}/studio-builder
  for sub in agent-core agent_builder jiuwen; do
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

# docker save studio-builder 为独立 StudioBuilder.tar.gz
function docker_save_builder() {
  cd ${DOCKER_DIR}
  if [ -f "StudioBuilder.tar.gz" ]; then
    rm -f "StudioBuilder.tar.gz"
  fi
  docker save studio-builder:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} | gzip > StudioBuilder.tar.gz
}

# 打studio-console的docker镜像
function docker_build_console() {
  IMAGE_NAME=studio-console
  cd ${DOCKER_DIR}/studio-console/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_NGINX} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
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
  docker save studio-service:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-service_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save studio-runtime:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-runtime_${BUILD_TIME}.${BUILD_PLATFORM}.tar
  docker save studio-console:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-console_${BUILD_TIME}.${BUILD_PLATFORM}.tar
}

# docker镜像打成压缩包
function package() {
  cd ${DOCKER_DIR}
  if [ -f "AgentBuilder.tar.gz" ]; then
      rm -f "AgentBuilder.tar.gz"
  fi
  tar -czvf AgentBuilder.tar.gz ./image ./compose ./k8s
}

main