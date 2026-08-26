#!/bin/bash
nginx_dic="/opt/cloud/wiseagent-nginx"
nginx_conf="$nginx_dic/conf"
export PATH=$PATH:${nginx_dic}/nginx/sbin

CERT_FILE="/home/secret/cert.pem"
PRI_KEY_FILE="/home/secret/pri_key.pem"
KEYPASS_FIFO="/home/service/nginx/keypassfifo"

function check_https_enabled() {
  if [ -f "$CERT_FILE" ] && [ -f "$PRI_KEY_FILE" ] && [ -f "$KEYPASS_FIFO" ]; then
    echo "[INFO]: HTTPS certificates detected, enabling HTTPS mode"
    return 0
  else
    echo "[INFO]: HTTPS certificates not found, enabling HTTP mode"
    return 1
  fi
}

function update_nginx_config_for_https() {
  echo "[INFO]: HTTPS remains unchanged"
}

function update_nginx_config_for_http() {
  sed -i "s/listen ${POD_IP}:443 ssl;/#listen ${POD_IP}:443 ssl;/g" $nginx_conf/nginx.conf
  sed -i "s/#listen ${POD_IP}:80;/listen ${POD_IP}:80;/g" $nginx_conf/nginx.conf
  sed -i 's/ssl_protocols/#ssl_protocols/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_session_timeout/#ssl_session_timeout/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_session_cache/#ssl_session_cache/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_session_tickets/#ssl_session_tickets/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_ciphers/#ssl_ciphers/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_prefer_server_ciphers/#ssl_prefer_server_ciphers/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_password_file/#ssl_password_file/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_certificate/#ssl_certificate/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_certificate_key/#ssl_certificate_key/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_stapling/#ssl_stapling/g' $nginx_conf/nginx.conf
  sed -i 's/ssl_stapling_verify/#ssl_stapling_verify/g' $nginx_conf/nginx.conf
  sed -i 's/http2 on;/#http2 on;/g' $nginx_conf/nginx.conf
  sed -i 's/set $server_scheme "https";/set $server_scheme "http";/g' $nginx_conf/nginx.conf
  sed -i 's/proxy_set_header X-Original-URL https:\/\/$host/proxy_set_header X-Original-URL http:\/\/$host/g' $nginx_conf/nginx.conf
}

# 准备nginx进程启动的所有配置文件
function init_config_file() {
  cd /home/service/
  cp /home/conf/nginx.conf $nginx_conf

  touch /opt/cloud/wiseagent-nginx/logs/access.log
  chmod 640 /opt/cloud/wiseagent-nginx/logs/access.log
  touch /opt/cloud/wiseagent-nginx/logs/error.log
  chmod 640 /opt/cloud/wiseagent-nginx/logs/error.log

  export POD_IP=$(ip addr | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | awk -F '/' '{print $1}' | head -1)
  sed -i "s/pod_ip/${POD_IP}/g" $nginx_conf/nginx.conf

  if check_https_enabled; then
    update_nginx_config_for_https
  else
    update_nginx_config_for_http
  fi
}

function init_env() {
    #ip to bind
    if [ -n "${NETWORK_DEFAULT_IP}" ]; then
      export SERVER_HOST=${NETWORK_DEFAULT_IP}
    else
      export SERVER_HOST=$(ip addr | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | awk -F '/' '{print $1}' | head -1)
      export NETWORK_DEFAULT_IP=${SERVER_HOST}
    fi
    echo "SERVER_HOST:${SERVER_HOST}"

    export PROG_ROOT_PATH="/usr/sbin"
    export USER_HOME="/home/service"
    export NGINX_START_USER="service"
    export NGINX_START_GROUP="servicegroup"
}

# 大 DSL 版本对比阈值：默认与前端 environment.ts 同值（压测前暂定 10MB / 上限 100MB），
# 一致性由 frontend/scripts/check-large-dsl-threshold-consistency.mjs 校验（npm run check:threshold）。
DEFAULT_LARGE_DSL_BYTES_THRESHOLD=10485760
MAX_LARGE_DSL_BYTES_THRESHOLD=104857600

# 静态首页统一初始化：模板恢复（无条件，保证占位符每次重新出现、重启不叠加）
#   + context_path 替换（保留原替换目标：首页 /openjiuwen/ 前缀 + nginx #rewritercontext_path rewrite）
#   + large_dsl 阈值注入（校验：正整数 + 长度<=9位 + <=MAX，防注入与 Bash 算术溢出；sed 零匹配也返回 0，
#     故替换前后 grep 显式检查，新脚本配旧前端产物等错误组合快速失败）。
# 由旧 add_context_path() 迁移整合而来，替换失败一律 exit 1 阻止启动，避免"配置表面存在实际未生效"。
function init_static_index(){
    local dist_dir="$nginx_dic/nginx/dist/hws"
    local index_html="$dist_dir/index.html"
    local template_html="$dist_dir/template_index.html"

    cd "$dist_dir" || { echo "[ERROR]: enter static path failed"; exit 1; }

    # 首次创建模板；之后每次启动从模板恢复 index.html（无论是否配置 context_path）
    if [ ! -f "$template_html" ]; then
      cp -v "$index_html" "$template_html" || { echo "[ERROR]: create template_index.html failed"; exit 1; }
    fi
    chmod 700 "$index_html"
    cp -f "$template_html" "$index_html" || { echo "[ERROR]: restore index.html failed"; exit 1; }

    # 1. context_path 替换（如有配置；替换目标与原实现一致，不能改成别的占位符）
    local context_path
    context_path=$(printenv "context_path")
    if [ -n "${context_path}" ]; then
      echo "start to replace console path: ${context_path}"
      sed -i "s#/openjiuwen/#${context_path}/openjiuwen/#g" "$index_html" \
        || { echo "[ERROR]: context_path index replace failed"; exit 1; }
      sed -i "s#\#rewritercontext_path#rewrite ^${context_path}/(.*) /\$1 last;#g" \
        "$nginx_conf/nginx.conf" \
        || { echo "[ERROR]: context_path nginx rewrite failed"; exit 1; }
      echo "finish to replace console path"
    else
      echo "skip replace console path: context_path is empty"
    fi

    # 2. large_dsl 阈值注入
    local val="${LARGE_DSL_BYTES_THRESHOLD:-$DEFAULT_LARGE_DSL_BYTES_THRESHOLD}"
    if ! [[ "$val" =~ ^[1-9][0-9]*$ ]]; then
      echo "[WARN]: invalid LARGE_DSL_BYTES_THRESHOLD '${val}', fallback to default"
      val="$DEFAULT_LARGE_DSL_BYTES_THRESHOLD"
    elif (( ${#val} > 9 )); then
      # 100MB 为 9 位数：先限长度再算术比较，避免超长数字串导致 Bash 算术溢出
      echo "[WARN]: LARGE_DSL_BYTES_THRESHOLD too long, fallback to default"
      val="$DEFAULT_LARGE_DSL_BYTES_THRESHOLD"
    elif (( val > MAX_LARGE_DSL_BYTES_THRESHOLD )); then
      echo "[WARN]: LARGE_DSL_BYTES_THRESHOLD > MAX, fallback to default"
      val="$DEFAULT_LARGE_DSL_BYTES_THRESHOLD"
    fi

    grep -q "large_dsl_placeholder" "$index_html" \
      || { echo "[ERROR]: large_dsl_placeholder not found (start.sh 与前端产物版本不匹配)"; exit 1; }
    sed -i "s/large_dsl_placeholder/${val}/g" "$index_html" \
      || { echo "[ERROR]: large_dsl replace failed"; exit 1; }
    grep -q "large_dsl_placeholder" "$index_html" \
      && { echo "[ERROR]: large_dsl_placeholder remains after replace"; exit 1; }
    echo "[INFO]: largeDslBytesThreshold = ${val}"

    chmod 500 "$index_html"
}

function start_nginx() {
  echo "[INFO]: Start to run nginx process"
    #启动Nginx进程
    nginx -g "daemon off;"

    TimeOut=30
    Num=0
    #等待Nginx启动完成
    while [ $Num -lt $TimeOut ]; do
      PID=$(ps -ef | grep "nginx" | grep "nginx: master process" | grep -v "grep" | awk '{print $2}')
      echo "[INFO]: nginx master process PID is ${PID}"
      if [ "$PID" != "" ]; then
        SUBPID=$(ps -ef | grep "nginx: worker process" | grep "$PID" | grep -v "grep" | awk '{print $2}')
        echo "[INFO]: nginx worker process PID is ${SUBPID}"
        if [ "$SUBPID" != "" ]; then
          break
        fi
      fi
      sleep 1
      Num=$(expr $Num + 1)
    done

    if [ $Num -eq $TimeOut ]; then
      echo "[ERROR]:start nginx timeout."
    fi
}


function main() {
  init_config_file

  init_env

  init_static_index

  start_nginx

 echo "[INFO]:main end"
}
main
