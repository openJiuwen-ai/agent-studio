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
    local os_type=${CONFIG["OS_TYPE"]}

    # Get value from associative array (error if not found)
    # if [ -z "${var_value}" ]; then  # 直接判断间接引用拿到的值
    #     error "Variable [${var_name}] not found! Please define in .env file"
    # fi 

    #info "  Replacing placeholder: ${placeholder} → ${var_value}"
    if [[ "$os_type" == "macos" ]]; then
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
    cp -f "${templatefile}" "${destfile}" || error "Cannot create target file: ${destfile}"

    # Loop to replace each placeholder
    info "Starting placeholder replacement..."
    for placeholder in "${placeholders[@]}"; do
        replace_placeholder "${placeholder}" "${destfile}" "${var_name}"
    done

    success "Final file: ${destfile}"
}

# ==== Generates all project config files by their template file ===
generate_config_files() {
    local nginx_template_file=${CONFIG["NGINX_TEMPLE_FILE"]}
    local nginx_dir="${CONFIG["CONFIG_DIR"]}/.nginx-files"
    local nginx_file="${nginx_dir}/nginx.conf.${DEPLOY_VARS["NAME_SUFFIX"]}"
    declare -A ALL_VARS

    for key in "${!DEPLOY_VARS[@]}"; do
        ALL_VARS["${key}"]="${DEPLOY_VARS[$key]}"
    done

    for key in "${!RUNTIME_VARS[@]}"; do
        ALL_VARS["${key}"]="${RUNTIME_VARS[$key]}"
    done

    mkdir -p ${nginx_dir}
    generate_config_file ${nginx_template_file} ${nginx_file} "ALL_VARS"

    for module in "${ALL_MODULES[@]}"; do
        local has_it="${DEPLOY_VARS["HAS_${module}_CONTAINER"]}"
        if [ "${has_it}" == "true" ]; then
            local template_file=${COMPOSE_TEMPLATE_FILES["${module}"]}
            local compose_file=${COMPOSE_FILES["${module}"]}
            local enable_linux_sandbox=$(echo "${DEPLOY_VARS["ENABLE_LINUX_SANDBOX"]}" | tr '[:upper:]' '[:lower:]')

            if [ "${module}" == "SANDBOX" -a "${enable_linux_sandbox}" == "true" ]; then
                ALL_VARS["PRIVILEGED_SECURITY_OPTS"]=$(cat <<'EOF'
cap_add:
      - SYS_ADMIN
    security_opt:
      - seccomp=unconfined
      - apparmor=unconfined
EOF
                )
            fi
            generate_config_file ${template_file} ${compose_file} "ALL_VARS"
        fi
    done
}
