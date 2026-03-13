# Swagger Importer - Architecture & Design

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenAPI/Swagger Source                       │
│  ┌──────────────┐              ┌──────────────┐                │
│  │  Remote URL  │              │  Local File  │                │
│  │   (JSON)     │              │ (JSON/YAML)  │                │
│  └──────┬───────┘              └──────┬───────┘                │
└─────────┼──────────────────────────────┼────────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Swagger Importer Module                       │
│                   (importer.py)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Fetch/Load Stage                                     │  │
│  │     - fetch_openapi_spec() → Fetch from URL             │  │
│  │     - load_openapi_spec()  → Load from file             │  │
│  │     - Parse JSON/YAML format                            │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. Extraction Stage                                     │  │
│  │     - extract_base_url()        → Get API base URL      │  │
│  │     - extract_authentication()  → Detect auth schemes   │  │
│  │     - extract_parameters()      → Parse parameters      │  │
│  │     - extract_request_body_params() → Parse schemas     │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. Resolution Stage                                     │  │
│  │     - resolve_ref() → Resolve $ref pointers             │  │
│  │     - Handle nested schemas                             │  │
│  │     - Flatten object definitions                        │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  4. Conversion Stage                                     │  │
│  │     - convert_openapi_to_plugin() → Main converter      │  │
│  │     - Create plugin template                            │  │
│  │     - Generate tools for each endpoint                  │  │
│  │     - Map parameters to plugin format                   │  │
│  │     - Add authentication config                         │  │
│  └──────────────────┬───────────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Plugin Creator Module                         │
│                   (plugins_creator.py)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  5. Save Stage                                           │  │
│  │     - save_plugin() → Save to JSON file                 │  │
│  │     - Validate against schema                           │  │
│  │     - Update index.json                                 │  │
│  └──────────────────┬───────────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Plugin Output                                │
│  ready_plugins/<category>/<plugin_id>.json                      │
│                                                                  │
│  {                                                               │
│    "plugin_id": "...",                                          │
│    "name": "...",                                               │
│    "api_prefix": "...",                                         │
│    "header_configuration": {...},                              │
│    "tools": [...]                                               │
│  }                                                               │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
OpenAPI Specification
        │
        ├─ info.title ──────────────────────► plugin.name
        ├─ info.description ─────────────────► plugin.description
        ├─ info.version ─────────────────────► plugin.version
        │
        ├─ servers[0].url ───────────────────► plugin.api_prefix
        │  (or host + basePath)
        │
        ├─ securityDefinitions ──────────────► plugin.header_configuration
        │  (or components.securitySchemes)    │
        │                                     ├─ oauth2 → Authorization: "Bearer ..."
        │                                     ├─ apiKey → X-API-Key: "..."
        │                                     └─ http bearer → Authorization: "Bearer ..."
        │
        └─ paths
           │
           ├─ /users/{id}
           │  │
           │  ├─ get ────────────────────────► tool
           │  │  │                             ├─ name: "Get User By Id"
           │  │  ├─ operationId ──────────────┤
           │  │  ├─ summary                   │
           │  │  ├─ description ──────────────► tool.description
           │  │  │
           │  │  └─ parameters
           │  │     │
           │  │     ├─ id (in: path) ─────────► request_params.id
           │  │     │                           └─ send_method: "Path"
           │  │     │
           │  │     └─ fields (in: query) ────► request_params.fields
           │  │                                 └─ send_method: "Query"
           │  │
           │  └─ post ───────────────────────► tool
           │     │
           │     ├─ requestBody
           │     │  └─ schema
           │     │     └─ properties
           │     │        ├─ name ────────────► request_params.name
           │     │        │                     └─ send_method: "Body"
           │     │        │
           │     │        └─ email ───────────► request_params.email
           │     │                              └─ send_method: "Body"
           │     │
           └─ /users (similar processing)
```

## Component Interactions

```
┌──────────────┐
│     CLI      │
│  (--url or   │
│   --file)    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│  importer.main()         │
│  - Parse arguments               │
│  - Route to interactive/CLI mode │
└──────┬───────────────────────────┘
       │
       ├─── Interactive Mode ────────┐
       │                             │
       │    ┌─────────────────────┐  │
       │    │ interactive_import()│  │
       │    │ - Prompt for source │  │
       │    │ - Show API info     │  │
       │    │ - Get config        │  │
       │    └─────────┬───────────┘  │
       │              │               │
       └─── CLI Mode │               │
                     ▼               ▼
       ┌──────────────────────────────────┐
       │  fetch_openapi_spec() or         │
       │  load_openapi_spec()             │
       └──────┬───────────────────────────┘
              │
              ▼
       ┌──────────────────────────────────┐
       │  convert_openapi_to_plugin()     │
       │  ┌────────────────────────────┐  │
       │  │ 1. Extract base URL        │  │
       │  │ 2. Extract authentication  │  │
       │  │ 3. Create plugin template  │  │
       │  │ 4. For each path:          │  │
       │  │    - For each method:      │  │
       │  │      - Extract params      │  │
       │  │      - Extract body        │  │
       │  │      - Create tool         │  │
       │  │      - Add to plugin       │  │
       │  └────────────────────────────┘  │
       └──────┬───────────────────────────┘
              │
              ▼
       ┌──────────────────────────────────┐
       │  save_plugin()                   │
       │  (from plugins_creator.py)       │
       │  - Validate against schema       │
       │  - Save to file                  │
       │  - Update index.json             │
       └──────────────────────────────────┘
```

## Class/Function Hierarchy

```
importer.py
│
├── main()                              # Entry point
│   ├── parse arguments
│   └── route to mode
│
├── interactive_import()                # Interactive mode
│   ├── get source (URL/file)
│   ├── show API info
│   ├── get plugin config
│   ├── convert_openapi_to_plugin()
│   └── save_plugin()
│
├── fetch_openapi_spec(url)            # URL fetching
│   ├── requests.get()
│   └── parse JSON/YAML
│
├── load_openapi_spec(filepath)        # File loading
│   └── parse JSON/YAML
│
├── convert_openapi_to_plugin()        # Main converter
│   ├── extract_base_url()
│   ├── extract_authentication()
│   ├── create_plugin_template()
│   │   (from templates.py)
│   └── for each path:
│       ├── extract_parameters()
│       ├── extract_request_body_params()
│       └── add_tool_to_plugin()
│           (from templates.py)
│
├── extract_base_url(spec)             # Extract API URL
│   ├── OpenAPI 3.x: servers[0].url
│   └── Swagger 2.0: scheme + host + basePath
│
├── extract_authentication(spec)       # Extract auth
│   ├── OpenAPI 3.x: components.securitySchemes
│   ├── Swagger 2.0: securityDefinitions
│   └── _parse_security_scheme()
│
├── _parse_security_scheme()           # Parse auth scheme
│   ├── oauth2 → oauth2 config
│   ├── apiKey → api_key config
│   └── http → bearer/basic config
│
├── extract_parameters(params, spec)   # Extract params
│   ├── resolve_ref() if needed
│   ├── map type
│   ├── map location → send_method
│   └── extract default/enum
│
├── extract_request_body_params()      # Extract body params
│   ├── resolve_ref() if needed
│   ├── get schema from content type
│   ├── extract properties
│   └── map to plugin format
│
└── resolve_ref(ref, spec)             # Resolve $ref pointers
    └── navigate spec by path
```

## Type Mappings

### Parameter Type Mapping
```python
OPENAPI_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object"
}
```

### Parameter Location Mapping
```python
OPENAPI_LOCATION_MAP = {
    "query": "Query",
    "header": "Header",
    "path": "Path",
    "body": "Body",
    "formData": "Body"
}
```

### Authentication Type Mapping
```python
OpenAPI Security Type     →  Plugin Auth Type
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
oauth2                    →  "oauth2"
apiKey                    →  "api_key"
http (scheme: bearer)     →  "bearer"
http (scheme: basic)      →  "basic"
```

## Error Handling

```
┌─────────────────────┐
│  User Input         │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Validation Layer               │
│  - URL accessibility            │
│  - File existence               │
│  - JSON/YAML syntax             │
│  - Schema validation            │
└─────────┬───────────────────────┘
          │
          ├─ Error ──► Log error & return
          │
          ▼
┌─────────────────────────────────┐
│  Conversion Layer               │
│  - Handle missing fields        │
│  - Resolve $ref failures        │
│  - Type conversion errors       │
└─────────┬───────────────────────┘
          │
          ├─ Error ──► Log error & continue
          │            (skip problematic item)
          ▼
┌─────────────────────────────────┐
│  Save Layer                     │
│  - Schema validation            │
│  - File write permissions       │
└─────────┬───────────────────────┘
          │
          ├─ Error ──► Prompt user to save anyway
          │
          ▼
┌─────────────────────┐
│  Success            │
└─────────────────────┘
```

## Module Dependencies

```
importer.py
│
├── Standard Library
│   ├── argparse
│   ├── json
│   ├── os
│   ├── sys
│   ├── re
│   └── typing
│
├── External (Optional)
│   ├── requests (URL fetching)
│   └── pyyaml (YAML parsing)
│
├── Internal Modules
│   ├── openjiuwen.core.common.logging → logger
│   ├── .categories → CATEGORIES
│   ├── .templates → create_plugin_template, add_tool_to_plugin
│   └── .plugins_creator → save_plugin
│
└── No Breaking Dependencies
    - Graceful degradation if optional deps missing
    - Clear error messages for required features
```

## Configuration Flow

```
Command Line Arguments
        │
        ├─ --url ────────────────► fetch_openapi_spec()
        ├─ --file ───────────────► load_openapi_spec()
        ├─ --id ─────────────────► plugin_id
        ├─ --category ───────────► category
        ├─ --limit ──────────────► max tools to import
        ├─ --skip-auth ──────────► skip auth processing
        └─ --output ─────────────► custom filename
                │
                ▼
        Plugin Configuration
                │
                ├─ plugin_id ────────► from --id or auto-generated
                ├─ name ─────────────► from spec.info.title
                ├─ description ──────► from spec.info.description
                ├─ category ─────────► from --category
                ├─ api_prefix ───────► from spec (servers/host)
                ├─ authentication ───► from spec (if not --skip-auth)
                └─ tools ────────────► from spec.paths (limited by --limit)
```

## Extension Points

The architecture is designed for easy extension:

### 1. Add New Authentication Types
```python
# In _parse_security_scheme()
elif scheme_type == "custom_type":
    return {
        "X-Custom-Header": {
            "value": "YOUR_CUSTOM_TOKEN",
            "description": "Custom authentication token"
        }
    }
```

### 2. Add Response Schema Processing
```python
# New function
def extract_response_params(responses, spec):
    # Extract response schemas
    # Convert to output parameters
    return response_params
```

### 3. Add Custom Parameter Processing
```python
# In extract_parameters()
# Add custom logic for specific parameter types
if param_name.startswith("X-"):
    # Custom header handling
```

### 4. Add Batch Import Support
```python
# New function
def batch_import(urls_or_files, config):
    results = []
    for source in urls_or_files:
        plugin = convert_openapi_to_plugin(...)
        save_plugin(...)
        results.append(plugin)
    return results
```

## Performance Considerations

### Time Complexity
- Spec loading: O(1) - Network/IO bound
- Parsing: O(n) - n = size of spec
- Path processing: O(p * m) - p = paths, m = methods
- Parameter extraction: O(p * m * k) - k = params per method
- $ref resolution: O(d) - d = depth of reference chain

### Space Complexity
- O(s) - s = size of spec
- Spec loaded into memory entirely
- Plugin config built incrementally

### Optimization Strategies
- Lazy loading of large specs
- Streaming JSON parsing for huge files
- Parameter limit to cap memory usage
- Caching of resolved $refs

## Security Considerations

### Input Validation
✅ URL scheme validation (https:// only recommended)
✅ File path validation (no path traversal)
✅ JSON/YAML schema validation
✅ Parameter type validation

### Safe Defaults
✅ Default to skip untrusted authentication
✅ Limit tool count to prevent DoS
✅ Timeout on HTTP requests
✅ Safe filename generation

### No Code Execution
✅ Pure data transformation
✅ No eval() or exec()
✅ No dynamic imports from spec
✅ No shell command execution

---

This architecture ensures:
- **Modularity**: Clear separation of concerns
- **Extensibility**: Easy to add new features
- **Reliability**: Graceful error handling
- **Security**: Safe input processing
- **Performance**: Efficient data processing
