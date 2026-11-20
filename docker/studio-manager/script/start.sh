#!/bin/bash

# 变量
APP_PATH=${APP_PATH:-/opt/cloud/studio-manager}
MICROSERVICE_NAME="studio-manager"
ACTIVE_PROFILES='manager'
if [[ "${spring_datasource_driver_class_name}" == org.postgresql.Driver ]]; then
    ACTIVE_PROFILES="${ACTIVE_PROFILES},postgres"
fi
# Calculate before certificate handling; invalid memory settings stop startup.
source "$(dirname "${BASH_SOURCE[0]}")/jvm-memory.sh" || exit 1
manager_configure_jvm_memory || exit 1
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
# 启动服务
exec java -Xms${INIT_JAVA_HEAP_SIZE} -Xmx${MAX_JAVA_HEAP_SIZE} \
  -XX:MaxDirectMemorySize=${MAX_DIRECT_MEMORY_SIZE} \
  -Dfile.encoding=UTF-8 \
  -jar ${APP_PATH}/app/${MICROSERVICE_NAME}.jar \
  --spring.config.additional-location=${APP_PATH}/config/ \
  --spring.profiles.active=${ACTIVE_PROFILES} \
  --logging.config=${APP_PATH}/config/log4j2.xml
