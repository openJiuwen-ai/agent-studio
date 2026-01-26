#!/usr/bin/env bash
set -euo >/dev/null 2>&1


# ===== Merges default/custom .env files, and writes to final .env file ===== 
generate_env_file() {
    local default_deploy_env_file=${CONFIG["DEFAULT_DEPLOY_ENV_FILE"]}
    local default_runtime_env_file=${CONFIG["DEFAULT_RUNTIME_ENV_FILE"]}
    local current_deploy_env_file=${CONFIG["ENV_FILE"]}
    local env_dirs=${CONFIG["ENV_DIR"]}

    read_env_from_file "${default_deploy_env_file}" "DEPLOY_VARS"
    read_env_from_file "${default_runtime_env_file}" "RUNTIME_VARS"
    read_custom_env_file
    get_public_ip
    setup_env_vars

    local suffix=${DEPLOY_VARS["NAME_SUFFIX"]}
    local deploy_env_file="${env_dirs}/env.deploy.${suffix}"
    local runtime_env_file="${env_dirs}/env.runtime.${suffix}"

    write_env_to_file "${current_deploy_env_file}" "DEPLOY_VARS"
    info "Copy ${current_deploy_env_file} to ${deploy_env_file}"
    mkdir -p ${env_dirs}
    cp ${current_deploy_env_file} ${deploy_env_file}

    write_env_to_file "${runtime_env_file}" "RUNTIME_VARS"
}

# ===== Writes sorted key-value pairs to .env.** file =====
write_env_to_file() {
    local env_file=$1
    local -n source_array=$2

    info "Writing variable array DEPLOY_VARS to file: ${env_file}"
    > "${env_file}"
    printf "%s\n" "${!source_array[@]}" | sort | while read -r key; do
        if [[ -n "${key}" ]]; then
            echo "${key}=${source_array[$key]}" >> "${env_file}"
        fi
    done
}

# read key-value pairs from .env.custom file into RUNTIME_VARS and DEPLOY_VARS array
read_custom_env_file() {
    local custom_env_file=${CONFIG["CUSTOM_ENV_FILE"]}
    if [ ! -f ${custom_env_file} ]; then
        return
    fi
    local os_type=${CONFIG["OS_TYPE"]}
    local -a default_deploy_keys=("${!DEPLOY_VARS[@]}")
    local -a default_runtime_keys=("${!RUNTIME_VARS[@]}")
    local -a other_deploy_keys=("${!NAMES[@]}")
    other_deploy_keys+=("${PORTS[@]}")
    default_deploy_keys+=("IP")

    # Read .env line by line, exclude comments and empty lines, store in associative array
    while IFS= read -r line || [[ -n "${line}" ]]; do
        if [[
            ! "${line}" =~ ^[[:space:]]*# &&  # Not a comment line
            -n "${line//[[:space:]]/}"        # Not empty (has content after removing all whitespace)
        ]]; then
            # Remove leading/trailing whitespace
            if [[ "$os_type" == "macos" ]]; then
                line_trimmed=$(echo "${line}" | sed -E 's/^[[:space:]]*//;s/[[:space:]]*$//')
            else
                line_trimmed=$(echo "${line}" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
            fi

            # Skip invalid lines without equals sign
            if [[ "${line_trimmed}" != *"="* ]]; then
                info "Skipping invalid line without equals sign: ${line_trimmed}"
                continue
            fi

            # Split key and value (supports values containing =)
            # Find first = position, left is key, right is value
            local key="${line_trimmed%%=*}"
            local value="${line_trimmed#*=}"

            # Remove outer single/double quotes from value
            if [[ "${value}" =~ ^\"(.*)\"$ ]]; then
                value="${BASH_REMATCH[1]}"
            elif [[ "${value}" =~ ^\'(.*)\'$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi

            if [[ " ${default_deploy_keys[*]} " =~ " ${key} " ]]; then
                info "Override deploy variable: ${key}=${value}"
                DEPLOY_VARS["${key}"]="${value}"
            elif [[ " ${default_runtime_keys[*]} " =~ " ${key} " ]]; then
                info "Override runtime variable: ${key}=${value}"
                RUNTIME_VARS["${key}"]="${value}"
            elif [[ " ${other_deploy_keys[*]} " =~ " ${key} " ]]; then
                info "Override deploy variable (no-default): ${key}=${value}"
                DEPLOY_VARS["${key}"]="${value}"
            else
                info "Override runtime variable (no-default): ${key}=${value}"
                RUNTIME_VARS["${key}"]="${value}"
            fi
        fi
    done < "${custom_env_file}"
}


# == read key-value pairs from .env.** file into array (for first start-up) ==
read_env_from_file() {
    local env_file=$1
    local -n target_array=$2
    local os_type=${CONFIG["OS_TYPE"]}

    if [ ! -f "${env_file}" ]; then
        error ".env file does not exist: ${env_file}"
    fi
    info "Loading .env file into variable array: ${env_file}"

    # Read .env.** line by line, exclude comments and empty lines, store in associative array
    while IFS= read -r line || [[ -n "${line}" ]]; do
        if [[
            ! "${line}" =~ ^[[:space:]]*# &&  # Not a comment line
            -n "${line//[[:space:]]/}"        # Not empty (has content after removing all whitespace)
        ]]; then
            # Remove leading/trailing whitespace
            if [[ "$os_type" == "macos" ]]; then
                line_trimmed=$(echo "${line}" | sed -E 's/^[[:space:]]*//;s/[[:space:]]*$//')
            else
                line_trimmed=$(echo "${line}" | sed -e 's/^[ \t]*//' -e 's/[ \t]*$//')
            fi

            # Skip invalid lines without equals sign
            if [[ "${line_trimmed}" != *"="* ]]; then
                info "Skipping invalid line without equals sign: ${line_trimmed}"
                continue
            fi

            # Split key and value (supports values containing =)
            # Find first = position, left is key, right is value
            key="${line_trimmed%%=*}"
            value="${line_trimmed#*=}"

            # Remove outer single/double quotes from value
            if [[ "${value}" =~ ^\"(.*)\"$ ]]; then
                value="${BASH_REMATCH[1]}"
            elif [[ "${value}" =~ ^\'(.*)\'$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi

            target_array["${key}"]="${value}"
        fi
    done < "${env_file}"
}


# ==== load key-value pairs from .env.** files into array (for restart-up/down/stop) ===
load_env_from_file() {
    local deploy_env_file=$1
    read_env_from_file "${deploy_env_file}" "DEPLOY_VARS"

    local suffix=${DEPLOY_VARS["NAME_SUFFIX"]}
    local env_dirs=${CONFIG["ENV_DIR"]}
    local runtime_env_file="${env_dirs}/env.runtime.${suffix}"
    read_env_from_file "${runtime_env_file}" "RUNTIME_VARS"
}

# ============ Processes .env.** file per command (up/down/stop) ========
process_env_file() {
    local cmd=${ARGS["CMD"]}
    local arg_env_file=${ARGS["ENV_FILE"]}
    local arg_new_svc=${ARGS["IS_NEW_SVC"]}
    local current_env_file=${CONFIG["ENV_FILE"]}

    case "${cmd}" in
        up)
            if [[ "${arg_new_svc}" == "true" || ( -z "${arg_env_file}" && ! -f "${current_env_file}" ) ]]; then
                generate_env_file
            elif [ -z "${arg_env_file}" ]; then
                load_env_from_file "${current_env_file}"
            else
                load_env_from_file "${arg_env_file}"
            fi
            generate_ssl_certs conf/.ssl-dirs/ssl-${DEPLOY_VARS["NAME_SUFFIX"]}
            ;;
    
        down|stop)
            if [ -z "${arg_env_file}" ]; then
                load_env_from_file "${current_env_file}"
            else
                load_env_from_file "${arg_env_file}"
            fi
            ;;
    esac
    fill_containers_name
}