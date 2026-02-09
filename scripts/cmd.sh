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
    local container_cmds=$2
    local docker_exec_prefix=""
    if [ "${DEPLOY_VARS["OS_TYPE"]}" == "windows" ]; then
        docker_exec_prefix="MSYS_NO_PATHCONV=1"
    fi
    local full_cmd="${docker_exec_prefix} docker exec -i ${container_name} /bin/bash -c \"${container_cmds}\""
    exec_cmd "${full_cmd}"
}
