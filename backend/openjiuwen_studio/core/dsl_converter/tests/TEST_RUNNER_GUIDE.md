# Import Workflow Test Runner Guide

## Quick Start

### Prerequisites

```bash
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
python run_tests.py converter     # Conversion tests (118 tests)
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
cd backend/openjiuwen_studio/core/dsl_converter/tests
chmod +x run_import_tests.sh   # first time only
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

# Run specific test file
pytest openjiuwen_studio/core/dsl_converter/tests/test_converter_n8n.py -v

# Run with coverage
pytest openjiuwen_studio/core/dsl_converter/tests/ \
  --cov=openjiuwen_studio.core.dsl_converter.converter \
  --cov-report=html \
  --cov-report=term
```

## Test Suite Overview

Total: **202 tests** covering the workflow import system

### Test Files

| File | Tests | Description |
|---|---|---|
| `test_detector.py` | 25 | Format detection (OpenJiuwen, n8n, unsupported) |
| `test_converter_native.py` | 16 | OpenJiuwen native format conversion |
| `test_converter_n8n.py` | 102 | n8n to OpenJiuwen conversion |
| `test_validator.py` | 20 | Schema and business logic validation |
| `test_importer.py` | 20 | Import orchestration, draft mode, error handling |
| `test_integration.py` | 19 | End-to-end pipeline, concurrent imports |

### test_converter_n8n.py breakdown

The n8n converter test file has two layers:

**Fixture-based** (`TestN8nWorkflowConverter` — 17 tests): runs the full pipeline against `n8n_workflow.json`.

**Per-node unit tests** (85 tests): each class builds a minimal `start → node → end` workflow
programmatically and asserts on the Jiuwen output. Run any class individually:

```bash
pytest test_converter_n8n.py::TestLLMNode -v
pytest test_converter_n8n.py::TestIFNode -v
pytest test_converter_n8n.py::TestLoopNode -v
pytest test_converter_n8n.py::TestCodeNode -v
pytest test_converter_n8n.py::TestSetNode -v
pytest test_converter_n8n.py::TestPluginNode -v
pytest test_converter_n8n.py::TestMergeNode -v
pytest test_converter_n8n.py::TestWorkflowNode -v
pytest test_converter_n8n.py::TestTriggerNodes -v
pytest test_converter_n8n.py::TestConnections -v
pytest test_converter_n8n.py::TestExpressions -v
pytest test_converter_n8n.py::TestModelMapping -v
pytest test_converter_n8n.py::TestNormalizePythonMain -v
pytest test_converter_n8n.py::TestFallbackNode -v
pytest test_converter_n8n.py::TestIDGenerator -v
pytest test_converter_n8n.py::TestStartEndNodes -v
```

## Test Fixtures

Located in: `fixtures/` (relative to tests directory)

- `openjiuwen_export.json` - Full OpenJiuwen workflow export
- `minimal_workflow.json` - Partial workflow (schema only)
- `n8n_workflow.json` - n8n format workflow (5 nodes, 4 connections)

## Common pytest Commands

```bash
cd backend/openjiuwen_studio/core/dsl_converter/tests

# Run tests matching a pattern
pytest . -k "n8n" -v
pytest . -k "TestIFNode" -v
pytest . -k "expression" -v

# Run a specific test
pytest test_converter_n8n.py::TestIFNode::test_single_branch_else_goes_to_end -v

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

After running `python run_tests.py coverage`:

```bash
open htmlcov/index.html      # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html     # Windows
```

Target coverage: **>90%**

## Troubleshooting

### pytest not found

```bash
pip install pytest pytest-asyncio pytest-mock
```

### Import errors

Make sure you're running from the correct directory:

```bash
cd backend/openjiuwen_studio/core/dsl_converter/tests
python run_tests.py all
```

### Coverage not working

```bash
pip install coverage pytest-cov
```

## More Information

See full documentation in `README.md` (same directory).