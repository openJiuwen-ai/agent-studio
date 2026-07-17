#!/usr/bin/env bash
set -xe

# ============================================================
# build_arm.sh — 在 x86 机器上交叉构建 ARM64 Docker 镜像
# 前置条件：
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker buildx create --name arm-builder --use --driver docker-container
# ============================================================

# 兼容 Docker Daemon API 版本（当 client 版本高于 daemon 时需要设置）
# 可通过 docker version 查看 daemon 的 API version，按需修改
export DOCKER_API_VERSION=1.43

# java基础镜像 (Debian-based, for manager/service)
BASE_IMAGE_JAVA="eclipse-temurin:17-jre"
# nginx基础镜像
BASE_IMAGE_NGINX="nginx:1.27"
# python基础镜像 (预编译Python 3.11)
BASE_IMAGE_PYTHON="python:3.11-slim"
# 镜像名
IMAGE_NAME=studio-console
# 版本号
VERSION=1.0.0
# 构建架构：固定 arm64（交叉编译）
BUILD_PLATFORM=arm64
# buildx builder 名称
BUILDER=arm-builder
# buildkitd 配置路径（为 docker-container 驱动提供镜像加速）
BUILDKITD_CONFIG="${DOCKER_DIR}/buildkitd.toml"
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
  log "开始构建 ARM64 Docker 镜像，DOCKER_DIR=${DOCKER_DIR}"
  log "VERSION=${VERSION}, BUILD_PLATFORM=${BUILD_PLATFORM}, BUILD_TIME=${BUILD_TIME}"

  # 校验 buildx builder 是否可用（不存在则自动创建，使用 buildkitd.toml 镜像加速配置）
  if ! docker buildx inspect ${BUILDER} > /dev/null 2>&1; then
    log "buildx builder '${BUILDER}' 不存在，正在创建（使用 ${BUILDKITD_CONFIG}）..."
    docker buildx create \
      --name ${BUILDER} \
      --driver docker-container \
      --config ${BUILDKITD_CONFIG} \
      --use
    docker buildx inspect --bootstrap
    log "buildx builder '${BUILDER}' 创建完成"
  fi

  log "[1/7] 构建 studio-manager 镜像 (arm64)"
  docker_build_manager
  log "[1/7] studio-manager 镜像构建完成"

  log "[2/7] 构建 studio-service 镜像 (arm64)"
  docker_build_service
  log "[2/7] studio-service 镜像构建完成"

  log "[3/7] 构建 studio-console 镜像 (arm64)"
  docker_build_console
  log "[3/7] studio-console 镜像构建完成"

  log "[4/7] 构建 runtime-base 基础镜像 (arm64, apt+pip)"
  docker_build_runtime_base
  log "[4/7] runtime-base 基础镜像构建完成"

  log "[5/7] 构建 studio-runtime 镜像 (arm64)"
  docker_build_runtime
  log "[5/7] studio-runtime 镜像构建完成"

  log "[6/7] 构建 studio-builder 镜像 (arm64)"
  copy_builder_sources
  docker_build_builder
  cleanup_builder_sources
  log "[6/7] studio-builder 镜像构建完成"

  log "[7/7] 打包所有镜像（含 builder）为 AgentBuilder-arm64.tar.gz"
  docker_save_package
  log "[7/7] 打包完成"

  log "ARM64 Docker 镜像构建全部完成"
}

# 打studio-manager的docker镜像 (arm64)
function docker_build_manager() {
  IMAGE_NAME=studio-manager
  cd ${DOCKER_DIR}/studio-manager
  echo "[BUILD] docker buildx build --platform linux/arm64 ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker buildx build \
    --builder ${BUILDER} \
    --platform linux/arm64 \
    --build-arg BASE_IMAGE=${BASE_IMAGE_JAVA} \
    --load \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

# 打studio-service的docker镜像 (arm64)
function docker_build_service() {
  IMAGE_NAME=studio-service
  cd ${DOCKER_DIR}/studio-service/
  echo "[BUILD] docker buildx build --platform linux/arm64 ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker buildx build \
    --builder ${BUILDER} \
    --platform linux/arm64 \
    --build-arg BASE_IMAGE=${BASE_IMAGE_JAVA} \
    --load \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

# 打runtime-base基础镜像 (arm64) — 包含 apt 系统依赖 + pip Python 依赖
# 使用 requirements.txt 的内容哈希作为镜像标签，依赖变更时自动触发重建
function docker_build_runtime_base() {
  cd ${DOCKER_DIR}/studio-runtime/
  # 根据 requirements.txt 内容计算哈希，作为基础镜像标签
  REQ_HASH=$(sha256sum requirements.txt | cut -c1-12)
  BASE_TAG="runtime-base-arm64:${REQ_HASH}"
  if docker image inspect ${BASE_TAG} > /dev/null 2>&1; then
    echo "[BUILD] ${BASE_TAG} 已存在（与当前 requirements.txt 一致），跳过构建"
  else
    echo "[BUILD] docker buildx build --platform linux/arm64 ${BASE_TAG} (requirements.txt 已变更，需要重建，约需 2 小时)"
    docker buildx build \
      --builder ${BUILDER} \
      --platform linux/arm64 \
      --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
      --load \
      -f Dockerfile.base \
      -t ${BASE_TAG} .
  fi
  # 始终将当前哈希标签同步到 latest，供 Dockerfile.arm 引用
  docker tag ${BASE_TAG} runtime-base-arm64:latest
}

# 打studio-runtime的docker镜像 (arm64)
# 使用原生 docker build (QEMU模拟) 以直接引用本地 runtime-base-arm64 基础镜像
# buildx docker-container driver 无法解析本地镜像，故不使用 buildx
function docker_build_runtime() {
  IMAGE_NAME=studio-runtime
  cd ${DOCKER_DIR}/studio-runtime/
  echo "[BUILD] docker build --platform linux/arm64 ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} (QEMU, 约3-5分钟)"
  docker build \
    --platform linux/arm64 \
    -f Dockerfile.arm \
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
  # 共享包 model_service / storage（agent_builder 运行时 import）：与 runtime 一致，靠
  # PYTHONPATH=app（builder CMD `cd app`）导入，非 pip 安装。
  echo "[BUILD] 复制 model_service 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/packages/model_service/model_service "${STAGE_BUILDER}/model_service"
  echo "[BUILD] 复制 storage 到构建上下文: ${STAGE_BUILDER}"
  cp -r ${WORKSPACE}/packages/storage/storage "${STAGE_BUILDER}/storage"
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
  for sub in agent_builder model_service storage; do
    if [ -d "${STAGE_BUILDER}/${sub}" ]; then
      echo "[BUILD] 清理构建上下文中的 ${sub}: ${STAGE_BUILDER}/${sub}"
      rm -rf "${STAGE_BUILDER}/${sub}"
    fi
  done
}

# 打studio-builder的docker镜像 (arm64) —— agent_builder 独立微服务镜像
# studio-builder 的 Dockerfile 使用公共 python:3.11-slim 基础镜像，无需 runtime-base 预构建
# 注意：builder 的 requirements.txt 含 transformers/pandas/scikit-learn 等重型依赖，
# QEMU 模拟下首次构建较慢（参考 runtime-base），后续可考虑为 builder 也做 base 镜像缓存优化
function docker_build_builder() {
  IMAGE_NAME=studio-builder
  cd ${DOCKER_DIR}/studio-builder/
  echo "[BUILD] docker buildx build --platform linux/arm64 ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker buildx build \
    --builder ${BUILDER} \
    --platform linux/arm64 \
    --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
    --load \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
}

# studio-builder 不再单独保存为 StudioBuilder-arm64.tar.gz —— 已并入 docker_save()，
# 与 manager/service/runtime/console 一起进 docker/image/ + AgentBuilder-arm64.tar.gz。

# 打studio-console的docker镜像 (arm64)
function docker_build_console() {
  IMAGE_NAME=studio-console
  cd ${DOCKER_DIR}/studio-console/
  echo "[BUILD] docker buildx build --platform linux/arm64 ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker buildx build \
    --builder ${BUILDER} \
    --platform linux/arm64 \
    --build-arg BASE_IMAGE=${BASE_IMAGE_NGINX} \
    --load \
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
  docker save studio-builder:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} > studio-builder_${BUILD_TIME}.${BUILD_PLATFORM}.tar
}

# docker镜像打成压缩包
function package() {
  cd ${DOCKER_DIR}
  if [ -f "AgentBuilder-arm64.tar.gz" ]; then
      rm -f "AgentBuilder-arm64.tar.gz"
  fi
  tar -czvf AgentBuilder-arm64.tar.gz ./image ./compose ./k8s ./init.sql
}

main
