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
case "$ACTION" in
  start|stop|status|ps|cert-status|prepare-cert|activate-cert|finalize-cert|prepare-credentials|finalize-credentials) ;;
  *) log_error "Usage: $0 [start|stop|status|cert-status|prepare-cert|activate-cert|finalize-cert|prepare-credentials|finalize-credentials]"; exit 1 ;;
esac

init_env() {
  if [ ! -f .env ]; then
    cp .env.template .env
    chmod 600 .env
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
  local host write_user write_pw query_user query_pw max_disk_usage min_free_disk
  host=$(get_env LOGS_GATEWAY_HOST)
  write_user=$(get_env LOGS_WRITE_USER)
  write_pw=$(get_env LOGS_WRITE_PASSWORD)
  query_user=$(get_env LOGS_QUERY_USER)
  query_pw=$(get_env LOGS_QUERY_PASSWORD)
  max_disk_usage=$(get_env VICTORIA_LOGS_MAX_DISK_USAGE_BYTES 10737418240)
  min_free_disk=$(get_env VICTORIA_LOGS_MIN_FREE_DISK_BYTES 2147483648)
  if [ -z "$host" ] || [ "$host" = "monitor.example.com" ]; then
    log_error "LOGS_GATEWAY_HOST 必须是 app 节点可访问、且与 TLS 证书 SAN 一致的域名或 IP"; exit 1
  fi
  if [ -z "$write_user" ] || [ -z "$query_user" ] || [ -z "$write_pw" ] || [ -z "$query_pw" ]; then
    log_error "LOGS_WRITE_* 与 LOGS_QUERY_* 均不能为空"; exit 1
  fi
  if ! [[ "$write_user" =~ ^[A-Za-z0-9._-]+$ ]] || ! [[ "$query_user" =~ ^[A-Za-z0-9._-]+$ ]]; then
    log_error "日志网关用户名仅允许字母、数字、点、下划线和连字符"; exit 1
  fi
  if [ "$write_pw" = "change-write-password" ] || [ "$query_pw" = "change-query-password" ]; then
    log_error "日志网关口令仍是模板默认值"; exit 1
  fi
  if [ "$write_user" = "$query_user" ] || [ "$write_pw" = "$query_pw" ]; then
    log_error "写入和查询必须使用不同的用户名及口令"; exit 1
  fi
  if ! [[ "$max_disk_usage" =~ ^[1-9][0-9]*$ ]]; then
    log_error "VICTORIA_LOGS_MAX_DISK_USAGE_BYTES 必须是大于 0 的字节数，禁止无限制写盘"; exit 1
  fi
  if ! [[ "$min_free_disk" =~ ^[1-9][0-9]*$ ]]; then
    log_error "VICTORIA_LOGS_MIN_FREE_DISK_BYTES 必须是大于 0 的字节数"; exit 1
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
  local write_user write_pw query_user query_pw next_user next_pw
  write_user=$(get_env LOGS_WRITE_USER); write_pw=$(get_env LOGS_WRITE_PASSWORD)
  query_user=$(get_env LOGS_QUERY_USER); query_pw=$(get_env LOGS_QUERY_PASSWORD)
  umask 027
  printf '%s:%s\n' "$write_user" "$(openssl passwd -apr1 "$write_pw")" > config/write.htpasswd
  printf '%s:%s\n' "$query_user" "$(openssl passwd -apr1 "$query_pw")" > config/query.htpasswd
  next_user=$(get_env LOGS_WRITE_USER_NEXT); next_pw=$(get_env LOGS_WRITE_PASSWORD_NEXT)
  if [ -n "$next_user" ] && [ -n "$next_pw" ]; then
    printf '%s:%s\n' "$next_user" "$(openssl passwd -apr1 "$next_pw")" >> config/write.htpasswd
  fi
  next_user=$(get_env LOGS_QUERY_USER_NEXT); next_pw=$(get_env LOGS_QUERY_PASSWORD_NEXT)
  if [ -n "$next_user" ] && [ -n "$next_pw" ]; then
    printf '%s:%s\n' "$next_user" "$(openssl passwd -apr1 "$next_pw")" >> config/query.htpasswd
  fi
  # nginx worker 需要读取 bind mount 文件；内容仅为 APR1 哈希，不含明文口令。
  chmod 644 config/write.htpasswd config/query.htpasswd
}

tls_san() {
  local host="$1"
  if [[ "$host" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || [[ "$host" == *:* ]]; then
    echo "IP:${host}"
  else
    echo "DNS:${host}"
  fi
}

generate_cert() {
  local cert="$1" key="$2" host days
  host=$(get_env LOGS_GATEWAY_HOST); days=$(get_env LOGS_GATEWAY_CERT_DAYS 825)
  openssl req -x509 -nodes -newkey rsa:2048 -days "$days" \
    -keyout "$key" -out "$cert" -subj "/CN=${host}" \
    -addext "subjectAltName=$(tls_san "$host")" >/dev/null 2>&1
  chmod 600 "$key"; chmod 644 "$cert"
}

gen_tls() {
  local host
  host=$(get_env LOGS_GATEWAY_HOST)
  if [ ! -s config/gateway.crt ] || [ ! -s config/gateway.key ]; then
    log_info "为 ${host} 生成自签名 TLS 证书"
    generate_cert config/gateway.crt config/gateway.key
  fi
  if [ -s config/gateway-next.crt ]; then
    cat config/gateway.crt config/gateway-next.crt > config/gateway-ca.crt
  elif [ -s config/gateway-previous.crt ]; then
    cat config/gateway-previous.crt config/gateway.crt > config/gateway-ca.crt
  else
    cp config/gateway.crt config/gateway-ca.crt
  fi
  chmod 644 config/gateway.crt config/gateway-ca.crt
}

compose_gateway_reload() {
  local project; project=$(get_env MONITOR_PROJECT_NAME observability-monitor)
  "${DC[@]}" -p "$project" --env-file .env -f docker-compose.monitor.yml exec -T nginx-gateway nginx -s reload
}

do_cert_status() {
  init_env
  for cert in config/gateway.crt config/gateway-next.crt config/gateway-previous.crt; do
    [ -s "$cert" ] || continue
    echo "--- ${cert}"
    openssl x509 -in "$cert" -noout -subject -issuer -dates -ext subjectAltName
    if openssl x509 -in "$cert" -checkend 2592000 -noout >/dev/null; then
      log_info "证书至少 30 天内有效"
    else
      log_warn "证书将在 30 天内过期或已经过期"
    fi
  done
}

do_prepare_cert() {
  init_env; validate_config
  [ ! -e config/gateway-next.crt ] && [ ! -e config/gateway-next.key ] || { log_error "next 证书已存在，请先完成或清理当前轮换"; exit 1; }
  gen_tls
  generate_cert config/gateway-next.crt config/gateway-next.key
  cat config/gateway.crt config/gateway-next.crt > config/gateway-ca.crt
  chmod 644 config/gateway-ca.crt
  log_info "已生成新证书和新旧 CA bundle；先把 config/gateway-ca.crt 安全分发到所有 app 节点并重启远程 Vector"
}

do_activate_cert() {
  init_env
  [ -s config/gateway-next.crt ] && [ -s config/gateway-next.key ] || { log_error "请先执行 prepare-cert"; exit 1; }
  cp config/gateway.crt config/gateway-previous.crt
  cp config/gateway.key config/gateway-previous.key
  cp config/gateway-next.crt config/gateway.crt
  cp config/gateway-next.key config/gateway.key
  cat config/gateway-previous.crt config/gateway.crt > config/gateway-ca.crt
  rm -f config/gateway-next.crt config/gateway-next.key
  compose_gateway_reload
  log_info "网关已启用新证书；确认所有 app 节点持续写入后执行 finalize-cert"
}

do_finalize_cert() {
  init_env
  [ -s config/gateway-previous.crt ] || { log_error "没有待完成的证书轮换"; exit 1; }
  cp config/gateway.crt config/gateway-ca.crt
  rm -f config/gateway-previous.crt config/gateway-previous.key
  log_info "已淘汰旧 CA；请再次分发 config/gateway-ca.crt 并在 app 节点重启远程 Vector"
}

validate_next_credentials() {
  local key value next_write_user next_query_user
  for key in LOGS_WRITE_USER_NEXT LOGS_WRITE_PASSWORD_NEXT LOGS_QUERY_USER_NEXT LOGS_QUERY_PASSWORD_NEXT; do
    value=$(get_env "$key")
    [ -n "$value" ] || { log_error "${key} 未配置"; exit 1; }
  done
  next_write_user=$(get_env LOGS_WRITE_USER_NEXT); next_query_user=$(get_env LOGS_QUERY_USER_NEXT)
  [[ "$next_write_user" =~ ^[A-Za-z0-9._-]+$ ]] && [[ "$next_query_user" =~ ^[A-Za-z0-9._-]+$ ]] || { log_error "新用户名包含非法字符"; exit 1; }
  [ "$next_write_user" != "$next_query_user" ] || { log_error "新读写用户名不能相同"; exit 1; }
  [ "$(get_env LOGS_WRITE_PASSWORD_NEXT)" != "$(get_env LOGS_QUERY_PASSWORD_NEXT)" ] || { log_error "新读写口令不能相同"; exit 1; }
  [ "$next_write_user" != "$(get_env LOGS_WRITE_USER)" ] || { log_error "新写入用户名必须区别于旧用户名，以支持重叠轮换"; exit 1; }
  [ "$next_query_user" != "$(get_env LOGS_QUERY_USER)" ] || { log_error "新查询用户名必须区别于旧用户名，以支持重叠轮换"; exit 1; }
}

rewrite_env_credentials() {
  local tmp=".env.rotation.$$"
  awk -F= '
    !/^LOGS_WRITE_USER=/ && !/^LOGS_WRITE_PASSWORD=/ && !/^LOGS_QUERY_USER=/ && !/^LOGS_QUERY_PASSWORD=/ &&
    !/^LOGS_WRITE_USER_NEXT=/ && !/^LOGS_WRITE_PASSWORD_NEXT=/ && !/^LOGS_QUERY_USER_NEXT=/ && !/^LOGS_QUERY_PASSWORD_NEXT=/ { print }
  ' .env > "$tmp"
  {
    echo "LOGS_WRITE_USER=$(get_env LOGS_WRITE_USER_NEXT)"
    echo "LOGS_WRITE_PASSWORD=$(get_env LOGS_WRITE_PASSWORD_NEXT)"
    echo "LOGS_QUERY_USER=$(get_env LOGS_QUERY_USER_NEXT)"
    echo "LOGS_QUERY_PASSWORD=$(get_env LOGS_QUERY_PASSWORD_NEXT)"
  } >> "$tmp"
  chmod --reference=.env "$tmp"; mv "$tmp" .env
}

do_prepare_credentials() {
  init_env; validate_next_credentials; gen_htpasswd; compose_gateway_reload
  log_info "网关已同时接受新旧凭据；把 app 节点 LOGS_WRITE_* 切换为 NEXT 值并重启远程 Vector"
}

do_finalize_credentials() {
  init_env; validate_next_credentials
  rewrite_env_credentials
  gen_htpasswd; compose_gateway_reload
  log_info "新凭据已提升为当前值，旧凭据已失效（未输出任何明文口令）"
}

do_start() {
  init_env; migrate_legacy_env; validate_config; resolve_grafana_image; gen_htpasswd; gen_tls
  local project
  project=$(get_env MONITOR_PROJECT_NAME observability-monitor)
  log_info "启动 VictoriaLogs、TLS 网关、监控节点 Vector 和 Grafana..."
  "${DC[@]}" -p "$project" --env-file .env -f docker-compose.monitor.yml up -d --wait
  local host port grafana_port
  host=$(get_env LOGS_GATEWAY_HOST); port=$(get_env LOGS_GATEWAY_HTTPS_PORT 3100); grafana_port=$(get_env GRAFANA_PORT 3000)
  log_info "Grafana: http://${host}:${grafana_port}/"
  log_info "日志 HTTPS 网关: https://${host}:${port}/"
  log_info "将 config/gateway-ca.crt 安全复制到每个 app 节点同一路径，再执行 bash ../deploy.sh logging-remote"
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

case "$ACTION" in
  start) do_start ;; stop) do_stop ;; status|ps) do_status ;;
  cert-status) do_cert_status ;; prepare-cert) do_prepare_cert ;; activate-cert) do_activate_cert ;; finalize-cert) do_finalize_cert ;;
  prepare-credentials) do_prepare_credentials ;; finalize-credentials) do_finalize_credentials ;;
esac
