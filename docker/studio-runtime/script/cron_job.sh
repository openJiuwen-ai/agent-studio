#!/bin/bash

SCRIPT_PATH=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
FUNCTION_NAME_BACKUP_COMMON_LOG=backup_common_log

echo $SCRIPT_PATH $SCRIPT_DIR $SCRIPT_NAME

function start_cron_job() {
    if [[ "${BACKUP_COMMON_LOG:-true}" != "true" ]]; then
        return 0
    fi
    sleep 10

    # 启动后1分钟开始定时任务
    sleep ${WATCH_DOG_INIT_TIME:-60}

    PERIOD_HOUR=${BACKUP_COMMON_LOG_PERIOD_HOUR:-4}
    STRATEGY=${BACKUP_COMMON_LOG_STRATEGY:-TIME}
    SIZE_INTERVAL=${BACKUP_COMMON_LOG_SIZE_CHECK_INTERVAL:-1}

    # 容器初始没有定时任务，不用缓存已有的定时任务
    # 滚动开关
    if [[ "${BACKUP_COMMON_LOG:-true}" == "true" ]]; then
      echo "BACKUP_COMMON_LOG_PERIOD_HOUR=${BACKUP_COMMON_LOG_PERIOD_HOUR}" > /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_BACKUP_NUM=${BACKUP_COMMON_LOG_BACKUP_NUM}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_DIR=${BACKUP_COMMON_LOG_DIR}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_FILE=${BACKUP_COMMON_LOG_FILE}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_STRATEGY=${BACKUP_COMMON_LOG_STRATEGY}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_COMPRESS=${BACKUP_COMMON_LOG_COMPRESS}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_MAX_SIZE=${BACKUP_COMMON_LOG_MAX_SIZE}" >> /tmp/cron_jobs
      echo "BACKUP_COMMON_LOG_SIZE_CHECK_INTERVAL=${BACKUP_COMMON_LOG_SIZE_CHECK_INTERVAL}" >> /tmp/cron_jobs
      # 按转储策略选 cron 节奏：TIME=每 PERIOD_HOUR 小时，SIZE=每 SIZE_INTERVAL 分钟
      if [[ "${STRATEGY}" == "SIZE" ]]; then
        if [[ "${SIZE_INTERVAL}" -le 1 ]]; then
          CRON_MIN="*"
        else
          CRON_MIN="*/${SIZE_INTERVAL}"
        fi
        CRON_SCHEDULE="${CRON_MIN} * * * *"
      else
        CRON_SCHEDULE="0 */${PERIOD_HOUR} * * *"
      fi
      echo "${CRON_SCHEDULE} bash -c 'cd ${SCRIPT_DIR} && source ${SCRIPT_DIR}/${SCRIPT_NAME} && ${FUNCTION_NAME_BACKUP_COMMON_LOG}'" >> /tmp/cron_jobs
    fi
    crontab /tmp/cron_jobs
    echo "current crontab list:"
    crontab -l
}


function backup_common_log() {
    backup_server_log
}

function backup_server_log() {
    BACKUP_PATH=${BACKUP_COMMON_LOG_DIR:-"/opt/cloud/logs/common_log_backup"}
    COMMON_LOG_FILE=${BACKUP_COMMON_LOG_FILE:-"/opt/cloud/logs/common.log"}
    BACKUP_NUM=${BACKUP_COMMON_LOG_BACKUP_NUM:-10}
    STRATEGY=${BACKUP_COMMON_LOG_STRATEGY:-TIME}
    COMPRESS=${BACKUP_COMMON_LOG_COMPRESS:-true}
    MAX_SIZE=${BACKUP_COMMON_LOG_MAX_SIZE:-500}

    if [[ ! -f "${COMMON_LOG_FILE}" ]]; then
        return 0
    fi

    # 按转储策略判断是否需要切分
    if [[ "${STRATEGY}" == "SIZE" ]]; then
        # 纯按大小：未到阈值不切
        file_size=$(stat -c%s "${COMMON_LOG_FILE}" 2>/dev/null || echo 0)
        max_bytes=$((MAX_SIZE * 1024 * 1024))
        if [[ "${file_size}" -lt "${max_bytes}" ]]; then
            return 0
        fi
    else
        # 仅判断是否为空，行里的函数无法获取文件信息
        if [ -z "$(tail -n 1 ${COMMON_LOG_FILE})" ]; then
            # 文件为空，不滚动
            return 0
        fi
    fi

    mkdir -p "$BACKUP_PATH"

    # flock 串行化，防止 SIZE 每分钟触发时上一轮压缩未完又重叠
    exec 9>/tmp/common.log.rotate.lock
    if ! flock -n 9; then
        echo "previous common.log rotation still running, skip"
        return 0
    fi
    # 统计目录中的文件数量（仅统计普通文件）
    file_count=$(find "$BACKUP_PATH" -maxdepth 1 -type f | wc -l)

    if [ "$file_count" -ge $BACKUP_NUM ]; then
        # 找到最旧的文件（按修改时间排序，最旧的在前）
        oldest_file=$(find $BACKUP_PATH -maxdepth 1 -type f -printf '%T@ %p\n' | sort -rnk 1 | tail -n 1 | awk '{print $2}')

        if [ -n "$oldest_file" ]; then
            echo "Removing oldest file: $oldest_file"
            rm -f "$oldest_file"
        fi
    fi

    backup_file="${BACKUP_PATH}/common.log.$(date +%Y%m%d_%H%M)00"
    cp "${COMMON_LOG_FILE}" "${backup_file}"
    echo "" > "${COMMON_LOG_FILE}"

    # 转储后按需 gzip 压缩
    if [[ "${COMPRESS}" == "true" ]]; then
        gzip "${backup_file}"
    fi
}

