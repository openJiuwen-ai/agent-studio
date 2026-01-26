#!/usr/bin/env bash
set -euo >/dev/null 2>&1

source "./global_vars.sh"
source "./common.sh"
source "./args_handler.sh"
source "./gen_ssl.sh"
source "./ports_handler.sh"
source "./envfile_handler.sh"
source "./template_handler.sh"
source "./container_handler.sh"
source "./vars_handler.sh"
source "./prompt_handler.sh"
source "./cmd.sh"

# ==== Executes Docker Compose commands (up/down/stop) for enabled modules ====
exec_service() {
    local cmd=${ARGS["CMD"]}
    local exec_cmd=${CONFIG["DOCKER_COMPOSE_CMD"]}

    local cmd_args=""
    if [ "${cmd}" = "up" ]; then
        cmd_args="-d"
    fi

    local modules=("${ARGS_MODULES[@]}")
    if [ ${#modules[@]} -eq 0 ]; then
        modules=("${ALL_MODULES[@]}")
    fi

    for module in "${modules[@]}"; do
        local has_it="${DEPLOY_VARS["HAS_${module}_CONTAINER"]}"
        if [ "${has_it}" == "true" ]; then
            local compose_file=${COMPOSE_FILES["${module}"]}
            case "${module}" in
                MYSQL)
                    exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args}"
                    if [ "${cmd}" == "up" ]; then
                        wait_for_mysql
                        create_db_if_not_exist
                    fi
                    ;;
                MILVUS)
                    local index_manager_type="${RUNTIME_VARS["INDEX_MANAGER_TYPE"]}"
                    local minio_service=${DEPLOY_VARS["MINIO_SERVICE"]}

                    if [ "${cmd}" == "up" ]; then
                        if [ "${index_manager_type}" == "chroma" ]; then
                            exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args} ${minio_service}"
                        else
                            exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args}" "false"
                        fi
                    else
                        if [ "${index_manager_type}" == "chroma" ]; then
                            exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args} ${minio_service}"
                        else
                            exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args}"
                        fi
                    fi
                    ;;
                JIUWEN|PLUGIN)
                    exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args}"
                    if [ "${cmd}" == "up" ]; then
                        check_containers "${CONTAINERS[${module}]}"
                    fi
                    ;;
                SANDBOX)
                    local enable_linux_sandbox=$(echo "${DEPLOY_VARS["ENABLE_LINUX_SANDBOX"]}" | tr '[:upper:]' '[:lower:]')
                    local sandbox_gateway_service=${DEPLOY_VARS["SANDBOX_GATEWAY_SERVICE"]}
                    local sandbox_gateway_docker=${DEPLOY_VARS["SANDBOX_GATEWAY_DOCKER"]}

                    if [ "${enable_linux_sandbox}" == "true" ]; then
                        exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args} ${sandbox_gateway_service}"
                        if [ "${cmd}" == "up" ]; then
                            check_containers "${sandbox_gateway_docker}"
                        fi
                    else
                        exec_cmd "${exec_cmd} -f ${compose_file} ${cmd} ${cmd_args}"
                        if [ "${cmd}" == "up" ]; then
                            check_containers "${CONTAINERS[${module}]}"
                        fi
                    fi

            esac
            success "${cmd} ${module} container"
        fi
    done
}


# ==================== Main function ====================
main() {
    parse_args "$@"
    detect_os
    check_docker
    process_env_file
    generate_config_files
    exec_service
    show_deploy_prompt
}

# Execute main function
main "$@"
