#!/bin/bash
# Script name: check_mysql.sh (macOS version)
# Function: Check MySQL configuration, provide configuration suggestions and repair solutions

set -uo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== MySQL Configuration Check Tool (macOS version) ===${NC}\n"

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo -e "${RED}❌ MySQL is not installed${NC}"
    echo -e "${YELLOW}Please install MySQL first:${NC}"
    echo "  brew install mysql"
    echo "  or use MySQL official installer: https://dev.mysql.com/downloads/mysql/"
    exit 1
fi

echo -e "${GREEN}✅ MySQL is installed${NC}"

# Check if MySQL service is running (macOS uses brew services)
if command -v brew &> /dev/null; then
    # Check if installed via Homebrew
    if brew list mysql &> /dev/null 2>&1; then
        # Use brew services to check status
        if ! brew services list | grep -q "mysql.*started"; then
            echo -e "${YELLOW}⚠️  MySQL service is not running, attempting to start...${NC}"
            brew services start mysql 2>/dev/null || {
                echo -e "${RED}❌ Unable to start MySQL service${NC}"
                echo -e "${YELLOW}Tip: You can try to start manually: brew services start mysql${NC}"
                exit 1
            }
            sleep 2
        fi
    else
        # Not installed via Homebrew, try other methods to check
        if ! pgrep -x mysqld > /dev/null; then
            echo -e "${YELLOW}⚠️  MySQL service is not running, please start manually${NC}"
            echo -e "${YELLOW}Tip: If using official installer, start MySQL through System Preferences${NC}"
        fi
    fi
else
    # No Homebrew, try to check process
    if ! pgrep -x mysqld > /dev/null; then
        echo -e "${YELLOW}⚠️  MySQL service may not be running, please check manually${NC}"
    fi
fi

echo -e "${GREEN}✅ MySQL service is running${NC}\n"

# Try to connect using root user (macOS usually requires password or sudo)
echo -e "${BLUE}Checking root user authentication method...${NC}"

# Try passwordless connection (some installation methods may allow this)
ROOT_AUTH=""
if mysql -u root -e "SELECT 1;" &> /dev/null 2>&1; then
    ROOT_AUTH=$(mysql -u root -e "SELECT plugin FROM mysql.user WHERE user='root' AND host='localhost';" 2>/dev/null | tail -n 1)
elif sudo mysql -u root -e "SELECT 1;" &> /dev/null 2>&1; then
    ROOT_AUTH=$(sudo mysql -u root -e "SELECT plugin FROM mysql.user WHERE user='root' AND host='localhost';" 2>/dev/null | tail -n 1)
fi

if [ -z "$ROOT_AUTH" ]; then
    echo -e "${YELLOW}⚠️  Unable to connect to MySQL automatically, password may be required${NC}"
    echo -e "${YELLOW}Please manually run the following command to check:${NC}"
    echo -e "  ${GREEN}mysql -u root -p${NC}"
    echo ""
    echo -e "${BLUE}Solution: Create new MySQL user (recommended)${NC}"
    echo "1. Run the following command to log in to MySQL:"
    echo -e "   ${GREEN}mysql -u root -p${NC}"
    echo ""
    echo "2. Execute the following SQL in MySQL (replace your_user_name and your_password):"
    echo -e "   ${GREEN}CREATE DATABASE IF NOT EXISTS openjiuwen_agent;${NC}"
    echo -e "   ${GREEN}CREATE DATABASE IF NOT EXISTS openjiuwen_ops;${NC}"
    echo -e "   ${GREEN}CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';${NC}"
    echo -e "   ${GREEN}GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO 'your_user_name'@'localhost';${NC}"
    echo -e "   ${GREEN}GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO 'your_user_name'@'localhost';${NC}"
    echo -e "   ${GREEN}FLUSH PRIVILEGES;${NC}"
    echo -e "   ${GREEN}EXIT;${NC}"
    echo ""
    echo "3. Configure in .env file:"
    echo -e "   ${GREEN}DB_USER=your_user_name${NC}"
    echo -e "   ${GREEN}DB_PASSWORD=your_password${NC}"
    exit 1
fi

echo -e "${YELLOW}Root user current authentication method: ${ROOT_AUTH}${NC}\n"

# If using auth_socket, provide solutions
if [ "$ROOT_AUTH" = "auth_socket" ] || [ "$ROOT_AUTH" = "unix_socket" ]; then
    echo -e "${YELLOW}⚠️  Detected root user using auth_socket authentication method${NC}"
    echo -e "${YELLOW}This means password connection is not possible, need to create new user or modify root authentication method${NC}\n"
    
    echo -e "${BLUE}Solution 1: Create new MySQL user (recommended)${NC}"
    echo "1. Run the following command to log in to MySQL:"
    echo -e "   ${GREEN}sudo mysql -u root${NC}"
    echo ""
    echo "2. Execute the following SQL in MySQL (replace your_user_name and your_password):"
    echo -e "   ${GREEN}CREATE DATABASE IF NOT EXISTS openjiuwen_agent;${NC}"
    echo -e "   ${GREEN}CREATE DATABASE IF NOT EXISTS openjiuwen_ops;${NC}"
    echo -e "   ${GREEN}CREATE USER 'your_user_name'@'localhost' IDENTIFIED BY 'your_password';${NC}"
    echo -e "   ${GREEN}GRANT ALL PRIVILEGES ON openjiuwen_agent.* TO 'your_user_name'@'localhost';${NC}"
    echo -e "   ${GREEN}GRANT ALL PRIVILEGES ON openjiuwen_ops.* TO 'your_user_name'@'localhost';${NC}"
    echo -e "   ${GREEN}FLUSH PRIVILEGES;${NC}"
    echo -e "   ${GREEN}EXIT;${NC}"
    echo ""
    echo "3. Configure in .env file:"
    echo -e "   ${GREEN}DB_USER=your_user_name${NC}"
    echo -e "   ${GREEN}DB_PASSWORD=your_password${NC}"
    echo ""
    
    echo -e "${BLUE}Solution 2: Modify root user authentication method (not recommended, lower security)${NC}"
    echo "1. Run the following command to log in to MySQL:"
    echo -e "   ${GREEN}sudo mysql -u root${NC}"
    echo ""
    echo "2. Execute the following SQL in MySQL (set a strong password):"
    echo -e "   ${GREEN}ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_strong_password';${NC}"
    echo -e "   ${GREEN}FLUSH PRIVILEGES;${NC}"
    echo -e "   ${GREEN}EXIT;${NC}"
    echo ""
    echo "3. Configure in .env file:"
    echo -e "   ${GREEN}DB_USER=root${NC}"
    echo -e "   ${GREEN}DB_PASSWORD=your_strong_password${NC}"
    echo ""
    
    exit 1
else
    echo -e "${GREEN}✅ Root user can use password authentication${NC}"
    echo -e "${YELLOW}Tip: It is recommended to create a dedicated user instead of using root user${NC}\n"
fi

# Check if databases exist
echo -e "${BLUE}Checking databases...${NC}"
DB_AGENT=0
DB_OPS=0

# Try passwordless connection check
if mysql -u root -e "SHOW DATABASES LIKE 'openjiuwen_agent';" 2>/dev/null | grep -q "openjiuwen_agent"; then
    DB_AGENT=1
fi
if mysql -u root -e "SHOW DATABASES LIKE 'openjiuwen_ops';" 2>/dev/null | grep -q "openjiuwen_ops"; then
    DB_OPS=1
fi

# If passwordless connection fails, try sudo
if [ "$DB_AGENT" = "0" ] || [ "$DB_OPS" = "0" ]; then
    if sudo mysql -u root -e "SHOW DATABASES LIKE 'openjiuwen_agent';" 2>/dev/null | grep -q "openjiuwen_agent"; then
        DB_AGENT=1
    fi
    if sudo mysql -u root -e "SHOW DATABASES LIKE 'openjiuwen_ops';" 2>/dev/null | grep -q "openjiuwen_ops"; then
        DB_OPS=1
    fi
fi

if [ "$DB_AGENT" = "0" ] || [ "$DB_OPS" = "0" ]; then
    echo -e "${YELLOW}⚠️  Databases do not exist, need to create${NC}"
    echo "Run the following command to create databases:"
    echo -e "  ${GREEN}mysql -u root -p${NC}"
    echo "Then execute:"
    echo -e "  ${GREEN}CREATE DATABASE openjiuwen_agent;${NC}"
    echo -e "  ${GREEN}CREATE DATABASE openjiuwen_ops;${NC}"
    echo ""
else
    echo -e "${GREEN}✅ Databases already exist${NC}"
fi

echo -e "\n${BLUE}=== Check completed ===${NC}"