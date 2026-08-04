#!/bin/bash
# Script name: install_and_check_git.sh (macOS version)
# Function: Check if Git is installed, install via Homebrew if not, and verify installation

# Enable strict mode for better robustness (exit on error, undefined variables cause error, pipe failures trigger exit)
set -euo pipefail

# Define color output (improves readability)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Reset color

# ===================== Core Function Definitions =====================
# Function 1: Check if Git is already installed
check_git_installed() {
    if command -v git &> /dev/null; then
        return 0  # Installed, return success code
    else
        return 1  # Not installed, return failure code
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

# Function 3: Install Git via Homebrew
install_git() {
    echo -e "${YELLOW}\nStarting Git installation via Homebrew...${NC}"
    
    # Ensure Homebrew is installed
    check_and_install_homebrew
    
    # Install Git
    brew install git
}

# Function 4: Verify Git installation result (version + functionality test)
verify_git() {
    echo -e "${YELLOW}\nVerifying Git installation status...${NC}"
    if check_git_installed; then
        # 1. Output Git version (basic verification)
        GIT_VERSION=$(git --version)
        echo -e "${GREEN}✅ Git installation successful! Version information: ${GIT_VERSION}${NC}"
        
        # 2. Functionality test (create temporary repository, verify core functionality)
        echo -e "${YELLOW}Testing Git core functionality (creating temporary repository)...${NC}"
        TEMP_DIR=$(mktemp -d -t git-test-XXXXXX)
        cd "$TEMP_DIR" || exit 1
        
        # Execute basic Git operations
        git init -q > /dev/null 2>&1          # Initialize repository (silent)
        touch test.txt                       # Create test file
        git add test.txt > /dev/null 2>&1    # Add file to staging area
        git commit -m "test commit" -q > /dev/null 2>&1  # Commit (silent)
        
        # Verify commit result
        if git log --oneline | grep -q "test commit"; then
            echo -e "${GREEN}✅ Git functionality test passed!${NC}"
        else
            echo -e "${YELLOW}⚠️ Git is installed but functionality test abnormal (possible permission issue)${NC}"
        fi
        
        # Clean up temporary files
        cd - > /dev/null 2>&1
        rm -rf "$TEMP_DIR"
    else
        echo -e "${RED}❌ Git installation failed, please check manually!${NC}"
        exit 1
    fi
}

# ===================== Main Logic =====================
echo -e "${YELLOW}=== Starting Git installation status detection ===${NC}"

# Step 1: Check if Git is already installed
if check_git_installed; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}Git is already installed, version information: ${GIT_VERSION}${NC}"
    verify_git  # Execute functionality test even if already installed
else
    echo -e "${RED}Git is not installed${NC}"
    
    # Execute installation + verification
    install_git
    verify_git
fi

echo -e "\n${GREEN}=== Operation completed ===${NC}"
exit 0