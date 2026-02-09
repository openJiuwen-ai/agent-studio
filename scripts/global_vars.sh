#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# =============================================================================
# CORE DATA STRUCTURE
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IPV4_REGEX="^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

# ===== Core project configuration (paths, ports, commands, OS info) =====
declare -A CONFIG=(
    ["ENV_DIR"]="${SCRIPT_DIR}/.envs"
    ["ENV_FILE"]="${SCRIPT_DIR}/.env"
    ["DEFAULT_DEPLOY_ENV_FILE"]="${SCRIPT_DIR}/.env.deploy.default"
    ["DEFAULT_RUNTIME_ENV_FILE"]="${SCRIPT_DIR}/.env.runtime.default"
    ["CUSTOM_ENV_FILE"]="${SCRIPT_DIR}/.env.custom"
    ["CONFIG_DIR"]="${SCRIPT_DIR}/conf"
    ["PRE_UPGRADE_ENV_DIR"]="${SCRIPT_DIR}/pre_upgrade_envs"
    ["NGINX_TEMPLATE_FILE"]="${SCRIPT_DIR}/conf/nginx.template.conf"
    ["MILVUS_BACKUP_TEMPLATE"]="${SCRIPT_DIR}/conf/milvus-backup.template.yml"
    ["DOCKER_COMPOSE_CMD"]=""
    ["START_PORT"]="3000"
    ["END_PORT"]="65535"
    ["OS_TYPE"]=""
)

# ===== Prefix-Naming conventions for Docker services/containers/volumes =====
declare -A NAMES=(
    ["JIUWEN_NETWORK_NAME"]="jiuwen-network"
    ["UPGRADE_TOOL_SERVICE"]="upgrade-tool"
    ["UPGRADE_TOOL_DOCKER"]="jiuwen-upgrade-tool"
    ["MYSQL_SERVICE"]="mysql"
    ["MYSQL_DOCKER"]="jiuwen-mysql"
    ["MYSQL_VOLUME"]="mysql-data"
    ["ETCD_SERVICE"]="etcd"
    ["ETCD_DOCKER"]="jiuwen-etcd"
    ["ETCD_VOLUME"]="etcd-data"
    ["MINIO_SERVICE"]="minio"
    ["MINIO_DOCKER"]="jiuwen-minio"
    ["MINIO_VOLUME"]="minio-data"
    ["MILVUS_SERVICE"]="milvus"
    ["MILVUS_DOCKER"]="jiuwen-milvus-standalone"
    ["MILVUS_VOLUME"]="milvus-data"
    ["DEEPSEARCH_SERVICE"]="deepsearch"
    ["DEEPSEARCH_DOCKER"]="jiuwen-deepsearch"
    ["BACKEND_SERVICE"]="backend"
    ["BACKEND_DOCKER"]="jiuwen-backend"
    ["SQLITE_VOLUME"]="sqlite-data"
    ["MEMORY_VOLUME"]="memory-data"
    ["KNOWLEDGE_VOLUME"]="knowledge-data"
    ["FRONTEND_SERVICE"]="frontend"
    ["FRONTEND_DOCKER"]="jiuwen-frontend"
    ["PLUGIN_SERVER_SERVICE"]="plugin-server"
    ["PLUGIN_SERVER_DOCKER"]="jiuwen-plugin-server"
    ["SANDBOX_GATEWAY_SERVICE"]="sandbox-gateway"
    ["SANDBOX_GATEWAY_DOCKER"]="jiuwen-sandbox-gateway"
    ["PYTHON_SERVER_SERVICE"]="python-server"
    ["PYTHON_SERVER_DOCKER"]="jiuwen-python-server"
    ["JS_SERVER_SERVICE"]="js-server"
    ["JS_SERVER_DOCKER"]="jiuwen-js-server"
)

# ===== Host port variables to allocate for services (dynamic assignment) =====
declare -ga PORTS=(
    FRONTEND_HOST_PORT
    MYSQL_HOST_PORT
    ETCD_HOST_PORT
    MINIO_SERVICE_HOST_PORT
    MINIO_CONSOLE_HOST_PORT
    MILVUS_HOST_PORT
    MILVUS_HTTP_HOST_PORT
    BACKEND_HOST_PORT
    PLUGIN_SERVER_HOST_PORT
    SANDBOX_GATEWAY_HOST_PORT
    PYTHON_SERVER_HOST_PORT
    JS_SERVER_HOST_PORT
    DEEPSEARCH_HOST_PORT
)

# ===== Container/service name variables for network address resolution =====
declare -ga CONTAINERS_ADDRS=(
    MYSQL_SERVICE
    MYSQL_DOCKER
    ETCD_SERVICE
    ETCD_DOCKER
    MINIO_SERVICE
    MINIO_DOCKER
    MILVUS_SERVICE
    MILVUS_DOCKER
    FRONTEND_SERVICE
    FRONTEND_DOCKER
    BACKEND_SERVICE
    BACKEND_DOCKER
    PLUGIN_SERVER_SERVICE
    PLUGIN_SERVER_DOCKER
    SANDBOX_GATEWAY_SERVICE
    SANDBOX_GATEWAY_DOCKER
    PYTHON_SERVER_SERVICE
    PYTHON_SERVER_DOCKER
    JS_SERVER_SERVICE
    JS_SERVER_DOCKER
    DEEPSEARCH_SERVICE
    DEEPSEARCH_DOCKER
)

# ==== Global deploy associative array ====
declare -A DEPLOY_VARS=(
    ["HAS_MYSQL"]="false"
    ["HAS_MILVUS"]="false"
    ["HAS_PLUGIN"]="false"
    ["HAS_SANDBOX"]="false"
    ["HAS_DEEPSEARCH"]="false"
    ["HAS_JIUWEN"]="false"
    ["HAS_UPGRADE"]="false"
    ["IS_UP_MYSQL"]="false"
    ["IS_UP_ETCD"]="false"
    ["IS_UP_MINIO"]="false"
    ["IS_UP_MILVUS"]="false"
    ["IS_UP_PLUGIN_SERVER"]="false"
    ["IS_UP_PYTHON_SERVER"]="false"
    ["IS_UP_JS_SERVER"]="false"
    ["IS_UP_SANDBOX_GATEWAY"]="false"
    ["IS_UP_DEEPSEARCH"]="false"
    ["IS_UP_BACKEND"]="false"
    ["IS_UP_FRONTEND"]="false"
    ["IS_UP_UPGRADE_TOOL"]="false"
    ["IS_UPGRADE_MYSQL"]="false"
    ["IS_UPGRADE_MILVUS"]="false"

)

# ==== Global runtime associative array ====
declare -A RUNTIME_VARS=(
)

declare -A DEEPSERACH_ENV_VARS=(
)

# ==== Global associative array to store all environment variables ====
declare -A ALL_VARS=(
)

# ==== Global associative array to store pre-upgrade environment variables ====
declare -A PRE_UPGRADE_VARS=(
)

#  ==== List of available ports for service allocation (dynamic generated) ====
declare -ga AVAILABLE_PORTS=()

# ==== List of ports already allocated to services (dynamic generated)  ==== 
declare -ga ALLOCATED_PORTS=()

# ==== All available modules ====
declare -ga ALL_MODULES=("UPGRADE" "MYSQL" "MILVUS" "PLUGIN" "SANDBOX" "DEEPSEARCH" "JIUWEN")

# ==== components of module ====
declare -A COMPONENTS=(
    ["UPGRADE"]="UPGRADE_TOOL"
    ["MYSQL"]="MYSQL"
    ["MILVUS"]="ETCD MINIO MILVUS"
    ["PLUGIN"]="PLUGIN_SERVER"
    ["SANDBOX"]="PYTHON_SERVER JS_SERVER SANDBOX_GATEWAY"
    ["DEEPSEARCH"]="DEEPSEARCH"
    ["JIUWEN"]="BACKEND FRONTEND"
)


# ==== Paths to Docker Compose template files per module ==== 
declare -A COMPOSE_TEMPLATE_FILES=(
    ["UPGRADE"]="${SCRIPT_DIR}/conf/docker-upgrade.template.yml"
    ["MYSQL"]="${SCRIPT_DIR}/conf/docker-mysql.template.yml"
    ["MILVUS"]="${SCRIPT_DIR}/conf/docker-milvus.template.yml"
    ["PLUGIN"]="${SCRIPT_DIR}/conf/docker-plugin.template.yml"
    ["SANDBOX"]="${SCRIPT_DIR}/conf/docker-sandbox.template.yml"
    ["DEEPSEARCH"]="${SCRIPT_DIR}/conf/docker-deepsearch.template.yml"
    ["JIUWEN"]="${SCRIPT_DIR}/conf/docker-jiuwen.template.yml"
)

# ==== Paths to final generated Docker Compose files per module ==== 
declare -A COMPOSE_FILES=(
    ["UPGRADE"]="${SCRIPT_DIR}/conf/docker-upgrade.yml"
    ["MYSQL"]="${SCRIPT_DIR}/conf/docker-mysql.yml"
    ["MILVUS"]="${SCRIPT_DIR}/conf/docker-milvus.yml"
    ["PLUGIN"]="${SCRIPT_DIR}/conf/docker-plugin.yml"
    ["SANDBOX"]="${SCRIPT_DIR}/conf/docker-sandbox.yml"
    ["DEEPSEARCH"]="${SCRIPT_DIR}/conf/docker-deepsearch.yml"
    ["JIUWEN"]="${SCRIPT_DIR}/conf/docker-jiuwen.yml"
)


# ==== Parsed command-line arguments (command and custom env file path) ====
declare -A ARGS=(
    ["CMD"]=""
    ["ENV_FILE"]=""
    ["IS_NEW_SVC"]="false"
    ["IS_UPGRADE"]="false"
)

# ==== Modules specified via command-line arguments ====
declare -ga ARGS_MODULES=()

# ==== Database migration revision IDs ====
declare -A REVISION_ID=(
    ["MYSQL_AGENT_0.1.1"]="54351e123cf0"
    ["MYSQL_AGENT_0.1.2"]="54351e123cf0"
    ["MYSQL_AGENT_0.1.3"]="06a1f79bce8b"
    ["MYSQL_OPS_0.1.1"]="80f110f929fc"
    ["MYSQL_OPS_0.1.2"]="80f110f929fc"
    ["MYSQL_OPS_0.1.3"]="13377a900fe2"
    ["SQLITE_AGENT_0.1.2"]="f458c7fb17a5"
    ["SQLITE_AGENT_0.1.3"]="031b34b4dd30"
    ["SQLITE_OPS_0.1.2"]="b4f4c6589bc5"
    ["SQLITE_OPS_0.1.3"]="f6e49cd8c97d"
)
