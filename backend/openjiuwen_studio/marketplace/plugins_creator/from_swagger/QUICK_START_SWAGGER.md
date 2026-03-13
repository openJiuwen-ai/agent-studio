# Quick Start: Swagger Importer

## One-Line Commands

### Import from URL
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --category developer
```

### Import from File
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file /path/to/swagger.json \
  --category ai
```

### Interactive Mode
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --interactive
```

## Common Use Cases

### 1. Quick Test (Limit to 5 endpoints)
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url <swagger-url> \
  --category developer \
  --limit 5
```

### 2. Custom Plugin ID
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url <swagger-url> \
  --id my_custom_api \
  --category ai
```

### 3. Skip Authentication (Configure Later)
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url <swagger-url> \
  --category data \
  --skip-auth
```

### 4. Import YAML File
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --file /path/to/openapi.yaml \
  --category social
```

## Installation

```bash
# Required for URL fetching
pip install requests

# Required for YAML support
pip install pyyaml

# Optional: for validation
pip install jsonschema
```

## Categories

- `ai` - AI & ML services
- `social` - Social media platforms
- `productivity` - Task management, calendars
- `data` - Data sources and analytics
- `communication` - Communication tools
- `developer` - Developer tools
- `other` - Everything else

## After Import

1. **Find your plugin:**
   ```bash
   ls backend/openjiuwen_studio/marketplace/ready_plugins/<category>/
   ```

2. **Validate:**
   ```bash
   python -m openjiuwen_studio.marketplace.plugins_creator.plugins_creator \
     --validate backend/openjiuwen_studio/marketplace/ready_plugins/<category>/<plugin>.json
   ```

3. **Review and edit** (optional):
   - Tool names
   - Descriptions
   - Parameter defaults
   - Authentication

4. **Test in UI:**
   - Start backend server
   - Open Plugin Marketplace
   - Install and test

## Real-World Examples

### Petstore API
```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://petstore.swagger.io/v2/swagger.json \
  --id petstore_api \
  --category developer
```

### JSONPlaceholder (Fake API for testing)
```bash
# Note: JSONPlaceholder doesn't have a swagger file, this is an example
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer \
  --url https://example.com/swagger.json \
  --id jsonplaceholder \
  --category developer \
  --limit 10
```

## Troubleshooting

### Can't fetch URL
- Check internet connection
- Try downloading and using `--file` instead
- Verify URL is publicly accessible

### Empty plugin (0 tools)
- Check that spec has `paths` section
- Verify HTTP methods are present
- Check logs for warnings

### Authentication not detected
- Use `--skip-auth` and add manually
- Check spec has `securityDefinitions` or `securitySchemes`

### Too many tools
- Use `--limit` to restrict number
- Import smaller subset, test, then regenerate

## Help

```bash
python -m openjiuwen_studio.marketplace.plugins_creator.from_swagger.importer --help
```

## Full Documentation

See [SWAGGER_IMPORTER_README.md](SWAGGER_IMPORTER_README.md) for complete documentation.
