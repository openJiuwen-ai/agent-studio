#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONITOR_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$MONITOR_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

get_env() {
  local key="$1" default="${2:-}" val
  val=$(grep -E "^${key}=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true)
  echo "${val:-$default}"
}

if docker compose version &>/dev/null; then DC=(docker compose)
elif command -v docker-compose &>/dev/null; then DC=(docker-compose)
else log_error "docker compose 未安装"; exit 1; fi

ACTION="${1:-start}"
case "$ACTION" in start|stop|status|ps) ;; *) log_error "Usage: $0 [start|stop|status]"; exit 1 ;; esac

init_env() {
  if [ ! -f .env ]; then
    cp .env.template .env
    log_warn "已从 .env.template 生成 .env；请配置镜像仓库、网关地址、读写口令和 Grafana 管理员口令后重试"
    exit 0
  fi
}

migrate_legacy_env() {
  # 兼容旧版统一 Gateway 账号；保留旧键以便人工核对，但新编排只读取新键。
  if ! grep -q '^LOGS_WRITE_USER=' .env && grep -q '^LOGS_GATEWAY_USER=' .env; then
    local legacy_user legacy_password legacy_port query_password
    legacy_user=$(get_env LOGS_GATEWAY_USER logs)
    legacy_password=$(get_env LOGS_GATEWAY_PASSWORD)
    legacy_port=$(get_env LOGS_GATEWAY_HTTP_PORT 3100)
    query_password=$(openssl rand -hex 24)
    {
      echo
      echo '# 自动从旧版 Gateway 配置迁移；旧键不再读取。'
      echo "LOGS_WRITE_USER=${legacy_user}-write"
      echo "LOGS_WRITE_PASSWORD=${legacy_password}"
      echo 'LOGS_QUERY_USER=logs-query'
      echo "LOGS_QUERY_PASSWORD=${query_password}"
      echo "LOGS_GATEWAY_HTTPS_PORT=${legacy_port}"
      echo 'LOGS_GATEWAY_CERT_DAYS=825'
    } >> .env
    log_info "已将旧版单账号 Gateway 配置迁移为独立读写账号（未输出口令）"
  fi
}

validate_config() {
  local host write_user write_pw query_user query_pw
  host=$(get_env LOGS_GATEWAY_HOST)
  write_user=$(get_env LOGS_WRITE_USER)
  write_pw=$(get_env LOGS_WRITE_PASSWORD)
  query_user=$(get_env LOGS_QUERY_USER)
  query_pw=$(get_env LOGS_QUERY_PASSWORD)
  if [ -z "$host" ] || [ "$host" = "monitor.example.com" ]; then
    log_error "LOGS_GATEWAY_HOST 必须是 app 节点可访问、且与 TLS 证书 SAN 一致的域名或 IP"; exit 1
  fi
  if [ -z "$write_user" ] || [ -z "$query_user" ] || [ -z "$write_pw" ] || [ -z "$query_pw" ]; then
    log_error "LOGS_WRITE_* 与 LOGS_QUERY_* 均不能为空"; exit 1
  fi
  if [ "$write_pw" = "change-write-password" ] || [ "$query_pw" = "change-query-password" ]; then
    log_error "日志网关口令仍是模板默认值"; exit 1
  fi
  if [ "$write_user" = "$query_user" ] || [ "$write_pw" = "$query_pw" ]; then
    log_error "写入和查询必须使用不同的用户名及口令"; exit 1
  fi
  if [ "$(get_env GRAFANA_ADMIN_PASSWORD admin)" = "admin" ]; then
    log_warn "Grafana 管理员口令仍为 admin，正式环境应立即修改"
  fi
}

resolve_grafana_image() {
  local image repository tag
  image=$(get_env GRAFANA_IMAGE)
  repository=$(get_env GHCR_IMAGE_REPOSITORY)
  tag=$(get_env GRAFANA_IMAGE_TAG 11.3.0-0.29.0)
  if [ -n "$image" ]; then
    export GRAFANA_IMAGE="$image"
  elif [ -n "$repository" ]; then
    export GRAFANA_IMAGE="${repository}/grafana-victorialogs:${tag}"
  else
    log_error "请在 .env 中配置 GRAFANA_IMAGE 或 GHCR_IMAGE_REPOSITORY"; exit 1
  fi
}

gen_htpasswd() {
  local write_user write_pw query_user query_pw
  write_user=$(get_env LOGS_WRITE_USER); write_pw=$(get_env LOGS_WRITE_PASSWORD)
  query_user=$(get_env LOGS_QUERY_USER); query_pw=$(get_env LOGS_QUERY_PASSWORD)
  umask 027
  printf '%s:%s\n' "$write_user" "$(openssl passwd -apr1 "$write_pw")" > config/write.htpasswd
  printf '%s:%s\n' "$query_user" "$(openssl passwd -apr1 "$query_pw")" > config/query.htpasswd
  # nginx worker 需要读取 bind mount 文件；内容仅为 APR1 哈希，不含明文口令。
  chmod 644 config/write.htpasswd config/query.htpasswd
}

gen_tls() {
  local host days san
  host=$(get_env LOGS_GATEWAY_HOST); days=$(get_env LOGS_GATEWAY_CERT_DAYS 825)
  if [ ! -s config/gateway.crt ] || [ ! -s config/gateway.key ]; then
    if [[ "$host" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || [[ "$host" == *:* ]]; then
      san="IP:${host}"
    else
      san="DNS:${host}"
    fi
    log_info "为 ${host} 生成自签名 TLS 证书"
    openssl req -x509 -nodes -newkey rsa:2048 -days "$days" \
      -keyout config/gateway.key -out config/gateway.crt \
      -subj "/CN=${host}" -addext "subjectAltName=${san}" >/dev/null 2>&1
    chmod 600 config/gateway.key
  fi
  cp config/gateway.crt config/gateway-ca.crt
  chmod 644 config/gateway.crt config/gateway-ca.crt
}

do_start() {
  init_env; migrate_legacy_env; validate_config; resolve_grafana_image; gen_htpasswd; gen_tls
  local project
  project=$(get_env MONITOR_PROJECT_NAME observability-monitor)
  log_info "启动 VictoriaLogs、TLS 网关和 Grafana..."
  "${DC[@]}" -p "$project" --env-file .env -f docker-compose.monitor.yml up -d --wait
  local host port grafana_port
  host=$(get_env LOGS_GATEWAY_HOST); port=$(get_env LOGS_GATEWAY_HTTPS_PORT 3100); grafana_port=$(get_env GRAFANA_PORT 3000)
  log_info "Grafana: http://${host}:${grafana_port}/"
  log_info "日志 HTTPS 网关: https://${host}:${port}/"
  log_info "将 config/gateway-ca.crt 安全复制到每个 app 节点同一路径，再执行 ./deploy.sh logging-remote"
}

do_stop() {
  local project; project=$(get_env MONITOR_PROJECT_NAME observability-monitor)
  if [ -f .env ]; then "${DC[@]}" -p "$project" --env-file .env -f docker-compose.monitor.yml down
  else "${DC[@]}" -p "$project" -f docker-compose.monitor.yml down; fi
}
do_status() {
  local project; project=$(get_env MONITOR_PROJECT_NAME observability-monitor)
  if [ -f .env ]; then "${DC[@]}" -p "$project" --env-file .env -f docker-compose.monitor.yml ps
  else "${DC[@]}" -p "$project" -f docker-compose.monitor.yml ps; fi
}

case "$ACTION" in start) do_start ;; stop) do_stop ;; status|ps) do_status ;; esac
