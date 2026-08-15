#!/bin/bash
# macOS one-click install and deploy script
set -uo pipefail  # Keep undefined variable and pipe failure checks, but do not exit on error

# ===================== Basic configuration =====================
WORK_HOME=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)  # Script directory (not CWD), more stable
BACKEND_DIR="${WORK_HOME}/agent-studio/backend"
FRONTEND_DIR="${WORK_HOME}/agent-studio/frontend"
TARGET_ENV_FILE="${WORK_HOME}/agent-studio/.env"
ENV_EXAMPLE_FILE="${WORK_HOME}/agent-studio/.env.example"
LOG_FILE="${WORK_HOME}/setup.log"
PROGRESS_FILE="${WORK_HOME}/.setup_progress"

# Colored output (for readability)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # Reset color

# ===================== Utility functions =====================
# Log: output to both console and log file
log() {
    local LEVEL=$1
    shift
    local MSG="$*"
    local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    local LOG_MSG="[${TIMESTAMP}] [${LEVEL}] ${MSG}"
    
    # Output to console (with color)
    case "$LEVEL" in
        ERROR)
            echo -e "${RED}${LOG_MSG}${NC}" >&2
            ;;
        WARN)
            echo -e "${YELLOW}${LOG_MSG}${NC}"
            ;;
        SUCCESS)
            echo -e "${GREEN}${LOG_MSG}${NC}"
            ;;
        INFO)
            echo -e "${BLUE}${LOG_MSG}${NC}"
            ;;
        *)
            echo "${LOG_MSG}"
            ;;
    esac
    
    # Also write to log file
    echo "${LOG_MSG}" >> "$LOG_FILE" 2>/dev/null || true
}

# Save progress
save_progress() {
    local STEP=$1
    echo "$STEP" > "$PROGRESS_FILE" 2>/dev/null || true
    log "INFO" "Progress saved: $STEP"
}

# Read progress
read_progress() {
    if [ -f "$PROGRESS_FILE" ]; then
        cat "$PROGRESS_FILE" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Clear progress
clear_progress() {
    rm -f "$PROGRESS_FILE" 2>/dev/null || true
}

# Find compatible Python in current environment
find_compatible_python() {
    local candidates=("python3.13" "python3.12" "python3.11" "python3")
    local cmd ver major minor
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" > /dev/null 2>&1; then
            ver=$("$cmd" -c 'import sys,math; v=sys.version_info; print(f"{v[0]}.{v[1]}.{v[2]}")' 2>/dev/null || echo "")
            major=${ver%%.*}
            minor=${ver#*.}; minor=${minor%%.*}
            if [ "$major" = "3" ] && [ "$minor" -ge 11 ] && [ "$minor" -le 13 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# Ensure Python is available and set global PYTHON_CMD
ensure_python_compatible() {
    if [ -n "${PYTHON_CMD:-}" ]; then
        return 0
    fi

    local cmd
    cmd=$(find_compatible_python) || cmd=""

    if [ -n "$cmd" ]; then
        PYTHON_CMD="$cmd"
        log "INFO" "Compatible Python found: $($cmd -V 2>/dev/null || echo "$cmd")"
        return 0
    fi

    # No suitable version found, try installing python@3.11 via Homebrew
    if command -v brew > /dev/null 2>&1; then
        log "INFO" "Python not found, installing Python 3.11 via Homebrew..."
        if ! retry_execute 1 5 "Install Python 3.11" "brew install python@3.11"; then
            error_exit "Install Python 3.11 failed; re-run the script or install Python 3.11 manually"
        fi
        PYTHON_CMD="python3.11"
        log "SUCCESS" "Python 3.11 installed, using: $PYTHON_CMD"
        return 0
    fi

    error_exit "Python not found; re-run the script or install Python 3.11 manually"
}

# Execute with retries
retry_execute() {
    local MAX_RETRIES=${1:-3}
    local RETRY_DELAY=${2:-5}
    local STEP_NAME="$3"
    shift 3
    local COMMAND="$*"
    
    local ATTEMPT=1
    local LAST_ERROR=1  # Initialize to non-zero to avoid undefined variable under set -u
    
    while [ $ATTEMPT -le $MAX_RETRIES ]; do
        log "INFO" "[Attempt $ATTEMPT/$MAX_RETRIES] Running: $STEP_NAME"
        
        eval "$COMMAND" 2>&1
        local err=$?
        if [ "$err" -eq 0 ]; then
            log "SUCCESS" "$STEP_NAME completed"
            return 0
        fi
        
        LAST_ERROR=$err
        log "WARN" "$STEP_NAME failed (exit ${LAST_ERROR}), retrying in ${RETRY_DELAY}s..."
        if [ $ATTEMPT -lt $MAX_RETRIES ]; then
            sleep $RETRY_DELAY
        fi
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    log "ERROR" "$STEP_NAME failed after $MAX_RETRIES attempts"
    LAST_ERROR=${LAST_ERROR:-1}
    return $LAST_ERROR
}

# Error handler (with recovery hint)
error_exit() {
    local MSG="$1"
    local RECOVERY_HINT="${2:-}"
    
    log "ERROR" "========================================="
    log "ERROR" "Deployment failed: $MSG"
    if [ -n "$RECOVERY_HINT" ]; then
        log "ERROR" ""
        log "ERROR" "Recovery suggestion:"
        echo -e "${YELLOW}$RECOVERY_HINT${NC}" >&2
    fi
    log "ERROR" "========================================="
    log "ERROR" "See log file: $LOG_FILE"
    log "ERROR" "Progress saved; re-run the script to continue"
    exit 1
}

# Load all required environments (NVM, Conda, pyenv, user PATH, etc.)
load_environments() {
    # Load NVM (if Node.js was installed via NVM)
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" 2>/dev/null || true
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" 2>/dev/null || true
    fi
    
    # Load pyenv (if Python was installed via pyenv)
    if [ -d "$HOME/.pyenv" ]; then
        export PYENV_ROOT="$HOME/.pyenv"
        if [[ ":$PATH:" != *":$PYENV_ROOT/bin:"* ]]; then
            export PATH="$PYENV_ROOT/bin:$PATH"
        fi
        # Initialize pyenv
        if command -v pyenv &> /dev/null; then
            eval "$(pyenv init -)" 2>/dev/null || true
            eval "$(pyenv init --path)" 2>/dev/null || true
        fi
    fi
    
    # Load Conda (if Python was installed via Conda)
    if [ -s "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null || true
    elif [ -s "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh" 2>/dev/null || true
    elif [ -s "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh" 2>/dev/null || true
    fi
    
    # Ensure user local bin is in PATH (uv, pip, etc. may be installed here)
    if [ -d "$HOME/.local/bin" ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if [ -d "/root/.local/bin" ] && [[ ":$PATH:" != *":/root/.local/bin:"* ]]; then
        export PATH="/root/.local/bin:$PATH"
    fi
}

# Check if command exists (with environment loading)
check_command() {
    local CMD="${1:-}"
    
    # Try loading environment first
    load_environments
    
    # Check if command exists
    if ! command -v "${CMD:-}" &> /dev/null; then
        # For specific commands, try special handling
        case "${CMD:-}" in
            node|npm)
                # Try loading NVM again
                if [ -s "$HOME/.nvm/nvm.sh" ]; then
                    export NVM_DIR="$HOME/.nvm"
                    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" 2>/dev/null || true
                fi
                ;;
            uv)
                # Auto-find uv installed via pip on macOS
                for PY_BIN in "$HOME/Library/Python/"*/bin/uv; do
                    if [ -f "$PY_BIN" ]; then
                        PY_BIN_DIR=$(dirname "$PY_BIN")
                        if [[ ":$PATH:" != *":$PY_BIN_DIR:"* ]]; then
                            export PATH="$PY_BIN_DIR:$PATH"
                        fi
                        break
                    fi
                done
                ;;
            python3.11)
                # Load all environments first
                load_environments
                
                # Check pyenv environment
                if [ -d "$HOME/.pyenv" ]; then
                    export PYENV_ROOT="$HOME/.pyenv"
                    # Add pyenv to PATH
                    if [[ ":$PATH:" != *":$PYENV_ROOT/bin:"* ]]; then
                        export PATH="$PYENV_ROOT/bin:$PATH"
                    fi
                    # Initialize pyenv
                    if command -v pyenv &> /dev/null; then
                        eval "$(pyenv init -)" 2>/dev/null || true
                        eval "$(pyenv init --path)" 2>/dev/null || true
                    fi
                    # Add pyenv shims to PATH (key for pyenv command management)
                    if [ -d "$PYENV_ROOT/shims" ] && [[ ":$PATH:" != *":$PYENV_ROOT/shims:"* ]]; then
                        export PATH="$PYENV_ROOT/shims:$PATH"
                    fi
                    # Find pyenv-installed python3.11 directly
                    for pyenv_python in "$PYENV_ROOT"/versions/*/bin/python3.11; do
                        if [ -f "$pyenv_python" ]; then
                            # If found, ensure its directory is in PATH
                            PYENV_BIN_DIR=$(dirname "$pyenv_python")
                            if [[ ":$PATH:" != *":$PYENV_BIN_DIR:"* ]]; then
                                export PATH="$PYENV_BIN_DIR:$PATH"
                            fi
                            break
                        fi
                    done
                fi
                
                # Check conda environment
                if [ -s "$HOME/miniconda3/envs/py311/bin/python3.11" ]; then
                    # Python in conda env, ensure conda is loaded
                    load_environments
                    # Check if symlink exists
                    if [ ! -f "/usr/local/bin/python3.11" ] && [ -f "$HOME/miniconda3/envs/py311/bin/python3.11" ]; then
                        # Try creating symlink (requires sudo, only hint here)
                        log "WARN" "python3.11 in conda env but symlink missing"
                    fi
                fi
                
                # Check Homebrew-installed Python (usually /opt/homebrew or /usr/local)
                if [ -f "/opt/homebrew/bin/python3.11" ] && [[ ":$PATH:" != *":/opt/homebrew/bin:"* ]]; then
                    export PATH="/opt/homebrew/bin:$PATH"
                elif [ -f "/usr/local/bin/python3.11" ] && [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
                    export PATH="/usr/local/bin:$PATH"
                fi
                ;;
        esac
        
        # Check again
        if ! command -v "${CMD:-}" &> /dev/null; then
            CMD_VALUE="${CMD:-unknown}"
            ERROR_MSG="Required command '${CMD_VALUE}' not found"
            RECOVERY_MSG="Install ${CMD_VALUE} and re-run the script"
            error_exit "$ERROR_MSG" "$RECOVERY_MSG"
        fi
    fi
}

# Check if file exists (optionally create)
check_file() {
    local FILE=$1
    local CREATE_IF_NOT_EXIST=${2:-false}
    if [ ! -f "$FILE" ]; then
        if [ "$CREATE_IF_NOT_EXIST" = true ]; then
            log "WARN" "File $FILE not found, creating empty file"
            mkdir -p "$(dirname "$FILE")" && touch "$FILE" || {
                error_exit "Failed to create $FILE" \
                    "Check directory permissions: $(dirname "$FILE")"
            }
        else
            error_exit "File $FILE not found, cannot continue" \
                "Ensure code is fetched or create the file manually"
        fi
    fi
}

# Check if directory exists
check_dir() {
    local DIR=$1
    if [ ! -d "$DIR" ]; then
        error_exit "Directory $DIR not found, cannot continue" \
            "Ensure code is fetched or create directory: mkdir -p $DIR"
    fi
}

# Check and fix script execute permission
check_script_permission() {
    local SCRIPT=$1
    if [ -f "$SCRIPT" ] && [ ! -x "$SCRIPT" ]; then
        log "WARN" "Script $SCRIPT missing execute permission, fixing..."
        chmod +x "$SCRIPT" || {
            log "WARN" "Could not add execute permission to $SCRIPT, will run with bash"
            return 1
        }
        log "SUCCESS" "Execute permission added to $SCRIPT"
    fi
}

# Check if MySQL service is running (macOS)
check_mysql_service() {
    # Check MySQL installed via Homebrew
    if brew services list 2>/dev/null | grep -q "mysql.*started"; then
        return 0
    fi
    
    # Check MySQL process
    if pgrep -x mysqld > /dev/null 2>&1 || pgrep -f "mysqld" > /dev/null 2>&1; then
        return 0
    fi
    
    # Check if MySQL port is in use
    if lsof -i :3306 > /dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Start MySQL service (macOS)
start_mysql_service() {
    log "INFO" "Starting MySQL service..."
    
    # Try starting via Homebrew
    if command -v brew &> /dev/null; then
        if brew services start mysql 2>/dev/null; then
            log "SUCCESS" "MySQL service started (via Homebrew)"
            sleep 3
            return 0
        fi
    fi
    
    # Try starting mysqld directly (if found)
    local MYSQLD_PATH=""
    if [ -f "/opt/homebrew/bin/mysqld_safe" ]; then
        MYSQLD_PATH="/opt/homebrew/bin/mysqld_safe"
    elif [ -f "/usr/local/bin/mysqld_safe" ]; then
        MYSQLD_PATH="/usr/local/bin/mysqld_safe"
    elif [ -f "/usr/local/mysql/bin/mysqld_safe" ]; then
        MYSQLD_PATH="/usr/local/mysql/bin/mysqld_safe"
    fi
    
    if [ -n "$MYSQLD_PATH" ] && [ -x "$MYSQLD_PATH" ]; then
        log "INFO" "Starting MySQL service directly..."
        nohup "$MYSQLD_PATH" > /dev/null 2>&1 &
        sleep 3
        if check_mysql_service; then
            log "SUCCESS" "MySQL service started"
            return 0
        fi
    fi
    
    log "WARN" "Could not start MySQL service automatically"
    return 1
}

# Verify MySQL command is available
verify_mysql_command() {
    local MYSQL_CMD="$1"
    
    # If full path given, test directly
    if [ -f "$MYSQL_CMD" ] && [ -x "$MYSQL_CMD" ]; then
        if "$MYSQL_CMD" --version > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # If command name, check if in PATH
    if command -v "$MYSQL_CMD" &> /dev/null; then
        if "$MYSQL_CMD" --version > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    return 1
}

# Check and install greenlet (Apple Silicon Mac compatibility)
check_and_install_greenlet() {
    local BACKEND_DIR="$1"
    
    # Only run on macOS
    if [[ "$(uname -s)" != "Darwin" ]]; then
        return 0
    fi
    
    log "INFO" "Checking greenlet module (Apple Silicon compatibility)"
    
    # Change to backend directory
    cd "$BACKEND_DIR" || {
        log "WARN" "Cannot enter backend dir, skipping greenlet check"
        return 0
    }
    
    # Check if virtual environment exists
    if [ ! -f ".venv/bin/activate" ]; then
        log "WARN" "Venv not found, skipping greenlet check"
        return 0
    fi
    
    # Check if in virtual environment (via VIRTUAL_ENV)
    local WAS_IN_VENV=false
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        WAS_IN_VENV=true
        log "INFO" "In venv, deactivating to install greenlet"
        deactivate 2>/dev/null || true
    fi
    
    # Try checking if greenlet is installed in venv
    local GREENLET_INSTALLED=false
    if source .venv/bin/activate 2>/dev/null; then
        # Try importing greenlet
        if python3 -c "import greenlet" 2>/dev/null; then
            GREENLET_INSTALLED=true
            log "SUCCESS" "greenlet module already installed"
        fi
        # Deactivate venv for subsequent install
        deactivate 2>/dev/null || true
    fi
    
    # If greenlet not installed, install it
    if [ "$GREENLET_INSTALLED" = false ]; then
        log "WARN" "greenlet not installed, installing..."
        log "INFO" "Some Apple Silicon Mac Python builds lack greenlet in stdlib"
        
        # Ensure not in virtual environment
        if [ -n "${VIRTUAL_ENV:-}" ]; then
            deactivate 2>/dev/null || true
        fi
        
        # Ensure uv command is available
        check_command "uv"
        
        # Install greenlet via uv add
        log "INFO" "Installing greenlet via uv add..."
        if ! retry_execute 3 10 "Install greenlet" "uv add greenlet"; then
            log "ERROR" "greenlet install failed"
            error_exit "greenlet installation failed" \
                "1. Check network\n\
2. Check uv: uv --version\n\
3. Manual: cd $BACKEND_DIR && deactivate && uv add greenlet && source .venv/bin/activate"
        fi
        
        log "SUCCESS" "greenlet installed"
        
        # Verify installation
        if source .venv/bin/activate 2>/dev/null; then
            if python3 -c "import greenlet" 2>/dev/null; then
                log "SUCCESS" "greenlet module verified"
            else
                log "WARN" "greenlet verification failed after install, continuing"
            fi
            # Deactivate venv (will be reactivated on next start)
            deactivate 2>/dev/null || true
        fi
    fi
    
    # If was in venv, no need to reactivate (will be activated on start)
    # Do not reactivate here; let caller decide when to activate
    
    return 0
}


# Test MySQL connection (with given username and password)
test_mysql_connection() {
    local DB_USER="$1"
    local DB_PASSWORD="$2"
    local DB_HOST="${3:-localhost}"
    local DB_PORT="${4:-3306}"
    
    if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        return 1
    fi
    
    # Find MySQL command
    local MYSQL_CMD_BIN=$(find_mysql_command)
    if [ -z "$MYSQL_CMD_BIN" ]; then
        MYSQL_CMD_BIN="mysql"
    fi
    
    # Ensure MySQL command is in PATH
    if [ "$MYSQL_CMD_BIN" != "mysql" ]; then
        local MYSQL_BIN_DIR=$(dirname "$MYSQL_CMD_BIN")
        if [[ ":$PATH:" != *":$MYSQL_BIN_DIR:"* ]]; then
            export PATH="$MYSQL_BIN_DIR:$PATH"
            if command -v mysql &> /dev/null && verify_mysql_command "mysql" 2>/dev/null; then
                MYSQL_CMD_BIN="mysql"
            fi
        fi
    fi
    
    # Test connection
    export MYSQL_PWD="$DB_PASSWORD"
    if [ "$MYSQL_CMD_BIN" = "mysql" ]; then
        mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1;" > /dev/null 2>&1
        local RESULT=$?
    else
        "$MYSQL_CMD_BIN" -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1;" > /dev/null 2>&1
        local RESULT=$?
    fi
    unset MYSQL_PWD
    
    return $RESULT
}


# Find MySQL executable path
# Read config value from .env file, handle quotes correctly
read_env_value() {
    local key="$1"
    local default_value="${2:-}"
    local env_file="${3:-$TARGET_ENV_FILE}"
    
    if [ ! -f "$env_file" ]; then
        echo "$default_value"
        return
    fi
    
    local value=$(grep "^${key}=" "$env_file" 2>/dev/null | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    if [ -z "$value" ]; then
        echo "$default_value"
        return
    fi
    
    # Strip leading/trailing matching quotes from quoted values
    if [[ "$value" =~ ^\".*\"$ ]]; then
        # Double-quoted
        value="${value#\"}"
        value="${value%\"}"
    elif [[ "$value" =~ ^\'.*\'$ ]]; then
        # Single-quoted
        value="${value#\'}"
        value="${value%\'}"
    fi
    
    echo "$value"
}

find_mysql_command() {
    # First check if mysql is in PATH
    if command -v mysql &> /dev/null; then
        if verify_mysql_command "mysql"; then
        echo "mysql"
        return 0
        fi
    fi
    
    # Check common MySQL install paths (macOS)
    local MYSQL_PATHS=(
        "/opt/homebrew/bin/mysql"           # Homebrew on Apple Silicon
        "/usr/local/bin/mysql"              # Homebrew on Intel
        "/usr/local/mysql/bin/mysql"        # Official package (default location)
        "/Applications/XAMPP/xamppfiles/bin/mysql"  # XAMPP
    )
    
    # Check fixed paths first
    for mysql_path in "${MYSQL_PATHS[@]}"; do
        if [ -f "$mysql_path" ] && [ -x "$mysql_path" ]; then
            if verify_mysql_command "$mysql_path"; then
            echo "$mysql_path"
            return 0
            fi
        fi
    done
    
    # If not in fixed paths, search common MySQL install dirs with find
    # Search /usr/local/mysql-*/bin/mysql (official package)
    if [ -d "/usr/local" ]; then
        local found_mysql=$(find /usr/local -maxdepth 3 -type f -name "mysql" -path "*/mysql*/bin/mysql" 2>/dev/null | head -1)
        if [ -n "$found_mysql" ] && [ -x "$found_mysql" ]; then
            if verify_mysql_command "$found_mysql"; then
            echo "$found_mysql"
            return 0
            fi
        fi
    fi
    
    # Also search /System/Volumes/Data/usr/local (macOS Big Sur+ system path)
    if [ -d "/System/Volumes/Data/usr/local" ]; then
        local found_mysql=$(find /System/Volumes/Data/usr/local -maxdepth 3 -type f -name "mysql" -path "*/mysql*/bin/mysql" 2>/dev/null | head -1)
        if [ -n "$found_mysql" ] && [ -x "$found_mysql" ]; then
            if verify_mysql_command "$found_mysql"; then
            echo "$found_mysql"
            return 0
            fi
        fi
    fi
    
    return 1
}

# Install MySQL (via Homebrew)
install_mysql_with_homebrew() {
    if ! command -v brew &> /dev/null; then
        log "ERROR" "Homebrew not installed, cannot install MySQL automatically"
        echo -e "${RED}Error: Homebrew not installed${NC}"
        echo -e "${YELLOW}Install Homebrew first, or install MySQL manually:${NC}"
        echo "  1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  2. Or use MySQL official package: https://dev.mysql.com/downloads/mysql/"
        echo "  3. After installation, re-run this script: ./setup.sh"
        return 1
    fi
    
    log "INFO" "Installing MySQL via Homebrew..."
    echo -e "${YELLOW}Installing MySQL via Homebrew (may take a few minutes)...${NC}"
    
    if brew install mysql 2>&1; then
        log "SUCCESS" "MySQL installed"
        
        # Start MySQL service
        log "INFO" "Starting MySQL service..."
        brew services start mysql 2>/dev/null || {
            log "WARN" "MySQL service failed to start; run manually: brew services start mysql"
        }
        
        # Wait for MySQL service to start
        sleep 3
        
        # Check if mysql command is available; if not, add to PATH
        if ! command -v mysql &> /dev/null; then
            # If mysql still not in PATH, try adding it
            if [ -f "/opt/homebrew/bin/mysql" ]; then
                export PATH="/opt/homebrew/bin:$PATH"
                log "INFO" "MySQL path added to PATH: /opt/homebrew/bin"
            elif [ -f "/usr/local/bin/mysql" ]; then
                export PATH="/usr/local/bin:$PATH"
                log "INFO" "MySQL path added to PATH: /usr/local/bin"
            fi
        fi
        
        # Verify installation succeeded
        if command -v mysql &> /dev/null || [ -f "/opt/homebrew/bin/mysql" ] || [ -f "/usr/local/bin/mysql" ]; then
            log "SUCCESS" "MySQL installed, command available"
            return 0
        else
            log "WARN" "MySQL installed but may not be in PATH; reopen terminal or add PATH manually"
            return 0  # Still return success since MySQL is installed
        fi
    else
        log "ERROR" "MySQL installation failed"
        return 1
    fi
}

# MySQL database configuration
configure_mysql_database() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}MySQL database configuration${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # 1. Ensure MySQL service is running
    if ! ensure_mysql_service_running; then
        return 1
    fi
    
    # 2. Get root connection
    if ! get_mysql_root_connection; then
        return 1
    fi
    
    # 3. Run auto config: create user + databases + grant + update .env
    create_mysql_user
}

# Ensure MySQL service is running
ensure_mysql_service_running() {
    if check_mysql_service; then
        log "SUCCESS" "MySQL service is running"
        return 0
    fi
    
    log "WARN" "MySQL service not running, attempting to start..."
    
    # Try to start automatically
    if start_mysql_service; then
        sleep 2
        if check_mysql_service; then
            log "SUCCESS" "MySQL service started"
            return 0
        fi
    fi
    
    # Auto-start failed, prompt user
    echo -e "${YELLOW}Could not start MySQL service automatically${NC}"
    echo "Please start MySQL service manually:"
    if command -v brew &> /dev/null; then
        echo "  brew services start mysql"
    else
        echo "  sudo systemctl start mysql  # or according to your system"
    fi
    echo ""
    read -p "Have you started MySQL service manually? (y/n, default y): " SERVICE_STARTED
    
    if [[ "${SERVICE_STARTED:-y}" = "y" ]]; then
        sleep 2
        if check_mysql_service; then
            log "SUCCESS" "MySQL service is running"
            return 0
        fi
    fi
    
    log "ERROR" "MySQL service not running"
    return 1
}

# Get MySQL root connection
get_mysql_root_connection() {
    echo ""
    echo -e "${YELLOW}Connecting to MySQL as root...${NC}"
    
    # Try connection without password
    if mysql -u root -e "SELECT 1;" &>/dev/null; then
        MYSQL_CMD="mysql -u root"
        log "SUCCESS" "MySQL connected"
        return 0
    fi
    
    # No password failed: prompt for password (retry up to 3 times on error)
    echo -e "${YELLOW}MySQL root access required${NC}"
    MAX_PASSWORD_ATTEMPTS=3
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_PASSWORD_ATTEMPTS ]; do
        read -sp "Enter MySQL root password (or press Enter to skip and configure later): " ROOT_PASSWORD
        echo
    
        if [ -z "$ROOT_PASSWORD" ]; then
            log "ERROR" "Could not connect as MySQL root"
            return 1
        fi
    
        if MYSQL_PWD="$ROOT_PASSWORD" mysql -u root -e "SELECT 1;" &>/dev/null; then
            MYSQL_CMD="MYSQL_PWD='$ROOT_PASSWORD' mysql -u root"
            log "SUCCESS" "Connected with password"
            return 0
        fi
    
        ATTEMPT=$((ATTEMPT + 1))
        log "ERROR" "Wrong password"
        if [ $ATTEMPT -lt $MAX_PASSWORD_ATTEMPTS ]; then
            echo -e "${YELLOW}$((MAX_PASSWORD_ATTEMPTS - ATTEMPT)) attempt(s) left, try again${NC}"
        else
            log "ERROR" "Wrong password after ${MAX_PASSWORD_ATTEMPTS} attempts"
            return 1
        fi
    done
    
    return 1
}

# Create MySQL user
create_mysql_user() {
    echo ""
    echo -e "${BLUE}Creating MySQL user (auto mode)${NC}"
    
    # Fixed username and password (avoid inconsistency from random password)
    NEW_DB_USER="openjiuwen"
    NEW_DB_PASSWORD="openjiuwen2026"
    
    # Run SQL: create databases + user + grant (in one go)
    echo ""
    echo -e "${YELLOW}Creating databases and user (openjiuwen)...${NC}"
    
    SQL_COMMANDS="
    CREATE DATABASE IF NOT EXISTS openjiuwen_agent;
    CREATE DATABASE IF NOT EXISTS openjiuwen_ops;
    CREATE USER IF NOT EXISTS '${NEW_DB_USER}'@'localhost' IDENTIFIED BY '${NEW_DB_PASSWORD}';
    ALTER USER '${NEW_DB_USER}'@'localhost' IDENTIFIED BY '${NEW_DB_PASSWORD}';
    GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO '${NEW_DB_USER}'@'localhost';
    GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO '${NEW_DB_USER}'@'localhost';
    FLUSH PRIVILEGES;
    "
    
    if ! eval "$MYSQL_CMD -e \"$SQL_COMMANDS\"" 2>/dev/null; then
        log "ERROR" "Failed to create database or user"
        log "ERROR" "Check MySQL version and password policy, or create user/grant manually and retry"
        return 1
    fi
    
    # Update .env file
    update_env_file "$NEW_DB_USER" "$NEW_DB_PASSWORD"
    
    echo ""
    echo -e "${GREEN}✅ Configuration complete${NC}"
    echo -e "${GREEN}   - User: ${NEW_DB_USER}${NC}"
    echo -e "${GREEN}   - Password: ${NEW_DB_PASSWORD}${NC}"
    echo -e "${GREEN}   - Databases: openjiuwen_agent, openjiuwen_ops${NC}"
    return 0
}

# Update .env file
update_env_file() {
    local user="$1"
    local password="$2"
    
    if [ ! -f "$TARGET_ENV_FILE" ]; then
        log "ERROR" ".env file not found"
        return 1
    fi
    
    # Update or add config directly (no .env.bak generated)
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "/^DB_USER=/d" "$TARGET_ENV_FILE"
        sed -i '' "/^DB_PASSWORD=/d" "$TARGET_ENV_FILE"
    else
        sed -i "/^DB_USER=/d" "$TARGET_ENV_FILE"
        sed -i "/^DB_PASSWORD=/d" "$TARGET_ENV_FILE"
    fi
    
    echo "DB_USER=$user" >> "$TARGET_ENV_FILE"
    echo "DB_PASSWORD=$password" >> "$TARGET_ENV_FILE"
    
    log "SUCCESS" ".env updated: DB_USER=$user"
}

# Wait for process to start (check if process is running)
wait_process() {
    local PID="${1:-}"
    local NAME="${2:-}"
    local TIMEOUT=30
    local COUNT=0
    
    # Ensure PID is set
    PID="${PID:-}"
    NAME="${NAME:-}"
    
    # Ensure PID is set
    if [ -z "$PID" ]; then
        log "ERROR" "${NAME:-unknown}: PID not set"
        return 1
    fi
    
    # Check if process already exists
    if ps -p "$PID" > /dev/null 2>&1; then
        log "SUCCESS" "${NAME:-unknown} already running (PID: ${PID})"
        return 0
    fi
    
    log "INFO" "Waiting for ${NAME:-unknown} to start (PID: ${PID})..."
    while [ $COUNT -lt $TIMEOUT ]; do
        if ps -p "$PID" > /dev/null 2>&1; then
            log "SUCCESS" "${NAME:-unknown} started (PID: ${PID})"
            return 0
        fi
        sleep 1
        COUNT=$((COUNT + 1))
    done
    
    log "WARN" "${NAME:-unknown} start timeout (no process after ${TIMEOUT}s)"
            return 1
}

# Get PID of process and all its children
get_process_tree() {
    local PID=${1:-}
    local PIDS=""
    
    if [ -z "$PID" ] || ! ps -p "$PID" > /dev/null 2>&1; then
        echo ""
        return 0
    fi
    
    PIDS="$PID"
    
    # Recursively get child processes
    local CHILDREN=$(pgrep -P "$PID" 2>/dev/null || echo "")
    if [ -n "$CHILDREN" ]; then
        for CHILD in $CHILDREN; do
            GRANDCHILDREN=$(get_process_tree "$CHILD")
            if [ -n "$GRANDCHILDREN" ]; then
                PIDS="$PIDS $GRANDCHILDREN"
        fi
    done
    fi
    
    echo "$PIDS"
}

# Stop process and all its children
stop_process_tree() {
    local PID=${1:-}
    local NAME=${2:-}
    
    if [ -z "$PID" ] || ! ps -p "$PID" > /dev/null 2>&1; then
        return 0
    fi
    
    # Get all child processes
    local ALL_PIDS=$(get_process_tree "$PID")
    
    # Stop all children first (from leaf nodes)
    for P in $ALL_PIDS; do
        if [ "$P" != "$PID" ] && ps -p "$P" > /dev/null 2>&1; then
            kill "$P" 2>/dev/null || true
        fi
    done
    sleep 1
    
    # Stop main process
    kill "$PID" 2>/dev/null || true
    sleep 2
    
    # Check if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        log "WARN" "$NAME did not respond to SIGTERM, forcing stop in 3s..."
        sleep 3
        if ps -p "$PID" > /dev/null 2>&1; then
            log "WARN" "Force stopping $NAME and child processes..."
            # Force stop all processes
            for P in $ALL_PIDS; do
                if ps -p "$P" > /dev/null 2>&1; then
                    kill -9 "$P" 2>/dev/null || true
                fi
            done
        fi
    fi
    
    # Final check
    sleep 1
    if ! ps -p "$PID" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Find process PID by port
find_pid_by_port() {
    local PORT=$1
    local PID=""
    
    if command -v lsof &> /dev/null; then
        PID=$(lsof -ti:$PORT 2>/dev/null | head -n 1 || echo "")
    elif command -v netstat &> /dev/null; then
        PID=$(netstat -tlnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1 | head -n 1 || echo "")
    elif command -v ss &> /dev/null; then
        PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP "pid=\K\d+" | head -n 1 || echo "")
    fi
    
    echo "$PID"
}

# Extract backend port from log
get_backend_port() {
    local LOG_FILE=$1
    local PID_FILE="${2:-}"
    local DEFAULT_PORT=${3:-8000}
    local PORT=""
    
    # Prefer PID file to find actual running process port
    if [ -n "$PID_FILE" ] && [ -f "$PID_FILE" ]; then
        local PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        PID="${PID:-}"
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            PORT=$(find_port_by_pid "$PID")
            if [ -n "$PORT" ] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ]; then
                echo "$PORT"
                return
            fi
        fi
    fi
    
    # Extract from log (macOS-compatible)
    if [ -f "$LOG_FILE" ]; then
        # Format: 0.0.0.0:8000 or http://0.0.0.0:8000
        PORT_FROM_LOG=$(grep -E "(0\.0\.0\.0|localhost|127\.0\.0\.1):[0-9]+" "$LOG_FILE" 2>/dev/null | sed -n 's/.*\(0\.0\.0\.0\|localhost\|127\.0\.0\.1\):\([0-9]\+\).*/\2/p' | tail -n 1 || echo "")
        if [ -n "$PORT_FROM_LOG" ] && [ "$PORT_FROM_LOG" -ge 1 ] && [ "$PORT_FROM_LOG" -le 65535 ]; then
            PORT="$PORT_FROM_LOG"
        fi
    fi
    
    # Extract from .env file (if present)
    if [ -z "$PORT" ]; then
        if [ -f "${WORK_HOME}/agent-studio/.env" ]; then
            ENV_PORT=$(grep -E "^SERVER_PORT=|^PORT=" "${WORK_HOME}/agent-studio/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" | head -n 1 || echo "")
            if [ -n "$ENV_PORT" ] && [ "$ENV_PORT" -ge 1 ] && [ "$ENV_PORT" -le 65535 ]; then
                PORT="$ENV_PORT"
            fi
        fi
    fi
    
    # If none found, use default
    if [ -z "$PORT" ]; then
        PORT="$DEFAULT_PORT"
    fi
    
    echo "$PORT"
}

# Find port used by process (including children) by PID
find_port_by_pid() {
    local PID=$1
    local PORT=""
    
    if [ -z "$PID" ] || ! ps -p "$PID" > /dev/null 2>&1; then
        echo ""
        return
    fi
    
    # Use lsof to find listening port(s) of process (including children)
    if command -v lsof &> /dev/null; then
        # Find TCP listening port (including children)
        PORT=$(lsof -Pan -p "$PID" -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}' | sed 's/.*://' | head -n 1 || echo "")
        # If not found, try child process port (e.g. npm run dev)
        if [ -z "$PORT" ] && command -v pgrep &> /dev/null; then
            local CHILD_PIDS=$(pgrep -P "$PID" 2>/dev/null || echo "")
            for CHILD_PID in $CHILD_PIDS; do
                local CHILD_PORT=$(lsof -Pan -p "$CHILD_PID" -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1 {print $9}' | sed 's/.*://' | head -n 1 || echo "")
                if [ -n "$CHILD_PORT" ] && [ "$CHILD_PORT" -ge 1 ] && [ "$CHILD_PORT" -le 65535 ]; then
                    PORT="$CHILD_PORT"
                    break
                fi
            done
        fi
    fi
    
    echo "$PORT"
}

# Extract frontend port from log
get_frontend_port() {
    local LOG_FILE=$1
    local PID_FILE="${2:-}"
    local DEFAULT_PORT=${3:-3000}
    local PORT=""
    
    # Prefer PID file to find actual running process port
    if [ -n "$PID_FILE" ] && [ -f "$PID_FILE" ]; then
        local PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        PID="${PID:-}"
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            PORT=$(find_port_by_pid "$PID")
            if [ -n "$PORT" ] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ]; then
                echo "$PORT"
                return
            fi
        fi
    fi
    
    # Extract from log (macOS-compatible)
    if [ -f "$LOG_FILE" ]; then
        PORT_FROM_LOG=$(grep -E "(Local:|Network:|➜)" "$LOG_FILE" 2>/dev/null | sed -n 's/.*http:\/\/[^:]*:\([0-9]\+\).*/\1/p' | tail -n 1 || echo "")
        if [ -n "$PORT_FROM_LOG" ] && [ "$PORT_FROM_LOG" -ge 1 ] && [ "$PORT_FROM_LOG" -le 65535 ]; then
            PORT="$PORT_FROM_LOG"
        else
            PORT_FROM_LOG=$(grep -E ":[0-9]+/" "$LOG_FILE" 2>/dev/null | sed -n 's/.*:\([0-9]\+\).*/\1/p' | tail -n 1 || echo "")
            if [ -n "$PORT_FROM_LOG" ] && [ "$PORT_FROM_LOG" -ge 1000 ] && [ "$PORT_FROM_LOG" -le 65535 ]; then
                PORT="$PORT_FROM_LOG"
            fi
        fi
    fi
    
    # Extract from vite.config.js or package.json (if present)
    if [ -z "$PORT" ]; then
        if [ -f "${WORK_HOME}/agent-studio/frontend/vite.config.js" ] || [ -f "${WORK_HOME}/agent-studio/frontend/vite.config.ts" ]; then
            VITE_CONFIG="${WORK_HOME}/agent-studio/frontend/vite.config.js"
            [ ! -f "$VITE_CONFIG" ] && VITE_CONFIG="${WORK_HOME}/agent-studio/frontend/vite.config.ts"
            if [ -f "$VITE_CONFIG" ]; then
                CONFIG_PORT=$(grep -E "port:\s*[0-9]+" "$VITE_CONFIG" 2>/dev/null | sed -n 's/.*port:\s*\([0-9]\+\).*/\1/p' | head -n 1 || echo "")
                if [ -n "$CONFIG_PORT" ] && [ "$CONFIG_PORT" -ge 1 ] && [ "$CONFIG_PORT" -le 65535 ]; then
                    PORT="$CONFIG_PORT"
                fi
            fi
        fi
    fi
    
    # If none found, use default
    if [ -z "$PORT" ]; then
        PORT="$DEFAULT_PORT"
    fi
    
    echo "$PORT"
}

# Resolve service status (shared by check_status and deploy completion): set BACKEND_PID/BACKEND_PORT, FRONTEND_PID/FRONTEND_PORT, LOCAL_IP, *_LOG, *_PID_FILE
resolve_service_status() {
    BACKEND_PID_FILE="${WORK_HOME}/backend.pid"
    FRONTEND_PID_FILE="${WORK_HOME}/frontend.pid"
    BACKEND_LOG="${WORK_HOME}/backend.log"
    FRONTEND_LOG="${WORK_HOME}/frontend.log"
    
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1 || echo "localhost")
    if [ -z "$LOCAL_IP" ] || [ "$LOCAL_IP" = "127.0.0.1" ] || [ "$LOCAL_IP" = "localhost" ]; then
        LOCAL_IP=$(route get default 2>/dev/null | grep interface | awk '{print $2}' | xargs ifconfig 2>/dev/null | grep "inet " | awk '{print $2}' | head -n 1 || echo "localhost")
    fi
    LOCAL_IP="${LOCAL_IP:-localhost}"
    
    BACKEND_PORT=$(get_backend_port "$BACKEND_LOG" "$BACKEND_PID_FILE" "8000")
    FRONTEND_PORT=$(get_frontend_port "$FRONTEND_LOG" "$FRONTEND_PID_FILE" "3000")
    BACKEND_PID=""
    FRONTEND_PID=""
    
    # Backend: PID file -> port -> pgrep
    if [ -f "$BACKEND_PID_FILE" ]; then
        _pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")
        _pid="${_pid:-}"
        if [ -n "$_pid" ] && ps -p "$_pid" > /dev/null 2>&1; then
            if ps -p "$_pid" -o command= 2>/dev/null | grep -qE "(python.*main\.py|uvicorn|fastapi)" 2>/dev/null; then
                BACKEND_PID="$_pid"
            fi
        fi
    fi
    if [ -z "$BACKEND_PID" ]; then
        _port_pid=$(find_pid_by_port "$BACKEND_PORT")
        _port_pid="${_port_pid:-}"
        if [ -n "$_port_pid" ] && ps -p "$_port_pid" > /dev/null 2>&1; then
            if ps -p "$_port_pid" -o command= 2>/dev/null | grep -qE "(python.*main\.py|uvicorn|fastapi)" 2>/dev/null; then
                BACKEND_PID="$_port_pid"
                echo "$BACKEND_PID" > "$BACKEND_PID_FILE" 2>/dev/null || true
            fi
        fi
    fi
    if [ -z "$BACKEND_PID" ] && command -v pgrep &> /dev/null; then
        for _pid in $(pgrep -f "python.*main\.py|uvicorn.*main" 2>/dev/null | grep -v "^$$" || true); do
            if ps -p "$_pid" -o command= 2>/dev/null | grep -qE "(main\.py|uvicorn)" 2>/dev/null; then
                if ps -p "$_pid" -o command= 2>/dev/null | grep -q "$BACKEND_DIR" 2>/dev/null; then
                    BACKEND_PID="$_pid"
                    echo "$BACKEND_PID" > "$BACKEND_PID_FILE" 2>/dev/null || true
                    break
                fi
            fi
        done
    fi
    if [ -n "$BACKEND_PID" ] && ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        _actual=$(find_port_by_pid "$BACKEND_PID")
        if [ -n "$_actual" ] && [ "$_actual" -ge 1 ] && [ "$_actual" -le 65535 ]; then
            BACKEND_PORT="$_actual"
        fi
    fi
    
    # Frontend: PID file -> port -> pgrep
    if [ -f "$FRONTEND_PID_FILE" ]; then
        _pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
        _pid="${_pid:-}"
        if [ -n "$_pid" ] && ps -p "$_pid" > /dev/null 2>&1; then
            if ps -p "$_pid" -o command= 2>/dev/null | grep -qE "(node|vite|npm.*dev)" 2>/dev/null; then
                FRONTEND_PID="$_pid"
            fi
        fi
    fi
    if [ -z "$FRONTEND_PID" ]; then
        _port_pid=$(find_pid_by_port "$FRONTEND_PORT")
        _port_pid="${_port_pid:-}"
        if [ -n "$_port_pid" ] && ps -p "$_port_pid" > /dev/null 2>&1; then
            if ps -p "$_port_pid" -o command= 2>/dev/null | grep -qE "(node|vite|npm.*dev)" 2>/dev/null; then
                FRONTEND_PID="$_port_pid"
                echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE" 2>/dev/null || true
            fi
        fi
    fi
    if [ -z "$FRONTEND_PID" ] && command -v pgrep &> /dev/null; then
        for _pid in $(pgrep -f "npm.*dev|vite|node.*frontend" 2>/dev/null | grep -v "^$$" || true); do
            if ps -p "$_pid" -o command= 2>/dev/null | grep -qE "(frontend|vite|npm.*dev)" 2>/dev/null; then
                _node_port=$(find_pid_by_port "$FRONTEND_PORT")
                _node_port="${_node_port:-}"
                if [ -n "$_node_port" ] && [ "$_node_port" = "$_pid" ]; then
                    FRONTEND_PID="$_pid"
                    echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE" 2>/dev/null || true
                    break
                fi
            fi
        done
    fi
    if [ -n "$FRONTEND_PID" ] && ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
        _actual=$(find_port_by_pid "$FRONTEND_PID")
        if [ -n "$_actual" ] && [ "$_actual" -ge 1 ] && [ "$_actual" -le 65535 ]; then
            FRONTEND_PORT="$_actual"
        fi
    fi
}

# Check service status
check_status() {
    resolve_service_status
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Service status${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    echo -e "${YELLOW}Backend:${NC}"
    if [ -n "$BACKEND_PID" ] && ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        echo -e "  Status: ${GREEN}Running${NC}"
        echo -e "  PID: ${BACKEND_PID}"
        echo -e "  Port: ${BACKEND_PORT}"
        echo -e "  Local: ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
        echo -e "  Network: ${GREEN}http://${LOCAL_IP}:${BACKEND_PORT}${NC}"
        echo -e "  API docs: ${GREEN}http://localhost:${BACKEND_PORT}/api/docs${NC}"
        echo -e "  Health: ${GREEN}http://localhost:${BACKEND_PORT}/api/health${NC}"
    else
        echo -e "  Status: ${RED}Not running${NC}"
        if [ -f "$BACKEND_PID_FILE" ]; then
            _old=$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")
            _old="${_old:-}"
            [ -n "$_old" ] && echo -e "  Note: PID file exists but process not found (PID: ${_old})"
        else
            echo -e "  Note: PID file not found"
        fi
    fi
    echo ""
    
    echo -e "${YELLOW}Frontend:${NC}"
    if [ -n "$FRONTEND_PID" ] && ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
        echo -e "  Status: ${GREEN}Running${NC}"
        echo -e "  PID: ${FRONTEND_PID}"
        echo -e "  Port: ${FRONTEND_PORT}"
        echo -e "  Local: ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
        echo -e "  Network: ${GREEN}http://${LOCAL_IP}:${FRONTEND_PORT}${NC}"
    else
        echo -e "  Status: ${RED}Not running${NC}"
        if [ -f "$FRONTEND_PID_FILE" ]; then
            _old=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
            _old="${_old:-}"
            [ -n "$_old" ] && echo -e "  Note: PID file exists but process not found (PID: ${_old})"
        else
            echo -e "  Note: PID file not found"
        fi
    fi
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Log files:${NC}"
    [ -f "$BACKEND_LOG" ] && echo -e "  Backend: ${BACKEND_LOG}"
    [ -f "$FRONTEND_LOG" ] && echo -e "  Frontend: ${FRONTEND_LOG}"
    return 0
}

# Gracefully stop services
stop_services() {
    log "INFO" "===== Stopping services ====="

    # Reuse status resolution to get PID / port / log files etc.
    resolve_service_status

    # Initialize local variables to avoid set -u undefined errors
    local STOPPED=0
    local B_PID=""
    local B_PORT=""
    local B_PORT_PID=""
    local F_PID=""
    local F_PORT=""
    local F_PORT_PID=""

    # ---------- Stop backend service ----------
    B_PID="${BACKEND_PID:-}"
    B_PORT="${BACKEND_PORT:-8000}"

    # If PID not resolved, try finding by port
    if [ -z "${B_PID:-}" ] || ! ps -p "${B_PID:-}" > /dev/null 2>&1; then
        B_PORT_PID=$(find_pid_by_port "$B_PORT" 2>/dev/null || echo "")
        B_PORT_PID="${B_PORT_PID:-}"
        B_PID="$B_PORT_PID"
    fi

    if [ -n "${B_PID:-}" ] && ps -p "${B_PID:-}" > /dev/null 2>&1; then
        log "INFO" "Stopping backend (PID: ${B_PID:-})..."
        if stop_process_tree "${B_PID:-}" "Backend"; then
            log "SUCCESS" "Backend stopped (PID: ${B_PID:-})"
            [ -n "${BACKEND_PID_FILE:-}" ] && [ -f "$BACKEND_PID_FILE" ] && rm -f "$BACKEND_PID_FILE"
            STOPPED=$((STOPPED + 1))
        else
            log "ERROR" "Failed to stop backend (PID: ${B_PID:-})"
        fi
    else
        log "INFO" "No running backend found"
        [ -n "${BACKEND_PID_FILE:-}" ] && [ -f "$BACKEND_PID_FILE" ] && rm -f "$BACKEND_PID_FILE"
    fi

    # ---------- Stop frontend service ----------
    F_PID="${FRONTEND_PID:-}"
    F_PORT="${FRONTEND_PORT:-3000}"

    if [ -z "${F_PID:-}" ] || ! ps -p "${F_PID:-}" > /dev/null 2>&1; then
        F_PORT_PID=$(find_pid_by_port "$F_PORT" 2>/dev/null || echo "")
        F_PORT_PID="${F_PORT_PID:-}"
        F_PID="$F_PORT_PID"
    fi

    if [ -n "${F_PID:-}" ] && ps -p "${F_PID:-}" > /dev/null 2>&1; then
        log "INFO" "Stopping frontend (PID: ${F_PID:-})..."
        if stop_process_tree "${F_PID:-}" "Frontend"; then
            log "SUCCESS" "Frontend stopped (PID: ${F_PID:-})"
            [ -n "${FRONTEND_PID_FILE:-}" ] && [ -f "$FRONTEND_PID_FILE" ] && rm -f "$FRONTEND_PID_FILE"
            STOPPED=$((STOPPED + 1))
        else
            log "ERROR" "Failed to stop frontend (PID: ${F_PID:-})"
        fi
    else
        log "INFO" "No running frontend found"
        [ -n "${FRONTEND_PID_FILE:-}" ] && [ -f "$FRONTEND_PID_FILE" ] && rm -f "$FRONTEND_PID_FILE"
    fi

    if [ "$STOPPED" -gt 0 ]; then
        log "SUCCESS" "Stopped $STOPPED service(s)"
    else
        log "INFO" "No running services to stop"
    fi

    return 0
}

# ===================== Help =====================
show_help() {
    cat << EOF
Usage: ${0} [options]
One-step deploy Agent-Studio; supports DB type and code branch.

Options:
  --db_type=<type>    Database type: mysql (default), sqlite
                     - --db_type=mysql: set DB_TYPE in .env to mysql
                     - --db_type=sqlite: set DB_TYPE in .env to sqlite
  --branch=<name>     Git branch to fetch, default: main
                     - --branch=main: fetch main (default)
                     - --branch=develop: fetch develop
                     - --branch=<other>: fetch specified branch
  --stop              Gracefully stop backend and frontend
  --restart           Restart backend and frontend (no reinstall deps/keys)
  --status            Show service status and URLs
  --help              Show this help and exit

Examples:
  ${0}                           # Default: DB_TYPE=mysql, branch=main
  ${0} --db_type=sqlite           # Use sqlite, main branch
  ${0} --branch=develop           # Use mysql, develop branch
  ${0} --db_type=sqlite --branch=develop  # Use sqlite, develop branch
  ${0} --stop                     # Stop services
  ${0} --restart                  # Restart services
  ${0} --status                   # Show status and URLs
  ${0} --help                     # Show help

Work directory: ${WORK_HOME}
EOF
    exit 0
}

# ===================== Argument parsing =====================
DB_TYPE="mysql"
GIT_BRANCH="main"  # Default branch
ACTION="install"   # Default action: install and deploy

for arg in "$@"; do
    case "$arg" in
        --help)
            show_help
            ;;
        --stop)
            ACTION="stop"
            ;;
        --restart)
            ACTION="restart"
            ;;
        --status)
            ACTION="status"
            ;;
        --db_type=*)
            DB_TYPE="${arg#*=}"
            # Strict validation
            if [[ $DB_TYPE != "mysql" && $DB_TYPE != "sqlite" ]]; then
                error_exit "--db_type must be mysql or sqlite, got: $DB_TYPE"
            fi
            log "INFO" "Database type: $DB_TYPE"
            ;;
        --branch=*)
            GIT_BRANCH="${arg#*=}"
            # Basic validation: branch name must not be empty
            if [ -z "$GIT_BRANCH" ]; then
                error_exit "--branch value cannot be empty"
            fi
            log "INFO" "Branch: $GIT_BRANCH"
            ;;
        *)
            error_exit "Invalid argument '$arg'; use --help for usage"
            ;;
    esac
done

# Handle special actions (stop, restart, status)
if [ "$ACTION" = "stop" ]; then
    stop_services
    exit 0
fi

if [ "$ACTION" = "status" ]; then
    check_status
    exit 0
fi

if [ "$ACTION" = "restart" ]; then
    log "INFO" "===== Restarting services ====="
    stop_services
    log "INFO" "Waiting 2s before starting services..."
    sleep 2
    # Clear start-related progress for restart
    # Set progress to deploy complete so install steps are skipped and services start directly
    save_progress "deploy_frontend"
    LAST_PROGRESS="deploy_frontend"
    log "INFO" "Progress set to deploy_frontend; skipping install steps, starting services"
fi

# ===================== Pre-checks =====================
log "INFO" "===== Starting Agent-Studio deployment ====="
log "INFO" "Work directory: ${WORK_HOME}"
log "INFO" "Log file: ${LOG_FILE}"

# Initialize log file
echo "=========================================" >> "$LOG_FILE"
echo "Deployment start time: $(date)" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"

# Load all required environments (NVM, Conda, user PATH, etc.)
load_environments
log "INFO" "Environments loaded (NVM, Conda, user PATH)"

# Check basic commands
check_command "bash"
check_command "sed"
check_command "grep"
check_command "mkdir"

# Check and fix execute permission for required scripts
log "INFO" "Checking script permissions..."
for script in "check_curl.sh" "check_git.sh" "check_nodejs.sh" "check_python.sh" "fetch_codes.sh" "check_mysql.sh"; do
    if [ -f "${WORK_HOME}/${script}" ]; then
        check_script_permission "${WORK_HOME}/${script}"
    fi
done

# Check whether to resume from last interruption (restart mode skips prompt)
if [ "$ACTION" != "restart" ]; then
    LAST_PROGRESS=$(read_progress)
    if [ -n "$LAST_PROGRESS" ]; then
        log "WARN" "Resuming from previous progress: $LAST_PROGRESS"
        read -p "Resume from last interruption? (y/n, default y): " CONTINUE
        if [[ "${CONTINUE:-y}" != "y" ]]; then
            clear_progress
            LAST_PROGRESS=""  # Reset progress variable
            log "INFO" "Progress cleared, starting fresh"
        fi
    else
        LAST_PROGRESS=""
    fi
else
    # Restart mode: use set progress directly, no prompt
    LAST_PROGRESS=$(read_progress)
    if [ -z "$LAST_PROGRESS" ]; then
        LAST_PROGRESS="deploy_frontend"
    fi
    log "INFO" "Restart mode: skipping install steps, progress: $LAST_PROGRESS"
fi

# ===================== Install base tools =====================
STEP="check_tools"
# Restart mode skips all install steps
if [ "$ACTION" = "restart" ]; then
    log "INFO" "Skipping: base tools check (restart mode)"
elif [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
    log "INFO" "===== Checking base tools ====="
    # Run check scripts (simplified output, less repetition)
    for script in "check_curl.sh" "check_git.sh" "check_nodejs.sh" "check_python.sh"; do
        SCRIPT_PATH="${WORK_HOME}/${script}"
        check_file "$SCRIPT_PATH"
        
        # Run script directly, capture output and filter repetition
        if ! bash "$SCRIPT_PATH" > /tmp/setup_${script}.log 2>&1; then
            log "ERROR" "Failed to run $script"
            echo -e "${RED}Error details:${NC}"
            cat /tmp/setup_${script}.log
            rm -f /tmp/setup_${script}.log
            error_exit "Failed to run $script" \
                "1. Check script permission: chmod +x $SCRIPT_PATH\n\
2. Inspect script content for issues\n\
3. Run script manually to debug: bash $SCRIPT_PATH"
        else
            # On success show only key lines (filter repeated prompts and progress)
            if grep -qE "(已安装|安装成功|功能测试通过|未安装|安装失败|操作完成|installed|Install success|Test passed|not installed|Install failed|Done)" /tmp/setup_${script}.log 2>/dev/null; then
                # Show only key result lines, not process
                grep -E "(已安装|安装成功|功能测试通过|未安装|安装失败|installed|Install success|Test passed|not installed|Install failed)" /tmp/setup_${script}.log 2>/dev/null | head -2 || true
            else
                # If no key info, show last line
                tail -1 /tmp/setup_${script}.log 2>/dev/null || true
            fi
            rm -f /tmp/setup_${script}.log
        fi
    done
    save_progress "$STEP"
else
    log "INFO" "Skipping: base tools check (done)"
fi

# ===================== Fetch code =====================
STEP="fetch_code"
# Restart mode skips all install steps
if [ "$ACTION" = "restart" ]; then
    log "INFO" "Skipping: code fetch (restart mode)"
    # Still check if directory exists
    if [ ! -d "${WORK_HOME}/agent-studio" ]; then
        log "WARN" "Code directory missing, run full install first"
        error_exit "Code directory missing, cannot restart" \
            "Run full install first: ./setup.sh"
    fi
elif [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
log "INFO" "===== Fetching code ====="
    echo -e "${GREEN}[Progress] Base tools done, fetching code (branch: ${GIT_BRANCH})...${NC}"
FETCH_SCRIPT="${WORK_HOME}/fetch_codes.sh"
check_file "$FETCH_SCRIPT"
    
    if ! retry_execute 3 10 "Fetch code" "bash '$FETCH_SCRIPT' '$GIT_BRANCH'"; then
        error_exit "Code fetch failed" \
            "1. Check network: ping -c 3 gitcode.com\n\
2. Check Git config: git config --list\n\
3. Fetch manually: cd $WORK_HOME && bash $FETCH_SCRIPT"
    fi

# Check code directories
check_dir "${WORK_HOME}/agent-studio"
check_dir "$BACKEND_DIR"
check_dir "$FRONTEND_DIR"
    echo -e "${GREEN}[Progress] Code fetch done${NC}\n"
    save_progress "$STEP"
else
    log "INFO" "Skipping: code fetch (done)"
    # Still check if directory exists
    if [ ! -d "${WORK_HOME}/agent-studio" ]; then
        log "WARN" "Code directory missing, re-fetching..."
        LAST_PROGRESS=""
    fi
fi

# ===================== Configure AES key =====================
STEP="config_aes"
# Restart mode skips all install steps
if [ "$ACTION" = "restart" ]; then
    log "INFO" "Skipping AES config (restart mode)"
    # Try to restore key from env or .env if needed
    if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ] && [ -f "$TARGET_ENV_FILE" ]; then
        log "WARN" "AES key not set, will read from .env if present"
    fi
elif [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
log "INFO" "===== Configuring AES key ====="
    echo -e "${GREEN}[Progress] Configuring AES key...${NC}"
AES_SCRIPT="${WORK_HOME}/agent-studio/scripts/build_AES_master_key.sh"
check_file "$AES_SCRIPT"
log "INFO" "Running AES key script: $AES_SCRIPT"
    
    # Run script and get key, with retry
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
3. Run script manually: bash $AES_SCRIPT\n\
4. Inspect script: cat $AES_SCRIPT"
    fi
    
export SERVER_AES_MASTER_KEY_ENV="$your_aes_key"
    log "SUCCESS" "AES key set: ${your_aes_key:0:8}**** (masked)"
    save_progress "$STEP"
else
    log "INFO" "Skipping: AES key config (done)"
    # Try to restore key from env or .env if needed
    if [ -z "${SERVER_AES_MASTER_KEY_ENV:-}" ] && [ -f "$TARGET_ENV_FILE" ]; then
        log "WARN" "AES key not set, will read from .env if present"
    fi
fi

# ===================== Configure .env =====================
STEP="config_env"
# Restart mode skips all install steps
if [ "${ACTION:-install}" = "restart" ]; then
    log "INFO" "Skipping .env config (restart mode)"
elif [[ "${LAST_PROGRESS:-}" != "${STEP:-config_env}"* ]] || [[ -z "${LAST_PROGRESS:-}" ]]; then
    log "INFO" "===== Configuring .env ====="
    echo -e "${GREEN}[Progress] AES done, configuring .env...${NC}"
    
    # Copy example file (backup before overwrite)
    check_file "$ENV_EXAMPLE_FILE"
    if [ -f "$TARGET_ENV_FILE" ]; then
        BACKUP_ENV="${TARGET_ENV_FILE}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$TARGET_ENV_FILE" "$BACKUP_ENV" || log "WARN" "Failed to backup .env, continuing"
        log "INFO" "Backed up .env to: $BACKUP_ENV"
    fi
    
    if ! cp "$ENV_EXAMPLE_FILE" "$TARGET_ENV_FILE" 2>/dev/null; then
        error_exit "Failed to copy .env.example" \
            "1. Check file permission: ls -l $ENV_EXAMPLE_FILE\n\
2. Check target dir: ls -ld $(dirname $TARGET_ENV_FILE)\n\
3. Copy manually: cp $ENV_EXAMPLE_FILE $TARGET_ENV_FILE"
    fi
    check_file "$TARGET_ENV_FILE"

    # Replace DB_TYPE (Linux/macOS compatible sed)
    OLD_MYSQL="DB_TYPE=mysql"
    NEW_SQLITE="DB_TYPE=sqlite"
    DB_TYPE_VALUE="${DB_TYPE:-mysql}"
    log "INFO" "Setting DB type: $DB_TYPE_VALUE"
    
    if [ "$DB_TYPE_VALUE" = "sqlite" ]; then
        # Linux: sed -i, macOS: sed -i ''
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|${OLD_MYSQL}|${NEW_SQLITE}|g" "$TARGET_ENV_FILE"
        else
            sed -i "s|${OLD_MYSQL}|${NEW_SQLITE}|g" "$TARGET_ENV_FILE"
        fi
    else
        # Ensure mysql (replace if file had sqlite)
        if [[ "$(uname -s)" == "Darwin" ]]; then
            sed -i '' "s|${NEW_SQLITE}|${OLD_MYSQL}|g" "$TARGET_ENV_FILE"
        else
            sed -i "s|${NEW_SQLITE}|${OLD_MYSQL}|g" "$TARGET_ENV_FILE"
        fi
    fi

    # Verify replacement result
    DB_TYPE_ACTUAL_VALUE="not_found"  # Default to avoid set -u error
    if [ -f "$TARGET_ENV_FILE" ]; then
        TEMP_RESULT=$(grep '^DB_TYPE=' "$TARGET_ENV_FILE" 2>/dev/null | cut -d'=' -f2 || true)
        if [ -n "${TEMP_RESULT:-}" ]; then
            DB_TYPE_ACTUAL_VALUE="$TEMP_RESULT"
        fi
    fi
    
    # Ensure variable is set to avoid log expansion error
    DB_TYPE_ACTUAL_VALUE="${DB_TYPE_ACTUAL_VALUE:-not_found}"
    DB_TYPE_VALUE="${DB_TYPE_VALUE:-mysql}"
    
    if [ "$DB_TYPE_ACTUAL_VALUE" != "$DB_TYPE_VALUE" ]; then
        WARN_MSG="DB_TYPE may not have taken effect, current: ${DB_TYPE_ACTUAL_VALUE} (expected: ${DB_TYPE_VALUE})"
        log "WARN" "$WARN_MSG"
    else
        SUCCESS_MSG="DB_TYPE configured: ${DB_TYPE_VALUE}"
        log "SUCCESS" "$SUCCESS_MSG"
    fi
    save_progress "${STEP:-config_env}"
else
    log "INFO" "Skipping: .env config (done)"
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

# ===================== Deploy backend =====================
STEP="deploy_backend"
# Restart mode skips deps install but must have venv
if [ "$ACTION" = "restart" ]; then
    log "INFO" "Skipping backend deps install (restart mode)"
    # Check if virtual environment exists
    if [ ! -f "${BACKEND_DIR}/.venv/bin/activate" ]; then
        log "ERROR" "Backend venv missing, cannot restart"
        error_exit "Backend venv missing, cannot restart" \
            "Run full install first: ./setup.sh"
    fi
    cd "$BACKEND_DIR" 2>/dev/null || log "WARN" "Cannot enter backend dir, continuing"
elif [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
log "INFO" "===== Deploying backend ====="
    echo -e "${GREEN}[Progress] .env done, deploying backend...${NC}"
    
    if ! cd "$BACKEND_DIR" 2>/dev/null; then
        error_exit "Failed to enter backend dir: $BACKEND_DIR" \
            "Check that code was fetched: ls -la $WORK_HOME/agent-studio"
    fi

# Install uv and create virtual environment
    # Ensure environment is loaded (especially conda)
    load_environments
    
    # Ensure Python is available and use PYTHON_CMD
    ensure_python_compatible
    
    log "INFO" "Installing uv (using ${PYTHON_CMD} -m pip)"
    if ! retry_execute 3 10 "Install uv" "${PYTHON_CMD} -m pip install uv --user"; then
        log "WARN" "User install failed, trying global (may need sudo)"
        if ! retry_execute 2 5 "Install uv globally" "${PYTHON_CMD} -m pip install uv"; then
            error_exit "uv install failed" \
                "1. Check network\n\
2. Check pip: ${PYTHON_CMD} -m pip --version\n\
3. Install manually: ${PYTHON_CMD} -m pip install uv"
        fi
    fi
    
    # Ensure uv is in PATH
    check_command "uv"
    log "INFO" "uv installed: $(uv --version 2>/dev/null || echo 'unknown')"
    
    log "INFO" "Creating/checking uv venv (using ${PYTHON_CMD})"
    
    # Avoid uv interactive prompt to replace .venv; clean if dir exists
    if [ -d ".venv" ]; then
        log "INFO" "Existing venv detected, recreating..."
        if rm -rf .venv 2>/dev/null; then
            log "SUCCESS" "Old venv removed"
        else
            log "WARN" "Could not remove old venv; run: rm -rf ${BACKEND_DIR}/.venv"
        fi
    fi
    
    # Use --python to specify compatible Python, avoid system default python3
    if ! retry_execute 2 5 "Create venv" "uv venv --python \"${PYTHON_CMD}\""; then
        error_exit "Failed to create venv" \
            "1. Check Python: ${PYTHON_CMD} --version\n\
2. Check disk: df -h\n\
3. Check dir permission: ls -ld ${BACKEND_DIR}\n\
4. Create manually: cd $BACKEND_DIR && uv venv --python \"${PYTHON_CMD}\""
    fi
    
    log "INFO" "Syncing dependencies (may take a few minutes)..."
    if ! retry_execute 3 30 "Sync deps" "uv sync"; then
        error_exit "Dependency sync failed" \
            "1. Check network\n\
2. Check disk: df -h\n\
3. On repeated failure try: rm -rf ${BACKEND_DIR}/.venv && cd ${BACKEND_DIR} && uv venv --python \"${PYTHON_CMD}\" && uv sync\n\
4. See errors: cd $BACKEND_DIR && uv sync"
    fi

    # Check and install greenlet (Apple Silicon Mac compatibility)
    check_and_install_greenlet "$BACKEND_DIR"

# Create log directory
    if ! mkdir -p logs/run 2>/dev/null; then
        error_exit "Failed to create backend log dir" \
            "Check dir permission: ls -ld $BACKEND_DIR"
    fi
    save_progress "$STEP"
else
    log "INFO" "Skipping backend deploy (already done)"
    cd "$BACKEND_DIR" 2>/dev/null || log "WARN" "Cannot enter backend dir, continuing"
fi

# Before starting backend, check DB config (MySQL mode)
if [ "${DB_TYPE:-mysql}" = "mysql" ] && [ "${ACTION:-install}" != "restart" ]; then
    log "INFO" "===== Checking MySQL config ====="
    
    # Check .env file
    if [ ! -f "$TARGET_ENV_FILE" ]; then
        error_exit ".env file not found" \
            "Ensure .env is configured: $TARGET_ENV_FILE"
    fi
    
    # 1. Check if MySQL is installed
    MYSQL_CMD_BIN=""
    MYSQL_CMD_BIN=$(find_mysql_command)
    if [ -z "${MYSQL_CMD_BIN:-}" ]; then
        log "WARN" "MySQL not found"
        echo ""
        echo -e "${YELLOW}MySQL not installed, will try Homebrew...${NC}"
        log "INFO" "Installing MySQL via Homebrew..."
        if install_mysql_with_homebrew; then
            log "SUCCESS" "MySQL installed"
            # Find MySQL command again
            MYSQL_CMD_BIN=$(find_mysql_command)
            if [ -z "${MYSQL_CMD_BIN:-}" ]; then
                error_exit "MySQL installed but command not available; reopen terminal or check PATH" \
                    "1. Reopen terminal and re-run\n2. Or check: which mysql"
            fi
        else
            error_exit "MySQL auto-install failed" \
                "1. Check network\n2. Install manually: brew install mysql\n3. Re-run script after install"
        fi
    else
        log "SUCCESS" "MySQL installed (path: ${MYSQL_CMD_BIN})"
    fi
    
    # Read DB config (using read_env_value)
    DB_HOST=$(read_env_value "DB_HOST" "localhost")
    DB_PORT=$(read_env_value "DB_PORT" "3306")
    DB_USER=$(read_env_value "DB_USER" "")
    DB_PASSWORD=$(read_env_value "DB_PASSWORD" "")
    DB_NAME=$(read_env_value "DB_NAME" "openjiuwen_agent")
    
    # Check if config is needed
    NEED_CONFIG=false
    CONFIG_REASON=""
    
    # 2. Check if MySQL service is running
    if ! check_mysql_service; then
        log "WARN" "MySQL service not running"
        NEED_CONFIG=true
        CONFIG_REASON="MySQL service not running"
    else
        log "SUCCESS" "MySQL service is running"
        
        # 3. Check if config is placeholder
        if [ -z "$DB_USER" ] || [ "$DB_USER" = "your_user_name" ] || \
           [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "your_password" ]; then
            NEED_CONFIG=true
            CONFIG_REASON="DB config not set (placeholder or empty)"
            log "WARN" "$CONFIG_REASON"
        else
            # 4. Config not placeholder, test connection
            log "INFO" "DB config set, testing MySQL connection..."
            if ! test_mysql_connection "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"; then
                NEED_CONFIG=true
                CONFIG_REASON="MySQL connection test failed (user missing or wrong password)"
                log "WARN" "$CONFIG_REASON"
            else
                log "SUCCESS" "MySQL connection OK"
            fi
        fi
    fi
    
    # If config needed, run config flow (auto, no prompt)
    if [ "$NEED_CONFIG" = true ]; then
        log "INFO" "MySQL config incorrect, auto-configuring..."
        if ! configure_mysql_database; then
            error_exit "MySQL config failed" \
                "Configure DB manually or run: bash ${WORK_HOME}/check_mysql.sh"
        fi
    fi
fi

# Start backend (background, redirect output, record PID)
STEP="start_backend"
if [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
BACKEND_LOG="${WORK_HOME}/backend.log"
BACKEND_PID_FILE="${WORK_HOME}/backend.pid"
    
    # Check greenlet again before start (so restart mode also checks)
    check_and_install_greenlet "$BACKEND_DIR"
    
    # Check if backend process already running
    OLD_PID=""
    if [ -f "$BACKEND_PID_FILE" ]; then
        OLD_PID=$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")
        OLD_PID="${OLD_PID:-}"
        if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
            log "WARN" "Backend already running (PID: ${OLD_PID}), skipping start"
            save_progress "$STEP"
        else
            log "INFO" "Cleaning old PID file"
            rm -f "$BACKEND_PID_FILE"
        fi
    fi
    
    if [ ! -f "$BACKEND_PID_FILE" ] || ! ps -p "$(cat "$BACKEND_PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
log "INFO" "Starting backend, log: $BACKEND_LOG"
        cd "$BACKEND_DIR" || error_exit "Cannot enter backend dir"
        
        if [ ! -f ".venv/bin/activate" ]; then
            error_exit "Venv not found" \
                "Re-run script or create manually: cd $BACKEND_DIR && uv venv"
        fi
        
        # Test MySQL connection before starting backend (if MySQL mode)
        if [ "${DB_TYPE:-mysql}" = "mysql" ]; then
            log "INFO" "Testing MySQL before starting backend..."
            DB_HOST=$(read_env_value "DB_HOST" "localhost" "$TARGET_ENV_FILE")
            DB_PORT=$(read_env_value "DB_PORT" "3306" "$TARGET_ENV_FILE")
            DB_USER=$(read_env_value "DB_USER" "" "$TARGET_ENV_FILE")
            DB_PASSWORD=$(read_env_value "DB_PASSWORD" "" "$TARGET_ENV_FILE")
            
            if [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then
                if ! test_mysql_connection "$DB_USER" "$DB_PASSWORD" "$DB_HOST" "$DB_PORT"; then
                    log "ERROR" "MySQL connection test failed, cannot start backend"
                    error_exit "MySQL connection test failed" \
                        "Check DB config: cat ${TARGET_ENV_FILE} | grep -E '^DB_'"
                else
                    log "SUCCESS" "MySQL connection OK"
                fi
            else
                log "WARN" "DB user/password not set, skipping connection test"
            fi
        fi
        
        source .venv/bin/activate || error_exit "Failed to activate venv"
        
        # Set environment variables
        if [ -n "${SERVER_AES_MASTER_KEY_ENV:-}" ]; then
            export SERVER_AES_MASTER_KEY_ENV
        fi
        
python main.py > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
if [ -z "$BACKEND_PID" ]; then
    log "ERROR" "Could not get backend PID"
    error_exit "Backend failed to start" "See log: $BACKEND_LOG"
fi
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
        
        # Wait for app to start
        sleep 3

        # Check backend process status
        BACKEND_PID="${BACKEND_PID:-}"
        if [ -z "$BACKEND_PID" ]; then
            log "ERROR" "Backend PID not set"
            error_exit "Backend failed to start" "See log: $BACKEND_LOG"
        fi
        
        # Check if process still running
        if ! ps -p "$BACKEND_PID" > /dev/null 2>&1; then
            log "ERROR" "Backend process exited"
            if [ -f "$BACKEND_LOG" ]; then
                log "ERROR" "Backend log (last 10 lines):"
                tail -n 10 "$BACKEND_LOG" 2>/dev/null || true
            fi
            rm -f "$BACKEND_PID_FILE"
            error_exit "Backend failed to start" "See: tail -n 10 ${BACKEND_LOG}"
        fi
        
        # Check log for startup failure
        if [ -f "$BACKEND_LOG" ]; then
            if grep -q "Application startup failed" "$BACKEND_LOG" 2>/dev/null; then
                log "ERROR" "Backend start failed (error detected)"
                log "ERROR" "Backend log (last 10 lines):"
                tail -n 10 "$BACKEND_LOG" 2>/dev/null || true
                
                # Stop the started process
                if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
                    kill "$BACKEND_PID" 2>/dev/null || true
                    sleep 1
                    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
                        kill -9 "$BACKEND_PID" 2>/dev/null || true
                    fi
                fi
                rm -f "$BACKEND_PID_FILE"
                error_exit "Backend failed to start" "See: tail -n 10 ${BACKEND_LOG}"
            fi
        fi
        
        # Check process again (may exit right after start)
        sleep 2
        if ! ps -p "$BACKEND_PID" > /dev/null 2>&1; then
            # Parent may have exited but child still running
            # Try to find actual backend process by port
            log "WARN" "Initial PID exited, looking for actual backend process..."
            
            # Get backend port
            BACKEND_PORT=$(get_backend_port "$BACKEND_LOG" "$BACKEND_PID_FILE" "8000")
            ACTUAL_PID=$(find_pid_by_port "$BACKEND_PORT")
            
            if [ -n "$ACTUAL_PID" ] && ps -p "$ACTUAL_PID" > /dev/null 2>&1; then
                # Check if it is backend service process
                if ps -p "$ACTUAL_PID" -o command= 2>/dev/null | grep -qE "(python.*main\.py|uvicorn|fastapi)" 2>/dev/null; then
                    log "SUCCESS" "Found backend process (PID: ${ACTUAL_PID}, was: ${BACKEND_PID})"
                    BACKEND_PID="$ACTUAL_PID"
                    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
                else
                    log "ERROR" "Backend exited and no valid process found"
                    if [ -f "$BACKEND_LOG" ]; then
                        log "ERROR" "Backend log (last 10 lines):"
                        tail -n 10 "$BACKEND_LOG" 2>/dev/null || true
                    fi
                    rm -f "$BACKEND_PID_FILE"
                    error_exit "Backend failed to start" "See: tail -n 10 ${BACKEND_LOG}"
                fi
            else
                # Try to find child via process tree
                if command -v pgrep &> /dev/null; then
                    # Find python processes that may be backend
                    PYTHON_PIDS=$(pgrep -f "python.*main\.py|uvicorn.*main" 2>/dev/null | grep -v "^$$" || echo "")
                    for PYTHON_PID in $PYTHON_PIDS; do
                        if ps -p "$PYTHON_PID" -o command= 2>/dev/null | grep -qE "(main\.py|uvicorn)" 2>/dev/null; then
                            # Check if process cwd is backend dir
                            if ps -p "$PYTHON_PID" -o command= 2>/dev/null | grep -q "$BACKEND_DIR" 2>/dev/null; then
                                log "SUCCESS" "Found backend via process (PID: ${PYTHON_PID}, was: ${BACKEND_PID})"
                                BACKEND_PID="$PYTHON_PID"
                                echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
                                break
                            fi
                        fi
                    done
                fi
                
                # If still not found, check log to confirm startup failure
                if ! ps -p "$BACKEND_PID" > /dev/null 2>&1; then
                    log "ERROR" "Backend exited and no valid process found"
                    if [ -f "$BACKEND_LOG" ]; then
                        log "ERROR" "Backend log (last 10 lines):"
                        tail -n 10 "$BACKEND_LOG" 2>/dev/null || true
                    fi
                    rm -f "$BACKEND_PID_FILE"
                    error_exit "Backend failed to start" "See: tail -n 10 ${BACKEND_LOG}"
                fi
            fi
        fi
        
        log "SUCCESS" "Backend started (PID: ${BACKEND_PID})"
        save_progress "$STEP"
    fi
else
    log "INFO" "Skipping: backend start (done)"
fi

# ===================== Deploy frontend =====================
STEP="deploy_frontend"
# Restart mode skips frontend deps install
if [ "$ACTION" = "restart" ]; then
    log "INFO" "Skipping frontend deps install (restart mode)"
    # Check if node_modules exists
    if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
        log "ERROR" "Frontend deps not installed, cannot restart"
        error_exit "Frontend deps not installed, cannot restart" \
            "Run full install first: ./setup.sh"
    fi
    cd "$FRONTEND_DIR" 2>/dev/null || log "WARN" "Cannot enter frontend dir, continuing"
elif [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]]; then
log "INFO" "===== Deploying frontend ====="
    echo -e "${GREEN}[Progress] Backend done, deploying frontend...${NC}"
    
    if ! cd "$FRONTEND_DIR" 2>/dev/null; then
        error_exit "Failed to enter frontend dir: $FRONTEND_DIR" \
            "Check that code was fetched: ls -la $WORK_HOME/agent-studio"
    fi

# Ensure environment loaded (double-check)
load_environments

# Check node/npm (check_command loads env)
check_command "node"
check_command "npm"

    log "INFO" "Installing frontend deps (may take a few minutes)..."
    if ! retry_execute 3 30 "Install frontend deps" "npm install"; then
        error_exit "Frontend deps install failed" \
            "1. Check network\n\
2. Clear npm cache and retry: npm cache clean --force && npm install\n\
3. Check disk: df -h\n\
4. Install manually: cd $FRONTEND_DIR && npm install"
    fi
    save_progress "$STEP"
else
    log "INFO" "Skipping frontend deps install (already done)"
    cd "$FRONTEND_DIR" 2>/dev/null || log "WARN" "Cannot enter frontend dir, continuing"
fi

# Start frontend
STEP="start_frontend"
if [[ "$LAST_PROGRESS" != "$STEP"* ]] || [[ -z "$LAST_PROGRESS" ]] || [[ "$ACTION" = "restart" ]]; then
FRONTEND_LOG="${WORK_HOME}/frontend.log"
FRONTEND_PID_FILE="${WORK_HOME}/frontend.pid"
    
    # Initialize OLD_PID (avoid set -u error)
    OLD_PID=""
    
    # If restart, ensure process is stopped
    if [ "$ACTION" = "restart" ]; then
        if [ -f "$FRONTEND_PID_FILE" ]; then
            OLD_PID=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
            OLD_PID="${OLD_PID:-}"
            if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
                log "WARN" "Frontend still running (PID: ${OLD_PID}), stopping..."
                kill "${OLD_PID}" 2>/dev/null || true
                sleep 2
                if ps -p "${OLD_PID}" > /dev/null 2>&1; then
                    kill -9 "${OLD_PID}" 2>/dev/null || true
                fi
            fi
            rm -f "$FRONTEND_PID_FILE"
        fi
    fi
    
    # Check if frontend process already running
    OLD_PID=""
    if [ -f "$FRONTEND_PID_FILE" ]; then
        OLD_PID=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
        OLD_PID="${OLD_PID:-}"
        if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
            log "WARN" "Frontend already running (PID: ${OLD_PID}), skipping start"
            save_progress "$STEP"
        else
            log "INFO" "Cleaning old PID file"
            rm -f "$FRONTEND_PID_FILE"
        fi
    fi
    
    if [ ! -f "$FRONTEND_PID_FILE" ] || ! ps -p "$(cat "$FRONTEND_PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
log "INFO" "Starting frontend, log: $FRONTEND_LOG"
        cd "$FRONTEND_DIR" || error_exit "Cannot enter frontend dir"
        
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
if [ -z "$FRONTEND_PID" ]; then
    log "ERROR" "Could not get frontend PID"
    error_exit "Frontend failed to start" "See: $FRONTEND_LOG"
fi
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
        
        # Wait a bit for process to start
        sleep 3

# Check frontend process
        FRONTEND_PID="${FRONTEND_PID:-}"
        if [ -z "$FRONTEND_PID" ]; then
            log "ERROR" "Frontend PID undefined"
            error_exit "Frontend failed to start" "See: $FRONTEND_LOG"
        fi
        if ! wait_process "$FRONTEND_PID" "Frontend"; then
            log "WARN" "Frontend start status abnormal, see: $FRONTEND_LOG"
            log "WARN" "Last 10 lines:"
            tail -n 10 "$FRONTEND_LOG" 2>/dev/null || true
        else
            FRONTEND_PID="${FRONTEND_PID:-}"
            if [ -n "$FRONTEND_PID" ]; then
                log "SUCCESS" "Frontend started (PID: ${FRONTEND_PID})"
            else
                log "SUCCESS" "Frontend started"
            fi
        fi
        save_progress "$STEP"
    fi
else
    log "INFO" "Skipping frontend start (already done)"
fi

log "SUCCESS" "========================================="
log "SUCCESS" "===== Deployment complete ====="
log "SUCCESS" "========================================="

# Reuse status resolution logic
resolve_service_status

# Script absolute path (for management commands)
SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
[ ! -f "$SCRIPT_PATH" ] && SCRIPT_PATH="${0}"
[[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)/$(basename "$SCRIPT_PATH")"

# Show backend (same as status: local/network, PID, port, log)
log "SUCCESS" "Backend:"
log "SUCCESS" "  - Local: http://localhost:$BACKEND_PORT"
log "SUCCESS" "  - Network: http://$LOCAL_IP:$BACKEND_PORT"

log "SUCCESS" "Frontend:"
log "SUCCESS" "  - Local: http://localhost:$FRONTEND_PORT"
log "SUCCESS" "  - Network: http://$LOCAL_IP:$FRONTEND_PORT"
log "SUCCESS" ""

# Clear progress file
clear_progress

log "SUCCESS" "Full log: $LOG_FILE"
log "SUCCESS" "========================================="

exit 0
