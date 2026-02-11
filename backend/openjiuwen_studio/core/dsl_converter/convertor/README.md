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
- Dry-run mode for preview
- Detailed warnings and error messages

✅ **Flexible Integration**
- REST API endpoint
- CLI tool
- Python API for programmatic use

## Architecture

```
┌──────────────┐
│   Detector   │  Identifies workflow format
└──────┬───────┘
       │
┌──────▼───────┐
│  Convertor   │  Transforms to OpenJiuwen format
│   Factory    │  - NativeConvertor (OpenJiuwen → OpenJiuwen)
│              │  - N8nConvertor (n8n → OpenJiuwen)
└──────┬───────┘
       │
┌──────▼───────┐
│  Validator   │  Validates converted workflow
└──────┬───────┘
       │
┌──────▼───────┐
│   Importer   │  Orchestrates import process
│              │  - Save to database
│              │  - Optional publish
└──────────────┘
```

## Usage

### 1. REST API

```bash
# Import as draft
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=abc123" \
  -F "import_mode=draft"

# Import and publish as v1.0.0
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=abc123" \
  -F "import_mode=draft_and_publish"

# With strict validation (compile workflow)
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=abc123" \
  -F "import_mode=draft" \
  -F "validate_strict=true"
```

### 2. CLI Tool

```bash
# Basic import
python -m cli.workflow_import workflow.json \
  --space-id abc123 \
  --user-id user456

# Import and publish
python -m cli.workflow_import workflow.json \
  --space-id abc123 \
  --user-id user456 \
  --publish

# Dry run (preview without saving)
python -m cli.workflow_import workflow.json \
  --space-id abc123 \
  --user-id user456 \
  --dry-run

# With strict validation
python -m cli.workflow_import workflow.json \
  --space-id abc123 \
  --user-id user456 \
  --validate

# Verbose output
python -m cli.workflow_import workflow.json \
  --space-id abc123 \
  --user-id user456 \
  --verbose
```

### 3. Python API

```python
import asyncio
from openjiuwen_studio.core.dsl_converter.convertor import (
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
      mode="draft",  # or "draft_and_publish"
      validate_strict=False,  # Set True for compilation validation
      dry_run=False  # Set True for preview
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

**Structure:**
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

**What happens:**
1. Validates structure
2. Regenerates workflow_id (avoids collisions)
3. Regenerates all node IDs in canvas
4. Updates timestamps
5. Clears version fields (imports as draft)

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
3. Converts connections to edges
4. Adds START and END nodes (n8n doesn't have explicit start/end)
5. Extracts input/output parameters
6. Creates workflow with metadata

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
    mode: str = "draft"              # "draft" | "draft_and_publish"
    validate_strict: bool = False     # Compile + validate
    auto_fix: bool = True            # Try to fix issues (future)
    dry_run: bool = False            # Preview only
```

### Mode Options

**draft** (default)
- Imports workflow as draft
- Saved to `workflow` table
- Can be edited in UI

**draft_and_publish**
- Imports as draft
- Automatically publishes as v1.0.0
- Saved to both `workflow` and `workflow_publish` tables
- Immutable published version

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

### 2. Create Convertor

```python
# convertor_your_format.py

from openjiuwen_studio.core.dsl_converter.convertor.convertor import WorkflowConvertor


class YourFormatConvertor(WorkflowConvertor):
   def convert(self, json_data: dict) -> WorkflowImportResult:
      # Implement conversion logic
      # Must return OpenJiuwen format workflow
      pass
```

### 3. Register in Factory

```python
# convertor.py

class ConvertorFactory:
    @staticmethod
    def create(format_type: WorkflowFormat) -> WorkflowConvertor:
        # ... existing formats ...

        elif format_type == WorkflowFormat.YOUR_FORMAT:
            from openjiuwen_studio.core.importer.convertor_your_format import YourFormatConvertor
            return YourFormatConvertor()
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

1. **Always use dry-run first**
   ```bash
   python -m cli.workflow_import workflow.json ... --dry-run
   ```

2. **Check warnings carefully**
   - Missing resource references
   - Model configurations
   - Sub-workflow dependencies

3. **Import dependencies first**
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
- Use CLI tool with shell scripts
- Import in parallel for independent workflows
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
