#!/usr/bin/env bash
set -xe

# 兼容 Docker Daemon API 版本（当 client 版本高于 daemon 时需要设置）
# 可通过 docker version 查看 daemon 的 API version，按需修改
# 注释掉：让 docker 自动协商 API 版本。原 1.43 在新 daemon（要求 ≥1.44）上会报
# "client version 1.43 is too old"。如需显式指定，改成 daemon 支持的版本（如 1.44）。
# export DOCKER_API_VERSION=1.43

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
  docker_build_runtime
  log "[4/6] studio-runtime 镜像构建完成"

  log "[5/6] 构建内置 VictoriaLogs 数据源的 Grafana 镜像"
  docker_build_grafana
  log "[5/6] Grafana 镜像构建完成"

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
function docker_build_runtime() {
  IMAGE_NAME=studio-runtime
  cd ${DOCKER_DIR}/studio-runtime/
  echo "[BUILD] docker build ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"
  docker build \
    --build-arg BASE_IMAGE=${BASE_IMAGE_PYTHON} \
    -t ${IMAGE_NAME}:${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM} .
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

function docker_build_grafana() {
  cd ${DOCKER_DIR}/grafana/
  docker build \
    --build-arg GRAFANA_VERSION=11.3.0 \
    --build-arg VICTORIA_LOGS_DATASOURCE_VERSION=0.29.0 \
    -t openjiuwen/grafana-victorialogs:11.3.0-0.29.0 .
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

main
