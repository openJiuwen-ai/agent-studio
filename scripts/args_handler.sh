#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ========== Parses command-line arguments ========== 
parse_args() {
    local i=0
    local args=("$@")
    local cmd=""
    local env_file=""
    local is_new_svc="false"
    local is_upgrade="false"
    local modules=()

    while [ $i -lt ${#args[@]} ]; do
        case "${args[$i]}" in
            -f|--file)
                # Parse -f option: must be followed by file path
                if [ $((i+1)) -ge ${#args[@]} ]; then
                    error "-f/--file option must be followed by <ENV_FILE> file path!"
                fi
                env_file="${args[$((i+1))]}"
                # Check if file exists
                if [ ! -f "${env_file}" ]; then
                    error "-f specified file does not exist: ${env_file}"
                fi
                i=$((i+2))  # Skip -f and file path
                ;;
            -n|--new)
                is_new_svc="true"
                i=$((i+1))
                ;;
            up|down|stop)
                # treat as commands
                if [ -n "$cmd" ]; then
                    error "please not specify two cmds: ${cmd} and ${args[$i]}"
                fi
                cmd="${args[$i]}"
                i=$((i+1))
                ;;
            upgrade|mysql|milvus|plugin|sandbox|deepsearch|jiuwen)
                # treat as modules
                local module="${args[$i]^^}"
                DEPLOY_VARS["HAS_${module}"]="true"
                modules+=("${module}")
                i=$((i+1))
                ;;
            --upgrade)
                is_upgrade="true"
                DEPLOY_VARS["HAS_UPGRADE"]="true"
                DEPLOY_VARS["IS_UP_UPGRADE_TOOL"]="true"
                i=$((i+1))
                ;;
            -h|--help)
                print_help
                ;;
            *)
                error "Invalid Args: ${args[$i]}"
                ;;
        esac
    done
    info "Executing command: $*"

    # Assign parsed commands to global variables for main function
    ARGS["CMD"]=${cmd}
    ARGS["ENV_FILE"]=${env_file}
    ARGS["IS_NEW_SVC"]=${is_new_svc}
    ARGS["IS_UPGRADE"]=${is_upgrade}

    process_module_args "${modules[@]}"
    valid_args
}

valid_args() {
    if [ -z "${ARGS["CMD"]}" ]; then
        error "No command specified"
    fi

    # Do not specify env file with new service creation
    if [[ "${ARGS["IS_NEW_SVC"]}" == "true" && -n "${ARGS["ENV_FILE"]}" ]]; then
        error "Option -f/--file and -n/--new cannot be specified simultaneously"
    fi

    # -n/--new only works with 'up' command
    if [[ "${ARGS["CMD"]}" != "up" && "${ARGS["IS_NEW_SVC"]}" == "true" ]]; then
        error "Option -n/--new is only supported with the 'up' command"
    fi

    # Upgrade requires both 'up' and -n/--new
    if [ "${ARGS["IS_UPGRADE"]}" == "true" ]; then
        if [[ "${ARGS["CMD"]}" != "up" || "${ARGS["IS_NEW_SVC"]}" != "true" ]]; then
            error "To upgrade from an old version existing instance to a new one, start the new instance with 'up -n/--new'"
        fi
    fi
}

process_module_args(){
    local modules=("$@")

    # deduplicate
    if [ ${#modules[@]} -gt 0 ]; then
        local deduped_modules=($(printf "%s\n" "${modules[@]}" | sort -u))
        ARGS_MODULES=("${deduped_modules[@]}")
    fi

    info "ARGS_MODULES: ${ARGS_MODULES[*]}"

    if [ ${#ARGS_MODULES[@]} -eq 0 ]; then
        for module in "MYSQL" "MILVUS" "PLUGIN" "SANDBOX" "DEEPSEARCH" "JIUWEN"
        do
            DEPLOY_VARS["HAS_${module}"]="true"
        done
    fi
}

# Print help info and exit
print_help() {
    cat << EOF
Usage: ./$(basename "$0") [MODULES] [COMMAND] [OPTIONS]

Commands:
  up        Start the services.
  down      Shutdown and clean up the services completely.
  stop      Pause the running services temporarily (can be restarted).

Options:
  -h,--help Show this help message and exit immediately.
  -f,--file Specify the path to the .env configuration file (for existing service).
  -n,--new  Force to start a BRAND NEW service (ignore existing .env file).
  --upgrade Start a new set of services upgraded from a lower version deployment.

Modules (optional):
  milvus        Deploy milvus module
  jiuwen        Deploy jiuwen module
  mysql         Deploy mysql module
  plugin        Deploy plugin module
  sandbox       Deploy sandbox module
  deepsearch    Deploy deepsearch module
Note: No module specified means deploy ALL modules.

Examples:
  1. Start all services (auto judge new/existing by .env existence)
     ./$(basename "$0") up
    Rule: If .env file does not exist -> start a brand new service;
          If .env file exists -> start the existing service.

  2. Start all services with specified .env file
     ./$(basename "$0") up -f .envs/env.<Instance ID>

  3. Force start a new service (ignore existing .env)
     ./$(basename "$0") up -n

  4. Start all services with specified .env file
     ./$(basename "$0") up -f .envs/env.<Instance ID>
 
  5. Start specified modules with current .env file
     ./$(basename "$0") milvus mysql up

  6. Start specified modules with specified .env file
     ./$(basename "$0") milvus mysql up -f .envs/env.<Instance ID>
 
  7. Pause all running services with current .env file
     ./$(basename "$0") stop

  8. Pause all running services with specified .env file
     ./$(basename "$0") stop -f .envs/env.<Instance ID>
 
  9. Shutdown all services completely with current .env file
     ./$(basename "$0") down

  10. Shutdown all services completely with specified .env file
     ./$(basename "$0") down -f .envs/env.<Instance ID>
EOF
    exit 0
}