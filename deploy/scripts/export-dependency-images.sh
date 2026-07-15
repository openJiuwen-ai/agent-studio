#!/usr/bin/env bash
# ============================================================
# openJiuwen AgentStudio — 离线依赖镜像导出脚本
# 执行环境：有网机器（用于离线部署准备）
# 执行方式：bash deploy/scripts/export-dependency-images.sh [output-dir]
# 示例：    bash deploy/scripts/export-dependency-images.sh ~/offline-deps
# 前置条件：已安装 Docker，可访问外网
# 说明：导出 MySQL、Redis、MinIO、MC 的 Docker 镜像，
#       用于在离线目标机器上部署外部依赖
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
OUTPUT_DIR="${1:-${SCRIPT_DIR}/../offline-deps}"

echo ""
echo "============================================================"
echo "  openJiuwen AgentStudio — 离线依赖镜像导出"
echo "============================================================"
echo ""

# 检查 Docker
if ! command -v docker &>/dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# 拉取并导出（使用固定版本号确保可复现）
IMAGES=("mysql:8.0" "redis:7" "minio/minio:RELEASE.2024-11-07T00-52-20Z" "minio/mc:RELEASE.2024-11-05T11-29-45Z" "victoriametrics/victoria-logs:v1.50.0" "timberio/vector:0.55.0-alpine")

for image in "${IMAGES[@]}"; do
    log_info "拉取镜像: ${image}"
    docker pull "${image}" || { log_error "拉取失败: ${image}"; exit 1; }

    # 将镜像名中的 / 和 : 替换为 _，生成文件名
    filename=$(echo "${image}" | sed 's/[\/:]/_/g').tar
    log_info "导出镜像: ${image} -> ${OUTPUT_DIR}/${filename}"
    docker save "${image}" -o "${OUTPUT_DIR}/${filename}"
done

# 导出 mc 客户端（MinIO 命令行工具，供手动操作时使用）
log_info "下载 mc 客户端..."
MC_ARCH="linux-amd64"
if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then
    MC_ARCH="linux-arm64"
fi
wget -q -O "${OUTPUT_DIR}/mc" "https://dl.min.io/client/mc/release/${MC_ARCH}/mc" || \
    log_warn "mc 客户端下载失败，请在目标机器上手动下载（架构：${MC_ARCH}）"

if [ -f "${OUTPUT_DIR}/mc" ]; then
    chmod +x "${OUTPUT_DIR}/mc"
fi

# 汇总
echo ""
echo "============================================================"
log_info "导出完成！"
echo "============================================================"
echo ""
echo "  导出目录：${OUTPUT_DIR}"
echo "  文件列表："
ls -lh "${OUTPUT_DIR}/"
echo ""
echo "  后续步骤："
echo "    1. 传输到目标机器：scp -r ${OUTPUT_DIR} user@target-host:~/"
echo "    2. 在目标机器上加载镜像："
echo "       cd ~/offline-deps"
echo "       for f in *.tar; do docker load -i \"\$f\"; done"
echo ""
echo "  注意：如果使用 prepare.sh 构建离线包，依赖镜像已自动包含"
echo "  此脚本仅用于单独导出依赖镜像的场景"
echo "============================================================"
