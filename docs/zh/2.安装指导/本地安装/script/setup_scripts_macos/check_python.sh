#!/bin/bash
# Script name: install_and_check_python311.sh (macOS version)
# Function: Check if Python 3.11 is installed, install via Homebrew if not

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PYTHON_VERSION="3.11"

# Detect Homebrew installation location
detect_homebrew_prefix() {
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo "/opt/homebrew"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        echo "/usr/local"
    else
        # Try to get from brew command
        if command -v brew &> /dev/null; then
            brew --prefix 2>/dev/null || echo "/usr/local"
        else
            echo "/usr/local"
        fi
    fi
}

# Fix Homebrew environment variable configuration
fix_homebrew_env() {
    echo -e "${YELLOW}Checking and fixing Homebrew environment configuration...${NC}"
    
    # Detect actual Homebrew location
    ACTUAL_PREFIX=""
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        ACTUAL_PREFIX="/opt/homebrew"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        ACTUAL_PREFIX="/usr/local"
    else
        return 1
    fi
    
    # Check if environment variables are consistent
    CURRENT_PREFIX="${HOMEBREW_PREFIX:-}"
    CURRENT_CELLAR="${HOMEBREW_CELLAR:-}"
    
    # If environment variables are inconsistent, reset them
    if [ -n "$CURRENT_PREFIX" ] && [ "$CURRENT_PREFIX" != "$ACTUAL_PREFIX" ]; then
        echo -e "${YELLOW}Detected inconsistent Homebrew environment variables, fixing...${NC}"
        echo -e "${YELLOW}  HOMEBREW_PREFIX: $CURRENT_PREFIX -> $ACTUAL_PREFIX${NC}"
    fi
    
    if [ -n "$CURRENT_CELLAR" ] && [ "$CURRENT_CELLAR" != "$ACTUAL_PREFIX/Cellar" ]; then
        echo -e "${YELLOW}  HOMEBREW_CELLAR: $CURRENT_CELLAR -> $ACTUAL_PREFIX/Cellar${NC}"
    fi
    
    # Reset environment variables
    export HOMEBREW_PREFIX="$ACTUAL_PREFIX"
    export HOMEBREW_CELLAR="$ACTUAL_PREFIX/Cellar"
    export HOMEBREW_REPOSITORY="$ACTUAL_PREFIX"
    export PATH="$ACTUAL_PREFIX/bin:$ACTUAL_PREFIX/sbin:$PATH"
    
    # Reload shellenv
    if [[ -f "$ACTUAL_PREFIX/bin/brew" ]]; then
        eval "$($ACTUAL_PREFIX/bin/brew shellenv)"
        echo -e "${GREEN}✅ Homebrew environment fixed${NC}"
        return 0
    fi
    
    return 1
}

check_python_installed() {
    # Check python3.11 command
    if command -v python${PYTHON_VERSION} &> /dev/null; then
        return 0
    fi
    # Check python3 version
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        if [ "$PYTHON_VER" = "${PYTHON_VERSION}" ]; then
            return 0
        fi
    fi
    # Check Python installed via pyenv
    if [ -d "$HOME/.pyenv" ]; then
        PYENV_PYTHON="$HOME/.pyenv/versions/${PYTHON_VERSION}/bin/python3"
        if [ -f "$PYENV_PYTHON" ] && "$PYENV_PYTHON" --version &> /dev/null; then
            return 0
        fi
    fi
    # Check Python installed via Homebrew
    HOMEBREW_PREFIX=$(detect_homebrew_prefix)
    PYTHON_PATH="${HOMEBREW_PREFIX}/opt/python@${PYTHON_VERSION}/bin/python3"
    if [ -f "$PYTHON_PATH" ] && "$PYTHON_PATH" --version &> /dev/null; then
        return 0
    fi
    return 1
}

check_pip_installed() {
    # Prefer python3.11
    if command -v python${PYTHON_VERSION} &> /dev/null; then
        if python${PYTHON_VERSION} -m pip --version &> /dev/null; then
            return 0
        fi
    fi
    # Fallback to python3
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        if [ "$PYTHON_VER" = "${PYTHON_VERSION}" ]; then
            if python3 -m pip --version &> /dev/null; then
                return 0
            fi
        fi
    fi
    # Check Python installed via pyenv
    if [ -d "$HOME/.pyenv" ]; then
        PYENV_PYTHON="$HOME/.pyenv/versions/${PYTHON_VERSION}/bin/python3"
        if [ -f "$PYENV_PYTHON" ] && "$PYENV_PYTHON" -m pip --version &> /dev/null; then
            return 0
        fi
    fi
    # Try to get from Homebrew path
    HOMEBREW_PREFIX=$(detect_homebrew_prefix)
    PYTHON_PATH="${HOMEBREW_PREFIX}/opt/python@${PYTHON_VERSION}/bin/python3"
    if [ -f "$PYTHON_PATH" ]; then
        if "$PYTHON_PATH" -m pip --version &> /dev/null; then
            return 0
        fi
    fi
    return 1
}

# Fix pkg-config link issues
fix_pkgconfig_link() {
    echo -e "${YELLOW}Checking and fixing pkg-config link issues...${NC}"
    
    # Check if pkg-config is installed but not linked
    if brew list pkgconf &> /dev/null 2>&1; then
        if ! brew link pkgconf &> /dev/null 2>&1; then
            echo -e "${YELLOW}Attempting to fix pkg-config link...${NC}"
            # Try force linking
            brew link --overwrite pkgconf 2>&1 | grep -v "Warning" || true
            # If still fails, try manual symbolic link creation (Apple Silicon only)
            HOMEBREW_PREFIX=$(detect_homebrew_prefix)
            if [ "$HOMEBREW_PREFIX" = "/opt/homebrew" ]; then
                echo -e "${YELLOW}Using manual method to fix link...${NC}"
                # Don't force creation, let Homebrew handle it
            fi
        fi
    fi
}

# Install Python using pyenv (alternative method)
install_python_with_pyenv() {
    echo -e "${YELLOW}Attempting to install Python${PYTHON_VERSION} using pyenv...${NC}"
    
    # Check if pyenv is installed
    if ! command -v pyenv &> /dev/null; then
        echo -e "${YELLOW}pyenv not installed, installing...${NC}"
        
        # Install pyenv
        if [ -d "$HOME/.pyenv" ]; then
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PATH"
        else
            # Use Homebrew to install pyenv (if available)
            if command -v brew &> /dev/null; then
                HOMEBREW_PREFIX=$(detect_homebrew_prefix)
                if fix_homebrew_env; then
                    brew install pyenv || {
                        echo -e "${YELLOW}Failed to install pyenv via Homebrew, trying manual installation...${NC}"
                        curl -fsSL https://pyenv.run | bash || {
                            echo -e "${RED}❌ pyenv installation failed${NC}"
                            return 1
                        }
                    }
                else
                    curl -fsSL https://pyenv.run | bash || {
                        echo -e "${RED}❌ pyenv installation failed${NC}"
                        return 1
                    }
                fi
            else
                curl -fsSL https://pyenv.run | bash || {
                    echo -e "${RED}❌ pyenv installation failed${NC}"
                    return 1
                }
            fi
            
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PATH"
        fi
        
        # Initialize pyenv
        if [ -f "$PYENV_ROOT/bin/pyenv" ]; then
            eval "$(pyenv init -)"
        else
            echo -e "${RED}❌ pyenv initialization failed${NC}"
            return 1
        fi
    else
        # Initialize pyenv
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)" 2>/dev/null || true
    fi
    
    # Install Python
    echo -e "${YELLOW}Installing Python ${PYTHON_VERSION} using pyenv (this may take a few minutes)...${NC}"
    if pyenv install -s ${PYTHON_VERSION}; then
        pyenv global ${PYTHON_VERSION} || pyenv local ${PYTHON_VERSION}
        
        # Ensure pyenv's Python is in PATH
        export PATH="$PYENV_ROOT/versions/${PYTHON_VERSION}/bin:$PATH"
        
        # Create symbolic links
        PYTHON_PATH="$PYENV_ROOT/versions/${PYTHON_VERSION}/bin/python3"
        if [ -f "$PYTHON_PATH" ]; then
            if [ -w "/usr/local/bin" ]; then
                ln -sf "$PYTHON_PATH" "/usr/local/bin/python3" 2>/dev/null || true
                ln -sf "$PYTHON_PATH" "/usr/local/bin/python${PYTHON_VERSION}" 2>/dev/null || true
            elif sudo -n true 2>/dev/null; then
                sudo ln -sf "$PYTHON_PATH" "/usr/local/bin/python3" 2>/dev/null || true
                sudo ln -sf "$PYTHON_PATH" "/usr/local/bin/python${PYTHON_VERSION}" 2>/dev/null || true
            fi
        fi
        
        echo -e "${GREEN}✅ Successfully installed Python${PYTHON_VERSION} using pyenv${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to install Python using pyenv${NC}"
        return 1
    fi
}

install_python_pip() {
    echo -e "${YELLOW}Starting Python${PYTHON_VERSION} installation via Homebrew...${NC}"
    
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}Error: Homebrew not installed, please install Homebrew first${NC}"
        # Try using pyenv
        if install_python_with_pyenv; then
            return 0
        else
            exit 1
        fi
    fi

    # Fix Homebrew environment
    if ! fix_homebrew_env; then
        echo -e "${YELLOW}⚠️  Homebrew environment fix failed, trying pyenv...${NC}"
        if install_python_with_pyenv; then
            return 0
        else
            echo -e "${RED}❌ All installation methods failed${NC}"
            exit 1
        fi
    fi

    # First try to fix pkg-config issues
    fix_pkgconfig_link

    # Install Python (no auto-linking to avoid permission issues)
    echo -e "${YELLOW}Installing python@${PYTHON_VERSION} (this may take a few minutes)...${NC}"
    
    # Use temporary file to capture errors
    INSTALL_OUTPUT=$(mktemp)
    if ! brew install python@${PYTHON_VERSION} > "$INSTALL_OUTPUT" 2>&1; then
        echo -e "${RED}❌ Python${PYTHON_VERSION} installation failed, error information:${NC}"
        cat "$INSTALL_OUTPUT"
        
        # Check if it's an rpath error (check before deleting file)
        IS_RPATH_ERROR=false
        if grep -q "rpath.*target.*should only be used" "$INSTALL_OUTPUT" 2>/dev/null; then
            IS_RPATH_ERROR=true
        fi
        
        # Check if it's a Homebrew configuration error
        IS_HOMEBREW_CONFIG_ERROR=false
        if grep -q "HOMEBREW_PREFIX.*HOMEBREW_CELLAR" "$INSTALL_OUTPUT" 2>/dev/null; then
            IS_HOMEBREW_CONFIG_ERROR=true
        fi
        
        rm -f "$INSTALL_OUTPUT"
        
        if [ "$IS_RPATH_ERROR" = true ] || [ "$IS_HOMEBREW_CONFIG_ERROR" = true ]; then
            echo -e "${YELLOW}Detected Homebrew configuration issue, trying pyenv as alternative...${NC}"
            if install_python_with_pyenv; then
                return 0
            else
                echo -e "${YELLOW}pyenv installation also failed, trying to fix Homebrew and retry...${NC}"
                # Try to uninstall problematic packages first
                brew uninstall --ignore-dependencies mpdecimal 2>/dev/null || true
                # Reinstall
                INSTALL_OUTPUT=$(mktemp)
                if brew install python@${PYTHON_VERSION} > "$INSTALL_OUTPUT" 2>&1; then
                    echo -e "${GREEN}✅ Reinstallation successful${NC}"
                    grep -E "(==>|Installing|Downloading|Pouring|🍺)" "$INSTALL_OUTPUT" | head -20 || true
                    rm -f "$INSTALL_OUTPUT"
                else
                    echo -e "${RED}❌ Reinstallation still failed${NC}"
                    cat "$INSTALL_OUTPUT"
                    rm -f "$INSTALL_OUTPUT"
                    echo -e "${YELLOW}Suggestion: Please manually fix Homebrew configuration or use pyenv to install Python${NC}"
                    exit 1
                fi
            fi
        else
            exit 1
        fi
    else
        # Display key information
        grep -E "(==>|Installing|Downloading|Pouring|🍺)" "$INSTALL_OUTPUT" | head -20 || true
        rm -f "$INSTALL_OUTPUT"
    fi
    
    # Try linking (don't exit even if fails)
    echo -e "${YELLOW}Attempting to link python@${PYTHON_VERSION}...${NC}"
    HOMEBREW_PREFIX=$(detect_homebrew_prefix)
    if ! brew link --overwrite python@${PYTHON_VERSION} 2>&1 | grep -v "Warning"; then
        echo -e "${YELLOW}⚠️  Auto-linking failed, but Python is installed${NC}"
        echo -e "${YELLOW}Can use full path to access: ${HOMEBREW_PREFIX}/opt/python@${PYTHON_VERSION}/bin/python3${NC}"
        
        # Try to create symbolic links to /usr/local/bin (if permissions allow)
        PYTHON_PATH="${HOMEBREW_PREFIX}/opt/python@${PYTHON_VERSION}/bin/python3"
        if [ -f "$PYTHON_PATH" ]; then
            # Check if /usr/local/bin is writable
            if [ -w "/usr/local/bin" ] || sudo -n true 2>/dev/null; then
                echo -e "${YELLOW}Attempting to create symbolic links to /usr/local/bin...${NC}"
                if [ -w "/usr/local/bin" ]; then
                    ln -sf "$PYTHON_PATH" "/usr/local/bin/python3" 2>/dev/null || true
                    ln -sf "$PYTHON_PATH" "/usr/local/bin/python${PYTHON_VERSION}" 2>/dev/null || true
                elif sudo -n true 2>/dev/null; then
                    sudo ln -sf "$PYTHON_PATH" "/usr/local/bin/python3" 2>/dev/null || true
                    sudo ln -sf "$PYTHON_PATH" "/usr/local/bin/python${PYTHON_VERSION}" 2>/dev/null || true
                fi
            fi
        fi
    fi
}

# Get available Python command
get_python_cmd() {
    # 1. Check python3.11 command
    if command -v python${PYTHON_VERSION} &> /dev/null; then
        echo "python${PYTHON_VERSION}"
        return
    fi
    
    # 2. Check python3 command and verify version
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
        if [ "$PYTHON_VER" = "${PYTHON_VERSION}" ]; then
            echo "python3"
            return
        fi
    fi
    
    # 3. Try to get from pyenv path
    if [ -d "$HOME/.pyenv" ]; then
        PYENV_PYTHON="$HOME/.pyenv/versions/${PYTHON_VERSION}/bin/python3"
        if [ -f "$PYENV_PYTHON" ]; then
            echo "$PYENV_PYTHON"
            return
        fi
        # Check pyenv's global version
        if command -v pyenv &> /dev/null; then
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PATH"
            eval "$(pyenv init -)" 2>/dev/null || true
            GLOBAL_VERSION=$(pyenv global 2>/dev/null | head -1 | xargs)
            if [ "$GLOBAL_VERSION" = "${PYTHON_VERSION}" ]; then
                PYENV_PYTHON="$HOME/.pyenv/versions/${PYTHON_VERSION}/bin/python3"
                if [ -f "$PYENV_PYTHON" ]; then
                    echo "$PYENV_PYTHON"
                    return
                fi
            fi
        fi
    fi
    
    # 4. Try to get from Homebrew path
    HOMEBREW_PREFIX=$(detect_homebrew_prefix)
    PYTHON_PATH="${HOMEBREW_PREFIX}/opt/python@${PYTHON_VERSION}/bin/python3"
    if [ -f "$PYTHON_PATH" ]; then
        echo "$PYTHON_PATH"
        return
    fi
    
    # 5. Not found
    echo ""
}

verify_python_pip() {
    echo -e "${YELLOW}Verifying Python${PYTHON_VERSION} and pip installation status...${NC}"
    
    PYTHON_CMD=$(get_python_cmd)
    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}❌ Python${PYTHON_VERSION} not found${NC}"
        exit 1
    fi
    
    if check_python_installed; then
        PYTHON_FULL_VERSION=$($PYTHON_CMD --version 2>&1)
        echo -e "${GREEN}✅ Python installation successful! Version: ${PYTHON_FULL_VERSION}${NC}"
        echo -e "${GREEN}   Python path: $PYTHON_CMD${NC}"
    else
        echo -e "${RED}❌ Python${PYTHON_VERSION} installation failed${NC}"
        exit 1
    fi

    if check_pip_installed; then
        PIP_FULL_VERSION=$($PYTHON_CMD -m pip --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✅ pip installation successful! Version: ${PIP_FULL_VERSION}${NC}"
    else
        echo -e "${YELLOW}⚠️  pip not installed, attempting installation...${NC}"
        $PYTHON_CMD -m ensurepip --upgrade || {
            curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON_CMD || {
                echo -e "${RED}❌ pip installation failed${NC}"
                exit 1
            }
        }
        PIP_FULL_VERSION=$($PYTHON_CMD -m pip --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}✅ pip installation successful! Version: ${PIP_FULL_VERSION}${NC}"
    fi
}

echo -e "${YELLOW}=== Starting Python${PYTHON_VERSION} and pip installation status check ===${NC}"

PYTHON_INSTALLED=false
PIP_INSTALLED=false

if check_python_installed; then
    PYTHON_CMD=$(get_python_cmd)
    if [ -n "$PYTHON_CMD" ]; then
        PYTHON_FULL_VERSION=$($PYTHON_CMD --version 2>&1)
        echo -e "${GREEN}Python${PYTHON_VERSION} is installed, version: ${PYTHON_FULL_VERSION}${NC}"
        PYTHON_INSTALLED=true
    fi
fi

if [ "$PYTHON_INSTALLED" = false ]; then
    echo -e "${RED}Python${PYTHON_VERSION} is not installed${NC}"
fi

if check_pip_installed; then
    PYTHON_CMD=$(get_python_cmd)
    if [ -n "$PYTHON_CMD" ]; then
        PIP_FULL_VERSION=$($PYTHON_CMD -m pip --version 2>&1 | awk '{print $2}')
        echo -e "${GREEN}pip is installed, version: ${PIP_FULL_VERSION}${NC}"
        PIP_INSTALLED=true
    fi
fi

if [ "$PIP_INSTALLED" = false ]; then
    echo -e "${RED}pip is not installed${NC}"
fi

if [ "$PYTHON_INSTALLED" = false ] || [ "$PIP_INSTALLED" = false ]; then
    install_python_pip
fi

verify_python_pip

echo -e "\n${GREEN}=== Operation completed ===${NC}"
PYTHON_CMD=$(get_python_cmd)
if [ -n "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}Tip: You can execute the following commands to manually verify:${NC}"
    echo -e "${YELLOW}  $PYTHON_CMD --version              # Check Python version${NC}"
    echo -e "${YELLOW}  $PYTHON_CMD -m pip --version       # Check pip version${NC}"
fi
exit 0