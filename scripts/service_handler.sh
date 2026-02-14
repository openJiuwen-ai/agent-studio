#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# Perform post-start setup operations for specific service modules
post_start_setup(){
    local module="$1"
    if [[ "${module}" == "MILVUS" 
        && "${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}" == "false" ]]; then
        info "No need to waiting for MILVUS container ready!"
        return
    fi

    if [ "${module}" == "MYSQL" ]; then
        wait_for_mysql
        if [ "${ARGS["IS_UPGRADE"]}" == "false" ]; then
            create_all_dbs
        fi
        return
    fi

    local container="$2"
    wait_for_container_healthy "${container}"
}

# Check if the specified module exists in the ARGS_MODULES
is_module_in_args() {
    local target_module="$1"

    if [ ${#ARGS_MODULES[@]} -eq 0 ]; then
        return 0
    fi

    for item in "${ARGS_MODULES[@]}"; do
        if [ "$item" == "$target_module" ]; then
            return 0
        fi
    done

    return 1
}

# Process a single service of a specified module (handle start/stop/etc. via docker compose)
process_service() {
    local module="$1"
    local component="$2"

    if [[ "${DEPLOY_VARS["HAS_${module}"]}" == "false" ||
         "${DEPLOY_VARS["IS_UP_${component}"]}" == "false" ]]; then
        info "Skip processing ${module}/${component}: disabled in deployment config"
        return
    fi

    if ! is_module_in_args "${module}"; then
        info "Skip processing ${module}/${component}: not included in arg modules"
        return
    fi

    local cmd=${ARGS["CMD"]}
    local compose_file=${COMPOSE_FILES["${module}"]}
    local service="${DEPLOY_VARS["${component}_SERVICE"]}"
    local container="${DEPLOY_VARS["${component}_DOCKER"]}"
    local cmd_args=""
    if [ "${cmd}" = "up" ]; then
        cmd_args="-d"
    fi

    info "[PROCESSING SERVICE] Module: ${module}, Component: ${component}, Cmd: ${cmd}"
    exec_cmd "docker compose -f ${compose_file} ${cmd} ${cmd_args} ${service}"
    if [ "${cmd}" == "up" ]; then
        post_start_setup "${module}" "${container}"
    fi

    success "${module}/${component} is ${cmd}!"
}

# Process all services of the specified module
process_services() {
    for module in $1
    do
        for component in ${COMPONENTS["${module}"]}
        do
            process_service "${module}" "${component}"
        done
    done
}

# Process all services of all modules
process_all_services() {
    process_services "UPGRADE"
    process_services "MYSQL"
    uprade_mysql
    process_services "MILVUS"
    upgrade_milvus
    process_services "PLUGIN"
    process_services "SANDBOX"
    process_services "DEEPSEARCH"
    process_service "JIUWEN" "BACKEND"
    upgrade_sqlite
    process_service "JIUWEN" "FRONTEND"
}