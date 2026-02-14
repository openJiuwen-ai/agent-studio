#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# Validate the pre-upgrade environment directory and its env files format
read_pre_upgrade_env(){
    local pre_upgrade_env_dir=${CONFIG["PRE_UPGRADE_ENV_DIR"]}

    info "Validating pre-upgrade environment directory: ${pre_upgrade_env_dir}"
    if [ ! -d "${pre_upgrade_env_dir}" ]; then
        error "Directory not found - ${pre_upgrade_env_dir}"
    fi

    local -a env_files=()
    while IFS= read -r file; do
        env_files+=("${file}")
    done < <(find "${pre_upgrade_env_dir}" -maxdepth 1 -type f ! -name ".gitkeep" -printf "%f\n" | sort)

    local file_count=${#env_files[@]}
    case ${file_count} in
        0)
            error "No files found."
            ;;
        1)
            local single_file=${env_files[0]}
            if [[ ! "${single_file}" =~ ^\.?env\.([a-z0-9]{5})$ ]]; then
                error "Expected format: env.<5-random-chars>, Actual: ${single_file}"
            fi
            info "1 valid file found: ${single_file}"

            DEPLOY_VARS["PRE_UPGRADE_ENV_FILE"]="${pre_upgrade_env_dir}/${single_file}"
            read_env_from_file "${DEPLOY_VARS["PRE_UPGRADE_ENV_FILE"]}" "PRE_UPGRADE_VARS"

            if [ -z "${PRE_UPGRADE_VARS["HAS_JIUWEN_CONTAINER"]:-}" ]; then
                DEPLOY_VARS["PRE_UPGRADE_VERSION"]="0.1.1"
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MYSQL"]="true"
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MILVUS"]="true"
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_BACKEND"]="true"
                PRE_UPGRADE_VARS["DB_TYPE"]="mysql"
            else
                DEPLOY_VARS["PRE_UPGRADE_VERSION"]="0.1.2"
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MYSQL"]=${PRE_UPGRADE_VARS["HAS_MYSQL_CONTAINER"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MILVUS"]=${PRE_UPGRADE_VARS["HAS_MILVUS_CONTAINER"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_BACKEND"]=${PRE_UPGRADE_VARS["HAS_JIUWEN_CONTAINER"]}
            fi

            DEPLOY_VARS["PRE_UPGRADE_IM_TYPE"]="milvus"
            DEPLOY_VARS["PRE_UPGRADE_BACKEND_DOCKER"]=${PRE_UPGRADE_VARS["BACKEND_DOCKER_NAME"]}
            ;;
        2)
            local deploy_file=""
            local runtime_file=""
            local deploy_file_suffix=""
            local runtime_file_suffix=""
            for file in "${env_files[@]}"; do
                if [[ "${file}" =~ ^env\.deploy\.([a-z0-9]{5})$ ]]; then
                    deploy_file="${file}"
                    deploy_file_suffix="${BASH_REMATCH[1]}"
                elif [[ "${file}" =~ ^env\.runtime\.([a-z0-9]{5})$ ]]; then
                    runtime_file="${file}"
                    runtime_file_suffix="${BASH_REMATCH[1]}"
                else
                    error "${file} is not 'env.deploy.<5-random-chars>' nor 'env.runtime.<5-random-chars>'"
                fi
            done
            if [ "${deploy_file_suffix}" != "${runtime_file_suffix}" ]; then
                print_array env_files
                error "5 random chars mismatched between deploy and runtime files."
            fi
            info "2 valid files found - ${deploy_file} ${runtime_file}"

            read_env_from_file "${pre_upgrade_env_dir}/${deploy_file}" "PRE_UPGRADE_VARS"
            read_env_from_file "${pre_upgrade_env_dir}/${runtime_file}" "PRE_UPGRADE_VARS"

            DEPLOY_VARS["PRE_UPGRADE_DEPLOY_ENV_FILE"]="${pre_upgrade_env_dir}/${deploy_file}"
            DEPLOY_VARS["PRE_UPGRADE_RUNTIME_ENV_FILE"]="${pre_upgrade_env_dir}/${runtime_file}"
            DEPLOY_VARS["PRE_UPGRADE_IM_TYPE"]=${PRE_UPGRADE_VARS["INDEX_MANAGER_TYPE"]}
            DEPLOY_VARS["PRE_UPGRADE_BACKEND_DOCKER"]=${PRE_UPGRADE_VARS["BACKEND_DOCKER"]}

            if [ -n "${PRE_UPGRADE_VARS["HAS_JIUWEN_CONTAINER"]:-}" ]; then
                DEPLOY_VARS["PRE_UPGRADE_VERSION"]="0.1.3"
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MYSQL"]=${PRE_UPGRADE_VARS["HAS_MYSQL_CONTAINER"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MILVUS"]=${PRE_UPGRADE_VARS["HAS_MILVUS_CONTAINER"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_BACKEND"]=${PRE_UPGRADE_VARS["HAS_JIUWEN_CONTAINER"]}
            else
                DEPLOY_VARS["PRE_UPGRADE_VERSION"]=$(extract_version "${PRE_UPGRADE_VARS["VERSION"]}") 
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MYSQL"]=${PRE_UPGRADE_VARS["IS_UP_MYSQL"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_MILVUS"]=${PRE_UPGRADE_VARS["IS_UP_MILVUS"]}
                DEPLOY_VARS["PRE_UPGRADE_IS_UP_BACKEND"]=${PRE_UPGRADE_VARS["IS_UP_BACKEND"]}
            fi
            ;;
        *)
            error "Too many files (max 2 allowed). Found ${file_count} files."
            ;;
    esac
    info "PRE_UPGRADE_VERSION: ${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}"
    success "Pre-upgrade environment validation Done!"
}


# Check compatibility of pre-upgrade and post-upgrade environment parameters
check_upgrade_env() {
    local pre_upgrade_db_type=${PRE_UPGRADE_VARS["DB_TYPE"]}
    local post_upgrade_db_type=${RUNTIME_VARS["DB_TYPE"]}
    if [ "${pre_upgrade_db_type}" != "${post_upgrade_db_type}" ]; then
        error "Not support to migrate from ${pre_upgrade_db_type} to ${post_upgrade_db_type}"
    fi

    if [[ ${DEPLOY_VARS["PRE_UPGRADE_IS_UP_MYSQL"]} == "true" && 
          ${DEPLOY_VARS["IS_UP_MYSQL"]} == "true" ]]; then
          DEPLOY_VARS["IS_UPGRADE_MYSQL"]="true"
    fi

    local pre_upgrade_im_type=${DEPLOY_VARS["PRE_UPGRADE_IM_TYPE"]}
    local post_upgrade_im_type=${RUNTIME_VARS["INDEX_MANAGER_TYPE"]}
    if [ "${pre_upgrade_im_type}" != "${post_upgrade_im_type}" ]; then
        error "Not support to migrate from ${pre_upgrade_im_type} to ${post_upgrade_im_type}"
    fi

    if [[ ${DEPLOY_VARS["PRE_UPGRADE_IS_UP_MILVUS"]} == "true" && 
          ${DEPLOY_VARS["IS_UP_MILVUS"]} == "true" ]]; then
        DEPLOY_VARS["IS_UPGRADE_MILVUS"]="true"
    fi
}

# validation of pre-upgrade (dir, env, compatibility)
valid_upgrade(){
    read_pre_upgrade_env
    check_upgrade_env

    if [[ "${RUNTIME_VARS["DB_TYPE"]}" != "sqlite" &&
         "${DEPLOY_VARS["IS_UPGRADE_MYSQL"]}" == "false" && 
         "${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}" == "false" ]]; then
        error "Does not meet the upgrade requirements"
    fi

    if [[ "${DEPLOY_VARS["IS_UPGRADE_MYSQL"]}" == "true" || 
          "${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}" == "true" ]]; then
        if [ -z "${PRE_UPGRADE_VARS["IP"]:-}" ]; then
            if version_is_less_than "${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}" "0.1.3"; then
                error "Please define IP in ${CONFIG["PRE_UPGRADE_ENV_DIR"]}/env.<Instance ID>"
            else
                error "Please define IP in ${CONFIG["PRE_UPGRADE_ENV_DIR"]}/env.deploy.<Instance ID>"
            fi
        fi
    fi

    success "Pre-upgrade validation fully passed"
    info "======================================="
    info "Version:           ${DEPLOY_VARS["PRE_UPGRADE_VERSION"]} to ${DEPLOY_VARS["VERSION"]}"
    info "DB_TYPE:           ${RUNTIME_VARS["DB_TYPE"]}"
    info "IS_UPGRADE_MYSQL:  ${DEPLOY_VARS["IS_UPGRADE_MYSQL"]}"
    info "IS_UPGRADE_MILVUS: ${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}"
    info "======================================="
}

set_sqlite_vars() {
    if [[ "${RUNTIME_VARS["DB_TYPE"]}" != "sqlite" ]]; then
        return
    fi

    DEPLOY_VARS["UPGRADE_SQLITE_SCRIPT"]="${CONFIG["UPGRADE_DIR"]}/upgrade-sqlite-${DEPLOY_VARS["NAME_SUFFIX"]}.sh"
}

# Set upgrade-related variables of MySQL
set_mysql_vars() {
    if [[ "${DEPLOY_VARS["IS_UPGRADE_MYSQL"]}" == "false" ]]; then
        return
    fi

    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_DB_HOST" "${PRE_UPGRADE_VARS["IP"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_DB_PORT" "${PRE_UPGRADE_VARS["MYSQL_HOST_PORT"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_DB_PWD" "${PRE_UPGRADE_VARS["DB_ROOT_PASSWORD"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_AGENT_DB_NAME" "${PRE_UPGRADE_VARS["AGENT_DB_NAME"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_OPS_DB_NAME" "${PRE_UPGRADE_VARS["OPS_DB_NAME"]}"
    if ! version_is_less_than "${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}" "0.1.4"; then
        set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_DEEPSEARCH_DB_NAME" "${PRE_UPGRADE_VARS["DEEPSEARCH_DB_NAME"]}"
    fi

    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_DB_HOST" "${RUNTIME_VARS["DB_HOST"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_DB_PORT" "${RUNTIME_VARS["DB_PORT"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_DB_PWD" "${DEPLOY_VARS["DB_ROOT_PASSWORD"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_AGENT_DB_NAME" "${RUNTIME_VARS["AGENT_DB_NAME"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_OPS_DB_NAME" "${RUNTIME_VARS["OPS_DB_NAME"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_DEEPSEARCH_DB_NAME" "${DEPLOY_VARS["DEEPSEARCH_DB_NAME"]}"

    DEPLOY_VARS["UPGRADE_MYSQL_SCRIPT"]="${CONFIG["UPGRADE_DIR"]}/upgrade-mysql-${DEPLOY_VARS["NAME_SUFFIX"]}.sh"
}

# Set upgrade-related variables of Milvus
set_milvus_vars() {
    if [[ "${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}" == "false" ]]; then
        return
    fi

    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_HOST" "${PRE_UPGRADE_VARS["IP"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_PORT" "${PRE_UPGRADE_VARS["MILVUS_HOST_PORT"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_TOKEN" "${PRE_UPGRADE_VARS["MILVUS_TOKEN"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MILVUS_HOST" "${RUNTIME_VARS["MILVUS_HOST"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MILVUS_PORT" "${RUNTIME_VARS["MILVUS_PORT"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MILVUS_TOKEN" "${RUNTIME_VARS["MILVUS_TOKEN"]}"

    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_HOST" "${PRE_UPGRADE_VARS["IP"]}"
    set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_PORT" "${PRE_UPGRADE_VARS["MINIO_SERVICE_HOST_PORT"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MINIO_HOST" "${RUNTIME_VARS["MINIO_HOST"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MINIO_PORT" "${RUNTIME_VARS["MINIO_PORT"]}"

    case "${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}" in
        0.1.1|0.1.2)
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_ACCESS_KEY" "minioadmin"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_SECRET_KEY" "minioadmin"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_HTTP_HOST_PORT" "9091"
            ;;
        0.1.3)
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_ACCESS_KEY" "${PRE_UPGRADE_VARS["MINIO_ACCESS_KEY"]}"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_SECRET_KEY" "${PRE_UPGRADE_VARS["MINIO_SECRET_KEY"]}"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_HTTP_HOST_PORT" "9091"
            ;;
        *)
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_ACCESS_KEY" "${PRE_UPGRADE_VARS["MINIO_ACCESS_KEY"]}"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MINIO_SECRET_KEY" "${PRE_UPGRADE_VARS["MINIO_SECRET_KEY"]}"
            set_if_empty "DEPLOY_VARS" "PRE_UPGRADE_MILVUS_HTTP_HOST_PORT" "${PRE_UPGRADE_VARS["MILVUS_HTTP_HOST_PORT"]}"
            ;;
    esac

    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MINIO_ACCESS_KEY" "${RUNTIME_VARS["MINIO_ACCESS_KEY"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MINIO_SECRET_KEY" "${RUNTIME_VARS["MINIO_SECRET_KEY"]}"
    set_if_empty "DEPLOY_VARS" "POST_UPGRADE_MILVUS_HTTP_HOST_PORT" "${DEPLOY_VARS["MILVUS_HTTP_HOST_PORT"]}"

    DEPLOY_VARS["UPGRADE_MILVUS_SCRIPT"]="${CONFIG["UPGRADE_DIR"]}/upgrade-milvus-${DEPLOY_VARS["NAME_SUFFIX"]}.sh"
}

# Generate Milvus backup/restore config file for pre/post upgrade phase
gen_milvus_backup_conf() {
    local upgrade_phase=$1
    local conf_dir=${CONFIG["CONFIG_DIR"]}
    local template_file=${CONFIG["MILVUS_BACKUP_TEMPLATE"]}
    local file="${conf_dir}/milvus-backup-$(format_dir_str "${upgrade_phase}").yml"
    local -A milvus_vars=(
        ["UPGRADE_PHASE"]="${upgrade_phase}"
        ["MILVUS_HOST"]=${DEPLOY_VARS["${upgrade_phase}_MILVUS_HOST"]}
        ["MILVUS_PORT"]=${DEPLOY_VARS["${upgrade_phase}_MILVUS_PORT"]}
        ["MILVUS_TOKEN"]=${DEPLOY_VARS["${upgrade_phase}_MILVUS_TOKEN"]}
        ["MINIO_HOST"]=${DEPLOY_VARS["${upgrade_phase}_MINIO_HOST"]}
        ["MINIO_PORT"]=${DEPLOY_VARS["${upgrade_phase}_MINIO_PORT"]}
        ["MINIO_ACCESS_KEY"]=${DEPLOY_VARS["${upgrade_phase}_MINIO_ACCESS_KEY"]}
        ["MINIO_SECRET_KEY"]=${DEPLOY_VARS["${upgrade_phase}_MINIO_SECRET_KEY"]}
        ["MILVUS_HTTP_HOST_PORT"]=${DEPLOY_VARS["${upgrade_phase}_MILVUS_HTTP_HOST_PORT"]}
    )

    generate_config_file ${template_file} ${file} "milvus_vars"
}

# Generate download MySQL data commands
gen_mysql_download_cmds() {
    local host=${DEPLOY_VARS["PRE_UPGRADE_DB_HOST"]}
    local port=${DEPLOY_VARS["PRE_UPGRADE_DB_PORT"]}
    local pass=${DEPLOY_VARS["PRE_UPGRADE_DB_PWD"]}
    local cmd_file="${DEPLOY_VARS["UPGRADE_MYSQL_SCRIPT"]}"

    cat >> "${cmd_file}" << EOF
echo =============== [INFO] Starting MySQL data download ============
mydumper -h ${host} -P ${port} -u root -p ${pass} -o /root/mysql_backup -t 4 -c --trx-consistency-only || exit 1
echo =============== [SUCCESS] MySQL data download Done ============
EOF
}

# Generate upload MySQL data commands
gen_mysql_upload_cmds() {
    local host=${DEPLOY_VARS["POST_UPGRADE_DB_HOST"]}
    local port=${DEPLOY_VARS["POST_UPGRADE_DB_PORT"]}
    local pass=${DEPLOY_VARS["POST_UPGRADE_DB_PWD"]}

    local db_keys=("AGENT_DB_NAME" "OPS_DB_NAME")
    if ! version_is_less_than "${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}" "0.1.4"; then
        db_keys+=("DEEPSEARCH_DB_NAME")
    fi

    local cmd_file="${DEPLOY_VARS["UPGRADE_MYSQL_SCRIPT"]}"
    for db_key in "${db_keys[@]}"
    do
        src_db=${DEPLOY_VARS["PRE_UPGRADE_${db_key}"]}
        dest_db=${DEPLOY_VARS["POST_UPGRADE_${db_key}"]}
        cat >> "${cmd_file}" << EOF
echo =============== [INFO] Starting MySQL data of ${dest_db} upload ============
myloader -h ${host} -P ${port} -u root -p ${pass} -B ${dest_db} -s ${src_db}  -d /root/mysql_backup -t 4 -o --overwrite-tables -v 3 --ssl || exit 1
echo =============== [SUCCESS] MySQL data of ${dest_db} upload Done ============
EOF
    done
}

# Generate database schema upgrade commands (alembic stamp + upgrade)
gen_db_upgrade_cmds() {
    local pre_version=${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}
    if [ "${pre_version}" == "${DEPLOY_VARS["VERSION"]}" ]; then
        info "No upgrade needed for database (version: ${pre_version}) - same version detected"
        return
    fi

    local db_type_lower=${RUNTIME_VARS["DB_TYPE"]}
    local db_type_upper=${db_type_lower^^}
    local cmd_file="${DEPLOY_VARS["UPGRADE_${db_type_upper}_SCRIPT"]}"
    cat >> "${cmd_file}" << EOF
cd /root/backend
source .venv/bin/activate
EOF

    for db_lower in agent ops
    do
        local db_upper=${db_lower^^}
        local revision_id=${REVISION_ID["${db_type_upper}_${db_upper}_${pre_version}"]}
        local alembic_tag="alembic_${db_type_lower}_${db_lower}"
        cat >> "${cmd_file}" << EOF
echo =============== [INFO] Starting ${db_type_upper}/${db_lower} data upgrade ============
alembic -n ${alembic_tag} stamp ${revision_id} || exit 1
alembic -n ${alembic_tag} upgrade head || exit 1
echo =============== [SUCCESS] ${db_type_upper}/${db_lower} data upgrade Done ============
EOF
    done
}

# Generate Milvus data migration commands (backup + restore)
gen_milvus_migrate_cmds() {
    local cmd_file="${DEPLOY_VARS["UPGRADE_MILVUS_SCRIPT"]}"

    cat >> "${cmd_file}" << EOF
cd /root
echo =============== [INFO] Starting Milvus data backup ============
milvus-backup create -n \$1 --config milvus-backup-pre-upgrade.yml || exit 1
echo =============== [SUCCESS] Milvus data backup Done ============

echo =============== [INFO] Starting Milvus data restoration ============
milvus-backup restore -n \$1 --config milvus-backup-post-upgrade.yml --drop_exist_collection --drop_exist_index --rebuild_index failed || exit 1
echo =============== [SUCCESS] Milvus data restoration Done ============
EOF
}

# Generate migration commands based on target module
gen_cmds() {
    local module="$1"

    info "Generating upgrade command script for ${module}"
    case "${module}" in
        sqlite)
            gen_db_upgrade_cmds
            ;;
        mysql)
            gen_mysql_download_cmds
            gen_mysql_upload_cmds
            gen_db_upgrade_cmds
            ;;
        milvus)
            gen_milvus_migrate_cmds
            ;;
    esac
    info "Generated upgrade command script for ${module}"
}

# Execute data upgrade for specified module in upgrade container
upgrade_data() {
    local module="$1"
    local docker_exec_prefix=""
    local cmd_file="${DEPLOY_VARS["UPGRADE_${module^^}_SCRIPT"]}"

    exec_cmd "mkdir -p ${CONFIG["UPGRADE_DIR"]}"
    exec_cmd "rm -f ${cmd_file}"
    gen_cmds "${module}"

     # If no command file was generated, no data migration is required for this module
    if [ -f "${cmd_file}" ]; then
        info "[UPGRADING] starting ${module} migration..."
        if [ "${DEPLOY_VARS["OS_TYPE"]}" == "windows" ]; then
            docker_exec_prefix="MSYS_NO_PATHCONV=1"
        fi
        if [ "${module}" == "milvus" ]; then
            docker_exec_cmd_file "${upgrade_container}" "${cmd_file}" "backup_milvus_${DEPLOY_VARS["NAME_SUFFIX"]}"
        else
            docker_exec_cmd_file "${upgrade_container}" "${cmd_file}"
        fi
        success "[UPGRADING] ${module} data migration Done!"
     else
        info "${module} data migration skipped: No migration scripts generated (no data changes required)"
    fi
}

# Handle MySQL upgrade (copy env file + execute migration commands)
uprade_mysql() {
    if [[ "${ARGS["IS_UPGRADE"]}" == "false" 
        || "${DEPLOY_VARS["IS_UPGRADE_MYSQL"]}" == "false" ]]; then
        info "Skip upgrade MySQL: disabled in deployment config"
        return
    fi

    info "[UPGRADING] starting MySQL upgrade process...."
    local upgrade_container=${DEPLOY_VARS["UPGRADE_TOOL_DOCKER"]}
    local env_file="${CONFIG["ENV_DIR"]}/env.runtime.${DEPLOY_VARS["NAME_SUFFIX"]}"
    exec_cmd "docker cp ${env_file} ${upgrade_container}:/root/.env"
    upgrade_data "mysql"

    if version_is_less_than "${DEPLOY_VARS["PRE_UPGRADE_VERSION"]}" "0.1.4" \
        && ! version_is_less_than "${DEPLOY_VARS["VERSION"]}" "0.1.4"; then
        create_db "${DEPLOY_VARS["DEEPSEARCH_DB_NAME"]}"
    fi
    success "[UPGRADING] MySQL upgrade process Done!"
}

# Handle SQLite upgrade (copy db files + execute schema upgrade + restore)
upgrade_sqlite(){
    if [[ "${ARGS["IS_UPGRADE"]}" == "false" ||
          "${RUNTIME_VARS["DB_TYPE"]}" != "sqlite" || 
          "${DEPLOY_VARS["IS_UP_BACKEND"]}" == "false" ]]; then
        info "Skip upgrade SQLITE: disabled in deployment config"
        return
    fi

    info "[UPGRADING] starting SQLITE upgrade process...."
    local src_container=${DEPLOY_VARS["PRE_UPGRADE_BACKEND_DOCKER"]}
    local src_path=${PRE_UPGRADE_VARS["SQLITE_DB_PATH"]}
    local src_path_name=$(basename "${src_path}")
    local dest_container=${DEPLOY_VARS["BACKEND_DOCKER"]}
    local dest_path=${RUNTIME_VARS["SQLITE_DB_PATH"]}
    local upgrade_container=${DEPLOY_VARS["UPGRADE_TOOL_DOCKER"]}
    local suffix=${DEPLOY_VARS["NAME_SUFFIX"]}
    local env_file="${CONFIG["ENV_DIR"]}/env.runtime.${suffix}"
    exec_cmd "docker cp ${env_file} ${upgrade_container}:/root/.env"

    local pre_upgrade_db_dir=".sqlite-dirs/databases.preupgrade.${suffix}"
    local post_upgrade_db_dir=".sqlite-dirs/databases.postupgrade.${suffix}"
    exec_cmd "mkdir -p .sqlite-dirs"
    exec_cmd "rm -rf ${pre_upgrade_db_dir}"
    exec_cmd "docker cp ${src_container}:/app/${src_path} ${pre_upgrade_db_dir}"
    docker_exec_cmd ${upgrade_container} "mkdir -p /root/backend/${dest_path} && rm -rf /root/backend/${dest_path}"
    exec_cmd "docker cp ${pre_upgrade_db_dir} ${upgrade_container}:/root/backend/${dest_path}"

    upgrade_data "sqlite"

    exec_cmd "rm -rf ${post_upgrade_db_dir}"
    exec_cmd "docker cp ${upgrade_container}:/root/backend/${dest_path} ${post_upgrade_db_dir}"
    exec_cmd "docker cp ${post_upgrade_db_dir}/agent.db ${dest_container}:/app/${dest_path}/agent.db"
    exec_cmd "docker cp ${post_upgrade_db_dir}/ops.db ${dest_container}:/app/${dest_path}/ops.db"
    exec_cmd "docker restart ${dest_container}"
    success "[UPGRADING] SQLITE upgrade process Done!"
}

# Handle Milvus upgrade (generate conf + copy conf + execute migration commands)
upgrade_milvus(){
    if [[ "${ARGS["IS_UPGRADE"]}" == "false" ||
          "${DEPLOY_VARS["IS_UPGRADE_MILVUS"]}" == "false" ]]; then
          info "Skip upgrade Milvus: disabled in deployment config"
        return
    fi

    info "[UPGRADING] starting Milvus upgrade process...."
    gen_milvus_backup_conf "PRE_UPGRADE"
    gen_milvus_backup_conf "POST_UPGRADE"

    local conf_dir=${CONFIG["CONFIG_DIR"]}
    local pre_upgrade_milvus_file="${conf_dir}/milvus-backup-pre-upgrade.yml"
    local post_upgrade_milvus_file="${conf_dir}/milvus-backup-post-upgrade.yml"
    local upgrade_container=${DEPLOY_VARS["UPGRADE_TOOL_DOCKER"]}
    exec_cmd "docker cp ${pre_upgrade_milvus_file} ${upgrade_container}:/root"
    exec_cmd "docker cp ${post_upgrade_milvus_file} ${upgrade_container}:/root"

    upgrade_data "milvus"
    success "[UPGRADING] Milvus upgrade process Done!"
}

set_upgrade_vars() {
    set_mysql_vars
    set_milvus_vars
    set_sqlite_vars
}

# Prepare upgrade environment if upgrade enabled
prepare_upgrade_env() {
    if [ "${ARGS["IS_UPGRADE"]}" == "false" ]; then
        info "Upgrade environment preparation skipped"
        return
    fi

    valid_upgrade
    set_upgrade_vars
    success "Upgrade environment preparation Done!"
}