#!/usr/bin/env bash
set -euo >/dev/null 2>&1

# ================= Count undefined ports ================
count_undefined_ports() {
    local undefined_count=0

    # Traverse port list, count undefined (empty/no key) ports
    for port_name in "${PORTS[@]}"; do
        if [ -z "${DEPLOY_VARS[${port_name}]:-}" ]; then
            undefined_count=$((undefined_count + 1))
            # info "[${port_name}] undefined, requires available port allocation"
        else
            local port=${DEPLOY_VARS[${port_name}]}
            ALLOCATED_PORTS+=("${port}")
            # info "[${port_name}] defined, value: ${port}"

            if is_port_occupied "${port}"; then
                error "[${port_name}]:${port} is occupied. Please specify an unoccupied port instead."
            fi
        fi
    done

    # Update configuration: number of ports to allocate = undefined port count
    CONFIG["ALLOC_PORT_NUM"]=${undefined_count}
    info "====================================="
    info "Total undefined ports: ${undefined_count} → Need to allocate ${undefined_count} available ports"
    info "====================================="
}

# ======== Check if a single port is occupied ===============
is_port_occupied() {
    local port="$1"
    local port_occupied=0
    local os_type=${DEPLOY_VARS["OS_TYPE"]}

    case "${os_type}" in
        macos)
            # macOS: use lsof which is more reliable
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                port_occupied=1
            fi
            ;;
        linux)
            # Linux: prefer ss command (more efficient)
            netstat_output=$(netstat -tuln 2>&1)
            if echo "${netstat_output}" | grep -q ":$port"; then
                port_occupied=1
            fi
            ;;
        windows)
            # Windows Git Bash/Cygwin: Match LISTENING state in netstat -an output
            if netstat -an | grep -qiE ":$port[^0-9].*LISTENING.*" 2>/dev/null; then
                port_occupied=1
            fi
            ;;
    esac

    # Return result: 0 = occupied, 1 = available
    if [ "$port_occupied" -eq 1 ]; then
        return 0
    else
        return 1
    fi
}

# =========== Allocate multiple available ports at once ==============
find_available_ports() {
    local start_port=${CONFIG["START_PORT"]}
    local end_port=${CONFIG["END_PORT"]}
    local need_port_num=${CONFIG["ALLOC_PORT_NUM"]}
    local allocated_ports=("${ALLOCATED_PORTS[@]:-}")

    if [ "$need_port_num" -eq 0 ]; then
        return
    fi
    
    info "Current allocated port list: ${allocated_ports[*]:-empty}"
    info "Scanning port range: $start_port ~ $end_port, need to allocate $need_port_num available ports"

    # Traverse ports, collect enough available ports
    for port in $(seq "$start_port" "$end_port"); do
        # Skip already allocated ports
        local is_allocated=0
        for allocated_port in "${allocated_ports[@]}"; do
            if [ -n "$allocated_port" ]; then
                if [ "$port" -eq "$allocated_port" ]; then
                    is_allocated=1
                    break
                fi
            fi 
        done

        if [ "$is_allocated" -eq 1 ]; then
            info "Port $port already allocated, skipping"
            continue
        fi

        # Check port occupancy via the reusable function
        if is_port_occupied "$port"; then
            # Return 0 means port is occupied → skip
            continue
        else
            # Return 1 means port is available → add to list
            AVAILABLE_PORTS+=("$port")
            # info "Found available port: $port (collected ${#AVAILABLE_PORTS[@]}/$need_port_num)"

            # Stop traversal when enough ports are collected
            if [ "${#AVAILABLE_PORTS[@]}" -ge "$need_port_num" ]; then
                break
            fi
        fi
    done

    # 4. Verify enough ports were collected
    if [ "${#AVAILABLE_PORTS[@]}" -lt "$need_port_num" ]; then
        error "Only found ${#AVAILABLE_PORTS[@]} available ports, insufficient for $need_port_num (port range: $start_port-$end_port)"
    fi

    # 5. Update global allocated port list (mark as allocated to avoid reuse)
    allocated_ports+=("${AVAILABLE_PORTS[@]}")
    info "Successfully collected $need_port_num available ports: ${AVAILABLE_PORTS[*]}"
}

# ===================== Dynamically assign ports to containers =====================
assign_ports() {
    local port_index=0  # Available port index (starting from 0)

    info "====================================="
    info "Starting to assign values to undefined ports..."
    info "====================================="

    # Traverse all port names, assign dynamically
    for port_name in "${PORTS[@]}"; do
        if [ -n "${DEPLOY_VARS[${port_name}]:-}" ]; then
            # Already defined: keep original value
            success "[${port_name}] already defined, keeping original value: ${DEPLOY_VARS[${port_name}]}"
        else
            # Undefined: take value from available port list by index
            if [ ${port_index} -lt ${#AVAILABLE_PORTS[@]} ]; then
                DEPLOY_VARS["${port_name}"]=${AVAILABLE_PORTS[${port_index}]}
                success "[${port_name}] undefined, assigning available port: ${DEPLOY_VARS[${port_name}]}"
                port_index=$((port_index + 1))  # Increment index for next undefined port
            else
                # Extreme case: insufficient available ports (shouldn't happen as find_available_ports already validates)
                error "[${port_name}] no available ports to assign (available ports: ${#AVAILABLE_PORTS[@]})"
            fi
        fi
    done

    info "============== All port assignments complete! =============="
}


process_ports() {
    count_undefined_ports
    find_available_ports
    assign_ports
}