# Workflow Import Test Suite

Comprehensive test suite for the workflow import system.

## Test Coverage

### Test Files

1. **test_detector.py** (25 tests)
   - Format detection for OpenJiuwen native workflows
   - Format detection for n8n workflows
   - Unsupported format detection
   - Edge cases (empty data, invalid JSON, etc.)

2. **test_convertor_native.py** (16 tests)
   - OpenJiuwen native format conversion using actual fixtures
   - Partial workflow support (only schema required)
   - ID regeneration (workflow_id, node IDs)
   - Timestamp updates
   - Reference updates (edges, input parameters)
   - Version field clearing
   - Space ID always ignored from source JSON
   - Default value injection for missing fields

3. **test_convertor_n8n.py** (18 tests)
   - n8n format conversion to OpenJiuwen using actual fixture
   - Node type mappings from fixture (httpRequest, code, if, webhook, respondToWebhook)
   - START/END node generation
   - Connections to edges conversion (n8n connections → OpenJiuwen edges with sourceNodeID/targetNodeID)
   - Position preservation
   - Header conversion
   - Input/output parameter extraction

4. **test_validator.py** (20 tests)
   - Schema validation
   - Business logic validation
   - START/END node validation
   - Disconnected node detection
   - Edge reference validation
   - Strict validation mode (compilation)

5. **test_importer.py** (20 tests)
   - Complete import orchestration
   - Draft mode import (always draft only)
   - Strict validation
   - Error handling (database, validation)
   - Metadata tracking

6. **test_integration.py** (19 tests)
   - End-to-end import workflows
   - Pipeline integration (detect → convert → validate → import)
   - Database persistence
   - Concurrent imports
   - Error propagation
   - Warning propagation

**Total: 118 test cases** (reduced from 136 - removed tests for non-existent features, now only test actual fixture data)

## Running Tests

### Quick Start (Recommended)

**Using the test runner script (cross-platform):**

```bash
# From tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests
python run_tests.py all          # Run all 118 tests
python run_tests.py importer     # Run just importer tests
python run_tests.py integration  # Run integration tests
python run_tests.py coverage     # Run with coverage report
python run_tests.py quick        # Run quick smoke tests
```

**Or on Linux/Mac using the shell script:**

```bash
# From tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests
./run_import_tests.sh all
./run_import_tests.sh importer
./run_import_tests.sh integration
```

See `TEST_RUNNER_GUIDE.md` in this directory for more options and examples.

### Run All Tests (Direct pytest)

```bash
# From backend directory
pytest openjiuwen_studio/core/dsl_converter/tests/ -v
```

### Run Specific Test File

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/test_detector.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_convertor_native.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_convertor_n8n.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_validator.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_importer.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_integration.py -v
```

### Run with Coverage

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ --cov=openjiuwen_studio.core.dsl_converter.convertor --cov-report=html
```

### Run Specific Test

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/test_detector.py::TestWorkflowDetector::test_detect_openjiuwen_format_from_fixture -v
```

### Run Tests Matching Pattern

```bash
# Run all n8n-related tests
pytest openjiuwen_studio/core/dsl_converter/tests/ -k "n8n" -v

# Run all validation tests
pytest openjiuwen_studio/core/dsl_converter/tests/ -k "validate" -v

# Run all integration tests
pytest openjiuwen_studio/core/dsl_converter/tests/test_integration.py -v
```

## Test Fixtures

All tests use **actual fixture files only** - no synthetic test data.

### 1. OpenJiuwen Full Export

**File:** `fixtures/openjiuwen_export.json`

Complete OpenJiuwen workflow export with all fields:
- Name: "check_weather"
- 3 nodes: START (type "1"), LLM (type "3"), END (type "2")
- 2 edges: start_1 → llm_1 → end_1 (using sourceNodeID/targetNodeID)
- Input parameters: `city`, `date`
- Output parameters: `result`
- Full metadata: workflow_id, space_id, timestamps, etc.

### 2. Minimal Workflow (Partial Import)

**File:** `fixtures/minimal_workflow.json`

**✨ NEW:** Demonstrates partial workflow import - only has `schema` field:
- 3 nodes: START, LLM, END
- 2 edges using sourceNodeID/targetNodeID
- LLM has `input` parameter
- No other fields (tests default value injection)

### 3. n8n Workflow Format

**File:** `fixtures/n8n_workflow.json`

n8n workflow with 5 nodes:
- webhook_1: Webhook trigger at [250, 300]
- http_request_1: HTTP Request at [450, 300]
- code_1: Code node at [650, 300]
- if_1: IF condition at [850, 300]
- respond_1: Respond to Webhook at [1050, 300]
- 4 connections: Webhook → HTTP Request → Process Data → Check Condition → Respond
- Uses n8n "connections" format (converted to OpenJiuwen "edges")

## Test Categories

### 1. Unit Tests

Test individual components in isolation:
- `test_detector.py` - Format detection logic
- `test_convertor_native.py` - Native conversion
- `test_convertor_n8n.py` - n8n conversion
- `test_validator.py` - Validation logic

### 2. Integration Tests

Test component interactions:
- `test_importer.py` - Import orchestration
- `test_integration.py` - End-to-end workflows

## Mocking Strategy

### Database Mocking

Tests mock the workflow repository to avoid database dependencies:

```python
with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
    mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})
```

### Workflow Manager Mocking

Tests mock the workflow manager for publish operations:

```python
with patch('openjiuwen_studio.core.manager.workflow.mgr') as mock_mgr:
    mock_mgr.workflow_publish = AsyncMock(return_value={"version": "1.0.0"})
```

### Flow Manager Mocking

Tests mock flow manager for strict validation:

```python
with patch('openjiuwen_studio.core.manager.workflow.flow_mgr') as mock_flow_mgr:
    mock_flow_mgr.validate = AsyncMock(return_value=None)
```

## Key Test Scenarios

### Format Detection

✅ Detects OpenJiuwen native format
✅ Detects n8n format (both old and new prefixes)
✅ Returns UNSUPPORTED for invalid formats
✅ Handles edge cases (empty, missing fields, invalid JSON)

### Conversion

✅ **Partial workflow import** - only schema required, all other fields get defaults
✅ **Space ID always ignored** - source space_id cleared, set by importer
✅ Converts OpenJiuwen → OpenJiuwen (ID regeneration)
✅ Converts n8n → OpenJiuwen (node mapping, connections → edges)
✅ **Edge format standardized** - all edges use sourceNodeID/targetNodeID
✅ Preserves workflow structure
✅ Updates references correctly (edges, input parameters)
✅ Generates START/END nodes for n8n
✅ Default value injection for missing fields

### Validation

✅ Validates workflow schema (Pydantic)
✅ Validates business logic (START/END, connections)
✅ Detects disconnected nodes (warning)
✅ Validates edge references
✅ Strict mode compiles workflow

### Import

✅ Draft mode saves to database (always draft only)
✅ Strict validation compiles workflow
✅ Handles errors gracefully
✅ Tracks metadata

### Integration

✅ Complete import pipeline works
✅ Error propagation across layers
✅ Warning propagation across layers
✅ Concurrent imports supported
✅ ID collision prevention

## Async Testing

All import operations are async. Tests use `pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_import_workflow(self, importer):
    result = await importer.import_workflow(...)
    assert result.success is True
```

## Fixtures

Tests use pytest fixtures for reusability:

```python
@pytest.fixture
def convertor(self):
    """Create convertor instance"""
    return N8nWorkflowConvertor()

@pytest.fixture
def simple_n8n_workflow(self):
    """Create simple n8n workflow"""
    return {...}
```

## Assertions

Tests verify:
- Success/failure status
- Error messages
- Warning messages
- Metadata content
- Database calls
- ID regeneration
- Reference updates

## Test Data

**All tests use ONLY actual fixture files** - no synthetic test data:
- **fixtures/openjiuwen_export.json** - Full OpenJiuwen workflow export
- **fixtures/minimal_workflow.json** - Partial workflow (only schema field)
- **fixtures/n8n_workflow.json** - n8n format workflow

For edge cases and error scenarios:
- Minimal valid data (e.g., workflow with empty nodes array)
- Invalid data structures (e.g., missing required fields)
- Small test objects for testing helper methods (_convert_headers, _generate_node_id)

## Coverage Goals

Target coverage: **>90%**

Critical paths to cover:
- ✅ All format detection paths
- ✅ All conversion paths (per format)
- ✅ All validation layers
- ✅ Draft import mode
- ✅ All error paths
- ✅ All warning paths

## CI/CD Integration

These tests should run on:
- Every commit (unit tests)
- Every PR (all tests)
- Daily (integration tests)

Example GitHub Actions:

```yaml
- name: Run Import Tests
  run: |
    cd backend
    pytest openjiuwen_studio/core/dsl_converter/tests/ --cov=openjiuwen_studio.core.dsl_converter.convertor
```

## Debugging Tests

### Verbose Output

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ -v -s
```

### Failed Tests Only

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ --lf
```

### Stop on First Failure

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ -x
```

### Show Print Statements

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ -s
```

## Test Maintenance

### Adding New Format

When adding a new format:
1. Add tests to `test_detector.py`
2. Create `test_convertor_newformat.py`
3. Add integration tests to `test_integration.py`
4. Create fixture file in `fixtures/`

### Adding New Validation

When adding new validation:
1. Add tests to `test_validator.py`
2. Test both success and failure cases
3. Test warning generation

### Adding New Feature

When adding new feature:
1. Add unit tests
2. Add integration tests
3. Update this README

## Known Issues

None currently.

## Future Enhancements

- [ ] Performance tests (large workflows)
- [ ] Load tests (concurrent imports)
- [ ] Stress tests (malformed data)
- [ ] Property-based tests (hypothesis)

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
