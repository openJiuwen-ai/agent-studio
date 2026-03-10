# Workflow Import Test Suite

Comprehensive test suite for the workflow import system.

## Test Coverage

### Test Files

1. **test_detector.py** (25 tests)
   - Format detection for OpenJiuwen native workflows
   - Format detection for n8n workflows
   - Unsupported format detection
   - Edge cases (empty data, invalid JSON, etc.)

2. **test_converter_native.py** (16 tests)
   - OpenJiuwen native format conversion using actual fixtures
   - Partial workflow support (only schema required)
   - ID regeneration (workflow_id, node IDs)
   - Timestamp updates
   - Reference updates (edges, input parameters)
   - Version field clearing
   - Space ID always ignored from source JSON
   - Default value injection for missing fields

3. **test_converter_n8n.py** (102 tests)

   **Fixture-based integration tests** (`TestN8nWorkflowConverter` — 17 tests)
   - Full pipeline conversion from `n8n_workflow.json` fixture
   - Node type mappings (httpRequest, code, if, webhook, respondToWebhook)
   - START/END node generation
   - Connections to edges conversion
   - Position preservation
   - Header conversion, input/output parameter extraction

   **Per-node unit tests** (85 tests) — each class builds a minimal `start → node → end`
   workflow programmatically and asserts on the resulting Jiuwen schema:

   | Class | Tests | What it covers |
   |---|---|---|
   | `TestIDGenerator` | 3 | Sequential ID generation, reset, independent prefixes |
   | `TestStartEndNodes` | 6 | Start/End creation, edge connectivity, generic outputs |
   | `TestTriggerNodes` | 5 | Webhook, chat, form, cron → Start node merging |
   | `TestLLMNode` | 7 | Agent/LLM prompts, model config, outputs, edges |
   | `TestIFNode` | 7 | Selector branches, port IDs, **else→end fallback fix** |
   | `TestLoopNode` | 5 | Batch size, block structure, output properties |
   | `TestCodeNode` | 9 | JS/Python wrapping, `def main`, exception config |
   | `TestSetNode` | 5 | Assignments, raw mode, passthrough optimisation |
   | `TestPluginNode` | 6 | HTTP/app nodes, plugin param, raw param forwarding |
   | `TestMergeNode` | 3 | Variable Merge node structure |
   | `TestWorkflowNode` | 4 | SubWorkflow node, workflowId/mode preservation |
   | `TestConnections` | 5 | Edge wiring, no duplicates, sourcePortID correctness |
   | `TestExpressions` | 8 | `{{ $json.x }}` → `{{x}}` conversion, field mapping |
   | `TestModelMapping` | 7 | GPT-4, Claude, Qwen, DeepSeek, Ollama, Gemini |
   | `TestNormalizePythonMain` | 3 | `def main(args):` wrapping logic |
   | `TestFallbackNode` | 2 | Unknown node → Code fallback with warning |

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

**Total: 202 test cases**

## Running Tests

### Quick Start (Recommended)

**Using the test runner script (cross-platform):**

```bash
# From tests directory
cd backend/openjiuwen_studio/core/dsl_converter/tests
python run_tests.py all          # Run all 202 tests
python run_tests.py importer     # Run just importer tests
python run_tests.py integration  # Run integration tests
python run_tests.py coverage     # Run with coverage report
python run_tests.py quick        # Run quick smoke tests
```

**Run a specific n8n converter suite:**

```bash
python -m pytest tests/test_converter_n8n.py::TestN8nWorkflowConverter -v  # fixture-based
python -m pytest tests/test_converter_n8n.py::TestIFNode -v
python -m pytest tests/test_converter_n8n.py::TestLLMNode -v
python -m pytest tests/test_converter_n8n.py::TestCodeNode -v
# ... any class name from the table above
```

**Or on Linux/Mac using the shell script:**

```bash
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
pytest openjiuwen_studio/core/dsl_converter/tests/test_converter_native.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_converter_n8n.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_validator.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_importer.py -v
pytest openjiuwen_studio/core/dsl_converter/tests/test_integration.py -v
```

### Run with Coverage

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ --cov=openjiuwen_studio.core.dsl_converter.converter --cov-report=html
```

### Run Specific Test

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/test_detector.py::TestWorkflowDetector::test_detect_openjiuwen_format_from_fixture -v
```

### Run Tests Matching Pattern

```bash
# Run all n8n-related tests
pytest openjiuwen_studio/core/dsl_converter/tests/ -k "n8n" -v

# Run all IF node tests
pytest openjiuwen_studio/core/dsl_converter/tests/test_converter_n8n.py -k "TestIFNode" -v

# Run all validation tests
pytest openjiuwen_studio/core/dsl_converter/tests/ -k "validate" -v
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

Demonstrates partial workflow import - only has `schema` field:
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

## Test Design

### Fixture-Based Integration Tests (`TestN8nWorkflowConverter`)

Load a real n8n workflow JSON fixture and run the full `converter.convert()` pipeline,
asserting on the complete `WorkflowImportResult`. These tests verify the end-to-end
contract between n8n input and Jiuwen output.

### Per-Node Unit Tests (all other classes)

Each class builds a **minimal n8n workflow programmatically** using shared helpers:

```python
node = make_node("Agent", "n8n-nodes-base.agent", {"text": "Hello {{input}}"})
nodes, edges = schema_from(make_workflow(node))
llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
assert "{{input}}" in llm["data"]["inputs"]["llmParam"]["prompt"]["content"]
```

The typical shape is **start → node under test → end**, keeping each test isolated
while still exercising the full conversion pipeline.

## Mocking Strategy

### Database Mocking

```python
with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
    mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})
```

### Workflow Manager Mocking

```python
with patch('openjiuwen_studio.core.manager.workflow.mgr') as mock_mgr:
    mock_mgr.workflow_publish = AsyncMock(return_value={"version": "1.0.0"})
```

### Flow Manager Mocking

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
✅ **IF else-branch fallback** - unwired else branch connects to End node
✅ **Passthrough Set node optimisation** - pure `$json` refs merged into predecessor
✅ Preserves workflow structure and node positions
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

## Coverage Goals

Target coverage: **>90%**

Critical paths to cover:
- ✅ All format detection paths
- ✅ All conversion paths (per format, per node type)
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
    pytest openjiuwen_studio/core/dsl_converter/tests/ --cov=openjiuwen_studio.core.dsl_converter.converter
```

## Debugging Tests

```bash
pytest openjiuwen_studio/core/dsl_converter/tests/ -v -s   # verbose + print
pytest openjiuwen_studio/core/dsl_converter/tests/ --lf    # failed tests only
pytest openjiuwen_studio/core/dsl_converter/tests/ -x      # stop on first failure
```

## Test Maintenance

### Adding a New n8n Node Type

1. Add a `TestXxxNode` class to `test_converter_n8n.py`
2. Use `make_node` / `make_workflow` / `schema_from` helpers
3. Cover: node created, key fields preserved, connected to end node

### Adding a New Format

1. Add tests to `test_detector.py`
2. Create `test_converter_newformat.py`
3. Add integration tests to `test_integration.py`
4. Create fixture file in `fixtures/`

### Adding New Validation

1. Add tests to `test_validator.py`
2. Test both success and failure cases
3. Test warning generation

## Known Issues

None currently.

## Future Enhancements

- [ ] Performance tests (large workflows)
- [ ] Load tests (concurrent imports)
- [ ] Stress tests (malformed data)
- [ ] Property-based tests (hypothesis)

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.