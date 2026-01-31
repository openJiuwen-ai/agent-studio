#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# =============================================================================
# CORE DATA STRUCTURE
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

# ===== Core project configuration (paths, ports, commands, OS info) =====
declare -A CONFIG=(
    ["ENV_DIR"]="${SCRIPT_DIR}/.envs"
    ["ENV_FILE"]="${SCRIPT_DIR}/.env"
    ["DEFAULT_DEPLOY_ENV_FILE"]="${SCRIPT_DIR}/.env.deploy.default"
    ["DEFAULT_RUNTIME_ENV_FILE"]="${SCRIPT_DIR}/.env.runtime.default"
    ["CUSTOM_ENV_FILE"]="${SCRIPT_DIR}/.env.custom"
    ["CONFIG_DIR"]="${SCRIPT_DIR}/conf"
    ["NGINX_TEMPLE_FILE"]="${SCRIPT_DIR}/conf/nginx.template.conf"
    ["DOCKER_COMPOSE_CMD"]=""
    ["START_PORT"]="3000"
    ["END_PORT"]="65535"
    ["OS_TYPE"]=""
)

# ===== Prefix-Naming conventions for Docker services/containers/volumes =====
declare -A NAMES=(
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
    ["FRONTEND_SERVICE"]="frontend"
    ["FRONTEND_DOCKER"]="jiuwen-frontend"
    ["BACKEND_SERVICE"]="backend"
    ["BACKEND_DOCKER"]="jiuwen-backend"
    ["SQLITE_VOLUME"]="sqlite-data"
    ["MEMORY_VOLUME"]="memory-data"
    ["KNOWLEDGE_VOLUME"]="knowledge-data"
    ["JIUWEN_NETWORK_NAME"]="jiuwen-network"
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
    BACKEND_HOST_PORT
    PLUGIN_SERVER_HOST_PORT
    SANDBOX_GATEWAY_HOST_PORT
    PYTHON_SERVER_HOST_PORT
    JS_SERVER_HOST_PORT
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
)

# ==== Global deploy associative array ====
# ==== (key=variable name, value=variable value) ====
declare -A DEPLOY_VARS=(
    ["HAS_MYSQL_CONTAINER"]="false"
    ["HAS_MILVUS_CONTAINER"]="false"
    ["HAS_PLUGIN_CONTAINER"]="false"
    ["HAS_SANDBOX_CONTAINER"]="false"
    ["HAS_JIUWEN_CONTAINER"]="false"
)

# ==== Global runtime associative array  ====
# ==== (key=variable name, value=variable value) ====
declare -A RUNTIME_VARS=(
)

#  ==== List of available ports for service allocation (dynamic generated) ====
declare -ga AVAILABLE_PORTS=()

# ==== List of ports already allocated to services (dynamic generated)  ==== 
declare -ga ALLOCATED_PORTS=()

# ==== All available modules ==== 
declare -ga ALL_MODULES=("MYSQL" "MILVUS" "PLUGIN" "SANDBOX" "JIUWEN")

# ==== Paths to Docker Compose template files per module ==== 
declare -A COMPOSE_TEMPLATE_FILES=(
    ["MYSQL"]="${SCRIPT_DIR}/conf/docker-mysql.template.yml"
    ["MILVUS"]="${SCRIPT_DIR}/conf/docker-milvus.template.yml"
    ["PLUGIN"]="${SCRIPT_DIR}/conf/docker-plugin.template.yml"
    ["SANDBOX"]="${SCRIPT_DIR}/conf/docker-sandbox.template.yml"
    ["JIUWEN"]="${SCRIPT_DIR}/conf/docker-jiuwen.template.yml"
)

# ==== Paths to final generated Docker Compose files per module ==== 
declare -A COMPOSE_FILES=(
    ["MYSQL"]="${SCRIPT_DIR}/conf/docker-mysql.yml"
    ["MILVUS"]="${SCRIPT_DIR}/conf/docker-milvus.yml"
    ["PLUGIN"]="${SCRIPT_DIR}/conf/docker-plugin.yml"
    ["SANDBOX"]="${SCRIPT_DIR}/conf/docker-sandbox.yml"
    ["JIUWEN"]="${SCRIPT_DIR}/conf/docker-jiuwen.yml"
)

# ==== Mapping of modules to their associated Docker container name keys ==== 
declare -A CONTAINER_KEYS=(
    ["MYSQL"]="MYSQL_DOCKER"
    ["MILVUS"]="ETCD_DOCKER MINIO_DOCKER MILVUS_DOCKER"
    ["PLUGIN"]="PLUGIN_SERVER_DOCKER"
    ["SANDBOX"]="PYTHON_SERVER_DOCKER JS_SERVER_DOCKER SANDBOX_GATEWAY_DOCKER"
    ["JIUWEN"]="BACKEND_DOCKER FRONTEND_DOCKER"
)

# == Final resolved container names for each module (populated dynamically) ==
declare -A CONTAINERS=(
    ["MYSQL"]="" 
    ["MILVUS"]=""
    ["PLUGIN"]=""
    ["SANDBOX"]=""
    ["JIUWEN"]=""
)

# ==== Parsed command-line arguments (command and custom env file path) ====
declare -A ARGS=(
    ["CMD"]=""
    ["ENV_FILE"]=""
    ["IS_NEW_SVC"]="false"
)

# ==== Modules specified via command-line arguments ====
declare -ga ARGS_MODULES=()
