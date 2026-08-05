#!/usr/bin/env bash
# ============================================================
# openJiuwen AgentStudio 离线资源准备脚本
# 使用场景：在有外网访问的机器上运行，打包所有部署资源
# 然后将生成的离线包传输到目标部署机器
# ============================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC}  $1"; }

# 脚本所在目录（deploy/offline/）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 部署根目录（deploy/）
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# 项目根目录
PROJECT_DIR="$(cd "${DEPLOY_DIR}/.." && pwd)"

# 默认版本号（可通过环境变量覆盖）
VERSION="${VERSION:-1.0.0}"
# 构建架构
BUILD_PLATFORM="$(uname -m)"
# 构建时间戳
BUILD_TIME="$(date +"%Y%m%d%H%M%S")"
# 镜像 tag
IMAGE_TAG="${VERSION}.${BUILD_TIME}.${BUILD_PLATFORM}"

# 输出目录
OUTPUT_DIR="${SCRIPT_DIR}/AgentBuilder-offline-${VERSION}"

# ========================================
# 清理旧的输出
# ========================================
clean_output() {
    log_step "清理旧的输出目录..."
    rm -rf "${OUTPUT_DIR}"
    mkdir -p "${OUTPUT_DIR}/images"
    mkdir -p "${OUTPUT_DIR}/dep-images"
    log_info "输出目录: ${OUTPUT_DIR}"
}

# ========================================
# 构建并导出 Docker 镜像
# ========================================
build_and_save_images() {
    log_step "构建 Docker 镜像..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，无法构建镜像"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行"
        exit 1
    fi

    local DOCKER_DIR="${PROJECT_DIR}/docker"

    # 构建基础镜像配置
    local BASE_IMAGE_JAVA="eclipse-temurin:17-jre"
    local BASE_IMAGE_NGINX="nginx:1.28"
    local BASE_IMAGE_PYTHON="python:3.11-slim"

    # ---- 拉取基础镜像 ----
    log_info "拉取基础镜像..."
    docker pull "${BASE_IMAGE_JAVA}" || log_warn "基础镜像 ${BASE_IMAGE_JAVA} 拉取失败，尝试使用本地缓存"
    docker pull "${BASE_IMAGE_NGINX}" || log_warn "基础镜像 ${BASE_IMAGE_NGINX} 拉取失败，尝试使用本地缓存"
    docker pull "${BASE_IMAGE_PYTHON}" || log_warn "基础镜像 ${BASE_IMAGE_PYTHON} 拉取失败，尝试使用本地缓存"

    # ---- 检查编译产物是否完整且与当前源码一致 ----
    local need_build=false
    # 产物路径需与 package.sh 实际输出一致：
    #   console 产出 agent-console.tar（不是 dist/ 目录）
    #   runtime 的 EIStart.py 位于 agent_runtime/ 下（不是 src/）
    if [ ! -f "${DOCKER_DIR}/studio-manager/lib/studio-manager.jar" ] || \
       [ ! -f "${DOCKER_DIR}/studio-console/agent-console.tar" ] || \
       [ ! -f "${DOCKER_DIR}/studio-runtime/agent_runtime/EIStart.py" ]; then
        need_build=true
    fi

    local hash_script="${DOCKER_DIR}/source_hash.sh"
    local hash_file="${DOCKER_DIR}/.source-build-hash"
    if [ "${need_build}" = false ] && [ -f "${hash_script}" ]; then
        local current_hash recorded_hash
        current_hash=$(bash "${hash_script}" 2>/dev/null || true)
        recorded_hash=$(cat "${hash_file}" 2>/dev/null || true)
        if [ -z "${current_hash}" ] || [ "${current_hash}" != "${recorded_hash}" ]; then
            log_warn "现有编译产物与当前源码指纹不一致"
            need_build=true
        fi
    fi

    if [ "${need_build}" = true ]; then
        log_warn "未检测到编译产物，将执行源码编译..."
        log_info "如果已有编译产物，请先运行 docker/package.sh"

        # 调用项目自带的 package.sh
        if [ -f "${DOCKER_DIR}/package.sh" ]; then
            log_info "执行 package.sh 编译源码..."
            cd "${PROJECT_DIR}"
            bash "${DOCKER_DIR}/package.sh"
        else
            log_error "未找到 package.sh，请手动编译后再运行此脚本"
            exit 1
        fi
    else
        log_info "检测到编译产物，跳过源码编译"
    fi

    # ---- 构建应用镜像和内置日志数据源的 Grafana 镜像 ----
    log_info "[1/5] 构建 studio-manager 镜像..."
    cd "${DOCKER_DIR}/studio-manager"
    docker build --build-arg BASE_IMAGE="${BASE_IMAGE_JAVA}" \
        -t "studio-manager:${IMAGE_TAG}" .

    log_info "[2/5] 构建 studio-console 镜像..."
    cd "${DOCKER_DIR}/studio-console"
    docker build --build-arg BASE_IMAGE="${BASE_IMAGE_NGINX}" \
        -t "studio-console:${IMAGE_TAG}" .

    log_info "[3/5] 构建 studio-runtime 镜像..."
    cd "${DOCKER_DIR}/studio-runtime"
    docker build --build-arg BASE_IMAGE="${BASE_IMAGE_PYTHON}" \
        -t "studio-runtime:${IMAGE_TAG}" .

    log_info "[4/5] 构建 studio-builder 镜像..."
    rm -rf "${DOCKER_DIR}/studio-builder/agent_builder" \
           "${DOCKER_DIR}/studio-builder/model_service" \
           "${DOCKER_DIR}/studio-builder/storage"\
           "${DOCKER_DIR}/studio-builder/common_utils"
    cp -rf "${PROJECT_DIR}/agent_builder" "${DOCKER_DIR}/studio-builder/agent_builder"
    cp -rf "${PROJECT_DIR}/packages/model_service/model_service" "${DOCKER_DIR}/studio-builder/model_service"
    cp -rf "${PROJECT_DIR}/packages/storage/storage" "${DOCKER_DIR}/studio-builder/storage"
    cp -rf "${PROJECT_DIR}/packages/common_utils/common_utils" "${DOCKER_DIR}/studio-builder/common_utils"
    cd "${DOCKER_DIR}/studio-builder"
    if ! docker build --build-arg BASE_IMAGE="${BASE_IMAGE_PYTHON}" \
        -t "studio-builder:${IMAGE_TAG}" .; then
        rm -rf agent_builder model_service storage common_utils
        return 1
    fi
    rm -rf agent_builder model_service storage common_utils

    log_info "[5/5] 构建内置 VictoriaLogs 数据源的 Grafana 镜像..."
    local grafana_image="openjiuwen/grafana-victorialogs:11.3.0-0.29.0"
    if docker image inspect "${grafana_image}" > /dev/null 2>&1; then
        log_info "${grafana_image} 已存在，跳过构建"
    else
        cd "${DOCKER_DIR}/grafana"
        docker build \
            --build-arg GRAFANA_VERSION=11.3.0 \
            --build-arg VICTORIA_LOGS_DATASOURCE_VERSION=0.29.0 \
            -t "${grafana_image}" .
    fi

    log_info "所有镜像构建完成"
}

# ========================================
# 导出应用 Docker 镜像为 tar
# ========================================
save_images() {
    log_step "导出应用 Docker 镜像到 tar 文件..."

    local images=("studio-manager" "studio-console" "studio-runtime" "studio-builder")

    for image in "${images[@]}"; do
        local tar_name="${image}_${BUILD_TIME}.${BUILD_PLATFORM}.tar"
        log_info "导出 ${image}:${IMAGE_TAG} -> images/${tar_name}"
        docker save "${image}:${IMAGE_TAG}" -o "${OUTPUT_DIR}/images/${tar_name}"
    done

    log_info "导出内置插件 Grafana 镜像"
    docker save "openjiuwen/grafana-victorialogs:11.3.0-0.29.0" \
        -o "${OUTPUT_DIR}/images/grafana-victorialogs_11.3.0-0.29.0.${BUILD_PLATFORM}.tar"

    log_info "所有应用镜像导出完成"
}

# ========================================
# 导出依赖 Docker 镜像
# ========================================
export_dep_images() {
    log_step "导出依赖镜像（基础设施与日志组件）..."

    local dep_images=(
        "mysql:8.0"
        "redis:7"
        "minio/minio:latest"
        "minio/mc:latest"
        "victoriametrics/victoria-logs:v1.50.0"
        "timberio/vector:0.55.0-alpine"
    )

    for image in "${dep_images[@]}"; do
        log_info "拉取并导出: ${image}"
        docker pull "${image}" || log_warn "拉取失败: ${image}，尝试使用本地缓存"
        local filename
        filename=$(echo "${image}" | sed 's/[\/:]/_/g').tar
        docker save "${image}" -o "${OUTPUT_DIR}/dep-images/${filename}"
    done

    log_info "依赖镜像导出完成"
}

# ========================================
# 复制部署配置文件
# ========================================
copy_configs() {
    log_step "复制部署配置文件..."

    # 统一 docker-compose.yml（infra + app 一体）
    cp "${DEPLOY_DIR}/docker-compose.yml" "${OUTPUT_DIR}/"

    # nginx.conf
    mkdir -p "${OUTPUT_DIR}/config"
    cp "${DEPLOY_DIR}/config/nginx.conf" "${OUTPUT_DIR}/config/"

    # L1 日志聚合配置
    cp "${DEPLOY_DIR}/config/vector.yaml" "${OUTPUT_DIR}/config/"
    cp "${DEPLOY_DIR}/config/grafana-datasources.yaml" "${OUTPUT_DIR}/config/"
    mkdir -p "${OUTPUT_DIR}/observability/config" "${OUTPUT_DIR}/observability/dashboards"
    cp "${DEPLOY_DIR}/observability/config/grafana-dashboards.yaml" \
        "${OUTPUT_DIR}/observability/config/"
    cp -R "${DEPLOY_DIR}/observability/dashboards/." \
        "${OUTPUT_DIR}/observability/dashboards/"

    # L2 跨节点日志聚合配置与脚本（TLS 证书和凭据在目标机生成，不打包）。
    mkdir -p "${OUTPUT_DIR}/observability/scripts"
    cp "${DEPLOY_DIR}/observability/docker-compose.monitor.yml" \
       "${DEPLOY_DIR}/observability/docker-compose.vector.yml" \
       "${DEPLOY_DIR}/observability/.env.template" \
       "${OUTPUT_DIR}/observability/"
    cp "${DEPLOY_DIR}/observability/config/vector.yaml" \
       "${DEPLOY_DIR}/observability/config/nginx-gateway.conf" \
       "${DEPLOY_DIR}/observability/config/grafana-datasources.yaml" \
       "${OUTPUT_DIR}/observability/config/"
    cp "${DEPLOY_DIR}/observability/scripts/deploy-monitor.sh" \
       "${DEPLOY_DIR}/observability/scripts/deploy-vector.sh" \
       "${OUTPUT_DIR}/observability/scripts/"

    # nginx-https.conf（可选）
    if [ -f "${DEPLOY_DIR}/config/nginx-https.conf" ]; then
        cp "${DEPLOY_DIR}/config/nginx-https.conf" "${OUTPUT_DIR}/config/"
    fi

    # init.sql（现在位于 deploy/ 下）
    if [ -f "${DEPLOY_DIR}/init.sql" ]; then
        cp "${DEPLOY_DIR}/init.sql" "${OUTPUT_DIR}/"
    else
        log_warn "未找到 init.sql，离线包将不包含数据库初始化脚本"
    fi

    # 统一 .env.template（替换镜像 tag 占位符，设置 IMAGE_SOURCE=offline，取消 STUDIO_*_IMAGE 注释）
    sed "s/TAG_PLACEHOLDER/${IMAGE_TAG}/g" "${DEPLOY_DIR}/.env.template" > "${OUTPUT_DIR}/.env.template"
    sed -i 's/^IMAGE_SOURCE=ghcr/IMAGE_SOURCE=offline/' "${OUTPUT_DIR}/.env.template"
    sed -i 's/^# \(STUDIO_.*_IMAGE=\)/\1/' "${OUTPUT_DIR}/.env.template"
    # 离线包内保存的是本地标签，避免目标机尝试访问 GHCR。
    sed -i 's|^GRAFANA_IMAGE=.*|GRAFANA_IMAGE=openjiuwen/grafana-victorialogs:11.3.0-0.29.0|' "${OUTPUT_DIR}/.env.template"

    # 统一部署脚本
    cp "${DEPLOY_DIR}/deploy.sh" "${OUTPUT_DIR}/"

    # 离线部署辅助脚本
    mkdir -p "${OUTPUT_DIR}/scripts"
    if [ -f "${DEPLOY_DIR}/scripts/install-docker-offline.sh" ]; then
        cp "${DEPLOY_DIR}/scripts/install-docker-offline.sh" "${OUTPUT_DIR}/scripts/"
    fi

    log_info "配置文件复制完成"
}

# ========================================
# 生成镜像 tag 记录
# ========================================
generate_image_info() {
    log_step "生成镜像信息文件..."

    cat > "${OUTPUT_DIR}/images/image_info.txt" << EOF
# openJiuwen AgentStudio 离线部署镜像信息
# 版本: ${VERSION}
# 构建时间: $(date '+%Y-%m-%d %H:%M:%S')
# 架构: ${BUILD_PLATFORM}
#
# 镜像 tag: ${IMAGE_TAG}
# 部署时 .env 中镜像配置应为:
STUDIO_CONSOLE_IMAGE=studio-console:${IMAGE_TAG}
STUDIO_MANAGER_IMAGE=studio-manager:${IMAGE_TAG}
STUDIO_RUNTIME_IMAGE=studio-runtime:${IMAGE_TAG}
STUDIO_BUILDER_IMAGE=studio-builder:${IMAGE_TAG}
EOF

    log_info "镜像信息文件已生成"
}

# ========================================
# 打包为压缩文件
# ========================================
package() {
    log_step "打包离线部署包..."

    local tarball="AgentBuilder-offline-${VERSION}.tar.gz"
    cd "${SCRIPT_DIR}"

    tar -czf "${tarball}" -C "${SCRIPT_DIR}" "AgentBuilder-offline-${VERSION}"

    local size
    size=$(du -h "${tarball}" | awk '{print $1}')
    log_info "离线部署包已生成: ${SCRIPT_DIR}/${tarball} (${size})"
}

# ========================================
# 主流程
# ========================================
main() {
    echo ""
    echo "============================================================"
    echo "  openJiuwen AgentStudio 离线资源准备"
    echo "  版本: ${VERSION}"
    echo "  镜像 Tag: ${IMAGE_TAG}"
    echo "============================================================"
    echo ""

    clean_output
    build_and_save_images
    save_images
    export_dep_images
    copy_configs
    generate_image_info

    log_step "打包离线部署包..."
    package

    echo ""
    echo "============================================================"
    echo -e "${GREEN}  离线资源准备完成！${NC}"
    echo "============================================================"
    echo ""
    echo "  离线部署包: ${SCRIPT_DIR}/AgentBuilder-offline-${VERSION}.tar.gz"
    echo ""
    echo "  离线包内容："
    echo "    images/              - 5个应用镜像 tar + image_info.txt"
    echo "    dep-images/          - MySQL/Redis/MinIO/MC 镜像 tar"
    echo "    scripts/             - 辅助脚本（install-docker-offline）"
    echo "    config/nginx.conf    - Nginx 配置（HTTP 模式）"
    echo "    init.sql             - 数据库初始化脚本"
    echo "    docker-compose.yml   - 统一服务编排（基础设施 + 应用）"
    echo "    .env.template        - 配置模板（IMAGE_SOURCE=offline，镜像 tag 已自动填入）"
    echo "    deploy.sh            - 统一部署管理脚本"
    echo ""
    echo "  后续步骤："
    echo "    1. 将离线部署包传输到目标部署机器："
    echo "       scp AgentBuilder-offline-${VERSION}.tar.gz user@target-host:~/"
    echo ""
    echo "    2. 在目标机器上解压并安装 Docker："
    echo "       tar -xzvf AgentBuilder-offline-${VERSION}.tar.gz"
    echo "       bash AgentBuilder-offline-${VERSION}/scripts/install-docker-offline.sh <docker-tgz-path>"
    echo ""
    echo "    3. 配置 .env（使用内置基础设施时默认值即可）："
    echo "       cd AgentBuilder-offline-${VERSION} && cp .env.template .env && vi .env"
    echo ""
    echo "    4. 一键启动（基础设施 + 应用）："
    echo "       bash deploy.sh all"
    echo "============================================================"
}

main "$@"
