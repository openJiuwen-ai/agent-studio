# OpenAPI/Swagger Plugin Importer

## Overview

The **Swagger Importer** is an automated tool that generates OpenJiuwen plugin configurations directly from OpenAPI/Swagger specifications. Instead of manually creating plugin JSON files, you can simply provide a Swagger/OpenAPI URL or file, and the tool will automatically extract endpoints, parameters, authentication, and generate a complete plugin configuration.

## Features

✅ **Automatic Plugin Generation**: Converts OpenAPI/Swagger specs to plugin JSON files
✅ **Multiple Input Methods**: Supports URLs, local files, JSON, and YAML formats
✅ **Authentication Detection**: Automatically extracts OAuth2, API Key, Bearer, and Basic auth
✅ **Parameter Extraction**: Converts path, query, header, and body parameters
✅ **Schema Resolution**: Resolves `$ref` pointers and nested schemas
✅ **Flexible Tool Limiting**: Import all endpoints or limit to a specific number
✅ **Interactive Mode**: Step-by-step guided import process
✅ **OpenAPI 2.0 & 3.x Support**: Works with both Swagger 2.0 and OpenAPI 3.x specifications

## Installation

### Required Dependencies

```bash
# For URL fetching (required for --url option)
pip install requests

# For YAML support (optional, required for .yaml/.yml files)
pip install pyyaml
```

## Usage

### 1. Interactive Mode (Recommended for First-Time Users)

```bash
cd backend
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --interactive
```

**Interactive mode will guide you through:**
1. Choosing input source (URL or file)
2. Displaying API information
3. Setting plugin ID and category
4. Limiting number of tools (optional)
5. Authentication handling
6. Automatic file generation and validation

### 2. Command-Line Mode

#### Import from URL

```bash
# Basic import
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --category developer

# With custom plugin ID
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --id petstore_api \
  --category developer

# Limit to 10 tools
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --category developer \
  --limit 10
```

#### Import from File

```bash
# Import from JSON file
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file /path/to/swagger.json \
  --category ai

# Import from YAML file
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file /path/to/openapi.yaml \
  --category data

# Skip authentication processing
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file swagger.json \
  --category social \
  --skip-auth
```

### 3. Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--interactive`, `-i` | Launch interactive mode | `--interactive` |
| `--url` | URL to OpenAPI/Swagger spec | `--url https://api.example.com/swagger.json` |
| `--file` | Path to local spec file | `--file /path/to/swagger.json` |
| `--id` | Custom plugin ID | `--id my_api_plugin` |
| `--category` | Plugin category | `--category ai` |
| `--limit` | Limit number of tools | `--limit 20` |
| `--skip-auth` | Skip authentication processing | `--skip-auth` |
| `--output`, `-o` | Custom output filename | `--output custom_name.json` |

### 4. Categories

Available categories:
- `social` - Social & Communication platforms
- `productivity` - Email, calendar, task management
- `ai` - AI & machine learning services
- `data` - Data sources and analytics
- `communication` - Communication tools
- `developer` - Developer tools and workflows
- `other` - Miscellaneous plugins (default)

## Examples

### Example 1: Import Petstore API

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --id petstore_api \
  --category developer
```

**Output:**
- Plugin ID: `petstore_api`
- Category: Developer Tools
- Base URL: Extracted from spec
- Authentication: API Key (automatically detected)
- Tools: All endpoints (pet, store, user operations)

### Example 2: Import with Tool Limit

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://api.example.com/swagger.json \
  --category ai \
  --limit 5
```

This will import only the first 5 endpoints, useful for large APIs.

### Example 3: Import from Local File

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file ~/Downloads/openapi.yaml \
  --category data \
  --id my_data_api
```

### Example 4: Skip Authentication (Manual Setup Later)

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://api.example.com/swagger.json \
  --category social \
  --skip-auth
```

Use this if you want to manually configure authentication later.

## How It Works

### 1. OpenAPI Specification Parsing

The importer reads OpenAPI/Swagger specifications and extracts:

- **API Information**: Title, description, version
- **Base URL**: From `servers` (OpenAPI 3.x) or `host` + `basePath` (Swagger 2.0)
- **Endpoints**: All paths with HTTP methods
- **Parameters**: Path, query, header, body parameters
- **Request Bodies**: Schema definitions for POST/PUT requests
- **Authentication**: Security schemes (OAuth2, API Key, Bearer, Basic)

### 2. Parameter Conversion

OpenAPI parameters are automatically converted to plugin format:

| OpenAPI Location | Plugin `send_method` |
|------------------|---------------------|
| `path` | `Path` |
| `query` | `Query` |
| `header` | `Header` |
| `body` / `requestBody` | `Body` |
| `formData` | `Body` |

| OpenAPI Type | Plugin Type |
|--------------|-------------|
| `string` | `string` |
| `integer` | `integer` |
| `number` | `number` |
| `boolean` | `boolean` |
| `array` | `array` |
| `object` | `object` |

### 3. Authentication Mapping

| OpenAPI Security Type | Plugin Auth Type | Credentials |
|----------------------|------------------|-------------|
| `oauth2` | `oauth2` | Token |
| `apiKey` | `api_key` | API Key |
| `http` (bearer) | `bearer` | Bearer Token |
| `http` (basic) | `basic` | Username + Password |

### 4. Schema Resolution

The importer automatically resolves:
- `$ref` pointers (e.g., `#/definitions/Pet`, `#/components/schemas/User`)
- Nested schemas in request/response bodies
- Common parameters defined at path level

### 5. Tool Generation

For each endpoint:
1. Extracts HTTP method and path
2. Generates tool name from `operationId` or `summary`
3. Converts all parameters to plugin format
4. Extracts request body schema (for POST/PUT/PATCH)
5. Creates tool JSON object

## Generated Plugin Structure

### Example: Petstore API

**Input:** `https://petstore.swagger.io/v2/swagger.json`

**Generated Plugin:**
```json
{
  "plugin_id": "swagger_petstore",
  "name": "Swagger Petstore",
  "description": "This is a sample server Petstore server...",
  "category": "developer",
  "icon_uri": "🛠️",
  "plugin_type": 1,
  "version": "1.0.7",
  "api_prefix": "https://petstore.swagger.io/v2",
  "header_configuration": {
    "api_key": {
      "value": "YOUR_API_KEY",
      "description": "API key for Swagger Petstore authentication"
    }
  },
  "tools": [
    {
      "name": "Add Pet",
      "path": "/pet",
      "method": "POST",
      "description": "Add a new pet to the store",
      "request_params": {
        "name": {
          "type": "string",
          "description": "Pet name",
          "required": true,
          "send_method": "Body"
        },
        "status": {
          "type": "string",
          "description": "Pet status",
          "required": false,
          "send_method": "Body",
          "enum": ["available", "pending", "sold"]
        }
      }
    },
    {
      "name": "Find Pet By Id",
      "path": "/pet/{petId}",
      "method": "GET",
      "description": "Returns a single pet",
      "request_params": {
        "petId": {
          "type": "integer",
          "description": "ID of pet to return",
          "required": true,
          "send_method": "Path"
        }
      }
    }
  ]
}
```

## Post-Import Steps

After generating a plugin:

### 1. Review Generated File
```bash
# View the generated plugin
cat backend/openjiuwen_studio/marketplace/ready_plugins/<category>/<plugin_id>.json
```

### 2. Validate Plugin
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --validate backend/openjiuwen_studio/marketplace/ready_plugins/<category>/<plugin_id>.json
```

### 3. Manual Adjustments (Optional)

You may want to manually adjust:
- **Tool Names**: Make them more descriptive
- **Descriptions**: Add context for LLM agents
- **Parameter Defaults**: Set sensible defaults
- **Authentication**: Add environment variable hints
- **Tool Filtering**: Remove unnecessary endpoints

### 4. Test in UI

1. Start backend server
2. Navigate to Plugins Marketplace
3. Find your plugin in the category
4. Click "Install"
5. Configure authentication
6. Test tools in Tool Configuration page

## Advanced Features

### Limiting Tools

Large APIs can have hundreds of endpoints. Use `--limit` to import only the first N tools:

```bash
# Import only 10 tools
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://large-api.com/swagger.json \
  --limit 10
```

You can later manually add more tools by editing the JSON file.

### Handling Complex Schemas

The importer handles:
- **Nested Objects**: Flattens request body schemas
- **Arrays**: Detects array types and item types
- **Enums**: Preserves allowed values
- **Required Fields**: Marks required parameters
- **Default Values**: Extracts default values from schemas

### Multi-Authentication APIs

If an API has multiple security schemes, the importer uses the first one. You can manually add additional authentication options by editing the generated JSON.

### Custom Base URLs

The importer extracts the first server URL from the spec. If you need to use a different base URL:

1. Generate the plugin
2. Edit the `api_prefix` field in the JSON file
3. Or set it when installing in the UI

## Troubleshooting

### Common Issues

#### 1. `requests` library not available

**Error:** `requests library is required for URL fetching`

**Solution:**
```bash
pip install requests
```

#### 2. YAML parsing failed

**Error:** `PyYAML library not available for YAML parsing`

**Solution:**
```bash
pip install pyyaml
```

#### 3. Failed to fetch from URL

**Error:** `Failed to fetch OpenAPI spec from URL`

**Solutions:**
- Check internet connection
- Verify URL is accessible
- Try downloading file and using `--file` instead
- Check for CORS or authentication requirements

#### 4. Invalid JSON/YAML

**Error:** `Failed to parse as JSON`

**Solutions:**
- Validate your OpenAPI spec at https://editor.swagger.io/
- Check for syntax errors
- Ensure file encoding is UTF-8

#### 5. Empty plugin (no tools generated)

**Solutions:**
- Check that spec has `paths` object
- Verify endpoints have valid HTTP methods
- Try increasing `--limit` value
- Check backend logs for warnings

### Debug Mode

For detailed logging, run with verbose Python logging:

```bash
PYTHONPATH=backend python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url <url> \
  --category developer
```

## Comparison: Manual vs. Swagger Importer

### Manual Plugin Creation

```bash
# 1. Create template
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator --interactive

# 2. Manually add each endpoint
# 3. Manually configure each parameter
# 4. Manually set authentication
# 5. Manually validate

# Time: 30-60 minutes for 10 endpoints
```

### Swagger Importer

```bash
# 1. Run importer
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://api.example.com/swagger.json \
  --category ai

# Time: 10-30 seconds for 50+ endpoints
```

**Benefits:**
- ✅ 100x faster for large APIs
- ✅ No manual typing errors
- ✅ Consistent parameter definitions
- ✅ Automatic authentication detection
- ✅ Preserves API documentation

## Best Practices

### 1. Use Interactive Mode First

Start with interactive mode to understand the process:
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --interactive
```

### 2. Preview Before Saving

The interactive mode shows API info before generating. Review it carefully.

### 3. Start with Limits

For large APIs, start with a small limit:
```bash
--limit 5
```

Test the plugin, then regenerate with more tools if needed.

### 4. Choose Correct Category

Categorize plugins correctly for easier discovery:
- AI services → `ai`
- Social media → `social`
- Data APIs → `data`
- Developer tools → `developer`

### 5. Review Authentication

Always review generated authentication config:
- Verify header names
- Update environment variable names
- Test with real credentials

### 6. Add Custom Descriptions

OpenAPI descriptions are often technical. Consider editing them to be more LLM-friendly:

**Before:**
```json
"description": "GET /api/v1/users/{id}"
```

**After:**
```json
"description": "Retrieve detailed user profile information by user ID"
```

### 7. Validate Before Committing

Always validate generated plugins:
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
  --validate path/to/plugin.json
```

## Real-World Examples

### OpenAI API

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml \
  --id openai_api \
  --category ai
```

### GitHub API

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json \
  --id github_api \
  --category developer \
  --limit 20
```

### Stripe API

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json \
  --id stripe_api \
  --category data \
  --limit 30
```

## Contributing

To add features or fix bugs in the Swagger Importer:

1. Edit `backend/openjiuwen_studio/marketplace/plugins_creator/from_swagger/importer.py`
2. Test with various OpenAPI specs
3. Update this README with new features
4. Submit a pull request

## Future Enhancements

Planned features:
- [ ] Support for OpenAPI callbacks
- [ ] Support for webhooks
- [ ] Import response schemas as output parameters
- [ ] Support for multiple security schemes
- [ ] Custom parameter mapping rules
- [ ] Batch import from directory of specs
- [ ] API testing after import
- [ ] Automatic versioning for updated specs

## Support

For issues or questions:
1. Check this README first
2. Validate your OpenAPI spec at https://editor.swagger.io/
3. Check backend logs for detailed error messages
4. Try interactive mode for step-by-step guidance

---

## License

Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
