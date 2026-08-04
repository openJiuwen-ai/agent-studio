#!/bin/bash
# Script name: install_and_check_nodejs.sh (macOS version)
# Function: Check if Node.js is installed, install specified version via NVM if not, verify installation result
set -euo pipefail  # Enable strict mode for enhanced script robustness

# Define color output (improves readability)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Reset color

# Configuration parameters (install only this version)
NODEJS_VERSION="22"
NVM_INSTALL_URL="https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh"

# ===================== Core Function Definitions =====================
# Function 1: Check if Node.js is installed
check_node_installed() {
    if command -v node &> /dev/null; then
        # Additional check if it's the specified version (optional)
        INSTALLED_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
        if [ "$INSTALLED_VERSION" = "$NODEJS_VERSION" ]; then
            return 0  # Installed and version matches
        else
            echo -e "${YELLOW}Node.js is installed but version is $(node -v), not the specified v${NODEJS_VERSION}${NC}"
            return 1
        fi
    else
        return 1  # Not installed
    fi
}

# Function 2: Check and install Homebrew (if not installed)
check_and_install_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}Homebrew not installed, starting Homebrew installation...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Configure PATH (required for Apple Silicon Mac)
        if [ -f "/opt/homebrew/bin/brew" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -f "/usr/local/bin/brew" ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
}

# Function 3: Check if NVM is installed, install if not
install_nvm() {
    echo -e "${YELLOW}\nNVM not detected, installing NVM first...${NC}"
    
    # Check if curl exists (NVM installation requires curl)
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}NVM installation depends on curl, installing curl first...${NC}"
        # Install curl via Homebrew
        check_and_install_homebrew
        brew install curl
    fi

    # Execute NVM installation command
    curl -o- "$NVM_INSTALL_URL" | bash
    
    # Load NVM environment (no terminal restart needed)
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    # For zsh, also need to load
    if [ -n "${ZSH_VERSION:-}" ]; then
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    
    # Verify NVM installation
    if command -v nvm &> /dev/null; then
        echo -e "${GREEN}✅ NVM installation successful! Version: $(nvm --version)${NC}"
    else
        echo -e "${RED}❌ NVM installation failed, please check manually!${NC}"
        exit 1
    fi
}

# Function 4: Install specified Node.js version via NVM (install only specified version)
install_nodejs() {
    echo -e "${YELLOW}\nStarting Node.js v${NODEJS_VERSION} installation...${NC}"
    
    # Check if NVM is installed, install NVM first if not
    if ! command -v nvm &> /dev/null; then
        install_nvm
    fi

    # Load NVM environment (ensure available in current session)
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    # For zsh, also need to load
    if [ -n "${ZSH_VERSION:-}" ]; then
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    # Install only specified version (remove redundant LTS installation steps)
    nvm install "$NODEJS_VERSION"

    # Set default Node.js version to specified version
    nvm alias default "$NODEJS_VERSION"
    nvm use default > /dev/null 2>&1
}

# Function 5: Verify Node.js and npm installation results
verify_nodejs() {
    if check_node_installed; then
        # Output Node.js and npm versions (core verification)
        NODE_VERSION=$(node -v)
        NPM_VERSION=$(npm -v)
        echo -e "${GREEN}✅ Node.js installation successful! Version: ${NODE_VERSION}${NC}"
        echo -e "${GREEN}✅ NPM installation successful! Version: ${NPM_VERSION}${NC}"
        
        # Additional functionality test: execute simple Node.js code
        echo -e "${YELLOW}Testing Node.js functionality...${NC}"
        if node -e "console.log('Node.js functionality normal')" &> /dev/null; then
            echo -e "${GREEN}✅ Node.js functionality test passed!${NC}"
        else
            echo -e "${YELLOW}⚠️ Node.js is installed but functionality test abnormal${NC}"
        fi
    else
        echo -e "${RED}❌ Node.js installation failed, please check manually!${NC}"
        exit 1
    fi
}

# ===================== Main Logic =====================
echo -e "${YELLOW}=== Starting Node.js v${NODEJS_VERSION} installation status check ===${NC}"

# Step 1: Check if Node.js is installed (and version matches)
if check_node_installed; then
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}Node.js v${NODEJS_VERSION} is installed, current version: ${NODE_VERSION}${NC}"
    verify_nodejs  # Even if already installed, perform functionality test
else
    echo -e "${RED}Node.js v${NODEJS_VERSION} is not installed${NC}"
    
    # Check network (GitHub access requires network)
    # Improvement: Check basic network connectivity, then check GitHub access
    echo -e "${YELLOW}Checking network connection...${NC}"
    
    # First check basic network (using Baidu as test, since previous curl test succeeded)
    if ! curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://www.baidu.com > /dev/null 2>&1; then
        echo -e "${RED}Error: Basic network connection failed, please check network settings${NC}"
        exit 1
    fi
    
    # Check GitHub access (accept 2xx and 3xx status codes, as GitHub may redirect)
    GITHUB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://github.com 2>/dev/null || echo "000")
    if [[ ! "$GITHUB_STATUS" =~ ^[23][0-9]{2}$ ]]; then
        echo -e "${YELLOW}⚠️ Warning: Cannot directly access GitHub (status code: ${GITHUB_STATUS})${NC}"
        echo -e "${YELLOW}Attempting to check NVM installation source...${NC}"
        
        # Try to access NVM installation script URL
        NVM_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$NVM_INSTALL_URL" 2>/dev/null || echo "000")
        if [[ ! "$NVM_STATUS" =~ ^[23][0-9]{2}$ ]]; then
            echo -e "${RED}Error: Cannot access NVM installation source (status code: ${NVM_STATUS})${NC}"
            echo -e "${YELLOW}Tip: If in mainland China, may need to configure proxy or use mirror source${NC}"
            echo -e "${YELLOW}Can try setting proxy: export https_proxy=http://your-proxy:port${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ NVM installation source accessible${NC}"
        fi
    else
        echo -e "${GREEN}✅ GitHub access normal (status code: ${GITHUB_STATUS})${NC}"
    fi

    # Execute installation + verification
    install_nodejs
    verify_nodejs
fi

echo -e "\n${GREEN}=== Operation completed ===${NC}"
echo -e "${YELLOW}Tip: If node command not available in new terminal, execute source ~/.zshrc or source ~/.bash_profile or restart terminal${NC}"
exit 0