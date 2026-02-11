# Workflow Import Test Suite

Comprehensive test suite for the workflow import system.

## Test Coverage

### Test Files

1. **test_detector.py** (25 tests)
   - Format detection for OpenJiuwen native workflows
   - Format detection for n8n workflows
   - Unsupported format detection
   - Edge cases (empty data, invalid JSON, etc.)

2. **test_convertor_native.py** (25 tests)
   - OpenJiuwen native format conversion
   - ID regeneration (workflow_id, node IDs)
   - Timestamp updates
   - Reference updates (edges, input parameters)
   - Version field clearing
   - Missing resource detection
   - Nested structure handling (loop nodes)

3. **test_convertor_n8n.py** (27 tests)
   - n8n format conversion to OpenJiuwen
   - Node type mappings (httpRequest, code, if, merge, etc.)
   - START/END node generation
   - Connection to edge conversion
   - Position preservation
   - Fallback creation for unsupported types
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
   - Draft mode import
   - Draft and publish mode
   - Dry-run mode
   - Strict validation
   - Error handling (database, publish, validation)
   - Metadata tracking

6. **test_integration.py** (19 tests)
   - End-to-end import workflows
   - Pipeline integration (detect → convert → validate → import)
   - Database persistence
   - Publish workflow
   - Concurrent imports
   - Error propagation
   - Warning propagation

**Total: 136 test cases**

## Running Tests

### Run All Tests

```bash
# From backend directory
pytest tests/importer/ -v
```

### Run Specific Test File

```bash
pytest tests/importer/test_detector.py -v
pytest tests/importer/test_convertor_native.py -v
pytest tests/importer/test_convertor_n8n.py -v
pytest tests/importer/test_validator.py -v
pytest tests/importer/test_importer.py -v
pytest tests/importer/test_integration.py -v
```

### Run with Coverage

```bash
pytest tests/importer/ --cov=openjiuwen_studio.core.dsl_converter.convertor --cov-report=html
```

### Run Specific Test

```bash
pytest tests/importer/test_detector.py::TestWorkflowDetector::test_detect_openjiuwen_format_from_fixture -v
```

### Run Tests Matching Pattern

```bash
# Run all n8n-related tests
pytest tests/importer/ -k "n8n" -v

# Run all validation tests
pytest tests/importer/ -k "validate" -v

# Run all integration tests
pytest tests/importer/test_integration.py -v
```

## Test Fixtures

### OpenJiuwen Export Format

**File:** `fixtures/openjiuwen_export.json`

Simple OpenJiuwen workflow with:
- START node
- LLM node (with input reference)
- END node
- Input parameter: `query`
- Output parameter: `result`

### n8n Workflow Format

**File:** `fixtures/n8n_workflow.json`

n8n workflow with:
- Webhook trigger
- HTTP Request node
- Code node
- IF condition node
- Response nodes (success/error)

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

✅ Converts OpenJiuwen → OpenJiuwen (ID regeneration)
✅ Converts n8n → OpenJiuwen (node mapping)
✅ Preserves workflow structure
✅ Updates references correctly
✅ Generates START/END nodes for n8n
✅ Creates fallback nodes for unsupported types

### Validation

✅ Validates workflow schema (Pydantic)
✅ Validates business logic (START/END, connections)
✅ Detects disconnected nodes (warning)
✅ Validates edge references
✅ Strict mode compiles workflow

### Import

✅ Draft mode saves to database
✅ Draft and publish mode publishes workflow
✅ Dry-run mode previews without saving
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

Tests use:
- Real fixture files (JSON)
- Inline test data (Python dicts)
- Invalid data for error cases
- Edge cases (empty, missing fields)

## Coverage Goals

Target coverage: **>90%**

Critical paths to cover:
- ✅ All format detection paths
- ✅ All conversion paths (per format)
- ✅ All validation layers
- ✅ All import modes
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
    pytest tests/importer/ --cov=openjiuwen_studio.core.dsl_converter.convertor
```

## Debugging Tests

### Verbose Output

```bash
pytest tests/importer/ -v -s
```

### Failed Tests Only

```bash
pytest tests/importer/ --lf
```

### Stop on First Failure

```bash
pytest tests/importer/ -x
```

### Show Print Statements

```bash
pytest tests/importer/ -s
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
