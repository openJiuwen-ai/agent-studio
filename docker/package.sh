#!/usr/bin/env bash
set -xe

# npm 中央仓库 (public)
NPM_CENTRAL_REPO="https://registry.npmjs.org/"

# 获取根路径
WORKSPACE=${WORKSPACE:-$(
  cd $(dirname $0/)/..
  pwd
)}

function log() {
  echo "========================================"
  echo "[PACKAGE] $(date '+%Y-%m-%d %H:%M:%S') $1"
  echo "========================================"
}

function main() {
  log "开始构建打包，WORKSPACE=${WORKSPACE}"

  log "[1/3] 后端编译复制 (studio-manager & studio-service)"
  backend_build_copy
  log "[1/3] 后端编译复制完成"

  log "[2/3] 前端编译复制 (studio-console)"
  frontend_build_copy
  log "[2/3] 前端编译复制完成"

  log "[3/3] studio-runtime 源码复制"
  runtime_copy
  log "[3/3] studio-runtime 源码复制完成"
#  默认编译和构建在同一环境执行，跳过清理步骤。若编译与构建跨环境（如构建环境不具备安装docker的环境），需放开以下步骤，将编译产物打成压缩包并清理中间文件
#  package_clean
#  log "构建打包全部完成"
}

function package_clean() {
  # 打包
  package
  # 清理中间产物
  clean
}

function backend_build_copy() {
  echo "[PACKAGE] 开始 Maven 打包..."
  cd ${WORKSPACE}/backend
  mvn clean package -Dmaven.test.skip=true -U
  echo "[PACKAGE] Maven 打包完成"

  echo "[PACKAGE] 复制 studio-manager 产物..."
  copy_manager
  echo "[PACKAGE] studio-manager 复制完成"

  echo "[PACKAGE] 复制 studio-service 产物..."
  copy_service
  echo "[PACKAGE] studio-service 复制完成"
}

function frontend_build_copy() {
  cd ${WORKSPACE}/frontend
  CONSOLE_TARGET_PATH=${WORKSPACE}/docker/studio-console

  echo "[PACKAGE] 安装 pnpm..."
  npm install -g pnpm --registry=${NPM_CENTRAL_REPO}

  echo "[PACKAGE] 安装前端依赖 (pnpm install)..."
  pnpm install --ignore-scripts

  echo "[PACKAGE] 构建前端 (pnpm run build)..."
  buildCmd="pnpm run build"
  $buildCmd
  if [ $? -eq 0 ]
     then
       echo "[PACKAGE] 前端构建成功，打包 dist..."
       tar -cf agent-console.tar dist
       rm -rf dist
       mv agent-console.tar ${CONSOLE_TARGET_PATH}
       echo "[PACKAGE] 前端产物已复制到 ${CONSOLE_TARGET_PATH}"

       # nginx.conf 已移至 compose/config/，复制到 studio-console build context 供 Dockerfile 使用
       mkdir -p ${CONSOLE_TARGET_PATH}/config
       cp -f ${WORKSPACE}/docker/compose/config/nginx.conf ${CONSOLE_TARGET_PATH}/config/nginx.conf
       echo "[PACKAGE] nginx.conf 已复制到 ${CONSOLE_TARGET_PATH}/config/"
     else
       echo "[PACKAGE] 前端构建失败！"
       exit 1
  fi
}

function runtime_copy() {
  RUNTIME_TARGET_PATH=${WORKSPACE}/docker/studio-runtime
  echo "[PACKAGE] 复制 agent-runtime 源码到 ${RUNTIME_TARGET_PATH}..."

  rm -rf ${RUNTIME_TARGET_PATH}/agent_builder
  cp -rf ${WORKSPACE}/agent_builder ${RUNTIME_TARGET_PATH}/agent_builder

  rm -rf ${RUNTIME_TARGET_PATH}/agent_runtime
  cp -rf ${WORKSPACE}/agent-runtime/agent_runtime ${RUNTIME_TARGET_PATH}/agent_runtime

  rm -rf ${RUNTIME_TARGET_PATH}/jiuwen
  cp -rf ${WORKSPACE}/agent-runtime/jiuwen ${RUNTIME_TARGET_PATH}/jiuwen

  rm -rf ${RUNTIME_TARGET_PATH}/tests
  cp -rf ${WORKSPACE}/agent-runtime/tests ${RUNTIME_TARGET_PATH}/tests

  cp -f ${WORKSPACE}/agent-runtime/requirements.txt ${RUNTIME_TARGET_PATH}/requirements.txt

  # 模型调用机制层共享包（packages/model_service）：作为纯模块目录放进 app/，
  # 与 agent_runtime/jiuwen 一致，靠 PYTHONPATH=$SERVICE_HOME/app 导入（非 pip 安装）。
  rm -rf ${RUNTIME_TARGET_PATH}/model_service
  cp -rf ${WORKSPACE}/packages/model_service/model_service ${RUNTIME_TARGET_PATH}/model_service

  rm -rf ${RUNTIME_TARGET_PATH}/bin
  cp -rf ${RUNTIME_TARGET_PATH}/script ${RUNTIME_TARGET_PATH}/bin

  echo "[PACKAGE] studio-runtime 源码复制完成"
}

function copy_manager() {
  # 复制studio-manager的jar包和配置文件
  MANAGER_TARGET_PATH=${WORKSPACE}/docker/studio-manager
  mkdir -pv ${MANAGER_TARGET_PATH}/lib
  cp -f ${WORKSPACE}/backend/studio-manager/target/studio-manager-*.jar ${MANAGER_TARGET_PATH}/lib/studio-manager.jar
  if [ -e ${WORKSPACE}/backend/studio-manager/target/lib ];then
    cp -f ${WORKSPACE}/backend/studio-manager/target/lib/* ${MANAGER_TARGET_PATH}/lib/
  fi
  mkdir -pv ${MANAGER_TARGET_PATH}/config
  cp -f ${WORKSPACE}/backend/studio-manager-service/src/main/resources/application-manager.yml ${MANAGER_TARGET_PATH}/config/
  cp -f ${WORKSPACE}/backend/studio-manager-service/src/main/resources/log4j2.xml ${MANAGER_TARGET_PATH}/config/
}

function copy_service() {
  # 复制studio-service的jar包和配置文件
  SERVICE_TARGET_PATH=${WORKSPACE}/docker/studio-service
  mkdir -pv ${SERVICE_TARGET_PATH}/lib
  cp -f ${WORKSPACE}/backend/studio-runtime/target/studio-runtime-*.jar ${SERVICE_TARGET_PATH}/lib/studio-service.jar
  if [ -e ${WORKSPACE}/backend/studio-runtime/target/lib ];then
    cp ${WORKSPACE}/backend/studio-runtime/target/lib/* ${SERVICE_TARGET_PATH}/lib/
  fi
  mkdir -pv ${SERVICE_TARGET_PATH}/config
  cp -f ${WORKSPACE}/backend/studio-runtime-service/src/main/resources/application-runtime.yml ${SERVICE_TARGET_PATH}/config/
  cp -f ${WORKSPACE}/backend/studio-runtime-service/src/main/resources/log4j2.xml ${SERVICE_TARGET_PATH}/config/
}

function package() {
  # 产物全部打成压缩包
  cd ${WORKSPACE}/docker
  if [ -f "package.tar.gz" ]; then
      rm -f "package.tar.gz"
  fi
  tar -czvf package.tar.gz ./compose ./k8s ./studio-manager ./studio-service ./studio-runtime ./studio-console ./build.sh
}

function clean() {
  # 清理中间产物
  if [ -d "${WORKSPACE}/docker/studio-manager/lib" ]; then
    rm -rf ${WORKSPACE}/docker/studio-manager/lib
  fi
  if [ -d "${WORKSPACE}/docker/studio-manager/config" ]; then
    rm -rf ${WORKSPACE}/docker/studio-manager/config
  fi
  if [ -d "${WORKSPACE}/docker/studio-service/lib" ]; then
    rm -rf ${WORKSPACE}/docker/studio-service/lib
  fi
  if [ -d "${WORKSPACE}/docker/studio-service/config" ]; then
    rm -rf ${WORKSPACE}/docker/studio-service/config
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/agent_runtime" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/agent_runtime
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/jiuwen" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/jiuwen
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/tests" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/tests
  fi
  if [ -f "${WORKSPACE}/docker/studio-runtime/requirements.txt" ]; then
    rm -f ${WORKSPACE}/docker/studio-runtime/requirements.txt
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/model_service" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/model_service
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/bin" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/bin
  fi
  if [ -d "${WORKSPACE}/docker/studio-runtime/agent-runtime" ]; then
    rm -rf ${WORKSPACE}/docker/studio-runtime/agent-runtime
  fi
  if [ -f "${WORKSPACE}/docker/studio-console/agent-console.tar" ]; then
    rm -rf ${WORKSPACE}/docker/studio-console/agent-console.tar
  fi
  if [ -d "${WORKSPACE}/docker/studio-console/config" ]; then
    rm -rf ${WORKSPACE}/docker/studio-console/config
  fi
}

main