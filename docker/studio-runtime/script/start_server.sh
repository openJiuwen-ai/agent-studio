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

  # jemalloc: 仅对 Python 服务进程生效（所有启动路径均经此函数：
  # start.sh 直接模式、start_nginx_lb.sh 负载均衡模式、watchdog.sh 重启）
  if [[ -z "${LD_PRELOAD}" && -f /usr/local/lib/libjemalloc.so.2 ]]; then
    export LD_PRELOAD=/usr/local/lib/libjemalloc.so.2
  fi

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

# FEAT-131: 构建 A2A 适配层启动参数
# 当 A2A_ADAPTER_ENABLED=true 时，在 uvicorn 前启动 TCP 适配层，剥离高码网关 h2c 升级头
# 非 LB 模式下需要启用（高码 gateway 直连 runtime）；LB 模式下 Nginx 已处理协议兼容，通常无需启用
# 多 worker（LB 模式）时按 worker 偏移量自动计算独立 adapter 端口，避免冲突
function build_adapter_args() {
  local uvicorn_port=$1
  local adapter_args=""
  if [[ "${A2A_ADAPTER_ENABLED,,}" == "true" ]]; then
    local base_adapter_port=${A2A_ADAPTER_PORT:-31016}
    local server_port=${PORT:-8000}
    local adapter_port=${base_adapter_port}
    # LB 模式下多 worker 各需独立 adapter 端口：base + (worker_port - server_port)
    if [[ "${uvicorn_port}" != "${server_port}" ]]; then
      adapter_port=$((base_adapter_port + uvicorn_port - server_port))
    fi
    adapter_args="--with-adapter --adapter-port ${adapter_port}"
    echo "A2A adapter enabled: uvicorn=${uvicorn_port}, adapter=${adapter_port}"
  fi
  echo "${adapter_args}"
}

function server_start(){
  # 先全部停掉
  ps -ef | grep EIStart |grep -v grep | awk '{print $2}' | xargs -r kill -9
  ps -ef | grep multiprocessing |grep -v grep | awk '{print $2}' | xargs -r kill -9

  echo "start to start python server"

  port=${PORT:-8000}
  base_port=$((${port}))
  adapter_args=$(build_adapter_args ${base_port})
  echo "nohup python -u ${server_path} --host 0.0.0.0 --port ${base_port} ${adapter_args} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &"
  nohup python -u ${server_path} --host 0.0.0.0 --port ${base_port} ${adapter_args} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function start_all(){
  env_init
  server_start
}

function start_sub_process(){
  server_port=$1
  # Free the port by actual listener, not just argv matching. argv grep is the
  # primary method; fuser is a fallback for when argv was rewritten/truncated
  # (uvicorn re-exec) so a stale holder doesn't keep the port bound.
  ps -ef | grep EIStart | grep -- "--port ${server_port}" |grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null
  if command -v fuser >/dev/null 2>&1; then
    fuser -k ${server_port}/tcp 2>/dev/null || true
  fi

  env_init

  adapter_args=$(build_adapter_args ${server_port})
  nohup python -u ${server_path} --host 0.0.0.0 --port ${server_port} ${adapter_args} >> ${LOGGING_LOG_PATH}/common.log 2>&1 &
}

function main(){
  if [[ ${START_PORT} != "" ]];then
    start_sub_process ${START_PORT}
  else
    start_all
  fi
}

main
