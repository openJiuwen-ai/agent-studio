#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# === Extracts and deduplicates <<variable>> placeholders from template ===
extract_placeholders() {
    local templatefile="$1"
    local -a placeholders=($(grep -oE '<<[^>]+>>' "${templatefile}" | sort -u))
    echo "${placeholders[@]}"
}

# ==== Replaces <<variable>> placeholder with its value ===
replace_placeholder() {
    local placeholder="$1"
    local destfile="$2"
    local vars_arr_name=$3
    local var_name=$(echo "${placeholder}" | sed -e 's/^<<//' -e 's/>>$//')
    local arr_key_ref="${vars_arr_name}[${var_name}]"
    local var_value="${!arr_key_ref:-}"
    local os_type=${DEPLOY_VARS["OS_TYPE"]}

    #info "  Replacing placeholder: ${placeholder} → ${var_value}"
    if [ "${os_type}" == "macos" ]; then
        # macOS sed requires backup extension with -i
        sed -i.bak "s|${placeholder}|${var_value}|g" "${destfile}"
        rm -f "${destfile}.bak"
    else
        # Linux/Windows: use awk
        awk -v ph="${placeholder}" -v val="${var_value}" '
            { gsub(ph, val); print }
        ' "${destfile}" > "${destfile}.tmp" && mv -f "${destfile}.tmp" "${destfile}"
    fi
}

# ==== Generates final config file by replacing placeholders in template ===
generate_config_file() {
    local templatefile=$1
    local destfile=$2
    local var_name=$3
    # Verify template file exists
    if [ ! -f "${templatefile}" ]; then
        error "Template file does not exist: ${templatefile}"
    fi
    info "Using template file: ${templatefile}"

    # Extract all placeholders
    local -a placeholders=($(extract_placeholders "${templatefile}"))
    if [ ${#placeholders[@]} -eq 0 ]; then
        warning "No <<variable_name>> format placeholders found in template file"
    fi

    # Copy template as target file
    exec_cmd "cp -f ${templatefile} ${destfile}"

    # Loop to replace each placeholder
    info "Starting placeholder replacement..."
    for placeholder in "${placeholders[@]}"; do
        replace_placeholder "${placeholder}" "${destfile}" "${var_name}"
    done

    success "Final file: ${destfile}"
}


# ==== Generate nginx file ===
generate_nginx_file() {
    local nginx_template_file=${CONFIG["NGINX_TEMPLATE_FILE"]}
    local nginx_dir="${CONFIG["CONFIG_DIR"]}/.nginx-files"
    local nginx_file="${nginx_dir}/nginx.conf.${DEPLOY_VARS["NAME_SUFFIX"]}"

    exec_cmd "mkdir -p ${nginx_dir}"
    generate_config_file ${nginx_template_file} ${nginx_file} "ALL_VARS"
}

generate_deepsearch_env_file() {
    local db_type="${RUNTIME_VARS["DB_TYPE"]}"
    DEEPSERACH_ENV_VARS["DB_TYPE"]="${db_type}"

    case "${db_type}" in
        mysql)
            DEEPSERACH_ENV_VARS["DB_HOST"]="${RUNTIME_VARS["DB_HOST"]}"
            DEEPSERACH_ENV_VARS["DB_PORT"]="${RUNTIME_VARS["DB_PORT"]}"
            DEEPSERACH_ENV_VARS["DB_USER"]="${RUNTIME_VARS["DB_USER"]}"
            DEEPSERACH_ENV_VARS["DB_PASSWORD"]="${RUNTIME_VARS["DB_PASSWORD"]}"
            DEEPSERACH_ENV_VARS["DEEPSEARCH_DB_NAME"]="${DEPLOY_VARS["DEEPSEARCH_DB_NAME"]}"
            ;;
        sqlite)
            DEEPSERACH_ENV_VARS["SQLITE_DB_PATH"]="${RUNTIME_VARS["SQLITE_DB_PATH"]}"
            DEEPSERACH_ENV_VARS["DEEPSEARCH_SQLITE_DB"]="${DEPLOY_VARS["DEEPSEARCH_SQLITE_DB"]}"
            ;;
    esac

    local env_file="${CONFIG["ENV_DIR"]}/env.deepsearch.${DEPLOY_VARS["NAME_SUFFIX"]}"
    write_env_to_file "${env_file}" "DEEPSERACH_ENV_VARS"
}

# ==== Generates all project config files by their template file ===
generate_config_files() {
    for key in "${!DEPLOY_VARS[@]}"; do
        ALL_VARS["${key}"]="${DEPLOY_VARS[${key}]}"
    done

    for key in "${!RUNTIME_VARS[@]}"; do
        ALL_VARS["${key}"]="${RUNTIME_VARS[${key}]}"
    done

    # generate docker compose file
    for module in "${ALL_MODULES[@]}"; do
        if [ "${DEPLOY_VARS["HAS_${module}"]}" == "false" ]; then
            continue
        fi
        case "${module}" in
            JIUWEN)
                generate_nginx_file
                ;;
            DEEPSEARCH)
                generate_deepsearch_env_file
                ;;
        esac

        local template_file=${COMPOSE_TEMPLATE_FILES["${module}"]}
        local compose_file=${COMPOSE_FILES["${module}"]}
        generate_config_file ${template_file} ${compose_file} "ALL_VARS"
    done
}
