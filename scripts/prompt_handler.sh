#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ==== Displays access prompts for openJiuwen Agent Platform ====
show_jiuwen_deploy_prompt() {
    local frontend_port=${DEPLOY_VARS["FRONTEND_HOST_PORT"]}
    info "openJiuwen Agent Platform:"
    info "\tLocal access: https://localhost:${frontend_port}"
    if [ -n "${DEPLOY_VARS["IP"]:-}" ]; then
        info "\tNetwork access: https://${DEPLOY_VARS["IP"]}:${frontend_port}"
    fi
}

# ==== Shows deployment prompts for started modules ====
show_deploy_prompt() {
    if [ "${ARGS["CMD"]}" != "up" ]; then
        return
    fi

    if [ "${DEPLOY_VARS["HAS_JIUWEN"]}" == "true" ]; then
        show_jiuwen_deploy_prompt
        return
    fi

    for module in "${ALL_MODULES[@]}"; do
        if [ "${DEPLOY_VARS["HAS_${module}"]}" == "false" ]; then
            continue
        fi
        case "${module}" in
            MYSQL)
                success "MYSQL Server started" 
                info "To use it, please set the following value in .env:"
                echo "DB_HOST=localhost"
                echo "DB_PORT=${DEPLOY_VARS["MYSQL_HOST_PORT"]}"
                echo "DB_USER=root"
                echo "DB_PASSWORD=${DEPLOY_VARS["DB_ROOT_PASSWORD"]}"
                info ""
                ;;
            MILVUS)
                success "Milvus Server started"
                info "To use it, please set the following value in .env:"
                echo "MILVUS_HOST=localhost"
                echo "MILVUS_PORT=${DEPLOY_VARS["MILVUS_HOST_PORT"]}"
                info ""
                ;;
            PLUGIN)
                success "Plugin Server started"
                info "To use it, please set the following value in .env:"
                echo "VITE_PLUGIN_CONFIG_PATH=/config.json"
                echo "VITE_PLUGIN_SERVICE_URL=http://localhost:${DEPLOY_VARS["PLUGIN_SERVER_HOST_PORT"]}"
                info ""
                ;;
            SANDBOX)
                success "Sandbox Server started"
                info "To use it, please set the following value in .env:"
                echo "CODE_SANDBOX_URL=http://localhost:${DEPLOY_VARS["SANDBOX_GATEWAY_HOST_PORT"]}/run"
                info ""
                ;;
            DEEPSEARCH)
                success "Deepsearch Server started"
                info "To use it, please set the following value in .env:"
                echo "DEEPSEARCH_AGENT_HOST=localhost"
                echo "DEEPSEARCH_AGENT_PORT=${DEPLOY_VARS["DEEPSEARCH_HOST_PORT"]}"
                info ""
                ;;
        esac
    done
}
