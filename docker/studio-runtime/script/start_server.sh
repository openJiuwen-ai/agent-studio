#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
#
#
START_PORT=$1

APP_LINK_FOLDER="/usr/local/lib/python3.11/site-packages"
APP_FOLDER=$(realpath ${APP_LINK_FOLDER})
echo "APP_FOLDER: ${APP_FOLDER}"

function env_init(){
  export PYTHONPATH=$PYTHON_PATH:"${APP_FOLDER}":"${SERVICE_HOME}":"${SERVICE_HOME}/app"
  if [[ "${INSTRUMENTATION_ENABLE}" == "true" && -e "/otel-auto-instrumentation-python" ]];then
    echo "instrumentation is enable."
    export PYTHONPATH=${PYTHONPATH}:/otel-auto-instrumentation-python
  fi
  echo "PYTHONPATH: ${PYTHONPATH}"

  export JIUWEN_EXTENSION_PATH=${SERVICE_HOME}/app/agent_runtime/extension

  # 创建容器中服务的日志目录，用于容器启动时将服务日志挂载到宿主机
  chmod -R 700 ${LOGGING_LOG_PATH}
  server_path=${SERVICE_HOME}/app/agent_runtime/EIStart.py

  hosts=`hostname -I`
  host=`echo "$hosts" | awk '{split($1, arr, " "); print arr[1]}'`
  echo "service host: $host"
  export host=${host}

  # 合并包修改agent-service的endpoint
  if [[ "${RUN_WITH_ENGINE}" == "true" ]]; then
      export AGENT_RUNTIME_ENDPOINT=https://${host}:31014
      echo "AGENT_RUNTIME_ENDPOINT: $AGENT_RUNTIME_ENDPOINT"
  fi
}

function server_start(){
  # 先全部停掉
  ps -ef | grep EIStart |grep -v grep | awk '{print $2}' | xargs kill -9
  ps -ef | grep multiprocessing |grep -v grep | awk '{print $2}' | xargs kill -9

  echo "start to start python server"

  port=${PORT:-8000}
  base_port=$((${port}))
  echo "nohup python -u ${server_path} --host 0.0.0.0 --port ${base_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &"
  nohup python -u ${server_path} --host 0.0.0.0 --port ${base_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function start_all(){
  env_init
  server_start
}

function start_sub_process(){
  server_port=$1
  ps -ef | grep EIStart | grep -- "--port ${server_port}" |grep -v grep | awk '{print $2}' | xargs kill -9

  env_init

  nohup python -u ${server_path} --host 0.0.0.0 --port ${server_port} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function main(){
  if [[ ${START_PORT} != "" ]];then
    start_sub_process ${START_PORT}
  else
    start_all
  fi
}

main
