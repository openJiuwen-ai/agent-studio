#!/usr/bin/env bash
# Sourced by start.sh. No Java process is launched here.

manager_memory_warning() {
    echo "WARNING: JVM memory: $*" >&2
}

# Update the budget using one kernel limit. Compare in awk before converting to
# MiB so v1 unlimited sentinels cannot overflow shell integer arithmetic.
manager_read_memory_limit() {
    local file=$1 version=$2 raw candidate
    if ! raw=$(cat "$file" 2>/dev/null); then
        manager_memory_warning "cannot read $file; effective limit may be incomplete"
        return 0
    fi
    if [[ "$version" == v2 && "$raw" == max ]]; then
        return 0
    fi
    if [[ ! "$raw" =~ ^[0-9]+$ ]]; then
        manager_memory_warning "invalid limit in $file; effective limit may be incomplete"
        return 0
    fi
    candidate=$(awk -v bytes="$raw" -v budget="$limit_in_mb" \
        'BEGIN {printf "%.0f", (bytes / 1048576 < budget ? int(bytes / 1048576) : budget)}')
    if (( candidate < 1 )); then
        echo "ERROR: JVM memory limit in $file is below 1 MiB" >&2
        return 1
    fi
    if (( candidate < limit_in_mb )); then
        limit_in_mb=$candidate
        memory_source=$file
    fi
}

# root is only a filesystem fixture prefix for tests; production passes no
# argument. Environment variables cannot redirect production cgroup discovery.
manager_detect_memory_budget() {
    local root=${1:-} proc version group_path mount_root mount_point relative node leaf
    local memberships mounts hierarchy matched=false
    proc="$root/proc"
    limit_in_mb=$(awk '/^MemTotal:[[:space:]]+[0-9]+[[:space:]]+kB$/ {printf "%.0f", int($2 / 1024)}' \
        "$proc/meminfo" 2>/dev/null)
    if [[ ! "$limit_in_mb" =~ ^[0-9]+$ ]] || \
        ! awk -v mb="$limit_in_mb" 'BEGIN {exit !(mb >= 1 && mb <= 2147483647)}'; then
        echo "ERROR: Cannot determine physical memory from $proc/meminfo" >&2
        return 1
    fi
    memory_source="$proc/meminfo"
    if [[ ! -r "$proc/self/cgroup" || ! -r "$proc/self/mountinfo" ]]; then
        manager_memory_warning "cgroup metadata unavailable; using physical memory, container limit unknown"
        return 0
    fi
    memberships=$(awk -F: '
        $1 == "0" && $2 == "" {print "v2\t" substr($0, index($0, "::") + 2)}
        ("," $2 ",") ~ /,memory,/ {print "v1\t" substr($0, index($0, ":" $2 ":") + length($2) + 2)}
    ' "$proc/self/cgroup")
    while IFS=$'\t' read -r version group_path; do
        [[ -n "$version" ]] || continue
        # Do not traverse outside a visible mount (e.g. a hidden namespace path).
        case "$group_path/" in
            /*/../*|/*/./*) continue ;;
        esac
        [[ "$group_path" == /* ]] || continue
        mounts=$(awk -v version="$version" '
            {for (i = 7; i <= NF; i++) if ($i == "-") {
                if ((version == "v2" && $(i+1) == "cgroup2") ||
                    (version == "v1" && $(i+1) == "cgroup" &&
                     ("," $(i+3) ",") ~ /,memory,/)) print $4 "\t" $5
                break
            }}' "$proc/self/mountinfo")
        while IFS=$'\t' read -r mount_root mount_point; do
            [[ -n "$mount_point" ]] || continue
            # mountinfo escapes spaces, tabs, newlines and backslashes as octal.
            printf -v mount_root '%b' "$mount_root"
            printf -v mount_point '%b' "$mount_point"
            if [[ "$mount_root" == / ]]; then
                relative=$group_path
            elif [[ "$group_path" == "$mount_root" ]]; then
                relative=/
            elif [[ "$group_path" == "$mount_root/"* ]]; then
                relative=${group_path#"$mount_root"}
            else
                continue
            fi
            mount_point="$root${mount_point%/}"
            node="$mount_point${relative%/}"
            leaf=$node
            [[ -d "$leaf" ]] || continue
            matched=true
            while :; do
                if [[ "$version" == v2 ]]; then
                    # The real hierarchy root has no memory.max. Namespace
                    # roots may have it; always read the file when present.
                    if [[ -e "$node/memory.max" || "$node" != "$mount_point" ]]; then
                        manager_read_memory_limit "$node/memory.max" v2 || return 1
                    elif [[ "$node" == "$leaf" ]]; then
                        manager_memory_warning "memory.max unavailable at $node; container limit unknown"
                    fi
                elif [[ "$node" == "$leaf" ]]; then
                    manager_read_memory_limit "$node/memory.limit_in_bytes" v1 || return 1
                else
                    # Legacy v1 ancestors only constrain descendants when
                    # hierarchical accounting is enabled at that ancestor.
                    hierarchy=$(cat "$node/memory.use_hierarchy" 2>/dev/null)
                    if [[ "$hierarchy" == 1 ]]; then
                        manager_read_memory_limit "$node/memory.limit_in_bytes" v1 || return 1
                    elif [[ "$hierarchy" != 0 ]]; then
                        manager_memory_warning "cannot determine hierarchy at $node; parent limit unknown"
                    fi
                fi
                [[ "$node" == "$mount_point" ]] && break
                node=${node%/*}
            done
        done <<< "$mounts"
    done <<< "$memberships"
    if [[ "$matched" == false ]]; then
        manager_memory_warning "no matching memory cgroup mount; using physical memory, container limit unknown"
    elif [[ "$memory_source" == "$proc/meminfo" ]]; then
        echo "INFO: JVM memory: no smaller finite limit found in visible cgroups; using physical memory"
    fi
}

manager_configure_jvm_memory() {
    local LC_ALL=C
    export LC_ALL
    local heap_ratio=${jvm_xmx_percent:-0.6}
    local direct_ratio=${jvm_direct_memory_ratio:-0.2}
    local direct_cap=${jvm_direct_memory_cap_mb:-1024}
    local heap_size direct_size
    # Validate configuration before arithmetic; use awk variables, never code
    # interpolation. A zero direct-memory limit would mean JVM auto-sizing.
    if [[ ! "$heap_ratio" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ||
          ! "$direct_ratio" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ||
          ! "$direct_cap" =~ ^[0-9]+$ ]] ||
        ! awk -v heap="$heap_ratio" -v direct="$direct_ratio" -v cap="$direct_cap" \
            'BEGIN {exit !(heap > 0 && heap < 1 && direct > 0 && direct < 1 && cap > 0)}'; then
        echo "ERROR: Invalid JVM memory configuration: require ratios between 0 and 1 and a positive integer cap (MiB)" >&2
        return 1
    fi
    manager_detect_memory_budget "${1:-}" || return 1
    heap_size=$(awk -v budget="$limit_in_mb" -v ratio="$heap_ratio" \
        'BEGIN {printf "%.0f", budget * ratio}')
    direct_size=$(awk -v budget="$limit_in_mb" -v ratio="$direct_ratio" -v cap="$direct_cap" \
        'BEGIN {size = budget * ratio; printf "%.0f", (size < cap ? size : cap)}')
    if (( heap_size < 1 || direct_size < 1 || heap_size + direct_size >= limit_in_mb )); then
        echo "ERROR: Invalid JVM memory budget: budget=${limit_in_mb}MiB heap=${heap_size}MiB direct=${direct_size}MiB; leave room for native memory" >&2
        return 1
    fi
    INIT_JAVA_HEAP_SIZE=${heap_size}m
    MAX_JAVA_HEAP_SIZE=${heap_size}m
    MAX_DIRECT_MEMORY_SIZE=${direct_size}m
    echo "INFO: JVM memory source=$memory_source budget=${limit_in_mb}MiB Xms=$INIT_JAVA_HEAP_SIZE Xmx=$MAX_JAVA_HEAP_SIZE direct=$MAX_DIRECT_MEMORY_SIZE"
}
