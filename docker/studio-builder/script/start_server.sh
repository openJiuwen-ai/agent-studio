#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#
# studio-builder 服务进程启动 —— 参考 studio-runtime/script/start_server.sh。
# 设置 PYTHONPATH（含 ${SERVICE_HOME}/app，使 storage/model_service/agent_builder 可被 import）、
# host、日志目录，后台 nohup 拉起 agent_builder.EIBuilder。
#

START_PORT=$1

APP_LINK_FOLDER="/usr/local/lib/python3.11/site-packages"
APP_FOLDER=$(realpath ${APP_LINK_FOLDER})
echo "APP_FOLDER: ${APP_FOLDER}"

# builder 默认日志目录（运行时也可由外部 LOGGING_LOG_PATH 覆盖）
export LOGGING_LOG_PATH=${LOGGING_LOG_PATH:-/opt/cloud/logs/agent-builder}

function env_init(){
  export PYTHONPATH=${PYTHON_PATH:-}:"${APP_FOLDER}":"${SERVICE_HOME}":"${SERVICE_HOME}/app"
  echo "PYTHONPATH: ${PYTHONPATH}"

  # 创建日志目录，用于容器启动时将服务日志挂载到宿主机
  mkdir -p ${LOGGING_LOG_PATH}
  chmod -R 700 ${LOGGING_LOG_PATH}

  # builder 入口模块；agent_builder/storage/model_service 经 PYTHONPATH=${SERVICE_HOME}/app 解析
  server_path=${SERVICE_HOME}/app/agent_builder/EIBuilder.py

  hosts=`hostname -I`
  host=`echo "$hosts" | awk '{split($1, arr, " "); print arr[1]}'`
  echo "service host: $host"
  export host=${host}
}

function server_start(){
  # 先全部停掉旧进程
  ps -ef | grep EIBuilder | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

  echo "start to start python server"

  port=${SERVER_PORT:-31015}
  base_port=$((${port}))
  echo "nohup python -u -m agent_builder.EIBuilder --host 0.0.0.0 --port ${base_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &"
  cd ${SERVICE_HOME}/app
  nohup python -u -m agent_builder.EIBuilder --host 0.0.0.0 --port ${base_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function start_all(){
  env_init
  server_start
}

function start_sub_process(){
  server_port=$1
  ps -ef | grep EIBuilder | grep -- "--port ${server_port}" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

  env_init

  cd ${SERVICE_HOME}/app
  nohup python -u -m agent_builder.EIBuilder --host 0.0.0.0 --port ${server_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function main(){
  if [[ ${START_PORT} != "" ]];then
    start_sub_process ${START_PORT}
  else
    start_all
  fi
}

main
