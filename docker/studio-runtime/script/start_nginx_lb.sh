#!/bin/bash
#
# Nginx load balancing mode entry point.
# Starts multiple Workers + Nginx, then watchdog.
# All logic in shell — does not depend on nginx_launcher.py or jinja2.
# Uses http reverse proxy (not stream) for broad nginx compatibility.
#
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#

umask 0027

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
NGINX_DIR=$(cd "${SCRIPT_DIR}/../nginx" && pwd)

# Compute the CPU count visible to this container, respecting cgroup CPU limits.
# K8s cpu request/limit sets a CFS quota but does not change sched_getaffinity,
# so `nproc` alone returns the HOST cpu count and over-provisions workers
# (e.g. 64-core node → 65 workers → OOM in a 4Gi pod). The default worker count
# below is this cgroup-aware cpu count + 1.
function _cpu_count() {
  local quota period
  if [[ -r /sys/fs/cgroup/cpu.max ]]; then            # cgroup v2
    read -r quota period < /sys/fs/cgroup/cpu.max
    if [[ "${quota}" =~ ^[0-9]+$ && "${period}" =~ ^[0-9]+$ && "${period}" -gt 0 && "${quota}" -gt 0 ]]; then
      echo $(( (quota + period - 1) / period ))
      return
    fi
  fi
  if [[ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us && -r /sys/fs/cgroup/cpu/cpu.cfs_period_us ]]; then  # cgroup v1
    quota=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null)
    period=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null)
    if [[ "${quota}" =~ ^[0-9]+$ && "${period}" =~ ^[0-9]+$ && "${period}" -gt 0 && "${quota}" -gt 0 ]]; then
      echo $(( (quota + period - 1) / period ))
      return
    fi
  fi
  nproc 2>/dev/null || echo 1                         # fallback: host online cpus
}

SERVER_PORT=${PORT:-8000}
DEFAULT_WORKER_NUM=$(( $(_cpu_count) + 1 ))
WORKER_NUM=${GUNICORN_WORK_NUM:-${DEFAULT_WORKER_NUM}}
LB_STRATEGY=${LB_STRATEGY:-least_conn}
LOG_DIR=${NGINX_LOG_DIR:-${LOGGING_LOG_PATH:-/opt/cloud/logs}}
NGINX_CONF="${LOG_DIR}/nginx.conf"
NGINX_PID="${LOG_DIR}/nginx.pid"

# CRITICAL: Force each Worker process to run as single-worker uvicorn.
# Without this, each Worker spawns GUNICORN_WORK_NUM uvicorn children,
# causing 4*4=16 processes and OOM in 4Gi containers.
export GUNICORN_WORK_NUM=1

# Save original WORKER_NUM for display (before GUNICORN_WORK_NUM override)
DISPLAY_WORKER_NUM=${WORKER_NUM}

# Export the real nginx-upstream worker count for watchdog.sh.
# GUNICORN_WORK_NUM is overridden to 1 above (to force single-process uvicorn),
# so watchdog must not reuse it as the number of ports to monitor.
export LB_WORKER_NUM=${DISPLAY_WORKER_NUM}

function generate_nginx_conf() {
  echo "Generating nginx.conf: strategy=${LB_STRATEGY}, server_port=${SERVER_PORT}, workers=${DISPLAY_WORKER_NUM}"

  mkdir -p ${LOG_DIR}/nginx

  # Build upstream server list
  UPSTREAM_SERVERS=""
  for i in $(seq 1 ${DISPLAY_WORKER_NUM}); do
    WORKER_PORT=$((SERVER_PORT + i))
    UPSTREAM_SERVERS="${UPSTREAM_SERVERS}
        server 127.0.0.1:${WORKER_PORT} max_fails=3 fail_timeout=30s;"
  done

  # Build strategy directive
  STRATEGY_LINE=""
  if [[ "${LB_STRATEGY}" == "least_conn" ]]; then
    STRATEGY_LINE="        least_conn;"
  elif [[ "${LB_STRATEGY}" == "ip_hash" ]]; then
    STRATEGY_LINE="        ip_hash;"
  fi
  # round_robin: no directive needed (default)

  # Build listen + SSL
  if [[ "${RUN_WITH_ENGINE}" == "true" ]]; then
    LISTEN_ADDR="127.0.0.1:${SERVER_PORT}"
  else
    LISTEN_ADDR="0.0.0.0:${SERVER_PORT}"
  fi

  SSL_BLOCK=""
  LISTEN_DIRECTIVE="listen ${LISTEN_ADDR};"
  if [[ "${HTTPS}" == "true" ]]; then
    LISTEN_DIRECTIVE="listen ${LISTEN_ADDR} ssl;"
    SSL_BLOCK="
        ssl_certificate      ${TLS_CERT_PATH};
        ssl_certificate_key  ${TLS_CERT_KEY_PATH};
        ssl_protocols        TLSv1.2 TLSv1.3;
        ssl_ciphers          ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers on;"
  fi

  # Build proxy_pass scheme — must match Worker's protocol
  if [[ "${HTTPS}" == "true" ]]; then
    PROXY_SCHEME="https"
    # Workers use self-signed certs — skip SSL verification on the proxy side
    PROXY_SSL_BLOCK="
            proxy_ssl_verify off;
            proxy_ssl_server_name on;"
  else
    PROXY_SCHEME="http"
    PROXY_SSL_BLOCK=""
  fi

  # Use http reverse proxy instead of stream module.
  # stream module may not be compiled into all nginx builds;
  # http proxy_pass with buffering disabled works equally well for SSE.
  cat > ${NGINX_CONF} <<NGINXEOF
daemon off;
worker_processes auto;
error_log ${LOG_DIR}/nginx/error.log;
pid ${NGINX_PID};

events {
    worker_connections 1024;
}

http {
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent"';
    access_log ${LOG_DIR}/nginx/access.log main;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream backend_workers {
${STRATEGY_LINE}
${UPSTREAM_SERVERS}
    }

    server {
        ${LISTEN_DIRECTIVE}
        client_max_body_size 0;

        location / {
            proxy_pass ${PROXY_SCHEME}://backend_workers;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            # SSE: disable buffering so events are forwarded immediately
            proxy_buffering off;
            proxy_cache off;
            chunked_transfer_encoding on;
            proxy_read_timeout 900s;
            proxy_send_timeout 900s;${PROXY_SSL_BLOCK}
        }${SSL_BLOCK}
    }
}
NGINXEOF

  echo "Nginx config written to: ${NGINX_CONF}"
  echo "--- nginx.conf content ---"
  cat ${NGINX_CONF}
  echo "--- end nginx.conf ---"
}

function start_workers() {
  echo "Starting ${DISPLAY_WORKER_NUM} workers..."
  for i in $(seq 1 ${DISPLAY_WORKER_NUM}); do
    WORKER_PORT=$((SERVER_PORT + i))
    echo "Starting worker on port ${WORKER_PORT}..."
    bash ${SCRIPT_DIR}/start_server.sh ${WORKER_PORT}
  done
}

function wait_for_workers() {
  HEALTH_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
  MAX_WAIT=180
  ELAPSED=0

  echo "Waiting for workers to be healthy (max ${MAX_WAIT}s)..."
  while [[ ${ELAPSED} -lt ${MAX_WAIT} ]]; do
    ALL_READY=true
    for i in $(seq 1 ${DISPLAY_WORKER_NUM}); do
      WORKER_PORT=$((SERVER_PORT + i))
      if [[ "${HTTPS}" == "true" ]]; then
        curl -sk --max-time 3 "https://127.0.0.1:${WORKER_PORT}/v1/health" > /dev/null 2>&1
      else
        curl -s --max-time 3 "http://127.0.0.1:${WORKER_PORT}/v1/health" > /dev/null 2>&1
      fi
      if [[ $? -ne 0 ]]; then
        ALL_READY=false
        break
      fi
    done

    if [[ "${ALL_READY}" == "true" ]]; then
      echo "All workers are healthy"
      return 0
    fi

    sleep 5
    ELAPSED=$((ELAPSED + 5))
  done

  echo "WARNING: Not all workers became healthy within ${MAX_WAIT}s" >&2
  return 1
}

function start_nginx_process() {
  # Prefer RELOAD over stop+start when nginx is already running.
  # stop+start releases the listening socket for a moment and races with the
  # supervisor while[1] loop at the bottom of this script, which would see nginx
  # "die", call start_nginx_process again, and collide on port 8000. reload
  # re-reads the config (picking up any new upstream list) without ever
  # releasing the socket, so port 8000 stays bound and the old supervisor never
  # sees nginx die. This also makes the script safe to re-run after a code
  # change (the whole point of restarting here).
  if [[ -f ${NGINX_PID} ]]; then
    OLD_PID=$(cat ${NGINX_PID} 2>/dev/null)
    if [[ -n "${OLD_PID}" ]] && kill -0 ${OLD_PID} 2>/dev/null; then
      echo "Reloading existing nginx (PID ${OLD_PID})..."
      if nginx -c ${NGINX_CONF} -s reload 2>/dev/null; then
        # Keep NGINX_PID pointing at the live master so the while[1] loop
        # monitors the right PID (the master survives a reload).
        NGINX_PID=${OLD_PID}
        return 0
      fi
      echo "Reload failed, falling back to stop+start (PID ${OLD_PID})..."
      kill ${OLD_PID} 2>/dev/null || true
      sleep 2
      kill -9 ${OLD_PID} 2>/dev/null || true
    fi
  fi

  echo "Starting nginx..."
  nginx -c ${NGINX_CONF} &
  NGINX_PID=$!
  echo "Nginx started with PID ${NGINX_PID}"
}

function after_start(){
  if [[ "${open_permissions}" == "true" ]]; then
    echo "---> change logs permission and umask"
    chmod -R 755 "${LOGGING_LOG_PATH}"
    umask 0022
  fi

  nohup bash -c "source ${SCRIPT_DIR}/cron_job.sh && start_cron_job" &
}

function cleanup_previous() {
  echo "Cleaning up previous instance before restart..."

  # Stop old watchdog(s). During the restart window workers are briefly down,
  # and a live watchdog would fire start_server.sh and re-bind occupied worker
  # ports (8001+) -> "address already in use". watchdog.sh is NOT the
  # container's PID 1, so killing it is safe. (We must NOT kill the old
  # start_nginx_lb.sh supervisor loop itself -- it is the container entrypoint's
  # keep-alive child; killing it would tear down the container. With the
  # reload-based nginx path above, that loop is now harmless.)
  pkill -f "watchdog.sh" 2>/dev/null || true
  # Reset watchdog fail counters so the fresh watchdog doesn't inherit a
  # near-threshold count from the previous run.
  rm -f "${WATCHDOG_LOG_DIR:-/opt/cloud/logs/watchdog}"/fail_*.count 2>/dev/null || true

  # Kill ALL old workers globally. The per-port argv grep in start_server.sh is
  # unreliable: uvicorn/gunicorn re-exec, argv rewrite, or ps truncation can
  # leave a stale worker holding a port, and the new worker then fails to bind.
  # This runs BEFORE any new worker is started, so it cannot touch the new ones.
  pkill -9 -f "EIStart" 2>/dev/null || true
  sleep 1
}

function main() {
  chmod 750 ${SERVICE_HOME}

  # 0. Tear down previous workers/watchdog so this re-run doesn't collide with
  # stale processes on the worker ports. (Nginx is handled by reload above.)
  cleanup_previous

  echo "=========================================="
  echo "Nginx Load Balancing Mode"
  echo "  SERVER_PORT=${SERVER_PORT}"
  echo "  WORKER_NUM=${DISPLAY_WORKER_NUM}"
  echo "  LB_STRATEGY=${LB_STRATEGY}"
  echo "  Worker ports: $((SERVER_PORT+1)) to $((SERVER_PORT+DISPLAY_WORKER_NUM))"
  echo "=========================================="

  # 1. Generate nginx config
  generate_nginx_conf

  # 2. Start all workers
  start_workers

  # 3. Wait for workers to be healthy
  wait_for_workers

  # 4. Start nginx
  start_nginx_process

  # 5. Start watchdog (delayed, LB mode only alerts)
  nohup bash -c "sleep 60; bash ${SCRIPT_DIR}/watchdog.sh" >> ${LOG_DIR}/watchdog.log 2>&1 &
  echo "watchdog will start in 60 seconds"

  after_start
}

main

# Keep container alive
while [ 1 ]; do
  # Monitor nginx: if it dies, restart it
  if ! kill -0 ${NGINX_PID} 2>/dev/null; then
    echo "WARNING: Nginx process died, restarting..." >> ${LOG_DIR}/nginx_restart.log
    start_nginx_process
  fi
  sleep 10
done