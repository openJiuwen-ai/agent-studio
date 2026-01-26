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