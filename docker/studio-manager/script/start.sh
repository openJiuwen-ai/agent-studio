#!/bin/bash

# 变量
APP_PATH=${APP_PATH:-/opt/cloud/studio-manager}
MICROSERVICE_NAME="studio-manager"
ACTIVE_PROFILES='manager'
PERCENT_AGE=${jvm_xmx_percent:-0.6}
DIRECT_RATIO=${jvm_direct_memory_ratio:-0.2}
DIRECT_CAP_MB=${jvm_direct_memory_cap_mb:-1024}
# https证书
if [ -z "$CB_CF_SERVER_KEYSTORE" ] || [ -z "$CB_CF_TRUST_KEYSTORE" ]; then
    echo "WARNING: SSL certificate env vars not set"
else
    mkdir -p ${APP_PATH}/ssl
    echo ${CB_CF_SERVER_KEYSTORE} | base64 --decode > ${APP_PATH}/ssl/server.keystore
    echo ${CB_CF_TRUST_KEYSTORE} | base64 --decode > ${APP_PATH}/ssl/trust.keystore
    chmod 700 ${APP_PATH}/ssl
    chmod 600 ${APP_PATH}/ssl/*.keystore
    echo "INFO: SSL certificate env vars set success"
fi
# 计算并设置堆内存大小
limit_in_bytes=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null)
if [ "$limit_in_bytes" -ne "9223372036854771712" ] && [ -n "$limit_in_bytes" ]; then
  limit_in_mb=$((${limit_in_bytes} / 1048576))
else
  limit_in_mb=$(free -m | awk '/^Mem:/{print $2}')
fi

heap_size=$(awk "BEGIN {printf \"%.0f\", $limit_in_mb * $PERCENT_AGE}")
INIT_JAVA_HEAP_SIZE=${heap_size}m
MAX_JAVA_HEAP_SIZE=${heap_size}m

direct_size=$(awk "BEGIN {printf \"%.0f\", $limit_in_mb * $DIRECT_RATIO}")
if [ "$direct_size" -gt "$DIRECT_CAP_MB" ]; then
  direct_size=$DIRECT_CAP_MB
fi
MAX_DIRECT_MEMORY_SIZE=${direct_size}m

# 启动服务
exec java -Xms${INIT_JAVA_HEAP_SIZE} -Xmx${MAX_JAVA_HEAP_SIZE} \
  -XX:MaxDirectMemorySize=${MAX_DIRECT_MEMORY_SIZE} \
  -Dfile.encoding=UTF-8 \
  -jar ${APP_PATH}/app/${MICROSERVICE_NAME}.jar \
  --spring.config.additional-location=${APP_PATH}/config/ \
  --spring.profiles.active=${ACTIVE_PROFILES} \
  --logging.config=${APP_PATH}/config/log4j2.xml
