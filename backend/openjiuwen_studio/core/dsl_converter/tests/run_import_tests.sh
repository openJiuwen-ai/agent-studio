#!/bin/bash
# Test runner for Workflow Import tests

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Workflow Import Test Runner ===${NC}\n"

# Change to tests directory
cd "$(dirname "$0")" || exit 1

# Check if pytest is installed
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "❌ pytest is not installed. Installing..."
    pip install pytest pytest-asyncio pytest-mock
fi

# Parse command line arguments
case "$1" in
    "all")
        echo -e "${GREEN}Running all import tests...${NC}"
        python -m pytest . -v
        ;;
    "detector")
        echo -e "${GREEN}Running detector tests...${NC}"
        python -m pytest test_detector.py -v
        ;;
    "converter")
        echo -e "${GREEN}Running converter tests...${NC}"
        python -m pytest test_converter_native.py test_converter_n8n.py -v
        ;;
    "validator")
        echo -e "${GREEN}Running validator tests...${NC}"
        python -m pytest test_validator.py -v
        ;;
    "importer")
        echo -e "${GREEN}Running importer tests...${NC}"
        python -m pytest test_importer.py -v
        ;;
    "integration")
        echo -e "${GREEN}Running integration tests...${NC}"
        python -m pytest test_integration.py -v
        ;;
    "coverage")
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        python -m pytest . --cov=openjiuwen_studio.core.dsl_converter.converter --cov-report=html --cov-report=term
        echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "quick")
        echo -e "${GREEN}Running quick smoke tests...${NC}"
        python -m pytest test_detector.py test_importer.py -v -k "test_detect_openjiuwen or test_import_openjiuwen_format_draft"
        ;;
    *)
        echo "Usage: $0 {all|detector|converter|validator|importer|integration|coverage|quick}"
        echo ""
        echo "Examples:"
        echo "  ./run_import_tests.sh all          # Run all 136 tests"
        echo "  ./run_import_tests.sh detector     # Run format detection tests"
        echo "  ./run_import_tests.sh converter    # Run conversion tests"
        echo "  ./run_import_tests.sh validator    # Run validation tests"
        echo "  ./run_import_tests.sh importer     # Run importer orchestration tests"
        echo "  ./run_import_tests.sh integration  # Run end-to-end integration tests"
        echo "  ./run_import_tests.sh coverage     # Run all tests with coverage report"
        echo "  ./run_import_tests.sh quick        # Run quick smoke tests"
        exit 1
        ;;
esac
