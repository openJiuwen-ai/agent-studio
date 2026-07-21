#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OBS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$OBS_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
get_env() { local v; v=$(grep -E "^${1}=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true); echo "${v:-${2:-}}"; }

if docker compose version &>/dev/null; then DC=(docker compose)
elif command -v docker-compose &>/dev/null; then DC=(docker-compose)
else log_error "docker compose 未安装"; exit 1; fi
VECTOR_PROJECT=$(get_env VECTOR_PROJECT_NAME observability-agent)
if [ -f .env ]; then
  DC_VECTOR=("${DC[@]}" -p "$VECTOR_PROJECT" --env-file .env -f docker-compose.vector.yml)
else
  DC_VECTOR=("${DC[@]}" -p "$VECTOR_PROJECT" -f docker-compose.vector.yml)
fi

init_env() {
  if [ ! -f .env ]; then
    cp .env.template .env
    chmod 600 .env
    log_warn "已生成 .env；请填写 LOGS_GATEWAY_HOST、LOGS_WRITE_* 和 NODE_NAME 后重试"
    exit 0
  fi
}

migrate_legacy_env() {
  if ! grep -q '^LOGS_WRITE_USER=' .env && grep -q '^LOGS_GATEWAY_USER=' .env; then
    {
      echo
      echo '# 自动从旧版 app 节点 Gateway 配置迁移；旧键不再读取。'
      echo "LOGS_WRITE_USER=$(get_env LOGS_GATEWAY_USER logs)-write"
      echo "LOGS_WRITE_PASSWORD=$(get_env LOGS_GATEWAY_PASSWORD)"
      echo "LOGS_GATEWAY_HTTPS_PORT=$(get_env LOGS_GATEWAY_HTTP_PORT 3100)"
    } >> .env
    log_info "已迁移旧版 Gateway 写入配置（未输出口令）"
  fi
}

validate_config() {
  local host user password
  host=$(get_env LOGS_GATEWAY_HOST); user=$(get_env LOGS_WRITE_USER); password=$(get_env LOGS_WRITE_PASSWORD)
  if [ -z "$host" ] || [ "$host" = "monitor.example.com" ]; then log_error "LOGS_GATEWAY_HOST 无效"; exit 1; fi
  if [ -z "$user" ] || [ -z "$password" ] || [ "$password" = "change-write-password" ]; then
    log_error "LOGS_WRITE_USER/LOGS_WRITE_PASSWORD 未正确配置"; exit 1
  fi
  if [ ! -s config/gateway-ca.crt ]; then
    log_error "缺少 config/gateway-ca.crt；请从监控节点安全复制该 CA 证书"; exit 1
  fi
}

validate_volumes() {
  local project missing=0 volume
  project=$(get_env APP_PROJECT_NAME deploy)
  for volume in manager_logs runtime_logs builder_logs console_logs; do
    if ! docker volume inspect "${project}_${volume}" >/dev/null 2>&1; then
      log_warn "缺少卷 ${project}_${volume}，请先启动或重建 app 服务"
      missing=1
    fi
  done
  [ "$missing" -eq 0 ] || { log_error "Vector 所需日志卷不完整"; exit 1; }
}

check_gateway() {
  local host port
  host=$(get_env LOGS_GATEWAY_HOST); port=$(get_env LOGS_GATEWAY_HTTPS_PORT 3100)
  if command -v timeout >/dev/null && timeout 3 bash -c "</dev/tcp/${host}/${port}" 2>/dev/null; then
    log_info "日志网关可达 (${host}:${port})"
  else
    log_warn "日志网关暂不可达；Vector 会把新日志缓存在磁盘并持续重试"
  fi
}

do_start() {
  init_env; migrate_legacy_env; validate_config; validate_volumes; check_gateway
  "${DC_VECTOR[@]}" up -d --wait
  log_info "Vector 已启动；状态: http://127.0.0.1:8686/health"
  log_info "排障: docker compose --env-file .env -f docker-compose.vector.yml logs --tail 50 vector"
}
do_stop() { "${DC_VECTOR[@]}" down; }
do_status() { "${DC_VECTOR[@]}" ps; }

case "${1:-start}" in start) do_start ;; stop) do_stop ;; status|ps) do_status ;; *) log_error "Usage: $0 [start|stop|status]"; exit 1 ;; esac
