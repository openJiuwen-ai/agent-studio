#!/usr/bin/env python3
"""
Cross-platform test runner for Workflow Import tests
"""

import sys
import subprocess
import logging
from pathlib import Path

# Color codes
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

TEST_DIR = Path(__file__).parent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def run_command(cmd):
    """Run command and return exit code"""
    logger.info(f"{BLUE}Running: {' '.join(cmd)}{NC}")
    return subprocess.call(cmd)


def main():
    if len(sys.argv) < 2:
        logger.error(f"{RED}Usage: python run_tests.py {{all|detector|converter|validator|importer|integration|coverage"
                     f"|quick}}{NC}\n")
        logger.info("Examples:")
        logger.info("  python run_tests.py all          # Run all 136 tests")
        logger.info("  python run_tests.py detector     # Run format detection tests")
        logger.info("  python run_tests.py converter    # Run conversion tests")
        logger.info("  python run_tests.py validator    # Run validation tests")
        logger.info("  python run_tests.py importer     # Run importer orchestration tests")
        logger.info("  python run_tests.py integration  # Run end-to-end integration tests")
        logger.info("  python run_tests.py coverage     # Run all tests with coverage report")
        logger.info("  python run_tests.py quick        # Run quick smoke tests")
        sys.exit(1)

    test_type = sys.argv[1]

    # Base pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]

    if test_type == "all":
        logger.info(f"{GREEN}Running all import tests...{NC}")
        cmd = pytest_cmd + [str(TEST_DIR), "-v"]
    elif test_type == "detector":
        logger.info(f"{GREEN}Running detector tests...{NC}")
        cmd = pytest_cmd + [str(TEST_DIR / "test_detector.py"), "-v"]
    elif test_type == "converter":
        logger.info(f"{GREEN}Running converter tests...{NC}")
        cmd = pytest_cmd + [
            str(TEST_DIR / "test_converter_native.py"),
            str(TEST_DIR / "test_converter_n8n.py"),
            "-v"
        ]
    elif test_type == "validator":
        logger.info(f"{GREEN}Running validator tests...{NC}")
        cmd = pytest_cmd + [str(TEST_DIR / "test_validator.py"), "-v"]
    elif test_type == "importer":
        logger.info(f"{GREEN}Running importer tests...{NC}")
        cmd = pytest_cmd + [str(TEST_DIR / "test_importer.py"), "-v"]
    elif test_type == "integration":
        logger.info(f"{GREEN}Running integration tests...{NC}")
        cmd = pytest_cmd + [str(TEST_DIR / "test_integration.py"), "-v"]
    elif test_type == "coverage":
        logger.info(f"{GREEN}Running tests with coverage report...{NC}")
        cmd = pytest_cmd + [
            str(TEST_DIR),
            "--cov=openjiuwen_studio.core.dsl_converter.converter",
            "--cov-report=html",
            "--cov-report=term"
        ]
    elif test_type == "quick":
        logger.info(f"{GREEN}Running quick smoke tests...{NC}")
        cmd = pytest_cmd + [
            str(TEST_DIR / "test_detector.py"),
            str(TEST_DIR / "test_importer.py"),
            "-v",
            "-k", "test_detect_openjiuwen or test_import_openjiuwen_format_draft"
        ]
    else:
        logger.error(f"{RED}Unknown test type: {test_type}{NC}")
        sys.exit(1)

    # Run the tests
    exit_code = run_command(cmd)

    if exit_code == 0:
        logger.info(f"\n{GREEN}✅ Tests passed!{NC}")
    else:
        logger.error(f"\n{RED}❌ Tests failed!{NC}")

    if test_type == "coverage":
        logger.info(f"\n{GREEN}Coverage report generated in htmlcov/index.html{NC}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
