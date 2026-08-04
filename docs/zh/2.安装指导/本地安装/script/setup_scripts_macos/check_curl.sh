#!/bin/bash
# Script name: install_and_check_curl.sh (macOS version)
# Function: Check if curl is installed, install via Homebrew if not, and verify installation

set -euo pipefail  # Enable strict mode for better robustness

# Define color output (optional, improves readability)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Reset color

# Function: Check if curl is installed
check_curl_installed() {
    if command -v curl &> /dev/null; then
        return 0  # Installed, return success
    else
        return 1  # Not installed, return failure
    fi
}

# Function: Check and install Homebrew (if not installed)
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

# Function: Install curl via Homebrew
install_curl() {
    echo -e "${YELLOW}Starting curl installation via Homebrew...${NC}"
    
    # Ensure Homebrew is installed
    check_and_install_homebrew
    
    # Install curl
    brew install curl
}

# Function: Verify curl installation result (only for verification after new installation)
verify_curl_after_install() {
    if check_curl_installed; then
        # Output curl version to confirm successful installation
        CURL_VERSION=$(curl --version | head -n1)
        echo -e "${GREEN}✅ curl installation successful! Version: ${CURL_VERSION}${NC}"
        
        # Additional test: Access a simple URL to verify functionality
        echo -e "${YELLOW}Testing curl functionality (accessing Baidu homepage)...${NC}"
        if curl -s -o /dev/null -w "%{http_code}" https://www.baidu.com | grep -q "200"; then
            echo -e "${GREEN}✅ curl functionality test passed!${NC}"
        else
            echo -e "${YELLOW}⚠️ curl is installed but access test failed (possible network issue)${NC}"
        fi
    else
        echo -e "${RED}❌ curl installation failed, please check manually!${NC}"
        exit 1
    fi
}

# Main logic
if check_curl_installed; then
    # curl is already installed, perform simple verification without excessive output
    CURL_VERSION=$(curl --version | head -n1)
    echo -e "${GREEN}curl is already installed, version: ${CURL_VERSION}${NC}"
    # Silent functionality test (no output during test)
    if ! curl -s -o /dev/null -w "%{http_code}" https://www.baidu.com | grep -q "200" 2>/dev/null; then
        echo -e "${YELLOW}⚠️ curl functionality test failed (possible network issue)${NC}"
    fi
else
    echo -e "${YELLOW}curl is not installed, starting installation...${NC}"
    install_curl
    verify_curl_after_install
fi
exit 0