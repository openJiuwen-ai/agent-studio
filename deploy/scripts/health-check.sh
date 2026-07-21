#!/usr/bin/env bash
# ============================================================
# openJiuwen AgentStudio — 健康检查脚本
# 执行环境：部署目标机器
# 执行方式：bash deploy/scripts/health-check.sh
# 前置条件：服务已启动
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${DEPLOY_DIR}/.env"

# ========================================
# 从 .env 文件安全读取配置值（不使用 source，避免注入风险）
# ========================================
get_env_value() {
    local key="$1"
    local default_value="${2:-}"
    local value
    value=$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -n 1 | cut -d'=' -f2- || true)
    value=${value%$'\r'}
    if [ -n "$value" ]; then
        printf "%s" "$value"
    else
        printf "%s" "$default_value"
    fi
}

# 加载配置
CONSOLE_PORT=$(get_env_value CONSOLE_PORT 80)
MANAGER_PORT=$(get_env_value MANAGER_PORT 31111)
RUNTIME_PORT=$(get_env_value RUNTIME_PORT 31014)
BUILDER_PORT=$(get_env_value BUILDER_PORT 31015)
HOST_IP=$(get_env_value HOST_IP 127.0.0.1)

# ========================================
# TCP 端口检查（支持 /dev/tcp、nc、curl 多种方式）
# ========================================
check_port() {
    local name="$1"
    local host="$2"
    local port="$3"

    if timeout 3 bash -c "echo > /dev/tcp/${host}/${port}" 2>/dev/null; then
        log_info "${name} (${host}:${port}) ✓ 端口可达"
        return 0
    elif command -v nc &>/dev/null && timeout 3 nc -z "${host}" "${port}" 2>/dev/null; then
        log_info "${name} (${host}:${port}) ✓ 端口可达 (nc)"
        return 0
    elif command -v curl &>/dev/null && curl -sf --connect-timeout 3 "http://${host}:${port}" &>/dev/null; then
        log_info "${name} (${host}:${port}) ✓ 端口可达 (curl)"
        return 0
    else
        log_error "${name} (${host}:${port}) ✗ 端口不可达"
        return 1
    fi
}

# ========================================
# HTTP 健康检查
# ========================================
check_http() {
    local name="$1"
    local url="$2"

    if ! command -v curl &>/dev/null; then
        log_warn "${name} — curl 未安装，跳过 HTTP 检查"
        return 1
    fi

    local http_code
    http_code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "${url}" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        log_info "${name} ✓ HTTP ${http_code}"
        return 0
    else
        log_warn "${name} — HTTP ${http_code}: ${url}"
        return 1
    fi
}

# ========================================
# 外部依赖检查
# ========================================
check_dependencies() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "  外部依赖连通性检查"
    echo "─────────────────────────────────────────"

    # 数据库
    local datasource_url
    datasource_url=$(get_env_value SPRING_DATASOURCE_URL "")
    if [ -n "${datasource_url}" ]; then
        local DB_HOST DB_PORT
        DB_HOST=$(echo "${datasource_url}" | sed -n 's/.*:\/\/\([^:\/]*\).*/\1/p')
        DB_PORT=$(echo "${datasource_url}" | sed -n 's/.*:\/\/[^:]*:\([0-9]*\).*/\1/p')
        if [ -n "${DB_HOST}" ] && [ -n "${DB_PORT}" ]; then
            check_port "数据库" "${DB_HOST}" "${DB_PORT}" || true
        fi
    fi

    # Redis
    local redis_host
    redis_host=$(get_env_value REDIS_HOST "")
    if [ -n "${redis_host}" ]; then
        local redis_port
        redis_port=$(get_env_value REDIS_PORT 6379)
        check_port "Redis" "${redis_host}" "${redis_port}" || true
    fi

    # 对象存储
    local obs_url
    obs_url=$(get_env_value OBS_URL "")
    if [ -n "${obs_url}" ]; then
        local OBS_HOST OBS_PORT
        OBS_HOST=$(echo "${obs_url}" | sed -n 's|.*://\([^:\/]*\).*|\1|p')
        OBS_PORT=$(echo "${obs_url}" | sed -n 's|.*://[^:]*:\([0-9]*\).*|\1|p')
        if [ -z "${OBS_PORT}" ]; then
            if echo "${obs_url}" | grep -q "https://"; then OBS_PORT=443; else OBS_PORT=9000; fi
        fi
        if [ -n "${OBS_HOST}" ]; then
            check_port "对象存储" "${OBS_HOST}" "${OBS_PORT}" || true
        fi
    fi
}

# ========================================
# 主流程
# ========================================
main() {
    echo ""
    echo "============================================================"
    echo "  openJiuwen AgentStudio — 健康检查"
    echo "============================================================"
    echo ""

    # 1. 外部依赖
    check_dependencies

    # 2. 服务端口
    echo ""
    echo "─────────────────────────────────────────"
    echo "  服务端口检查"
    echo "─────────────────────────────────────────"

    local pass=0
    local fail=0

    check_port "studio-console" "127.0.0.1" "${CONSOLE_PORT}" && pass=$((pass+1)) || fail=$((fail+1))
    check_port "studio-manager" "127.0.0.1" "${MANAGER_PORT}" && pass=$((pass+1)) || fail=$((fail+1))
    check_port "studio-runtime" "127.0.0.1" "${RUNTIME_PORT}" && pass=$((pass+1)) || fail=$((fail+1))
    check_port "studio-builder" "127.0.0.1" "${BUILDER_PORT}" && pass=$((pass+1)) || fail=$((fail+1))

    # 3. HTTP 健康端点
    echo ""
    echo "─────────────────────────────────────────"
    echo "  服务健康端点检查"
    echo "─────────────────────────────────────────"

    check_http "studio-manager" "http://${HOST_IP}:${MANAGER_PORT}/health" || true
    check_http "studio-runtime" "http://${HOST_IP}:${RUNTIME_PORT}/v1/health" || true
    check_http "studio-builder" "http://${HOST_IP}:${BUILDER_PORT}/v1/health" || true

    # 4. 前端页面
    echo ""
    echo "─────────────────────────────────────────"
    echo "  前端页面检查"
    echo "─────────────────────────────────────────"

    check_http "studio-console" "http://${HOST_IP}:${CONSOLE_PORT}/openjiuwen/" || true

    # 汇总
    echo ""
    echo "============================================================"
    if [ ${fail} -eq 0 ]; then
        log_info "所有服务端口检查通过 (${pass}/${pass})"
    else
        log_warn "端口检查：${pass} 通过，${fail} 失败"
        echo ""
        echo "  排查建议："
        echo "    查看容器状态：cd ${DEPLOY_DIR} && docker compose ps"
        echo "    查看容器日志：cd ${DEPLOY_DIR} && docker compose logs -f <服务名>"
        echo "    服务名列表：studio-console, studio-manager, studio-runtime, studio-builder"
    fi
    echo "============================================================"
}

main "$@"
