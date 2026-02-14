#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# === Generates unique suffix for container/service/volume/... names (uses random chars if not set in .env)  =====
generate_final_names() {
    local name_suffix=$(generate_random_chars)
    DEPLOY_VARS["NAME_SUFFIX"]=${name_suffix}

    info "Generating name...."
    for key in "${!NAMES[@]}"; do
        # info "Generating name for ${key}"
        set_if_empty "DEPLOY_VARS" "${key}" "${NAMES[${key}]}-${name_suffix}"
    done
    success "Generating name Done!"
}

# === Configures no_proxy/NO_PROXY env vars to bypass proxy for internal container/host connections =====
setup_no_proxy_vars() {
    local no_proxy_addrs="localhost,127.0.0.1"

    # Public IP Address of host machine
    if [ -n "${DEPLOY_VARS["IP"]:-}" ]; then
        no_proxy_addrs="${no_proxy_addrs},${DEPLOY_VARS["IP"]}"
    fi

    # all containers
    for addr in "${CONTAINERS_ADDRS[@]}"; do
        if [ -n "${DEPLOY_VARS[${addr}]:-}" ]; then
            no_proxy_addrs="${no_proxy_addrs},${DEPLOY_VARS[${addr}]}"
        fi
    done

    if [ -n "${no_proxy:-}" ]; then
        no_proxy_str="no_proxy=${no_proxy_addrs},${no_proxy}"
    else
        no_proxy_str="no_proxy=${no_proxy_addrs}"
    fi

    if [ -n "${NO_PROXY:-}" ]; then
        NO_PROXY_STR="NO_PROXY=${no_proxy_addrs},${NO_PROXY}"
    else
        NO_PROXY_STR="NO_PROXY=${no_proxy_addrs}"
    fi

    DEPLOY_VARS["no_proxy_str"]="${no_proxy_str}"
    DEPLOY_VARS["NO_PROXY_STR"]="${NO_PROXY_STR}"
}

valid_env_vars() {
    if [[ "${RUNTIME_VARS["MEMORY_DATA_PATH"]}" =~ ^/ ]]; then
        error "MEMORY_DATA_PATH only supports relative paths for container deployment!"
    else
        RUNTIME_VARS["MEMORY_DATA_PATH"]="/app/${RUNTIME_VARS["MEMORY_DATA_PATH"]}"
    fi

    if [[ "${DEPLOY_VARS["HAS_JIUWEN"]}" == "true" ||
          "${DEPLOY_VARS["HAS_DEEPSEARCH"]}" == "true" ]]; then
        if [[ "${RUNTIME_VARS["DB_TYPE"]}" == "mysql" &&
               -z "${RUNTIME_VARS["DB_HOST"]:-}" ]]; then
            error "Validation failed: DB_HOST is a mandatory configuration item that must be defined in .env.custom!"
        fi
    fi
}

# === env variable setup (ports, names, proxy, module config, nginx timeout) ===
process_env_vars() {
    process_ports
    generate_final_names
    setup_no_proxy_vars
    configure_module_env
    valid_env_vars

    local tms=${RUNTIME_VARS["VITE_API_PROXY_TIMEOUT"]}
    if ! [[ "${tms}" =~ ^[0-9]+$ ]]; then
        error "Error: The value of VITE_API_PROXY_TIMEOUT [${tms}] is not a valid number (only non-negative integers are supported)!"
    fi

    local nginx_read_timeout=$(( tms / 1000 ))
    DEPLOY_VARS["NGINX_READ_TIMEOUT"]=${nginx_read_timeout}
    DEPLOY_VARS["VERSION"]=$(extract_version "${DEPLOY_VARS["VERSION"]}")
}

# =========  Detect if it start the container, set env vars if yes =========
configure_module_env() {
    for module in "${ALL_MODULES[@]}"; do
        if [ "${DEPLOY_VARS["HAS_${module}"]}" == "false" ]; then
            continue
        fi
        case "${module}" in
            UPGRADE)
                if [ ${DEPLOY_VARS["HAS_UPGRADE"]}=="true" ]; then
                    DEPLOY_VARS["IS_UP_UPGRADE_TOOL"]="true"
                fi
                ;;
            MYSQL)
                if [ "${RUNTIME_VARS["DB_TYPE"]:-}" != "mysql" ]; then
                    DEPLOY_VARS["HAS_MYSQL"]="false"
                    continue
                fi
                if [ -n "${RUNTIME_VARS["DB_HOST"]:-}" ]; then
                    DEPLOY_VARS["HAS_MYSQL"]="false"
                    continue
                fi
                DEPLOY_VARS["HAS_MYSQL"]="true"
                DEPLOY_VARS["IS_UP_MYSQL"]="true"
                RUNTIME_VARS["DB_HOST"]=${DEPLOY_VARS["MYSQL_SERVICE"]}
                RUNTIME_VARS["DB_PORT"]="3306"
                ;;
            MILVUS)
                if [[ -n "${RUNTIME_VARS["MILVUS_HOST"]:-}" ||
                     -n "${RUNTIME_VARS["MINIO_HOST"]:-}" ]]; then
                    DEPLOY_VARS["HAS_MILVUS"]="false"
                    continue
                fi
                DEPLOY_VARS["HAS_MILVUS"]="true"
                local imt="${RUNTIME_VARS["INDEX_MANAGER_TYPE"]}"
                if [ "${imt}" == "milvus" ]; then
                    DEPLOY_VARS["IS_UP_ETCD"]="true"
                    DEPLOY_VARS["IS_UP_MILVUS"]="true"
                    RUNTIME_VARS["MILVUS_HOST"]=${DEPLOY_VARS["MILVUS_SERVICE"]}
                    RUNTIME_VARS["MILVUS_PORT"]="19530"
                fi
                DEPLOY_VARS["IS_UP_MINIO"]="true"
                RUNTIME_VARS["MINIO_HOST"]=${DEPLOY_VARS["MINIO_SERVICE"]}
                ;;
            PLUGIN)
                if [ -n "${RUNTIME_VARS["VITE_PLUGIN_SERVICE_URL"]:-}" ]; then
                    DEPLOY_VARS["HAS_PLUGIN"]="false"
                    continue
                fi
                local plugin_service=${DEPLOY_VARS["PLUGIN_SERVER_SERVICE"]}
                local plugin_port=${DEPLOY_VARS["PLUGIN_SERVER_PORT"]}
                DEPLOY_VARS["HAS_PLUGIN"]="true"
                DEPLOY_VARS["IS_UP_PLUGIN_SERVER"]="true"
                RUNTIME_VARS["VITE_PLUGIN_SERVICE_URL"]="http://${plugin_service}:${plugin_port}"
                ;;
            SANDBOX)
                if [ -n "${RUNTIME_VARS["CODE_SANDBOX_URL"]:-}" ]; then
                    DEPLOY_VARS["HAS_SANDBOX"]="false"
                    continue
                fi

                local gateway_service=${DEPLOY_VARS["SANDBOX_GATEWAY_SERVICE"]}
                local gateway_port=${DEPLOY_VARS["SANDBOX_GATEWAY_PORT"]}
                DEPLOY_VARS["HAS_SANDBOX"]="true"
                DEPLOY_VARS["IS_UP_SANDBOX_GATEWAY"]="true"
                RUNTIME_VARS["CODE_SANDBOX_URL"]="http://${gateway_service}:${gateway_port}/run"

                local els="${DEPLOY_VARS["ENABLE_LINUX_SANDBOX"],,}"
                if [ "${els}" == "false" ]; then
                    DEPLOY_VARS["IS_UP_PYTHON_SERVER"]="true"
                    DEPLOY_VARS["IS_UP_JS_SERVER"]="true"
                fi
                ;;
            JIUWEN)
                if [ -n "${RUNTIME_VARS["VITE_API_PROXY_TARGET"]:-}" ]; then
                    DEPLOY_VARS["HAS_JIUWEN"]="false"
                    continue
                fi
                local backend_service=${DEPLOY_VARS["BACKEND_SERVICE"]}
                local backend_port=${RUNTIME_VARS["BACKEND_PORT"]}
                DEPLOY_VARS["HAS_JIUWEN"]="true"
                DEPLOY_VARS["IS_UP_BACKEND"]="true"
                DEPLOY_VARS["IS_UP_FRONTEND"]="true"
                RUNTIME_VARS["VITE_API_PROXY_TARGET"]="http://${backend_service}:${backend_port}/"
                ;;
            DEEPSEARCH)
                if [ -n "${RUNTIME_VARS["DEEPSEARCH_AGENT_HOST"]:-}" ]; then
                    DEPLOY_VARS["HAS_DEEPSEARCH"]="false"
                    continue
                fi
                DEPLOY_VARS["HAS_DEEPSEARCH"]="true"
                DEPLOY_VARS["IS_UP_DEEPSEARCH"]="true"
                RUNTIME_VARS["DEEPSEARCH_AGENT_HOST"]=${DEPLOY_VARS["DEEPSEARCH_SERVICE"]}
                RUNTIME_VARS["DEEPSEARCH_AGENT_PORT"]="8000"
        esac
    done
}
