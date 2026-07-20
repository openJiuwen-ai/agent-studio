#!/usr/bin/env bash
# ============================================================
# openJiuwen AgentStudio 统一部署管理脚本
# 在线部署：IMAGE_SOURCE=ghcr/dockerhub，自动 pull 镜像
# 离线部署：IMAGE_SOURCE=offline，自动 docker load 镜像
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"
# project 名与 docker compose 默认值(目录名)保持一致
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$SCRIPT_DIR")}"

INFRA_SERVICES=(mysql redis minio minio-init)
APP_SERVICES=(studio-manager studio-runtime studio-builder studio-console)
ALL_SERVICES=("${INFRA_SERVICES[@]}" "${APP_SERVICES[@]}")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ========================================
# Docker Compose 检测
# ========================================
detect_compose_cmd() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD=(docker compose)
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD=(docker-compose)
    else
        COMPOSE_CMD=()
    fi
}

# ========================================
# 从 .env 文件读取配置值
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

require_env_value() {
    local key="$1"
    local value
    value=$(get_env_value "$key" "")
    if [ -z "$value" ]; then
        log_error "$key is required in $ENV_FILE"
        exit 1
    fi
}

# ========================================
# 镜像来源解析（在线/离线统一入口）
# ========================================
prepare_compose_env() {
    local image_source image_tag
    image_source=$(get_env_value IMAGE_SOURCE ghcr)
    image_tag=$(get_env_value IMAGE_TAG latest)

    case "$image_source" in
        ghcr|github)
            local ghcr_repo
            ghcr_repo=$(get_env_value GHCR_IMAGE_REPOSITORY "")
            require_env_value GHCR_IMAGE_REPOSITORY
            export STUDIO_CONSOLE_IMAGE="${ghcr_repo}/studio-console:${image_tag}"
            export STUDIO_MANAGER_IMAGE="${ghcr_repo}/studio-manager:${image_tag}"
            export STUDIO_RUNTIME_IMAGE="${ghcr_repo}/studio-runtime:${image_tag}"
            export STUDIO_BUILDER_IMAGE="${ghcr_repo}/studio-builder:${image_tag}"
            export APP_PULL_POLICY="always"
            ;;
        dockerhub|docker)
            local dockerhub_repo
            dockerhub_repo=$(get_env_value DOCKERHUB_IMAGE_REPOSITORY "")
            require_env_value DOCKERHUB_IMAGE_REPOSITORY
            export STUDIO_CONSOLE_IMAGE="${dockerhub_repo}:studio-console-${image_tag}"
            export STUDIO_MANAGER_IMAGE="${dockerhub_repo}:studio-manager-${image_tag}"
            export STUDIO_RUNTIME_IMAGE="${dockerhub_repo}:studio-runtime-${image_tag}"
            export STUDIO_BUILDER_IMAGE="${dockerhub_repo}:studio-builder-${image_tag}"
            export APP_PULL_POLICY="always"
            ;;
        offline)
            # 离线部署：镜像通过 docker load 加载，STUDIO_*_IMAGE 在 .env 中已指定
            require_env_value STUDIO_CONSOLE_IMAGE
            require_env_value STUDIO_MANAGER_IMAGE
            require_env_value STUDIO_RUNTIME_IMAGE
            require_env_value STUDIO_BUILDER_IMAGE
            export STUDIO_CONSOLE_IMAGE="$(get_env_value STUDIO_CONSOLE_IMAGE)"
            export STUDIO_MANAGER_IMAGE="$(get_env_value STUDIO_MANAGER_IMAGE)"
            export STUDIO_RUNTIME_IMAGE="$(get_env_value STUDIO_RUNTIME_IMAGE)"
            export STUDIO_BUILDER_IMAGE="$(get_env_value STUDIO_BUILDER_IMAGE)"
            export APP_PULL_POLICY="never"
            ;;
        custom)
            require_env_value STUDIO_CONSOLE_IMAGE
            require_env_value STUDIO_MANAGER_IMAGE
            require_env_value STUDIO_RUNTIME_IMAGE
            require_env_value STUDIO_BUILDER_IMAGE
            export STUDIO_CONSOLE_IMAGE="$(get_env_value STUDIO_CONSOLE_IMAGE)"
            export STUDIO_MANAGER_IMAGE="$(get_env_value STUDIO_MANAGER_IMAGE)"
            export STUDIO_RUNTIME_IMAGE="$(get_env_value STUDIO_RUNTIME_IMAGE)"
            export STUDIO_BUILDER_IMAGE="$(get_env_value STUDIO_BUILDER_IMAGE)"
            export APP_PULL_POLICY="$(get_env_value APP_PULL_POLICY 'if_not_present')"
            ;;
        *)
            log_error "Unsupported IMAGE_SOURCE '$image_source'. Use ghcr, dockerhub, offline, or custom."
            exit 1
            ;;
    esac

    # Grafana 是项目构建的定制镜像。优先使用显式地址；否则复用 GHCR 仓库前缀。
    # 非日志命令也需要给 Compose 一个合法值，但 start_logging 会严格校验来源。
    local grafana_image grafana_tag grafana_repo
    grafana_image=$(get_env_value GRAFANA_IMAGE "")
    grafana_tag=$(get_env_value GRAFANA_IMAGE_TAG "11.3.0-0.29.0")
    grafana_repo=$(get_env_value GHCR_IMAGE_REPOSITORY "")
    if [ -n "$grafana_image" ]; then
        export GRAFANA_IMAGE="$grafana_image"
    elif [ -n "$grafana_repo" ]; then
        export GRAFANA_IMAGE="${grafana_repo}/grafana-victorialogs:${grafana_tag}"
    else
        export GRAFANA_IMAGE="grafana-victorialogs:${grafana_tag}"
    fi
}

validate_logging_image_source() {
    if [ -z "$(get_env_value GRAFANA_IMAGE '')" ] && [ -z "$(get_env_value GHCR_IMAGE_REPOSITORY '')" ]; then
        log_error "Logging requires GRAFANA_IMAGE or GHCR_IMAGE_REPOSITORY in $ENV_FILE"
        exit 1
    fi
}

# ========================================
# Docker Compose 封装
# ========================================
compose() {
    prepare_compose_env
    "${COMPOSE_CMD[@]}" --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# ========================================
# 前置检查
# ========================================
check_docker_prerequisites() {
    log_info "Checking Docker prerequisites..."
    local missing=0

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        missing=1
    fi

    detect_compose_cmd
    if [ ${#COMPOSE_CMD[@]} -eq 0 ]; then
        log_error "Docker Compose is not installed"
        missing=1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        missing=1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$SCRIPT_DIR/.env.template" ]; then
            log_info ".env not found, creating from template..."
            cp "$SCRIPT_DIR/.env.template" "$ENV_FILE"
            log_info "Created $ENV_FILE with defaults (built-in infrastructure, IMAGE_SOURCE=ghcr)"
            log_warn "If using private registry or external infrastructure, edit .env first: vi $ENV_FILE"
        else
            log_error ".env not found and no .env.template available"
            missing=1
        fi
    fi

    if [ $missing -eq 1 ]; then
        exit 1
    fi

    log_info "Docker prerequisites satisfied"
}

check_runtime_prerequisites() {
    check_docker_prerequisites
    local missing=0

    if [ ! -f "$SCRIPT_DIR/config/nginx.conf" ]; then
        log_error "nginx config not found at $SCRIPT_DIR/config/nginx.conf"
        missing=1
    fi

    if [ ! -f "$SCRIPT_DIR/init.sql" ]; then
        log_error "init.sql not found at $SCRIPT_DIR/init.sql"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        exit 1
    fi

    log_info "Runtime prerequisites satisfied"
}

check_image_prerequisites() {
    local image_source
    image_source=$(get_env_value IMAGE_SOURCE ghcr)
    if [ "$image_source" != "offline" ]; then
        return 0  # 在线模式 pull 镜像，无需本地文件
    fi

    if [ ! -d "$SCRIPT_DIR/images" ]; then
        log_error "images/ directory not found (required for IMAGE_SOURCE=offline)"
        exit 1
    fi
    local count
    count=$(find "$SCRIPT_DIR/images" -maxdepth 1 -name '*.tar' 2>/dev/null | wc -l)
    if [ "$count" -eq 0 ]; then
        log_error "No .tar files found in images/ directory"
        exit 1
    fi
}

check_curl_prerequisite() {
    if ! command -v curl &> /dev/null; then
        log_warn "curl is not installed, skipping HTTP verification"
        return 1
    fi
    return 0
}

# ========================================
# 镜像加载（离线模式）
# ========================================
load_images() {
    local image_dir="$SCRIPT_DIR/images"
    if [ ! -d "$image_dir" ]; then
        log_warn "images/ directory not found, skipping image load"
        return 0
    fi

    local tar_files
    mapfile -t tar_files < <(find "$image_dir" -maxdepth 1 -name '*.tar' 2>/dev/null | sort)
    if [ ${#tar_files[@]} -eq 0 ] || [ ! -f "${tar_files[0]:-}" ]; then
        log_warn "No .tar files found in images/, skipping image load"
        return 0
    fi

    local count=0
    for tar_file in "${tar_files[@]}"; do
        [ -z "$tar_file" ] && continue
        log_info "Loading image: $(basename "$tar_file")"
        docker load -i "$tar_file"
        count=$((count + 1))
    done
    log_info "Loaded ${count} application images"
}

load_dep_images() {
    local dep_dir="$SCRIPT_DIR/dep-images"
    if [ ! -d "$dep_dir" ]; then
        log_warn "dep-images/ directory not found, skipping dependency image load"
        return 0
    fi

    local tar_files
    mapfile -t tar_files < <(find "$dep_dir" -maxdepth 1 -name '*.tar' 2>/dev/null | sort)
    if [ ${#tar_files[@]} -eq 0 ] || [ ! -f "${tar_files[0]:-}" ]; then
        log_warn "No .tar files found in dep-images/, skipping"
        return 0
    fi

    local count=0
    for tar_file in "${tar_files[@]}"; do
        [ -z "$tar_file" ] && continue
        log_info "Loading dependency image: $(basename "$tar_file")"
        docker load -i "$tar_file"
        count=$((count + 1))
    done
    log_info "Loaded ${count} dependency images"
}

# ========================================
# 镜像准备（统一入口：pull 或 load）
# ========================================
prepare_images() {
    local image_source
    image_source=$(get_env_value IMAGE_SOURCE ghcr)

    case "$image_source" in
        ghcr|github|dockerhub|docker)
            login_registries
            compose pull
            ;;
        offline)
            load_dep_images
            load_images
            ;;
        custom)
            log_info "Using custom images, skipping pull/load"
            ;;
    esac
}

# ========================================
# 镜像仓库登录
# ========================================
login_registries() {
    local ghcr_username ghcr_token dockerhub_username dockerhub_token
    ghcr_username=$(get_env_value GHCR_USERNAME "")
    ghcr_token=$(get_env_value GHCR_TOKEN "")
    dockerhub_username=$(get_env_value DOCKERHUB_USERNAME "")
    dockerhub_token=$(get_env_value DOCKERHUB_TOKEN "")

    if [ -n "$ghcr_username" ] && [ -n "$ghcr_token" ]; then
        log_info "Logging in to GHCR..."
        echo "$ghcr_token" | docker login ghcr.io -u "$ghcr_username" --password-stdin
    fi

    if [ -n "$dockerhub_username" ] && [ -n "$dockerhub_token" ]; then
        log_info "Logging in to Docker Hub..."
        echo "$dockerhub_token" | docker login -u "$dockerhub_username" --password-stdin
    fi
}

# ========================================
# 容器健康检查
# ========================================
container_is_ready() {
    local service="$1"
    local container_id state exit_code

    # -a: 包含已停止/已退出的容器，否则一次性容器（如 minio-init）执行完毕后无法被检测到
    container_id=$(compose ps -a -q "$service" 2>/dev/null || true)
    if [ -z "$container_id" ]; then
        return 1
    fi

    state=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)
    exit_code=$(docker inspect --format '{{.State.ExitCode}}' "$container_id" 2>/dev/null || true)

    case "$state" in
        healthy|running)
            return 0
            ;;
        exited)
            [ "$exit_code" = "0" ]
            return
            ;;
        unhealthy)
            return 1
            ;;
        *)
            return 1
            ;;
    esac
}

# ========================================
# 等待服务就绪
# ========================================
wait_for_services() {
    local timeout="${WAIT_TIMEOUT_SECONDS:-300}"
    local interval="${WAIT_INTERVAL_SECONDS:-5}"
    local deadline=$((SECONDS + timeout))
    local services=("$@")

    log_info "Waiting for services to become healthy: ${services[*]}"
    while [ $SECONDS -lt $deadline ]; do
        local pending=()
        local service
        for service in "${services[@]}"; do
            if ! container_is_ready "$service"; then
                pending+=("$service")
            fi
        done

        if [ ${#pending[@]} -eq 0 ]; then
            log_info "All services are healthy"
            return 0
        fi

        log_warn "Still waiting for: ${pending[*]}"
        sleep "$interval"
    done

    log_error "Timed out waiting for services: ${services[*]}"
    compose ps
    return 1
}

# ========================================
# 健康验证（非阻塞，失败仅 warn）
# ========================================
verify_deployment() {
    if ! check_curl_prerequisite; then
        return 0
    fi

    local console_port manager_port runtime_port builder_port
    console_port=$(get_env_value CONSOLE_PORT 80)
    manager_port=$(get_env_value MANAGER_PORT 31111)
    runtime_port=$(get_env_value RUNTIME_PORT 31014)
    builder_port=$(get_env_value BUILDER_PORT 31015)

    log_info "Verifying HTTP endpoints..."

    # Frontend
    local code
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:${console_port}/openjiuwen/" 2>/dev/null || echo "000")
    if [ "$code" = "200" ] || [ "$code" = "301" ] || [ "$code" = "302" ]; then
        log_info "Frontend ✓ (HTTP ${code})"
    else
        log_warn "Frontend not ready (HTTP ${code})"
    fi

    # studio-manager
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:${manager_port}/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        log_info "studio-manager /health ✓"
    else
        log_warn "studio-manager /health not ready (HTTP ${code})"
    fi

    # studio-runtime
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:${runtime_port}/v1/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        log_info "studio-runtime /v1/health ✓"
    else
        log_warn "studio-runtime /v1/health not ready (HTTP ${code})"
    fi

    # studio-builder
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:${builder_port}/v1/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        log_info "studio-builder /v1/health ✓"
    else
        log_warn "studio-builder /v1/health not ready (HTTP ${code})"
    fi
}

# ========================================
# 数据库初始化
# ========================================
init_database() {
    log_info "Initializing database and object storage..."
    cd "$SCRIPT_DIR"

    # 启动 infra 服务（如果尚未运行）
    local mysql_running=false
    if compose ps -q mysql 2>/dev/null | grep -q .; then
        mysql_running=true
    fi

    if [ "$mysql_running" = false ]; then
        compose up -d "${INFRA_SERVICES[@]}"
        wait_for_services "${INFRA_SERVICES[@]}"
    fi

    # 执行 init.sql
    log_info "Executing init.sql..."
    local db_password
    db_password=$(get_env_value SPRING_DATASOURCE_PASSWORD 123456)
    compose exec -T mysql sh -c "mysql -uroot -p'${db_password}' < /docker-entrypoint-initdb.d/init.sql" 2>/dev/null || \
        compose exec -T mysql sh -c "mysql -uroot < /docker-entrypoint-initdb.d/init.sql" 2>/dev/null || \
        log_warn "Database init failed (may already be initialized)"

    # MinIO 桶由 minio-init 在 compose up 时自动创建（mc mb --ignore-existing）
    log_info "Database and object storage initialized"
}

# ========================================
# 启动基础设施
# ========================================
start_infra() {
    log_info "Starting infrastructure services..."
    cd "$SCRIPT_DIR"

    local image_source
    image_source=$(get_env_value IMAGE_SOURCE ghcr)
    if [ "$image_source" = "offline" ]; then
        load_dep_images
    fi

    init_database

    log_info "============================================"
    log_info " Infrastructure started successfully!"
    log_info "============================================"
    local host_ip
    host_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    local db_port redis_ext_port minio_api_port minio_console_port
    db_port=$(get_env_value DB_PORT 3306)
    redis_ext_port=$(get_env_value REDIS_EXTERNAL_PORT 6379)
    minio_api_port=$(get_env_value MINIO_API_PORT 9000)
    minio_console_port=$(get_env_value MINIO_CONSOLE_PORT 9001)
    log_info ""
    log_info "  MySQL    : ${host_ip}:${db_port}"
    log_info "  Redis    : ${host_ip}:${redis_ext_port}"
    log_info "  MinIO    : http://${host_ip}:${minio_api_port}"
    log_info "  Console  : http://${host_ip}:${minio_console_port}"
    log_info ""
    log_info "  Next     : $0 start"
    log_info "============================================"
}

# ========================================
# 启动所有服务
# ========================================
start_services() {
    log_info "Starting all services..."
    cd "$SCRIPT_DIR"

    local image_source
    image_source=$(get_env_value IMAGE_SOURCE ghcr)
    if [ "$image_source" = "offline" ]; then
        load_images
    fi

    init_database
    compose up -d "${APP_SERVICES[@]}"
    wait_for_services "${ALL_SERVICES[@]}"
    verify_deployment

    log_info "============================================"
    log_info " Services started successfully!"
    log_info "============================================"
    local console_port manager_port runtime_port builder_port host_ip
    console_port=$(get_env_value CONSOLE_PORT 80)
    manager_port=$(get_env_value MANAGER_PORT 31111)
    runtime_port=$(get_env_value RUNTIME_PORT 31014)
    builder_port=$(get_env_value BUILDER_PORT 31015)
    host_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    log_info ""
    log_info "  Frontend : http://${host_ip}:${console_port}/openjiuwen/"
    log_info "  Manager  : http://${host_ip}:${manager_port}/health"
    log_info "  Runtime  : http://${host_ip}:${runtime_port}/v1/health"
    log_info "  Builder  : http://${host_ip}:${builder_port}/v1/health"
    log_info ""
    log_info "  Stop     : $0 stop"
    log_info "  Logs     : $0 logs [service]"
    log_info "============================================"
}

# ========================================
# 停止服务
# ========================================
stop_services() {
    log_info "Stopping all services..."
    cd "$SCRIPT_DIR"
    compose down --remove-orphans
    log_info "All services stopped"
}

stop_infra() {
    log_info "Stopping infrastructure services..."
    cd "$SCRIPT_DIR"
    compose stop mysql redis minio minio-init
    log_info "Infrastructure services stopped"
}

stop_all() {
    stop_services
}

# ========================================
# 重启应用服务
# ========================================
restart_services() {
    log_info "Restarting application services..."
    cd "$SCRIPT_DIR"
    compose restart "${APP_SERVICES[@]}"
    wait_for_services "${ALL_SERVICES[@]}"
    verify_deployment
    log_info "Services restarted"
}

# ========================================
# 用本地已有镜像重建容器（不 pull）
# 适用：docker build + docker tag 之后，切换到新镜像（restart 不会换镜像，update 会 pull 覆盖本地）
# ========================================
recreate_services() {
    cd "$SCRIPT_DIR"
    local services=()
    if [ $# -ge 1 ]; then
        services=("$@")
    else
        services=("${APP_SERVICES[@]}")
    fi
    log_info "Recreating from LOCAL images (no pull): ${services[*]}"
    # prepare_compose_env 设 STUDIO_*_IMAGE（compose 文件依赖），但 ghcr/dockerhub 模式会
    # 同时把 APP_PULL_POLICY 设成 always——这里强制改回 if_not_present，避免 up 时 pull
    # 覆盖本地刚 build/retag 的新镜像。故不走 compose()（它会再次 prepare 覆盖回来）。
    prepare_compose_env
    export APP_PULL_POLICY=if_not_present
    "${COMPOSE_CMD[@]}" --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
        up -d --force-recreate "${services[@]}"
    wait_for_services "${services[@]}"
    verify_deployment
    log_info "Services recreated"
}

# ========================================
# 使用 docker/build.sh 最近一次构建的本地镜像
# ========================================
deploy_local_build() {
    local build_info="$SCRIPT_DIR/../docker/.last-build.env"
    if [ ! -f "$build_info" ]; then
        log_error "Local build metadata not found: $build_info"
        log_error "Run: bash docker/build.sh"
        exit 1
    fi

    local services=()
    local explicit_services=false
    if [ $# -gt 0 ]; then
        services=("$@")
        explicit_services=true
    else
        services=("${APP_SERVICES[@]}")
    fi

    # 先提供完整 Compose 镜像变量，再用本次本地构建覆盖对应服务。
    prepare_compose_env
    # 文件由 docker/build.sh 生成，只包含受控的 KEY=VALUE 镜像信息。
    # shellcheck disable=SC1090
    source "$build_info"
    export STUDIO_CONSOLE_IMAGE STUDIO_MANAGER_IMAGE STUDIO_RUNTIME_IMAGE STUDIO_BUILDER_IMAGE
    export GRAFANA_IMAGE="${GRAFANA_IMAGE:-grafana-victorialogs:11.3.0-0.29.0}"
    export APP_PULL_POLICY=never

    local service image key
    for service in "${services[@]}"; do
        case "$service" in
            studio-console) key=STUDIO_CONSOLE_IMAGE; image="$STUDIO_CONSOLE_IMAGE" ;;
            studio-manager) key=STUDIO_MANAGER_IMAGE; image="$STUDIO_MANAGER_IMAGE" ;;
            studio-runtime) key=STUDIO_RUNTIME_IMAGE; image="$STUDIO_RUNTIME_IMAGE" ;;
            studio-builder) key=STUDIO_BUILDER_IMAGE; image="$STUDIO_BUILDER_IMAGE" ;;
            *) log_error "Unsupported local application service: $service"; exit 1 ;;
        esac
        if ! grep -q "^${key}=" "$build_info"; then
            log_error "$service was not part of the latest local build"
            log_error "Build it first: bash docker/build.sh"
            exit 1
        fi
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            log_error "Local image not found: $image"
            log_error "Run a complete build first: bash docker/build.sh"
            exit 1
        fi
    done

    log_info "Deploying local build (${BUILD_PLATFORM:-unknown}): ${services[*]}"
    cd "$SCRIPT_DIR"
    local up_args=(up -d --force-recreate)
    if [ "$explicit_services" = true ]; then
        # 单服务/指定服务更新只替换目标容器，保持其依赖和其他业务容器原状。
        up_args+=(--no-deps)
    fi
    "${COMPOSE_CMD[@]}" --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" \
        "${up_args[@]}" "${services[@]}"
    wait_for_services "${services[@]}"
    verify_deployment
    log_info "Local build deployed successfully"
}

# ========================================
# 更新服务
# ========================================
update_services() {
    log_info "Updating services..."
    cd "$SCRIPT_DIR"

    local image_source
    image_source=$(get_env_value IMAGE_SOURCE ghcr)
    if [ "$image_source" = "offline" ]; then
        load_images
    else
        login_registries
        compose pull
    fi

    init_database
    compose up -d --force-recreate "${APP_SERVICES[@]}"
    wait_for_services "${ALL_SERVICES[@]}"
    verify_deployment
    log_info "Services updated successfully"
}

# ========================================
# 清理
# ========================================
clean_all() {
    local mode="${1:-data}"
    local down_flags="-v --remove-orphans"

    if [ "$mode" = "images" ] || [ "$mode" = "all" ]; then
        down_flags="$down_flags --rmi all"
    elif [ "$mode" != "data" ]; then
        log_error "Unknown clean target '$mode'. Usage: $0 clean [data|images|all]"
        exit 1
    fi

    log_warn "============================================================"
    log_warn " This will remove project '$PROJECT_NAME' resources (IRREVERSIBLE):"
    log_warn "   - Containers / Networks / Volumes (data will be lost)"
    if [ "$mode" = "images" ] || [ "$mode" = "all" ]; then
        log_warn "   - Images (need to re-pull/re-load on next deploy)"
    else
        log_warn "   - Images preserved by default"
    fi
    log_warn "============================================================"

    if [ "${FORCE_CLEAN:-}" != "yes" ]; then
        local confirm=""
        if ! read -r -p "Type YES to confirm: " confirm; then
            log_warn "Non-interactive or read failed, cancelled. Set FORCE_CLEAN=yes to skip."
            return 0
        fi
        if [ "$confirm" != "YES" ]; then
            log_info "Cancelled, nothing was deleted"
            return 0
        fi
    fi

    log_info "Removing containers, networks and volumes..."
    cd "$SCRIPT_DIR"
    compose down $down_flags

    log_info "Cleanup complete"
    [ "$mode" = "images" ] || [ "$mode" = "all" ] && log_info "Images removed"
    log_info "Redeploy: $0 all"
}

# ========================================
# 查看日志
# ========================================
show_logs() {
    cd "$SCRIPT_DIR"
    if [ -n "${1:-}" ]; then
        compose logs -f "$1"
    else
        compose logs -f
    fi
}

# ========================================
# 查看状态
# ========================================
show_status() {
    cd "$SCRIPT_DIR"
    compose ps
}

# ========================================
# 日志聚合栈（VictoriaLogs + Vector + Grafana，可选组件，profiles: logging）
# 默认 infra/start 不会启动；通过 `logging` 子命令显式启停。
# ========================================
start_logging() {
    validate_logging_image_source
    local max_disk_usage min_free_disk
    max_disk_usage=$(get_env_value VICTORIA_LOGS_MAX_DISK_USAGE_BYTES 10737418240)
    min_free_disk=$(get_env_value VICTORIA_LOGS_MIN_FREE_DISK_BYTES 2147483648)
    if ! [[ "$max_disk_usage" =~ ^[1-9][0-9]*$ ]]; then
        log_error "VICTORIA_LOGS_MAX_DISK_USAGE_BYTES 必须是大于 0 的字节数，禁止无限制写盘"
        exit 1
    fi
    if ! [[ "$min_free_disk" =~ ^[1-9][0-9]*$ ]]; then
        log_error "VICTORIA_LOGS_MIN_FREE_DISK_BYTES 必须是大于 0 的字节数"
        exit 1
    fi
    log_info "Starting logging stack (victoria-logs / vector / grafana)..."
    cd "$SCRIPT_DIR"
    compose --profile logging up -d victoria-logs vector grafana
    wait_for_services victoria-logs vector grafana

    local host_ip grafana_port grafana_pw
    host_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    grafana_port=$(get_env_value GRAFANA_PORT 3000)
    grafana_pw=$(get_env_value GRAFANA_ADMIN_PASSWORD admin)
    log_info "============================================"
    log_info " Logging stack started!"
    log_info "============================================"
    log_info ""
    log_info "  Grafana : http://${host_ip}:${grafana_port}/"
    log_info "            (login: admin / ${grafana_pw})"
    log_info ""
    log_info "  Stop    : $0 logging stop"
    log_info "  Status  : $0 logging status"
    log_info "============================================"
}

stop_logging() {
    log_info "Stopping logging stack (victoria-logs / vector / grafana)..."
    cd "$SCRIPT_DIR"
    compose --profile logging stop victoria-logs vector grafana
    log_info "Logging stack stopped"
}

status_logging() {
    cd "$SCRIPT_DIR"
    compose --profile logging ps victoria-logs vector grafana
}

# ========================================
# 使用说明
# ========================================
print_usage() {
    echo "Usage: $0 {infra|init-db|start|stop|stop-infra|stop-all|restart|update|recreate [service...]|local [service...]|clean [data|images|all]|logs [service]|status|verify|all}"
    echo ""
    echo "  infra     - Start MySQL/Redis/MinIO and initialize database + MinIO bucket"
    echo "  init-db   - Initialize database and MinIO bucket (infra must be running)"
    echo "  start     - Start all services (infra + app) and verify"
    echo "  stop      - Stop all services (preserves data)"
    echo "  stop-infra- Stop infrastructure services only"
    echo "  stop-all  - Stop all services (same as stop)"
    echo "  restart   - Restart application services"
    echo "  update    - Pull/load images and recreate services"
    echo "  recreate  - Recreate services from LOCAL images (no pull)."
    echo "              Use after docker build + retag. Optional: recreate studio-manager studio-runtime studio-builder"
    echo "  local     - Deploy images from the latest docker/build.sh run (no retag or .env edits)."
    echo "  clean     - Remove containers, networks and VOLUMES (data lost). Optional: clean images|all"
    echo "  logs      - Tail service logs (optional: service name)"
    echo "  status    - Show service status"
    echo "  logging   - Manage optional logging stack (VictoriaLogs + Vector + Grafana)."
    echo "              Subcommands: logging start | stop | status  (default: start)"
    echo "  logging-remote - Manage L2 remote Vector on this app node (push to monitor node)."
    echo "              Subcommands: logging-remote start | stop | status  (default: start)"
    echo "  monitor   - Deploy L2 logging stack on this MONITOR node (VictoriaLogs+Grafana+gateway)."
    echo "              Subcommands: monitor start | stop | status  [--local-storage]  (default: start)"
    echo "  verify    - Verify HTTP health endpoints"
    echo "  all       - Pull/load images, start all services, and verify (first-time deploy)"
    echo ""
    echo "  IMAGE_SOURCE in .env controls image acquisition:"
    echo "    ghcr      - Pull from GHCR (online)"
    echo "    dockerhub - Pull from Docker Hub (online)"
    echo "    offline   - Load from local images/*.tar (offline)"
    echo "    custom    - Use explicit STUDIO_*_IMAGE values"
}

# ========================================
# 主入口
# ========================================
detect_compose_cmd

case "${1:-}" in
    infra)
        check_runtime_prerequisites
        check_image_prerequisites
        start_infra
        ;;
    init-db)
        check_runtime_prerequisites
        init_database
        ;;
    start)
        check_runtime_prerequisites
        check_image_prerequisites
        start_services
        ;;
    stop)
        check_docker_prerequisites
        stop_services
        ;;
    stop-infra)
        check_docker_prerequisites
        stop_infra
        ;;
    stop-all)
        check_docker_prerequisites
        stop_all
        ;;
    clean)
        check_docker_prerequisites
        clean_all "${2:-}"
        ;;
    restart)
        check_runtime_prerequisites
        check_image_prerequisites
        restart_services
        ;;
    update)
        check_runtime_prerequisites
        check_image_prerequisites
        update_services
        ;;
    recreate)
        # 用本地镜像重建容器（不 pull）。docker build + docker tag 后用此切换新镜像。
        # 可带参数指定服务：recreate studio-manager studio-runtime studio-builder
        check_runtime_prerequisites
        recreate_services "${@:2}"
        ;;
    local)
        check_runtime_prerequisites
        deploy_local_build "${@:2}"
        ;;
    logs)
        check_docker_prerequisites
        show_logs "${2:-}"
        ;;
    status)
        check_docker_prerequisites
        show_status
        ;;
    logging)
        check_docker_prerequisites
        case "${2:-start}" in
            start)      start_logging ;;
            stop)       stop_logging ;;
            status|ps)  status_logging ;;
            *) log_error "Usage: $0 logging [start|stop|status]"; exit 1 ;;
        esac
        ;;
    logging-remote)
        # L2：在 app 节点启动/停止远程 Vector（push 到监控节点）。
        check_docker_prerequisites
        VECTOR_SCRIPT="$SCRIPT_DIR/observability/scripts/deploy-vector.sh"
        if [ ! -f "$VECTOR_SCRIPT" ]; then
            log_error "L2 Vector 脚本不存在: $VECTOR_SCRIPT"
            exit 1
        fi
        bash "$VECTOR_SCRIPT" "${2:-start}"
        ;;
    monitor)
        # L2：在【监控节点】部署日志聚合栈（VictoriaLogs/Grafana/gateway）。转发到 observability 脚本。
        # 注意：不调 check_docker_prerequisites —— 那会创建 deploy/.env（app 节点用），监控节点不需要。
        # docker/compose 检测由 deploy-monitor.sh 自身完成。监控节点只需此子命令。
        MONITOR_SCRIPT="$SCRIPT_DIR/observability/scripts/deploy-monitor.sh"
        if [ ! -f "$MONITOR_SCRIPT" ]; then
            log_error "L2 monitor 脚本不存在: $MONITOR_SCRIPT"
            exit 1
        fi
        bash "$MONITOR_SCRIPT" "${@:2}"
        ;;
    verify)
        check_docker_prerequisites
        verify_deployment
        ;;
    all)
        check_runtime_prerequisites
        check_image_prerequisites
        prepare_images
        start_services
        ;;
    *)
        print_usage
        exit 1
        ;;
esac
