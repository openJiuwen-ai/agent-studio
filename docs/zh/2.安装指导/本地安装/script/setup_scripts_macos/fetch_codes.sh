#!/bin/bash
# Script name: clone_agent_studio.sh
# Function: Safely clone agent-studio repository (check if directory exists first)

set -x
set -euo pipefail

# Define color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration parameters
REPO_URL="https://gitcode.com/openJiuwen/agent-studio.git"
TARGET_DIR="agent-studio"  # Target directory name for cloning
GIT_BRANCH="${1:-main}"  # Get branch name from command line argument, default is main

# ===================== Core Functions =====================
# Check if git is installed
check_git() {
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Error: git is not installed, please install git and try again${NC}"
        exit 1
    fi
}

# Check if directory exists and handle it
check_and_handle_dir() {
    echo -e "${YELLOW}Checking if target directory [${TARGET_DIR}] exists...${NC}"
    
    if [ -d "${TARGET_DIR}" ]; then
        # Directory exists, check if it's a git repository
        if [ -d "${TARGET_DIR}/.git" ]; then
            echo -e "${YELLOW}⚠️ Directory ${TARGET_DIR} already exists and is a git repository!${NC}"
            
            # Check current branch
            cd "${TARGET_DIR}" || exit 1
            CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
            echo -e "${YELLOW}Current branch: ${CURRENT_BRANCH}, target branch: ${GIT_BRANCH}${NC}"
            
            if [ "$CURRENT_BRANCH" != "$GIT_BRANCH" ]; then
                echo -e "${YELLOW}Branches don't match, switching to ${GIT_BRANCH} branch...${NC}"
                # Get latest code
                git fetch origin 2>/dev/null || true
                # Switch to specified branch
                if git checkout -b "${GIT_BRANCH}" "origin/${GIT_BRANCH}" 2>/dev/null || git checkout "${GIT_BRANCH}" 2>/dev/null; then
                    echo -e "${GREEN}✅ Successfully switched to branch ${GIT_BRANCH}${NC}"
                    # Pull latest code
                    git pull origin "${GIT_BRANCH}" 2>/dev/null || true
                else
                    echo -e "${RED}❌ Failed to switch to branch ${GIT_BRANCH}, please check if the branch exists${NC}"
                    exit 1
                fi
            else
                echo -e "${GREEN}Already on ${GIT_BRANCH} branch, pulling latest code...${NC}"
                git pull origin "${GIT_BRANCH}" 2>/dev/null || true
            fi
            cd - > /dev/null || exit 1
            exit 0  # Skip cloning, exit normally
        else
            # Directory exists but is not a git repository, prompt user
            echo -e "${YELLOW}⚠️ Directory ${TARGET_DIR} already exists but is not a git repository!${NC}"
            read -p "Please choose an option: 1=Delete existing directory and re-clone 2=Keep directory and skip cloning(default 2): " OPTION
            
            case "${OPTION:-2}" in
                1)
                    echo -e "${YELLOW}Deleting existing directory ${TARGET_DIR}...${NC}"
                    rm -rf "${TARGET_DIR}"
                    echo -e "${GREEN}Directory deleted, preparing to clone repository...${NC}"
                    ;;
                2)
                    echo -e "${YELLOW}Keeping existing directory, skipping cloning operation${NC}"
                    exit 0  # Skip cloning, exit normally
                    ;;
                *)
                    echo -e "${YELLOW}Invalid input, defaulting to keep directory and skip cloning${NC}"
                    exit 0
                    ;;
            esac
        fi
    else
        echo -e "${GREEN}Target directory doesn't exist, can proceed with normal cloning${NC}"
    fi
}

# Clone repository
clone_repo() {
    echo -e "${YELLOW}Starting to clone repository: ${REPO_URL} (branch: ${GIT_BRANCH})${NC}"
    git clone -b "${GIT_BRANCH}" "${REPO_URL}" "${TARGET_DIR}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Repository cloned successfully! Target directory: $(pwd)/${TARGET_DIR}, branch: ${GIT_BRANCH}${NC}"
    else
        echo -e "${RED}❌ Repository cloning failed, please check network, repository URL or branch name (${GIT_BRANCH})${NC}"
        exit 1
    fi
}

# ===================== Main Logic =====================
echo -e "${YELLOW}=== Starting agent-studio repository cloning process (branch: ${GIT_BRANCH}) ===${NC}"

# Step 1: Check if git is installed
check_git

# Step 2: Check and handle target directory
check_and_handle_dir

# Step 3: Execute cloning
clone_repo

echo -e "\n${GREEN}=== Operation completed ===${NC}"
exit 0