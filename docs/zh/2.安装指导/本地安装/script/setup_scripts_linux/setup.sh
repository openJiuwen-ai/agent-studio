#!/bin/bash
# Note: do not use set -e, for better control of error handling and retry
set -uo pipefail  # undefined var check and pipefail, but do not auto-exit

# ===================== Basic config =====================
# Resolve setup.sh to an absolute path first: if BASH_SOURCE[0] is relative (e.g. ./setup.sh),
# later "cd" into agent-runtime would make $(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd) resolve to CWD.
_SETUP_SRC="${BASH_SOURCE[0]}"
if [[ "$_SETUP_SRC" != /* ]]; then
    _SETUP_SRC="$(pwd)/$_SETUP_SRC"
fi
WORK_HOME="$(cd "$(dirname "$_SETUP_SRC")" && pwd)"
unset _SETUP_SRC
BACKEND_DIR="${WORK_HOME}/agent-studio/backend"
FRONTEND_DIR="${WORK_HOME}/agent-studio/frontend"
RUNTIME_DIR="${WORK_HOME}/agent-runtime"
TARGET_ENV_FILE="${WORK_HOME}/agent-studio/.env"
ENV_EXAMPLE_FILE="${WORK_HOME}/agent-studio/.env.example"
LOG_FILE="${WORK_HOME}/setup.log"
PROGRESS_FILE="${WORK_HOME}/.setup_progress"

INSTALL_STEPS=(
    "check_tools"
    "fetch_code"
    "config_aes"
    "config_env"
    "fetch_runtime_code"
    "config_runtime_env"
    "config_mysql"
    "install_backend_dep"
    "install_frontend_dep"
    "start_services"
)

# Load utils: OS helpers, proxy, colors, and setup orchestration helpers (log, progress, retry, etc.)
if [ ! -f "${WORK_HOME}/utils.sh" ]; then
    echo "ERROR: utils.sh not found: ${WORK_HOME}/utils.sh" >&2
    exit 1
fi
# shellcheck source=utils.sh
. "${WORK_HOME}/utils.sh"
apply_http_proxy

if [ ! -f "${WORK_HOME}/manage_service.sh" ]; then
    echo "ERROR: manage_service.sh not found: ${WORK_HOME}/manage_service.sh" >&2
    exit 1
fi
# shellcheck source=manage_service.sh
. "${WORK_HOME}/manage_service.sh"

# ===================== Help =====================
show_help() {
    cat << EOF
Usage: ${0} [options]
One-shot deploy Agent-Studio with configurable DB type and code branch.

Options:
  --db_type=<type>    Database type: mysql (default), sqlite
  --branch=<name>     Git branch for agent-studio and agent-runtime, default: main
  --app_db_user=<user>     MySQL application user (default: openjiuwen)
  --app_db_password=<pwd>  MySQL application user password (default: openjiuwen)
  --frontend_port=<port>  Frontend port (default: 3000), written to .env FRONTEND_PORT
  --backend_port=<port>   Backend port (default: 8000), written to .env BACKEND_PORT
  --stop              Gracefully stop runtime, backend, and frontend services
  --start             Start runtime, backend, and frontend (no reinstall of deps/keys)
  --restart           Restart runtime, backend, and frontend
  --status            Show service status and access URLs
  --help              Show this help and exit

Examples:
  ${0}                           # Default: DB_TYPE=mysql, branch=main, ports 3000/8000
  ${0} --db_type=sqlite           # Use sqlite, main branch
  ${0} --branch=develop          # Use mysql, develop branch
  ${0} --app_db_user=myuser --app_db_password='secret'  # Custom MySQL app account
  ${0} --frontend_port=3001 --backend_port=8001
  ${0} --stop                     # Stop services
  ${0} --start                    # Start services
  ${0} --restart                  # Restart services
  ${0} --status                   # Show status
  ${0} --help                     # Show help

Work directory: ${WORK_HOME}
EOF
    exit 0
}

# ===================== Parse args =====================
DB_TYPE="mysql"
GIT_BRANCH="main"
APP_DB_USER="openjiuwen"
APP_DB_PASSWORD="openjiuwen"
FRONTEND_PORT="3000"
BACKEND_PORT="8000"
ACTION="install"

for arg in "$@"; do
    case "$arg" in
        --help)
            show_help
            ;;
        --stop)
            ACTION="stop"
            ;;
        --start)
            ACTION="start"
            ;;
        --restart)
            ACTION="restart"
            ;;
        --status)
            ACTION="status"
            ;;
        --db_type=*)
            DB_TYPE="${arg#*=}"
            if [[ $DB_TYPE != "mysql" && $DB_TYPE != "sqlite" ]]; then
                error_exit "Option --db_type must be mysql or sqlite, got: $DB_TYPE"
            fi
            log "INFO" "Database type: $DB_TYPE"
            ;;
        --branch=*)
            GIT_BRANCH="${arg#*=}"
            if [ -z "$GIT_BRANCH" ]; then
                error_exit "Option --branch: branch name cannot be empty"
            fi
            log "INFO" "Git branch: $GIT_BRANCH"
            ;;
        --app_db_user=*)
            APP_DB_USER="${arg#*=}"
            if [ -z "$APP_DB_USER" ]; then
                error_exit "Option --app_db_user: user name cannot be empty"
            fi
            log "INFO" "MySQL app user: $APP_DB_USER"
            ;;
        --app_db_password=*)
            APP_DB_PASSWORD="${arg#*=}"
            ;;
        --frontend_port=*)
            FRONTEND_PORT="${arg#*=}"
            check_port "frontend_port" "$FRONTEND_PORT"
            log "INFO" "Frontend port: $FRONTEND_PORT"
            ;;
        --backend_port=*)
            BACKEND_PORT="${arg#*=}"
            check_port "backend_port" "$BACKEND_PORT"
            log "INFO" "Backend port: $BACKEND_PORT"
            ;;
        *)
            error_exit "Invalid option '$arg', use --help for usage"
            ;;
    esac
done

# Handle stop/start/restart/status
if [ "$ACTION" = "stop" ]; then
    stop_services
    exit 0
fi

if [ "$ACTION" = "status" ]; then
    check_status
    exit 0
fi

if [ "$ACTION" = "start" ]; then
    start_services
    exit 0
fi

if [ "$ACTION" = "restart" ]; then
    restart_services
    exit 0
fi

# ===================== Pre-checks =====================
log "INFO" "===== Starting Agent-Studio deployment ====="
log "INFO" "Work directory: ${WORK_HOME}"
log "INFO" "Log file: ${LOG_FILE}"

# Init log file
echo "=========================================" >> "$LOG_FILE"
echo "Deployment started: $(date)" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"

load_environments
log "INFO" "Environment loaded (NVM, Conda, user PATH)"

check_command "bash"
check_command "sed"
check_command "grep"
check_command "mkdir"

log "INFO" "Checking script permissions..."
for script in "check_curl.sh" "check_git.sh" "check_nodejs.sh" "check_python.sh" "check_mysql.sh"; do
    if [ -f "${WORK_HOME}/${script}" ]; then
        check_script_permission "${WORK_HOME}/${script}"
    fi
done

LAST_PROGRESS=$(read_progress)
if [ -n "$LAST_PROGRESS" ]; then
    log "WARN" "Previous deployment progress found: $LAST_PROGRESS"
    read -p "Resume from last step? (y/n, default y): " CONTINUE
    if [[ "${CONTINUE:-y}" != "y" ]]; then
        clear_progress
        LAST_PROGRESS=""
        log "INFO" "Progress cleared, starting from beginning"
    fi
else
    LAST_PROGRESS=""
fi

# ===================== Install base tools =====================
STEP="check_tools"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: base tools check (already done)"
else
    log "INFO" "===== Installing base tools ====="
    SCRIPTS=("check_curl.sh" "check_git.sh" "check_nodejs.sh" "check_python.sh")
    
    if [ "$DB_TYPE" = "mysql" ]; then
        SCRIPTS+=("check_mysql.sh")
        log "INFO" "DB type is MySQL, will run MySQL check script"
    fi
    
    for script in "${SCRIPTS[@]}"; do
        SCRIPT_PATH="${WORK_HOME}/${script}"
        check_file "$SCRIPT_PATH"
        log "INFO" "Running script: $SCRIPT_PATH"
        echo -e "${GREEN}[Progress] Running: ${script}${NC}"
        
        if [ "$script" = "check_mysql.sh" ]; then
            # Source check_mysql.sh so MYSQL_PWD entered by user stays in current shell env
            if ! retry_execute 3 5 "Run $script" "source '$SCRIPT_PATH'"; then
                error_exit "Running $script failed" \
                    "1. Check script permission: chmod +x $SCRIPT_PATH\n\
2. Inspect script content\n\
3. Run manually: source $SCRIPT_PATH"
            fi
        elif ! retry_execute 3 5 "Run $script" "bash '$SCRIPT_PATH'"; then
            error_exit "Running $script failed" \
                "1. Check script permission: chmod +x $SCRIPT_PATH\n\
2. Inspect script content\n\
3. Run manually: bash $SCRIPT_PATH"
        fi
        echo -e "${GREEN}[Progress] ${script} done${NC}\n"
    done
    save_progress "$STEP"
fi

# ===================== Fetch code =====================
STEP="fetch_code"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: code fetch (already done)"
    if [ ! -d "${WORK_HOME}/agent-studio" ]; then
        log "WARN" "Code directory missing, re-fetching..."
        LAST_PROGRESS=""
    fi
else
    log "INFO" "===== Fetching code ====="
    echo -e "${GREEN}[Progress] Base tools done, fetching code (branch: ${GIT_BRANCH})...${NC}"

    STUDIO_REPO_URL="https://gitcode.com/openJiuwen/agent-studio.git"
    AGENT_STUDIO_DIR="${WORK_HOME}/agent-studio"
    log "INFO" "Agent-studio repository: ${STUDIO_REPO_URL}"
    log "INFO" "Branch: ${GIT_BRANCH} (same as --branch for agent-runtime)"

    if [ -d "$AGENT_STUDIO_DIR" ]; then
        log "INFO" "Agent-studio directory already exists, updating code..."
        if ! cd "$AGENT_STUDIO_DIR"; then
            error_exit "Cannot cd to agent-studio directory: $AGENT_STUDIO_DIR" \
                "Check directory permissions and path."
        fi
        if ! git fetch origin --prune || ! git pull origin "$GIT_BRANCH"; then
            error_exit "Failed to update agent-studio code" \
                "Try manually: cd $AGENT_STUDIO_DIR && git fetch origin --prune && git pull origin $GIT_BRANCH"
        fi
    else
        log "INFO" "Cloning agent-studio repository..."
        if ! cd "$WORK_HOME"; then
            error_exit "Cannot cd to work home: $WORK_HOME" \
                "Check script execution directory."
        fi
        if ! git clone -b "$GIT_BRANCH" "$STUDIO_REPO_URL" "agent-studio"; then
            error_exit "Failed to clone agent-studio repository" \
                "Check network and git access: $STUDIO_REPO_URL"
        fi
    fi
    cd "$WORK_HOME" || error_exit "Cannot cd to WORK_HOME: $WORK_HOME" \
        "Check permissions on $WORK_HOME"

    check_dir "${WORK_HOME}/agent-studio"
    check_dir "$BACKEND_DIR"
    check_dir "$FRONTEND_DIR"
    echo -e "${GREEN}[Progress] Code fetch done${NC}\n"
    save_progress "$STEP"
fi

# ===================== Configure AES key =====================
STEP="config_aes"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: AES key config (already done)"
    if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ] && [ -f "$TARGET_ENV_FILE" ]; then
        log "WARN" "AES key not set, will read from .env if present"
    fi
else
log "INFO" "===== Configuring AES key ====="
    echo -e "${GREEN}[Progress] Configuring AES key...${NC}"
AES_SCRIPT="${WORK_HOME}/agent-studio/scripts/build_AES_master_key.sh"
check_file "$AES_SCRIPT"
log "INFO" "Running AES key script: $AES_SCRIPT"
    
    your_aes_key=""
    ATTEMPT=1
    MAX_RETRIES=3
    
    while [ $ATTEMPT -le $MAX_RETRIES ]; do
        log "INFO" "[Attempt $ATTEMPT/$MAX_RETRIES] Generating AES key"
        your_aes_key=$(bash "$AES_SCRIPT" 2>/dev/null || echo "")
        
        if [ -n "$your_aes_key" ] && [ ${#your_aes_key} -gt 10 ]; then
            log "SUCCESS" "AES key generated"
            break
        else
            log "WARN" "AES key generation failed or invalid, retrying in 2s..."
            if [ $ATTEMPT -lt $MAX_RETRIES ]; then
                sleep 2
            fi
            ATTEMPT=$((ATTEMPT + 1))
        fi
    done
    
    if [ -z "$your_aes_key" ] || [ ${#your_aes_key} -le 10 ]; then
        error_exit "AES key generation failed after $MAX_RETRIES attempts" \
            "1. Check script permission: chmod +x $AES_SCRIPT\n\
2. Check Python: python3.11 --version\n\
3. Run manually: bash $AES_SCRIPT\n\
4. Inspect script: cat $AES_SCRIPT"
    fi
    
export SERVER_AES_MASTER_KEY_ENV="$your_aes_key"
    log "SUCCESS" "AES key set: ${your_aes_key:0:8}**** (partially hidden)"
    save_progress "$STEP"
fi

# ===================== Configure .env =====================
STEP="config_env"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: .env config (already done)"
else
log "INFO" "===== Configuring .env ====="
    echo -e "${GREEN}[Progress] AES done, configuring .env...${NC}"
check_file "$ENV_EXAMPLE_FILE"
if [ -f "$TARGET_ENV_FILE" ]; then
    BACKUP_ENV="${TARGET_ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$TARGET_ENV_FILE" "$BACKUP_ENV" || log "WARN" "Backup .env failed, continuing"
    log "INFO" "Backed up .env to: $BACKUP_ENV"
fi
    
    if ! cp "$ENV_EXAMPLE_FILE" "$TARGET_ENV_FILE" 2>/dev/null; then
        error_exit "Failed to copy .env.example" \
            "1. Check file permission: ls -l $ENV_EXAMPLE_FILE\n\
2. Check target dir: ls -ld $(dirname $TARGET_ENV_FILE)\n\
3. Copy manually: cp $ENV_EXAMPLE_FILE $TARGET_ENV_FILE"
    fi
check_file "$TARGET_ENV_FILE"

OLD_MYSQL="DB_TYPE=mysql"
NEW_SQLITE="DB_TYPE=sqlite"
log "INFO" "Setting DB type: $DB_TYPE"
if [ "$DB_TYPE" = "sqlite" ]; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|${OLD_MYSQL}|${NEW_SQLITE}|g" "$TARGET_ENV_FILE"
    else
        sed -i "s|${OLD_MYSQL}|${NEW_SQLITE}|g" "$TARGET_ENV_FILE"
    fi
elif [ "$DB_TYPE" = "mysql" ]; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|${NEW_SQLITE}|${OLD_MYSQL}|g" "$TARGET_ENV_FILE"
    else
        sed -i "s|${NEW_SQLITE}|${OLD_MYSQL}|g" "$TARGET_ENV_FILE"
    fi
fi

log "INFO" "Setting FRONTEND_PORT=$FRONTEND_PORT, BACKEND_PORT=$BACKEND_PORT"
if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' "s|^FRONTEND_PORT=[0-9]*|FRONTEND_PORT=$FRONTEND_PORT|" "$TARGET_ENV_FILE"
    sed -i '' "s|^BACKEND_PORT=[0-9]*|BACKEND_PORT=$BACKEND_PORT|" "$TARGET_ENV_FILE"
    sed -i '' "s|VITE_API_PROXY_TARGET=http://localhost:[0-9]*/|VITE_API_PROXY_TARGET=http://localhost:${BACKEND_PORT}/|" "$TARGET_ENV_FILE"
    sed -i '' "s|ALLOWED_ORIGINS=\[\"http://localhost:[0-9]*\",\"http://127.0.0.1:[0-9]*\"\]|ALLOWED_ORIGINS=[\"http://localhost:${FRONTEND_PORT}\",\"http://127.0.0.1:${FRONTEND_PORT}\"]|" "$TARGET_ENV_FILE"
else
    sed -i "s|^FRONTEND_PORT=[0-9]*|FRONTEND_PORT=$FRONTEND_PORT|" "$TARGET_ENV_FILE"
    sed -i "s|^BACKEND_PORT=[0-9]*|BACKEND_PORT=$BACKEND_PORT|" "$TARGET_ENV_FILE"
    sed -i "s|VITE_API_PROXY_TARGET=http://localhost:[0-9]*/|VITE_API_PROXY_TARGET=http://localhost:${BACKEND_PORT}/|" "$TARGET_ENV_FILE"
    sed -i "s|ALLOWED_ORIGINS=\[\"http://localhost:[0-9]*\",\"http://127.0.0.1:[0-9]*\"\]|ALLOWED_ORIGINS=[\"http://localhost:${FRONTEND_PORT}\",\"http://127.0.0.1:${FRONTEND_PORT}\"]|" "$TARGET_ENV_FILE"
fi

load_db_host_port_from_user_config
log "INFO" "Setting DB_USER / DB_PASSWORD from --app_db_user / --app_db_password"
if grep -q "^DB_USER=" "$TARGET_ENV_FILE"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|^DB_USER=.*|DB_USER=${APP_DB_USER}|" "$TARGET_ENV_FILE"
    else
        sed -i "s|^DB_USER=.*|DB_USER=${APP_DB_USER}|" "$TARGET_ENV_FILE"
    fi
else
    echo "DB_USER=${APP_DB_USER}" >> "$TARGET_ENV_FILE"
fi
ESCAPED_APP_DB_PASSWORD=$(printf '%s\n' "$APP_DB_PASSWORD" | sed 's/[[\.*^$()+?{|]/\\&/g')
if grep -q "^DB_PASSWORD=" "$TARGET_ENV_FILE"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|^DB_PASSWORD=.*|DB_PASSWORD=${ESCAPED_APP_DB_PASSWORD}|" "$TARGET_ENV_FILE"
    else
        sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${ESCAPED_APP_DB_PASSWORD}|" "$TARGET_ENV_FILE"
    fi
else
    echo "DB_PASSWORD=${APP_DB_PASSWORD}" >> "$TARGET_ENV_FILE"
fi
log "INFO" "Setting DB_HOST / DB_PORT from user_config.sh"
if grep -q "^DB_HOST=" "$TARGET_ENV_FILE"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|^DB_HOST=.*|DB_HOST=${DB_HOST}|" "$TARGET_ENV_FILE"
    else
        sed -i "s|^DB_HOST=.*|DB_HOST=${DB_HOST}|" "$TARGET_ENV_FILE"
    fi
else
    echo "DB_HOST=${DB_HOST}" >> "$TARGET_ENV_FILE"
fi
if grep -q "^DB_PORT=" "$TARGET_ENV_FILE"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|^DB_PORT=.*|DB_PORT=${DB_PORT}|" "$TARGET_ENV_FILE"
    else
        sed -i "s|^DB_PORT=.*|DB_PORT=${DB_PORT}|" "$TARGET_ENV_FILE"
    fi
else
    echo "DB_PORT=${DB_PORT}" >> "$TARGET_ENV_FILE"
fi
log "SUCCESS" ".env updated: DB_USER=${APP_DB_USER} (DB_PASSWORD set), DB_HOST=${DB_HOST}, DB_PORT=${DB_PORT}"

DB_TYPE_ACTUAL=$(grep '^DB_TYPE=' "$TARGET_ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "not found")
if [ "$DB_TYPE_ACTUAL" != "$DB_TYPE" ]; then
    log "WARN" "DB_TYPE may not have applied, current: $DB_TYPE_ACTUAL (expected: $DB_TYPE)"
else
    log "SUCCESS" "DB_TYPE set: $DB_TYPE"
fi
FRONTEND_PORT_ACTUAL=$(grep '^FRONTEND_PORT=' "$TARGET_ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "not found")
BACKEND_PORT_ACTUAL=$(grep '^BACKEND_PORT=' "$TARGET_ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "not found")
log "INFO" "FRONTEND_PORT: $FRONTEND_PORT_ACTUAL, BACKEND_PORT: $BACKEND_PORT_ACTUAL"
    save_progress "$STEP"
fi

# ===================== Persist AES key into .env =====================
# The AES key generated in the config_aes step is exported to the current
# shell only. If it is not written back to .env, manage_service.sh will
# generate a *new* random key on every restart, making previously encrypted
# API keys undecryptable (issue #1236). Persist it here so restarts reuse
# the same key.
if [ -n "${SERVER_AES_MASTER_KEY_ENV:-}" ] && [ -f "$TARGET_ENV_FILE" ]; then
    if grep -q '^SERVER_AES_MASTER_KEY=' "$TARGET_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^SERVER_AES_MASTER_KEY=.*|SERVER_AES_MASTER_KEY=${SERVER_AES_MASTER_KEY_ENV}|" "$TARGET_ENV_FILE"
        else
            sed -i "s|^SERVER_AES_MASTER_KEY=.*|SERVER_AES_MASTER_KEY=${SERVER_AES_MASTER_KEY_ENV}|" "$TARGET_ENV_FILE"
        fi
    else
        printf '\nSERVER_AES_MASTER_KEY=%s\n' "${SERVER_AES_MASTER_KEY_ENV}" >> "$TARGET_ENV_FILE"
    fi
    log "SUCCESS" "AES key persisted to .env (SERVER_AES_MASTER_KEY)"
fi

# ===================== Download Runtime Code =====================
STEP="fetch_runtime_code"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: runtime code download/update (already done)"
else
    log "INFO" "===== Downloading Runtime Code ====="
    RUNTIME_REPO_URL="https://gitcode.com/openJiuwen/agent-runtime.git"
    log "INFO" "Runtime repository: ${RUNTIME_REPO_URL}"
    log "INFO" "Runtime branch: ${GIT_BRANCH} (same as --branch for agent-studio)"

    if [ -d "$RUNTIME_DIR" ]; then
        log "INFO" "Runtime directory already exists, updating code..."
        if ! cd "$RUNTIME_DIR"; then
            error_exit "Cannot cd to runtime directory: $RUNTIME_DIR" \
                "Check directory permissions and path."
        fi
        if ! git fetch origin --prune || ! git pull origin "$GIT_BRANCH"; then
            error_exit "Failed to update runtime code" \
                "Try manually: cd $RUNTIME_DIR && git fetch origin --prune && git pull origin $GIT_BRANCH"
        fi
    else
        log "INFO" "Cloning runtime repository..."
        if ! cd "$WORK_HOME"; then
            error_exit "Cannot cd to work home: $WORK_HOME" \
                "Check script execution directory."
        fi
        if ! git clone -b "$GIT_BRANCH" "$RUNTIME_REPO_URL" "agent-runtime"; then
            error_exit "Failed to clone runtime repository" \
                "Check network and git access: $RUNTIME_REPO_URL"
        fi
    fi
    cd "$WORK_HOME" || error_exit "Cannot cd to WORK_HOME: $WORK_HOME" \
        "Check permissions on $WORK_HOME"
    save_progress "$STEP"
fi

# ===================== Configure Runtime .env =====================
STEP="config_runtime_env"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: Runtime .env configuration (already completed)"
else
    log "INFO" "===== Configuring Runtime .env ====="
    RUNTIME_SERVER_DIR="${RUNTIME_DIR}/server"
    RUNTIME_ENV_EXAMPLE="${RUNTIME_SERVER_DIR}/.env.example"
    RUNTIME_ENV_FILE="${RUNTIME_SERVER_DIR}/.env"
    check_dir "$RUNTIME_SERVER_DIR"
    check_file "$RUNTIME_ENV_EXAMPLE"

    if [ ! -f "$RUNTIME_ENV_FILE" ]; then
        log "INFO" "Runtime .env not found, copying from .env.example"
        if ! cp "$RUNTIME_ENV_EXAMPLE" "$RUNTIME_ENV_FILE"; then
            error_exit "Failed to create runtime .env from .env.example" \
                "Try manually: cp $RUNTIME_ENV_EXAMPLE $RUNTIME_ENV_FILE"
        fi
    fi

    log "INFO" "Setting runtime DB_TYPE to: $DB_TYPE"
    if grep -q "^DB_TYPE=" "$RUNTIME_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^DB_TYPE=.*|DB_TYPE=$DB_TYPE|" "$RUNTIME_ENV_FILE"
        else
            sed -i "s|^DB_TYPE=.*|DB_TYPE=$DB_TYPE|" "$RUNTIME_ENV_FILE"
        fi
    else
        printf '\nDB_TYPE=%s\n' "$DB_TYPE" >> "$RUNTIME_ENV_FILE"
    fi

    load_db_host_port_from_user_config
    log "INFO" "Setting runtime DB_USER / DB_PASSWORD from --app_db_user / --app_db_password"
    if grep -q "^DB_USER=" "$RUNTIME_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^DB_USER=.*|DB_USER=${APP_DB_USER}|" "$RUNTIME_ENV_FILE"
        else
            sed -i "s|^DB_USER=.*|DB_USER=${APP_DB_USER}|" "$RUNTIME_ENV_FILE"
        fi
    else
        echo "DB_USER=${APP_DB_USER}" >> "$RUNTIME_ENV_FILE"
    fi
    ESCAPED_RT_DB_PASSWORD=$(printf '%s\n' "$APP_DB_PASSWORD" | sed 's/[[\.*^$()+?{|]/\\&/g')
    if grep -q "^DB_PASSWORD=" "$RUNTIME_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^DB_PASSWORD=.*|DB_PASSWORD=${ESCAPED_RT_DB_PASSWORD}|" "$RUNTIME_ENV_FILE"
        else
            sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${ESCAPED_RT_DB_PASSWORD}|" "$RUNTIME_ENV_FILE"
        fi
    else
        echo "DB_PASSWORD=${APP_DB_PASSWORD}" >> "$RUNTIME_ENV_FILE"
    fi
    log "INFO" "Setting runtime DB_HOST / DB_PORT from user_config.sh"
    if grep -q "^DB_HOST=" "$RUNTIME_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^DB_HOST=.*|DB_HOST=${DB_HOST}|" "$RUNTIME_ENV_FILE"
        else
            sed -i "s|^DB_HOST=.*|DB_HOST=${DB_HOST}|" "$RUNTIME_ENV_FILE"
        fi
    else
        echo "DB_HOST=${DB_HOST}" >> "$RUNTIME_ENV_FILE"
    fi
    if grep -q "^DB_PORT=" "$RUNTIME_ENV_FILE"; then
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|^DB_PORT=.*|DB_PORT=${DB_PORT}|" "$RUNTIME_ENV_FILE"
        else
            sed -i "s|^DB_PORT=.*|DB_PORT=${DB_PORT}|" "$RUNTIME_ENV_FILE"
        fi
    else
        echo "DB_PORT=${DB_PORT}" >> "$RUNTIME_ENV_FILE"
    fi
    log "SUCCESS" "Runtime .env updated: DB_USER=${APP_DB_USER} (DB_PASSWORD set), DB_HOST=${DB_HOST}, DB_PORT=${DB_PORT}"

    RUNTIME_DB_TYPE_ACTUAL=$(grep '^DB_TYPE=' "$RUNTIME_ENV_FILE" 2>/dev/null | cut -d'=' -f2- || echo "not found")
    if [ "$RUNTIME_DB_TYPE_ACTUAL" != "$DB_TYPE" ]; then
        log "WARN" "Runtime DB_TYPE may not have applied, current: $RUNTIME_DB_TYPE_ACTUAL (expected: $DB_TYPE)"
    else
        log "INFO" "Runtime DB_TYPE configured successfully: $DB_TYPE"
    fi

    save_progress "$STEP"
fi

# ===================== Configure MySQL =====================
STEP="config_mysql"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: MySQL configuration (already done)"
elif [ "$DB_TYPE" = "mysql" ]; then
    log "INFO" "===== Configuring MySQL ====="
    CONFIG_MYSQL_SH="${WORK_HOME}/config_mysql.sh"
    if [ ! -f "$CONFIG_MYSQL_SH" ]; then
        log "ERROR" "config_mysql.sh not found: $CONFIG_MYSQL_SH"
        exit 1
    fi
    # shellcheck source=config_mysql.sh
    source "$CONFIG_MYSQL_SH"
    if ! type interactive_mysql_setup &>/dev/null; then
        log "ERROR" "Function interactive_mysql_setup not found in config_mysql.sh"
        exit 1
    fi
    interactive_mysql_setup "$APP_DB_USER" "$APP_DB_PASSWORD"
    save_progress "$STEP"
else
    log "INFO" "Skipping: MySQL configuration (not applicable, DB_TYPE=$DB_TYPE)"
    save_progress "$STEP"
fi

# ===================== Install backend dependencies =====================
STEP="install_backend_dep"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: install backend dependencies (already done)"
    cd "$BACKEND_DIR" 2>/dev/null || log "WARN" "Cannot cd to backend dir, continuing"
else
    log "INFO" "===== Installing backend dependencies ====="
    echo -e "${GREEN}[Progress] Installing backend dependencies (uv venv + uv sync)...${NC}"
    
    if ! cd "$BACKEND_DIR" 2>/dev/null; then
        error_exit "Cannot cd to backend directory: $BACKEND_DIR" \
            "Check code fetch: ls -la $WORK_HOME/agent-studio"
    fi

    load_environments

    check_command "python3.11"
    check_command "uv"
    log "INFO" "uv: $(uv --version 2>/dev/null || echo 'unknown')"

    log "INFO" "Creating/resetting uv venv (Python 3.11)"
    if ! retry_execute 2 5 "Create venv" "uv venv --clear --python python3.11"; then
        log "WARN" "Failed with --python python3.11, trying full path"
        PYTHON311_PATH=$(which python3.11 2>/dev/null || echo "")
        if [ -n "$PYTHON311_PATH" ]; then
            if ! retry_execute 2 5 "Create venv with full path" "uv venv --clear --python '$PYTHON311_PATH'"; then
                error_exit "Create venv failed" \
                    "1. Check Python3.11: python3.11 --version\n\
2. Check disk: df -h\n\
3. Create manually: cd $BACKEND_DIR && uv venv --python python3.11"
            fi
        else
            error_exit "python3.11 not found, cannot create venv" \
                "Ensure Python3.11 is installed: which python3.11"
        fi
    fi

    get_uv_index_args_from_user_config

    log "INFO" "Syncing dependencies with uv (project + default groups from pyproject.toml, e.g. dev)"
    UV_SYNC_OK=false
    for _ in 1 2 3; do
        if uv sync --python "${BACKEND_DIR}/.venv/bin/python" "${UV_INDEX_ARGS[@]}"; then
            UV_SYNC_OK=true
            log "SUCCESS" "Dependencies synced (uv sync)"
            break
        fi
        log "WARN" "uv sync failed, retrying in 30s..."
        sleep 30
    done
    if [ "$UV_SYNC_OK" != "true" ]; then
        error_exit "uv sync failed" \
            "1. Check network\n\
2. Check disk: df -h\n\
3. Retry manually: cd $BACKEND_DIR && uv sync --python .venv/bin/python ${UV_INDEX_ARGS[*]}"
    fi

    if ! mkdir -p logs/run 2>/dev/null; then
        error_exit "Failed to create backend log directory" \
            "Check directory permission: ls -ld $BACKEND_DIR"
    fi
    save_progress "$STEP"
fi

# ===================== Install frontend dependencies =====================
STEP="install_frontend_dep"
if should_skip_step "$STEP" "$LAST_PROGRESS"; then
    log "INFO" "Skipping: install frontend dependencies (already done)"
    cd "$FRONTEND_DIR" 2>/dev/null || log "WARN" "Cannot cd to frontend dir, continuing"
else
    log "INFO" "===== Installing frontend dependencies ====="
    echo -e "${GREEN}[Progress] Backend dependencies done, installing frontend dependencies (npm install)...${NC}"
    
    if ! cd "$FRONTEND_DIR" 2>/dev/null; then
        error_exit "Cannot cd to frontend directory: $FRONTEND_DIR" \
            "Check code fetch: ls -la $WORK_HOME/agent-studio"
    fi

load_environments

check_command "node"
check_command "npm"

    log "INFO" "Installing frontend dependencies (may take a few minutes)..."
    if ! retry_execute 3 30 "Install frontend dependencies" "npm install"; then
        error_exit "Install frontend dependencies failed" \
            "1. Check network\n\
2. Clear npm cache and retry: npm cache clean --force && npm install\n\
3. Check disk: df -h\n\
4. Install manually: cd $FRONTEND_DIR && npm install"
    fi
    save_progress "$STEP"
fi

# ===================== Start services (runtime / backend / frontend) =====================
STEP="start_services"
if [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
    start_services
    save_progress "$STEP"
else
    log "INFO" "Skipping: start services (already done)"
fi

# ===================== Done =====================
log "SUCCESS" "========================================="
log "SUCCESS" "===== Deployment complete ====="
log "SUCCESS" "========================================="

check_status

clear_progress
log "SUCCESS" "========================================="

exit 0
