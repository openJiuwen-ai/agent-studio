# Workflow Import System

This module provides functionality to import workflows from various sources into OpenJiuwen.

## Features

✅ **Multi-Format Support**
- OpenJiuwen native format (exported workflows)
- n8n workflow format
- Extensible architecture for adding more formats

✅ **Automatic Format Detection**
- Detects workflow format from JSON structure
- No manual format specification needed

✅ **Robust Validation**
- Schema validation (Pydantic)
- Business logic validation
- Optional strict validation (compilation)

✅ **Safe Import**
- Regenerates IDs to avoid collisions
- Detailed warnings and error messages

✅ **Flexible Integration**
- REST API endpoint
- Python API for programmatic use

## Architecture

```
┌──────────────┐
│   Detector   │  Identifies workflow format
└──────┬───────┘
       │
┌──────▼───────┐
│  Converter   │  Transforms to OpenJiuwen format
│   Factory    │  - NativeConverter (OpenJiuwen → OpenJiuwen)
│              │  - N8nConverter (n8n → OpenJiuwen)
└──────┬───────┘
       │
┌──────▼───────┐
│  Validator   │  Validates converted workflow
└──────┬───────┘
       │
┌──────▼───────┐
│   Importer   │  Orchestrates import process
│              │  - Save to database as draft
└──────────────┘
```

## Usage

### 1. REST API

```bash
# Import as draft
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=abc123"

# With strict validation (compile workflow)
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=abc123" \
  -F "validate_strict=true"
```

### 2. Python API

```python
import asyncio
from openjiuwen_studio.core.dsl_converter.converter import (
   WorkflowImporter,
   ImportOptions
)


async def import_workflow():
   # Load workflow JSON
   with open('workflow.json') as f:
      json_data = json.load(f)

   # Create importer
   importer = WorkflowImporter()

   # Configure options
   options = ImportOptions(
      validate_strict=False  # Set True for compilation validation
   )

   # Import
   result = await importer.import_workflow(
      json_data=json_data,
      space_id="your-space-id",
      current_user={"user_id": "user123"},
      options=options
   )

   # Check result
   if result.success:
      print(f"✓ Imported: {result.workflow_id}")
      print(f"  Name: {result.workflow_name}")
      if result.warnings:
         print(f"  Warnings: {len(result.warnings)}")
   else:
      print(f"✗ Import failed")
      for error in result.errors:
         print(f"  - {error}")


# Run
asyncio.run(import_workflow())
```

## Supported Formats

### OpenJiuwen Native Format

**✨ NEW: Supports PARTIAL workflows - only `schema` is required!**

**Full Structure (all fields optional except `schema`):**
```json
{
  "workflow_id": "uuid",
  "name": "My Workflow",
  "desc": "Description",
  "space_id": "space_uuid",
  "schema": "{\"nodes\":[...],\"edges\":[...]}",
  "input_parameters": [...],
  "output_parameters": [...],
  "create_time": 1234567890,
  "update_time": 1234567890
}
```

**Minimal Structure (only schema required):**
```json
{
  "schema": {
    "nodes": [
      {"id": "start_1", "type": "1", "data": {"title": "Start"}},
      {"id": "llm_1", "type": "3", "data": {"title": "LLM", ...}},
      {"id": "end_1", "type": "2", "data": {"title": "End"}}
    ],
    "edges": [
      {"sourceNodeID": "start_1", "targetNodeID": "llm_1"},
      {"sourceNodeID": "llm_1", "targetNodeID": "end_1"}
    ]
  }
}
```

**Default values for missing fields:**
- `workflow_id`: Generated UUID
- `space_id`: **ALWAYS cleared** - source space_id is ignored, importer sets target space_id
- `name`: "Imported Workflow"
- `desc`: ""
- `url`: ""
- `icon_uri`: ""
- `input_parameters`: []
- `output_parameters`: []
- `create_time`: Current timestamp
- `update_time`: Current timestamp

**Important:** The `space_id` from the imported JSON is always ignored. The workflow will be imported into the space specified in the import request/context.

**What happens:**
1. Validates that `schema` field exists (only required field)
2. Adds default values for any missing fields
3. Validates complete structure
4. Regenerates workflow_id (avoids collisions)
5. Regenerates all node IDs in canvas
6. Updates timestamps
7. Clears version fields (imports as draft)

### n8n Format

**Structure:**
```json
{
  "name": "My n8n Workflow",
  "nodes": [
    {
      "id": "node-1",
      "type": "n8n-nodes-base.httpRequest",
      "name": "API Call",
      "parameters": {...},
      "position": [100, 200]
    }
  ],
  "connections": {
    "node-1": {
      "main": [[{"node": "node-2", "type": "main", "index": 0}]]
    }
  }
}
```

**Conversion mapping:**

| n8n Node Type | OpenJiuwen Component | Notes |
|---------------|----------------------|-------|
| `httpRequest` | `PLUGIN (SERVICE)` | Maps to Restful API plugin |
| `code`, `function` | `CODE` | JavaScript code preserved |
| `if`, `switch` | `IF` | Branch logic converted |
| `merge` | `VARIABLE_MERGE` | Variable merging |
| `set` | `TEXT_EDITOR` | Text manipulation |
| **Unsupported** | `CODE` (fallback) | Generated with TODO comment |

**What happens:**
1. Detects n8n format
2. Converts nodes to OpenJiuwen components
3. **Converts connections to edges** - n8n "connections" → OpenJiuwen "edges" with `sourceNodeID`/`targetNodeID`
4. Adds START and END nodes (n8n doesn't have explicit start/end)
5. Extracts input/output parameters
6. Creates workflow with metadata

**Important:** All edges use standardized field names:
- ✅ **`sourceNodeID`** - The ID of the source node
- ✅ **`targetNodeID`** - The ID of the target node
- ❌ NOT "source" or "target" (n8n uses different format internally)

## Validation Layers

Import performs multi-layer validation:

### Layer 1: Canvas Schema Validation
- Validates JSON structure
- Checks field types
- Verifies required fields

### Layer 2: Business Logic Validation
- Checks START/END nodes exist
- Validates component configurations
- Checks for disconnected nodes

### Layer 3: Strict Validation (Optional)
- Compiles workflow
- Validates component compilation
- Checks resource availability

## Import Options

```python
@dataclass
class ImportOptions:
    validate_strict: bool = False     # Compile + validate
    auto_fix: bool = True            # Try to fix issues (future)
```

All workflows are imported as drafts only and saved to the database. If you want to publish an imported workflow, you can do so manually after import through the UI or API.

## Import Result

```python
@dataclass
class ImportResult:
    success: bool                    # Import succeeded?
    workflow_id: Optional[str]       # Generated workflow ID
    workflow_name: Optional[str]     # Workflow name
    warnings: List[str]              # Non-fatal issues
    errors: List[str]                # Fatal errors
    metadata: Dict[str, Any]         # Additional info
```

### Example Success Result

```python
ImportResult(
    success=True,
    workflow_id="abc123-def456",
    workflow_name="Imported Workflow",
    warnings=[
        "Referenced resource may not exist: sub_workflow_xyz"
    ],
    errors=[],
    metadata={
        "source_format": "n8n",
        "original_name": "My n8n Workflow",
        "converted_nodes": 5,
        "original_nodes": 3,
        "saved_to_db": True,
        "published": False
    }
)
```

### Example Failure Result

```python
ImportResult(
    success=False,
    workflow_id="abc123-def456",
    workflow_name="Invalid Workflow",
    warnings=[],
    errors=[
        "Canvas validation failed: Workflow has no START node",
        "Canvas validation failed: Workflow has no END node"
    ],
    metadata={}
)
```

## Adding New Formats

To add support for a new workflow format:

### 1. Update Detector

```python
# detector.py

class WorkflowFormat(str, Enum):
    OPENJIUWEN_NATIVE = "openjiuwen"
    N8N = "n8n"
    YOUR_FORMAT = "your_format"  # Add here

class WorkflowDetector:
    def detect_format(self, json_data: dict) -> WorkflowFormat:
        # ... existing checks ...

        # Add your format detection
        if self._is_your_format(json_data):
            return WorkflowFormat.YOUR_FORMAT

    def _is_your_format(self, data: dict) -> bool:
        # Implement detection logic
        return "your_unique_field" in data
```

### 2. Create Converter

```python
# converter_your_format.py

from openjiuwen_studio.core.dsl_converter.converter.converter import WorkflowConverter


class YourFormatConverter(WorkflowConverter):
   def convert(self, json_data: dict) -> WorkflowImportResult:
      # Implement conversion logic
      # Must return OpenJiuwen format workflow
      pass
```

### 3. Register in Factory

```python
# converter.py

class ConverterFactory:
    @staticmethod
    def create(format_type: WorkflowFormat) -> WorkflowConverter:
        # ... existing formats ...

        elif format_type == WorkflowFormat.YOUR_FORMAT:
            from openjiuwen_studio.core.importer.converter_your_format import YourFormatConverter
            return YourFormatConverter()
```

## Error Handling

The import system handles errors at multiple levels:

### Conversion Errors
- Invalid JSON structure
- Unsupported node types
- Missing required fields

**Handling:** Converted to warnings when possible, fallback nodes created

### Validation Errors
- Missing START/END nodes
- Invalid component configurations
- Disconnected nodes

**Handling:** Reported as errors, import blocked

### Database Errors
- Duplicate workflow_id (shouldn't happen due to regeneration)
- Database connection issues
- Permission issues

**Handling:** Reported as errors, import rolled back

## Best Practices

### For OpenJiuwen Native Imports

1. **Check warnings carefully**
   - Missing resource references
   - Model configurations
   - Sub-workflow dependencies

2. **Import dependencies first**
   - Import sub-workflows before parent workflows
   - Ensure referenced models exist

### For n8n Imports

1. **Review converted nodes**
   - Check CODE components with TODO comments
   - Verify API endpoints are correct
   - Test converted IF conditions

2. **Manual adjustments needed**
   - LLM model configurations
   - Authentication credentials
   - API keys and secrets

3. **Test thoroughly**
   - Run workflow in debug mode
   - Verify all components work
   - Check data flow between nodes

## Troubleshooting

### "Unsupported workflow format"
- Check JSON is valid
- Verify file contains expected structure
- Try opening in text editor to inspect

### "Validation failed: Workflow has no START node"
- For n8n: START node should be auto-generated
- Check conversion logic didn't fail
- Verify original workflow has entry points

### "Referenced resource may not exist"
- Sub-workflows: Import dependencies first
- Models: Configure in OpenJiuwen before import
- Plugins: Ensure plugins are installed

### Import succeeds but workflow doesn't run
- Use `--validate` flag to catch issues
- Check component configurations in UI
- Review conversion warnings

## Performance Considerations

### Large Workflows
- Workflows with >100 nodes may take longer to import
- Use `validate_strict=False` for faster import
- Validate separately after import

### Batch Imports
- Import in parallel for independent workflows using Python API
- Monitor database connection pool

### Memory Usage
- JSON files are loaded entirely into memory
- Large workflows (>10MB) may require more RAM
- Consider splitting very large workflows

## Security Considerations

### API Endpoint
- Requires authentication
- Validates space_id permissions
- Limits file size (configurable)

### File Validation
- JSON structure validated before processing
- No code execution during import
- Malicious code in CODE components not executed until runtime

### Sensitive Data
- API keys and secrets in n8n workflows
- Must be reconfigured after import
- Not automatically transferred for security

## Testing

Run tests:
```bash
# Unit tests
pytest backend/tests/importer/

# Integration tests
pytest backend/tests/importer/test_integration.py

# With coverage
pytest --cov=openjiuwen_studio.core.importer backend/tests/importer/
```

## Future Enhancements

- [ ] Support for more formats (Zapier, Make, etc.)
- [ ] Auto-fix for common issues (`auto_fix=True`)
- [ ] Bulk import from directory
- [ ] Import history tracking
- [ ] Conflict resolution UI
- [ ] Credential migration helper
- [ ] Workflow comparison tool

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
