#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ===== Execute command with failure control:   ====
# ===== exit on error unless arg2 is 'false' (arg2 optional)  ====
exec_cmd() {
    local cmd=$1
    local fail_quit="${2:-true}"

    info "${cmd}"
    if [ "${fail_quit}" == "false" ]; then
        eval "${cmd}" || warning "${cmd} failed"
    else
        eval "${cmd}" || error "${cmd} failed"
    fi 
}

docker_exec_cmd() {
    local container_name=$1
    local cmds=$2
    local docker_exec_prefix=""
    if [ "${DEPLOY_VARS["OS_TYPE"]}" == "windows" ]; then
        docker_exec_prefix="MSYS_NO_PATHCONV=1"
    fi
    local full_cmd="${docker_exec_prefix} docker exec -i ${container_name} /bin/bash -c \"${cmds}\""
    exec_cmd "${full_cmd}"
}

# Copy the local command file to container, and executes it
docker_exec_cmd_file() {
    local container_name=$1
    local host_cmd_file=$2
    local cmd_file_name=$(basename "${host_cmd_file}")
    local container_cmd_file="/root/${cmd_file_name}"
    local docker_exec_prefix=""
    if [ "${DEPLOY_VARS["OS_TYPE"]}" == "windows" ]; then
        docker_exec_prefix="MSYS_NO_PATHCONV=1"
    fi

    exec_cmd "docker cp ${host_cmd_file} ${upgrade_container}:${container_cmd_file}"

    local chmod_cmd="${docker_exec_prefix} docker exec -i ${container_name} chmod +x ${container_cmd_file}"
    exec_cmd "${chmod_cmd}"

    local full_cmd="${docker_exec_prefix} docker exec -i ${container_name} /bin/bash -c \"${container_cmd_file}\""
    exec_cmd "${full_cmd}"
}