#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ====== Wait for container to reach Healthy status (infinite wait) ==========
wait_for_container_healthy() {
    # Parameter 1: Container name (required)
    # Parameter 2: Check interval (seconds, optional, default 10)
    # Note: Infinite wait (no timeout), user can interrupt with Ctrl+C
    local container_name="$1"
    local check_interval=${2:-10}  # Default check interval 10 seconds

    # Validate parameters
    if [ -z "${container_name}" ]; then
        error "wait_for_container_healthy function missing required parameter: container name"
    fi

    # Log startup message (inform user about infinite wait and interrupt method)
    info "Waiting for container [${container_name}] to reach Healthy status (infinite wait - press Ctrl+C to interrupt)"

    local start_time=$(date +%s)  # Only for calculating elapsed wait time (no timeout)
    local health_status
    local current_time
    local elapsed_time

    # Infinite loop to check health status (user can Ctrl+C to interrupt)
    while true; do
        # Calculate elapsed time (only for log display)
        current_time=$(date +%s)
        elapsed_time=$((current_time - start_time))

        # Get container health status (docker inspect precise value)
        # Status values: healthy / starting / unhealthy / none (no health check configured)
        health_status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "${container_name}" 2>/dev/null)

        # Status evaluation
        case "${health_status}" in
            "healthy")
                echo ""
                success "Container [${container_name}] reached Healthy status! (total wait ${elapsed_time} seconds)"
                return
                ;;
            "starting")
                echo -n "."
                ;;
            "unhealthy")
                echo ""
                error "Container [${container_name}] health check failed (unhealthy)!"
                ;;
            "no_healthcheck")
                echo ""
                error "Container [${container_name}] has no health check configured, cannot wait for Healthy status!"
                ;;
            *)
                info "Container [${container_name}] unknown status (${health_status}), waited ${elapsed_time} seconds..."
                ;;
        esac

        # Not ready, wait and retry
        sleep "${check_interval}"
    done
}

# ====== Wait for the all listed containers to reach Healthy status ==========
check_containers() {
    local container_str="$1"  
    local container

    if [ -z "${container_str}" ]; then
        info "No containers to check (empty string received)"
        return
    fi

    IFS=' ' read -r -a containers <<< "${container_str}"
    for container in "${containers[@]}"; do
        if [ -n "${container}" ]; then
            wait_for_container_healthy "${container}"
        fi
    done
}

# ==== Wait for MySQL container to fully start (can connect + execute SQL)======
wait_for_mysql() {
    # Parameters: 
    #   - MySQL container name (from DEPLOY_VARS["MYSQL_DOCKER"])
    #   - Root password (from DEPLOY_VARS["DB_ROOT_PASSWORD"])
    # Behavior: Infinite loop to check MySQL readiness (user can interrupt with Ctrl+C)
    local mysql_container=${DEPLOY_VARS["MYSQL_DOCKER"]}
    local db_password=${DEPLOY_VARS["DB_ROOT_PASSWORD"]}
    local check_interval=3

    # Log startup message (inform user about infinite wait and interrupt method)
    info "Waiting for MySQL container [${mysql_container}] to start (infinite wait - press Ctrl+C to interrupt)"

    # Infinite loop to check MySQL status
    while true; do
        # Core check: Execute test SQL to verify MySQL is ready (connect + run simple query)
        # Use docker exec to run "SELECT 1" - success means MySQL is fully ready
        if docker exec -i "${mysql_container}" mysql -u root -p"${db_password}" -h 127.0.0.1 -e "SELECT 1" 2>/dev/null; then
            success "MySQL container [${mysql_container}] is fully ready!"
            return
        fi

        # MySQL not ready yet: print progress dot and retry after 1 second
        echo -n "."
        sleep "${check_interval}"
    done
}

# create databases all needed if not existed
create_all_dbs() {
    local db_names=(
        "${RUNTIME_VARS["AGENT_DB_NAME"]}"
        "${RUNTIME_VARS["OPS_DB_NAME"]}"
        "${DEPLOY_VARS["DEEPSEARCH_DB_NAME"]}"
    )

    for db_name in "${db_names[@]}"; do
        create_db "${db_name}"
    done
}

# create database  if not existed
create_db() {
    local mysql_container=${DEPLOY_VARS["MYSQL_DOCKER"]}
    local db_password=${DEPLOY_VARS["DB_ROOT_PASSWORD"]}
    local db_name="$1"

    info "Checking if database ${db_name} is created"
    docker exec -i "${mysql_container}" mysql -u root -p"${db_password}" -h 127.0.0.1 << EOF
CREATE DATABASE IF NOT EXISTS ${db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
    if [ $? -eq 0 ]; then
        success "Database ${db_name} is created"
    else
        error "Database ${db_name} creation failed! Check container logs or network connection"
    fi
}

# Check if container exists and is in running status
check_container_running() {
    local container_name="$1"

    # Check if container exists
    if ! docker ps -a --format "{{.Names}}" | grep -qw "$container_name"; then
        error "Container $container_name does not exist"
    fi

    # Check if container is running
    local status=$(docker inspect --format "{{.State.Status}}" "$container_name" 2>/dev/null)
    if [[ "$status" != "running" ]]; then
        error "Container $container_name is not running. Current status: $status"
    fi
    success "Container $container_name is running"
}

# Check if container exists and is in healthy status
check_container_healthy() {
    local container_name="$1"
    check_container_running ${container_name}

    local health=$(docker inspect --format "{{.State.Health.Status}}" "$container_name" 2>/dev/null)
    if [[ "$health" == "unhealthy" ]]; then
        error "Container $container_name is unhealthy"
    fi

    success "Container $container_name is healthy"
}