# Import Workflow Test Runner Guide

## Quick Start

### Prerequisites

```bash
# Make sure pytest is installed
pip install pytest pytest-asyncio pytest-mock coverage
```

### Running Tests

**Option 1: Use the Python test runner (recommended, cross-platform)**

```bash
# Navigate to the tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests

# Run all tests
python run_tests.py all

# Run specific test suites
python run_tests.py detector      # Format detection tests (25 tests)
python run_tests.py convertor     # Conversion tests (52 tests)
python run_tests.py validator     # Validation tests (20 tests)
python run_tests.py importer      # Importer orchestration tests (20 tests)
python run_tests.py integration   # End-to-end integration tests (19 tests)

# Run with coverage report
python run_tests.py coverage

# Run quick smoke tests
python run_tests.py quick
```

**Option 2: Use the shell script (Linux/Mac only)**

```bash
# Navigate to the tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests

# Make executable (first time only)
chmod +x run_import_tests.sh

# Run tests
./run_import_tests.sh all
./run_import_tests.sh importer
./run_import_tests.sh integration
./run_import_tests.sh coverage
```

**Option 3: Use pytest directly**

```bash
# From backend directory
cd backend
pytest openjiuwen_studio/core/dsl_converter/tests/ -v

# Or from tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests
pytest . -v

# Run specific test file
pytest test_importer.py -v

# Run with coverage
pytest . --cov=openjiuwen_studio.core.dsl_converter.convertor \
  --cov-report=html \
  --cov-report=term
```

## Test Suite Overview

Total: **136 tests** covering the workflow import system

### Test Files

1. **test_detector.py** (25 tests)
   - Format detection (OpenJiuwen, n8n, unsupported)
   - Edge cases and error handling

2. **test_convertor_native.py** (25 tests)
   - OpenJiuwen native format conversion
   - ID regeneration and reference updates

3. **test_convertor_n8n.py** (27 tests)
   - n8n to OpenJiuwen conversion
   - Node type mappings and transformations

4. **test_validator.py** (20 tests)
   - Schema validation
   - Business logic validation (START/END, connections)

5. **test_importer.py** (20 tests)
   - Complete import orchestration
   - Draft mode (always draft only)
   - Error handling and metadata tracking

6. **test_integration.py** (19 tests)
   - End-to-end import workflows
   - Pipeline integration
   - Concurrent imports

## Test Fixtures

Located in: `fixtures/` (relative to tests directory)

- `openjiuwen_export.json` - OpenJiuwen native workflow
- `n8n_workflow.json` - n8n workflow

## Common pytest Commands

```bash
# From tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests

# Run tests matching a pattern
pytest . -k "n8n" -v

# Run a specific test
pytest test_importer.py::TestWorkflowImporter::test_import_openjiuwen_format_draft_mode -v

# Stop on first failure
pytest . -x

# Show print statements
pytest . -s

# Re-run only failed tests
pytest . --lf

# Show local variables on failure
pytest . -l
```

## Coverage Report

After running `python run_tests.py coverage`, view the HTML report:

```bash
# Open the coverage report in browser
open htmlcov/index.html     # Mac
xdg-open htmlcov/index.html # Linux
start htmlcov/index.html    # Windows
```

Target coverage: **>90%**

## Troubleshooting

### pytest not found

```bash
pip install pytest pytest-asyncio pytest-mock
```

### Import errors

Make sure you're in the correct directory:
```bash
cd backend/openjiuwen_studio/core/dsl_converter/tests
python run_tests.py all
```

### Coverage not working

```bash
pip install coverage pytest-cov
```

## More Information

See detailed documentation in `README.md` (same directory)
