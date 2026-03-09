# Workflow Import CLI Tool (Experimental)

Command-line interface for importing workflows into OpenJiuwen Studio.

⚠️ **EXPERIMENTAL**: This CLI tool is in experimental stage and not recommended for production use. Use the REST API endpoint for production workflows.

## Features

- Import workflows from JSON files (OpenJiuwen native, n8n formats)
- Automatic format detection
- Strict validation option (compiles workflow)
- Verbose output for debugging
- Detailed success/error reporting
- Draft-only import (no automatic publishing)

## Installation

The CLI tool requires the following dependencies:

```bash
pip install click
```

All other dependencies are part of the OpenJiuwen Studio backend.

## Usage

### Basic Syntax

```bash
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  <json_file> \
  --space-id <workspace_id> \
  --user-id <user_id> \
  [OPTIONS]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `json_file` | Path to workflow JSON file (OpenJiuwen or n8n format) |
| `--space-id` | Target workspace ID where workflow will be imported |
| `--user-id` | User ID performing the import |

### Optional Flags

| Flag | Description |
|------|-------------|
| `--validate` | Enable strict validation (compiles workflow before import) |
| `--no-validate` | Disable strict validation (default) |
| `--verbose`, `-v` | Enable verbose output for debugging |

## Examples

### 1. Basic Import

Import workflow as draft without strict validation:

```bash
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  my_workflow.json \
  --space-id space_12345 \
  --user-id user_67890
```

**Output:**
```
============================================================
OpenJiuwen Workflow Import Tool
============================================================

✓ Loaded workflow JSON: my_workflow.json
  File size: 2,543 bytes
  Detected format: openjiuwen_native

Import settings:
  Space ID: space_12345
  User ID: user_67890
  Strict validation: False

Importing workflow...

============================================================
✓ Import Successful!
============================================================

Workflow ID: abc123-def456-789ghi
Workflow Name: My Workflow (Imported)

Metadata:
  original_workflow_id: original-123
  source_format: openjiuwen_native
  regenerated_nodes: 3
```

### 2. Import with Strict Validation

Compile and validate workflow before import:

```bash
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  my_workflow.json \
  --space-id space_12345 \
  --user-id user_67890 \
  --validate
```

### 3. Import n8n Workflow

Import n8n format workflow (auto-detected):

```bash
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  n8n_export.json \
  --space-id space_12345 \
  --user-id user_67890
```

**Output:**
```
✓ Loaded workflow JSON: n8n_export.json
  File size: 4,823 bytes
  Detected format: n8n

...

Metadata:
  source: n8n
  original_name: My n8n Workflow
  converted_nodes: 7
  original_nodes: 5
```

### 4. Verbose Mode for Debugging

Enable detailed logging output:

```bash
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  my_workflow.json \
  --space-id space_12345 \
  --user-id user_67890 \
  --verbose
```

## Supported Formats

The CLI tool automatically detects and imports:

### 1. OpenJiuwen Native Format

**Full Export:**
```json
{
  "workflow_id": "...",
  "name": "My Workflow",
  "desc": "...",
  "space_id": "...",
  "schema": {...},
  "input_parameters": [...],
  "output_parameters": [...],
  "create_time": 1234567890,
  "update_time": 1234567890
}
```

**Partial Export (Minimal):**
```json
{
  "schema": {
    "nodes": [...],
    "edges": [...]
  }
}
```

Only `schema` is required. Missing fields get default values:
- `name`: "Imported Workflow"
- `desc`: ""
- `input_parameters`: []
- `output_parameters`: []
- All other fields: auto-generated

### 2. n8n Format

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

## Output

### Success Output

On successful import:
- ✓ Success message
- Workflow ID (generated)
- Workflow name
- Metadata (source format, conversion stats)
- Warnings (if any, non-fatal)

**Exit code:** 0

### Error Output

On failed import:
- ✗ Error message
- List of errors with details
- Warnings (if any)

**Exit code:** 1

### Special Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Import failed (validation error, conversion error, etc.) |
| 130 | Cancelled by user (Ctrl+C) |

## Error Handling

### Common Errors

**Invalid JSON:**
```
✗ ERROR: Invalid JSON file: Expecting property name enclosed in double quotes: line 5 column 3
```

**Unsupported Format:**
```
✗ ERROR: Unsupported workflow format
  Supported formats: OpenJiuwen native, n8n
```

**Validation Errors:**
```
============================================================
✗ Import Failed
============================================================

Errors (2):
  ✗ Canvas validation failed: Workflow has no START node
  ✗ Canvas validation failed: Workflow has no END node
```

### Warnings

Non-fatal issues that don't prevent import:

```
⚠ Warnings (1):
  • Referenced resource may not exist: sub_workflow_xyz
```

## Import Behavior

### What Gets Imported

✅ Workflow saved as **draft only** (never published)
✅ New `workflow_id` generated (avoids collisions)
✅ All node IDs regenerated
✅ Timestamps set to current time
✅ Version fields cleared

### What Gets Ignored

❌ Source `space_id` (replaced with target `--space-id`)
❌ Source `workflow_id` (new one generated)
❌ Version information (imported as draft)
❌ Publish history

### What Gets Preserved

✓ Workflow name (with "(Imported)" suffix if needed)
✓ Description
✓ Schema structure (nodes, edges, connections)
✓ Input/output parameters
✓ Node configurations
✓ Node positions

## Validation Modes

### Standard Validation (Default)

- Schema structure validation
- Business logic validation (START/END nodes, etc.)
- Edge reference validation

```bash
# Default - no --validate flag needed
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  workflow.json --space-id space1 --user-id user1
```

### Strict Validation

Adds workflow compilation check:
- Validates all component configurations
- Checks resource availability (models, plugins)
- Ensures workflow can be executed

```bash
# Enable with --validate flag
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import \
  workflow.json --space-id space1 --user-id user1 --validate
```

⚠️ **Note:** Strict validation is more thorough but slower.

## Troubleshooting

### Import Fails with "Invalid JSON"

**Problem:** JSON file is malformed

**Solution:**
1. Validate JSON syntax with: `python -m json.tool workflow.json`
2. Check for trailing commas, missing quotes, etc.

### Import Succeeds but Workflow Doesn't Run

**Problem:** Workflow has runtime configuration issues

**Solution:**
1. Use `--validate` flag to enable strict validation
2. Check warnings in output
3. Manually verify workflow in UI after import

### "Module not found" Error

**Problem:** CLI tool not run from correct location

**Solution:**
```bash
# Run from backend directory
cd /path/to/backend
python -m openjiuwen_studio.core.dsl_converter.experimental.cli.workflow_import ...
```

### Permission Denied

**Problem:** User doesn't have access to target workspace

**Solution:**
- Verify `--user-id` has permission to create workflows in `--space-id`
- Check workspace exists and is accessible

## Limitations

⚠️ **Experimental Status - Known Limitations:**

1. **No batch import** - One workflow at a time
2. **No interactive mode** - All parameters must be provided upfront
3. **No workflow update** - Creates new workflow only (no overwrite)
4. **No publish option** - Always imports as draft
5. **Limited error recovery** - Import fails entirely on error (no partial import)
6. **No progress indicator** - For large workflows, no progress shown
7. **Database required** - Must have access to OpenJiuwen database

## Production Alternative

For production use, use the **REST API endpoint** instead:

```bash
curl -X POST "http://localhost:8000/workflows/import" \
  -H "Authorization: Bearer {token}" \
  -F "file=@workflow.json" \
  -F "space_id=space_12345" \
  -F "validate_strict=false"
```

Benefits over CLI:
- ✅ Authentication & authorization
- ✅ Rate limiting
- ✅ API versioning
- ✅ Transaction management
- ✅ Proper error handling
- ✅ Logging & monitoring
- ✅ Production-ready

## Development

### Running Tests

Currently no dedicated tests for CLI tool. Integration tests cover underlying import functionality:

```bash
cd backend/openjiuwen_studio/core/dsl_converter/tests
python run_tests.py integration
```

### Adding Features

CLI tool is a thin wrapper around `WorkflowImporter`. To add features:

1. Add functionality to `WorkflowImporter` class
2. Expose via CLI arguments/flags in `workflow_import.py`
3. Update this README

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
