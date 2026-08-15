#!/bin/bash
#
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
#
#
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LOGGING_LOG_PATH="${LOGGING_LOG_PATH:-/opt/cloud/logs}"
WATCHDOG_LOG_DIR="${WATCHDOG_LOG_DIR:-/opt/cloud/logs/watchdog}"

function check_fail_count() {
  local SERVER_PORT=$1
  filename="${WATCHDOG_LOG_DIR}/fail_${SERVER_PORT}.count"
  max_fail_time=${HEALTH_CHECK_FAIL_COUNT:-3}

  if [ ! -f "$filename" ]; then
    echo "0" > "$filename"
  else
    value=$(cat "$filename")

    if [[ "$value" =~ ^[0-9]+$ ]]; then
      echo "valid integer: $value"
    else
      echo "not valid integer: $value"
      echo "0" > "$filename"
    fi

    if [ "$value" -lt $((max_fail_time - 1)) ]; then
      value=$((value + 1))
      echo "$value" > "$filename"
    else
      echo "0" > "$filename"
      return 1
    fi
  fi
  return 0
}

function server_health_check(){
  local CHECK_RSP=$1
  local HEALTH_CHECK_TIMEOUT=$2
  local SERVER_PORT=$3
  if [[ "${HTTPS}" == "false" ]]; then
    health_check=$(curl -k --location --request GET "http://127.0.0.1:${SERVER_PORT}/v1/health" --max-time ${HEALTH_CHECK_TIMEOUT})
  else
    health_check=$(curl -k --location --request GET "https://127.0.0.1:${SERVER_PORT}/v1/health" --max-time ${HEALTH_CHECK_TIMEOUT})
  fi
  if [ $? -eq 0 ]; then
        echo health_check success
        echo "0" > "${WATCHDOG_LOG_DIR}/fail_${SERVER_PORT}.count"
        return 0
    else
        echo "health_check ${SERVER_PORT} port fail"  >> ${LOGGING_LOG_PATH}/common.log
        check_fail_count ${SERVER_PORT}
        if [ $? -eq 0 ]; then
          echo "continue check ${SERVER_PORT} port" >> ${LOGGING_LOG_PATH}/common.log
        else
          echo "check fail too much, restart ${SERVER_PORT} port" >> ${LOGGING_LOG_PATH}/common.log
          nohup bash ${SCRIPT_DIR}/start_server.sh ${SERVER_PORT} > /dev/null 2>&1 &
        fi
    fi
}

function set_no_proxy() {
  hosts=`hostname -I`
  host=`echo "$hosts" | awk '{split($1, arr, " "); print arr[1]}'`
  if [[ ! -z "${no_proxy}" ]];then
    export no_proxy="${no_proxy},127.0.0.1,${host}"
  elif [[ ! -z "${NO_PROXY}" ]];then
    export NO_PROXY="${NO_PROXY},127.0.0.1,${host}"
  else
    export no_proxy="127.0.0.1,${host}"
  fi
  echo "no_proxy=${no_proxy}"
  echo "NO_PROXY=${NO_PROXY}"
}

function watchdog() {
  set_no_proxy

  mkdir -p ${WATCHDOG_LOG_DIR}
  CHECK_RSP="good"
  if [[ -z "${CUSTOM_HEALTH_CHECK_RSP}" ]];then
    CHECK_RSP="${CUSTOM_HEALTH_CHECK_RSP}"
  fi
  HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
  PERIOD_SECONDS=${HEALTH_CHECK_PERIOD_SECONDS:-30}
  SERVER_PORT=${PORT:-8000}

  if [[ "${NGINX_LOAD_BALANCING}" == "true" ]]; then
    # Multi-port mode: monitor all worker ports.
    # LB_WORKER_NUM is exported by start_nginx_lb.sh (the real nginx-upstream
    # worker count). GUNICORN_WORK_NUM is overridden to 1 there to force
    # single-process uvicorn, so it must NOT be used as the port count here.
    WORKER_NUM=${LB_WORKER_NUM:-${GUNICORN_WORK_NUM:-1}}
    echo "Watchdog: monitoring ${WORKER_NUM} workers (ports $((SERVER_PORT+1)) to $((SERVER_PORT+WORKER_NUM)))"
    while [ 1 ]; do
      sleep ${PERIOD_SECONDS}
      for i in $(seq 1 ${WORKER_NUM}); do
        WORKER_PORT=$((SERVER_PORT + i))
        server_health_check "${CHECK_RSP}" "${HEALTH_CHECK_TIMEOUT}" "${WORKER_PORT}"
      done
    done
  else
    # Original single-port mode
    while [ 1 ]; do
      sleep ${PERIOD_SECONDS}
      server_health_check "${CHECK_RSP}" "${HEALTH_CHECK_TIMEOUT}" "${SERVER_PORT}"
    done
  fi
}

watchdog
