#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# Extracts a clean version string by removing non-numeric/dot prefixes and suffixes
extract_version() {
    local version="$1"
    
     # Remove all prefixes (non-digit/dot characters like v, V, leading letters)
    version=$(echo "${version}" | sed -E 's/^[^0-9.]+//')

    # Remove all suffixes (content after first non-digit/dot character like -desktop.1, -rc1)
    version=$(echo "${version}" | sed -E 's/[^0-9.].*//')

    echo ${version}
}

# Converts a semantic version string (x.y.z) to a numeric integer for easy comparison
get_version_number() {
    local version="$1"

    local major=$(echo "${version}" | cut -d. -f1)
    local middle=$(echo "${version}" | cut -d. -f2)
    local minor=$(echo "${version}" | cut -d. -f3)
    echo $((10000 * major + 100 * middle + minor))
}

# Checks if the first version is less than the second version
version_is_less_than() {
    local version=$(extract_version "$1")
    local min_version=$(extract_version "$2")

    local version_num=$(get_version_number "${version}")
    local min_version_num=$(get_version_number "${min_version}")

    info "Version: ${version} → ${version_num}, ${min_version} → ${min_version_num}"
    if [[ "${version_num}" -lt "${min_version_num}" ]]; then
        return 0
    fi
    return 1
}

# Check docker version and availability
check_docker() {
    local version=$(docker version --format '{{.Server.Version}}')
    local min_version="20.10"

    info "Checking Docker..."
    command -v docker >/dev/null 2>&1 || {
        error "Docker is not installed. Please install Docker ${min_version} or higher first."
    }
    
    docker info >/dev/null 2>&1 || {
        error "Docker daemon is not running. Please start it first."
    }

    if version_is_less_than "${version}" "${min_version}"; then
         error "Unsupported Docker version: ${version}. Required minimum version is ${min_version}."
    fi
    success "Docker: ${version} (≥ ${min_version})"
}

# Check docker compose version and availability
check_docker_compose() {
    local min_version="v2.19.1"
    info "Checking Docker Compose installation..."
    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose not installed. Please install Docker Compose ${min_version} or higher first.."
    fi

    local version=$(docker compose version)
    version=$(echo "${version}" | sed -E 's/^[^0-9.]+//')

    if version_is_less_than "${version}" "${min_version}"; then
         error "Unsupported Docker Compose version: ${version}. Required minimum version is ${min_version}."
    fi
    success "Docker Compose: ${version} (≥ ${min_version})"
}

# Checks a software dependency for installation status and minimum version requirement
check_software_dependency() {
    check_docker
    check_docker_compose
    check_cmds
}

check_cmds() {
    for cmd in sed awk grep sort head wc tr cut od chmod mkdir cp rm mv cat echo printf seq netstat openssl
    do
        check_cmd ${cmd}
    done

    local os_type=${DEPLOY_VARS["OS_TYPE"]}
    if [ "${os_type}" == "macos" ]; then
        for cmd in jot lsof
        do
            check_cmd ${cmd}
        done
    fi
}

check_cmd() {
    if command -v "$1" >/dev/null 2>&1; then
        success "$1 is OK."
    else
        error "$1 is not installed. Please install it first."
    fi
}
