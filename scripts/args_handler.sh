#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ========== Parses command-line arguments ========== 
parse_args() {
    local i=0
    local args=("$@")
    local cmd=""
    local env_file=""
    local is_new_svc="false"
    local modules=()

    while [ $i -lt ${#args[@]} ]; do
        case "${args[$i]}" in
            -f|--file)
                # Parse -f option: must be followed by file path
                if [ $((i+1)) -ge ${#args[@]} ]; then
                    error "-f/--file option must be followed by .env file path!"
                fi
                env_file="${args[$((i+1))]}"
                # Check if file exists (optional, can also check in read_env_from_file)
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
            milvus|jiuwen|mysql|plugin|sandbox)
                # treat as modules
                local module=$(echo "${args[$i]}" | tr 'a-z' 'A-Z')
                modules+=("${module}")
                key="HAS_${module}_CONTAINER"
                DEPLOY_VARS["${key}"]="true"
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
    if [ -z "${cmd}" ]; then
        error "No command specified"
    fi
    
    # deduplicate
    if [ ${#modules[@]} -gt 0 ]; then
        local deduped_modules=($(printf "%s\n" "${modules[@]}" | sort -u))
        modules=("${deduped_modules[@]}")
    fi

    # should not specify .env when bring up new services
    if [[ "${is_new_svc}" == "true" && -n "${env_file}" ]]; then
        error "Please do not specify -f and -n in the sametime"
    fi

    # Assign parsed commands to global variables for main function
    ARGS["CMD"]=${cmd}
    ARGS["ENV_FILE"]=${env_file}
    ARGS["IS_NEW_SVC"]=${is_new_svc}
    ARGS_MODULES=("${modules[@]}")

    if [ ${#ARGS_MODULES[@]} -eq 0 ]; then
        info "ARGS_MODULES: <full>"
    else
        info "ARGS_MODULES: ${ARGS_MODULES[*]}"
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

Modules (for service.sh/cluster.sh, optional):
  milvus    Deploy milvus module
  jiuwen    Deploy jiuwen module
  mysql     Deploy mysql module
  plugin    Deploy plugin module
  sandbox   Deploy sandbox module
Note: No module specified means deploy ALL modules.

Examples:
  1. Start all services (auto judge new/existing by .env existence)
     ./$(basename "$0") up
    Rule: If .env file does not exist -> start a brand new service;
          If .env file exists -> start the existing service.

  2. Start all services with specified .env file
     ./$(basename "$0") up -f .envs/env.<*****>

  3. Force start a new service (ignore existing .env)
     ./$(basename "$0") up -n

  4. Start all services with specified .env file
     ./$(basename "$0") up -f .envs/env.<*****>
 
  5. Start specified modules with current .env file
     ./$(basename "$0") milvus mysql up

  6. Start specified modules with specified .env file
     ./$(basename "$0") milvus mysql up -f .envs/env.<*****>
 
  7. Pause all running services with current .env file
     ./$(basename "$0") stop

  8. Pause all running services with specified .env file
     ./$(basename "$0") stop -f .envs/env.<*****>
 
  9. Shutdown all services completely with current .env file
     ./$(basename "$0") down

  10. Shutdown all services completely with specified .env file
     ./$(basename "$0") down -f .envs/env.<*****> 
EOF
    exit 0
}