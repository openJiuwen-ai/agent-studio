# HTTP Tool Schema Conventions

> This document describes, for **HTTP / OpenAPI plugin tools** in Studio:  
> (1) the **full request body fields** for creating/updating a tool; (2) the syntax and validation rules of `input_schema` / `output_schema`.  
> Audience: developers and implementation engineers who register tools via API, imported JSON, or hand-written schemas.  
> The "Create Tool" wizard in the UI generates compliant schemas automatically; this document covers the contract behind the wizard so you don't have to learn by trial and error.

Related capability: plugin tools with `call_mode = api` (registering an external HTTP API as a tool callable by Agents / workflows).  
For custom Python plugins (`call_mode = custom`), see the [Custom Plugin Development Guide](./custom-plugin-development-guide.md).

---

## 1. Create / Update Tool Request Body Fields

This section describes the **entire tool-creation request** (not a specific tool instance).  
There are two endpoints (validated by the same `JsonSchemaUtils`):

| Endpoint | Path | Form |
|------|------|------|
| **v1 standalone tool** | `POST/PUT /v1/{project_id}/agent-manager/tools` | A single standalone Tool record |
| **v2 plugin tool** | `POST/PUT /v2/{project_id}/agent-manager/tools` | Attached to an existing plugin (requires `plugin_id`); the UI "Create Tool / Update Tool" uses this |

Both endpoints require the `workspace_id` query parameter.

### 1.1 Top-level Fields (CreateToolReq / CreatePluginToolReq)

| Field | Type | Required | Description |
|------|------|------|------|
| `plugin_id` | string | **Required** for v2; optional for v1 | The owning plugin ID. v2 tool creation/update must point to an existing plugin |
| `tool_display_name` | string | **Required** | English identifier. v1: `^[a-zA-Z0-9_]+$`, 1–64; v2 plugin tools commonly `^[a-zA-Z0-9_]{2,64}$`. UI "Name" |
| `tool_chinese_name` | string | Depends on endpoint | Chinese display name, 1–64. UI "Display Name". Often required for v2 creation |
| `tool_desc` | string | **Required** (most paths) | Tool description, 1–600. UI "Description" (tool-level, **not** the parameter-level `description`) |
| `icon` | string | No | Icon URL or resource name |
| `request_info` | object | **Yes** (for HTTP/`api` tools in this document) | See table below. Must contain a valid `url` / `method`; missing values return business error `02401001` instead of persisting with a 500 |
| `auth_info` | object | No | Auth configuration (Service / IAM / HIS_IAM etc.); see auth-related documents for structure |
| `visibility` | string | No | Visibility, e.g. `project` / `user`. For **v1 standalone tools** (`buildToolEntity`) and **plugin creation** (`POST .../plugins` → `getPluginDTO`), the default is `project` when omitted; invalid values raise an error. v2 tools attached to an existing plugin generally inherit the plugin's visibility |
| `intf_type` | string | No | Interface form. Common values: `blocking` (synchronous), `streaming` (streaming; output schema validation may be skipped). Other values may appear in the UI or historical data |
| `call_mode` | string | Plugin side | Usually `api` (HTTP) or `custom` (Python etc.). This document only covers `api` |
| `input_schema` | **JSON string** | No (empty = no input params) | Input contract, see Section 2 onward. **Max ~200,000 characters** |
| `output_schema` | **JSON string** | No (empty = no output params) | Output contract. **Max ~200,000 characters** |
| `is_input_list` | boolean | No | Default `false`. When `true`, inputs are wrapped as a list (UI "Parameter Wrapping") |
| `is_output_list` | boolean | No | Default `false`. Whether outputs are wrapped as a list |
| `metadata` | string | No | Metadata JSON string, max ~4096 |
| `auth_required` | boolean | No | Whether authentication is required, default `false` |
| `test_status` | string | No (tool update) | e.g. `SUCCESS` / `FAILED`; affects the persisted tool debug status |

### 1.2 `request_info` Sub-fields

| Field | Type | Required | Description |
|------|------|------|------|
| `url` | string | **Required** | Full HTTP(S) URL, length ~8–256. The URL check runs under the `tool.url.enable-check` switch: `false` in the application default config (`application-manager.yml`), while the Docker Compose / Kubernetes deployment templates set it to `true`. When enabled, `UrlCheckUtils` may reject intranet/private IPs. In v2 it is usually appended after the plugin's `basic_info` (protocol/host/path), then the server splits out the tool `path` |
| `method` | enum | **Required** | `RequestInfo.MethodEnum` currently only supports **`GET`** / **`POST`** |
| `headers` | object\<string,string\> | No | Static request headers, e.g. `{"Content-Type":"application/json"}` |
| `path_params` | string | No | Path parameter supplement, max ~2000 |
| `input_schema` | string | No | A few paths attach the schema inside `request_info`; **use the top-level `input_schema` for the actual tool input** |

### 1.3 Schema Field Transport Notes

- `input_schema` / `output_schema` are **strings** when persisted and transported over the API; the content itself is a JSON document. Escape properly before writing, or serialize with `JSON.stringify` on the frontend before submitting.
- Empty string / `null` means no parameters; `JsonSchemaUtils` passes them through directly.
- The root node must be a schema node with a `type`; when properties exist it is usually:

```json
{
  "type": "object",
  "properties": { "...": "see below" },
  "required": ["list of required parameter names"]
}
```

---

## 2. Supported Types

Every property node must have a `type`. The platform currently recognizes:

| `type` | Description |
|--------|------|
| `string` | String |
| `number` | Number (decimals allowed) |
| `integer` | Integer |
| `boolean` | Boolean |
| `null` | Empty (usually reverse-generated from examples; rarely selected directly in the create-tool type dropdown) |
| `object` | Object, must have `properties` |
| `array` | Array, must have `items` |
| `file/<subtype>` | **Input only** (the output UI does not support File). The backend allows types with the `file/` prefix |

**`file/<subtype>`** (matching the create-tool UI cascade; persisted as the full string):

| Persisted `type` | UI leaf | Description |
|-------------|---------|------|
| `file/default` | Default | Generic file |
| `file/doc` | Doc | Document |
| `file/txt` | Txt | Text |
| `file/excel` | Excel | Spreadsheet |
| `file/ppt` | PPT | Presentation |
| `file/image` | Image | Image |
| `file/audio` | Audio | Audio |
| `file/video` | Video | Video |

When `file/*` inputs are present, debugging/invocation often treats the request as **multipart/form-data** rather than a pure JSON Body. `file/*` **can only** be placed in `location = Body` (the UI disables it for Query / Headers / Path).

The following standard JSON Schema features are **not supported**:

- `additionalProperties` (validation fails whenever it appears)
- Combinators such as `oneOf` / `anyOf` / `allOf` (reserved in frontend types but not recognized by backend validation)
- Arrays nested in arrays (`items.type === "array"`)

`array<string>`, `array<object>`, etc. commonly seen in the UI are flattened UI notations and are **converted to** `type: "array"` + `items` when persisted / submitted.

---

## 3. Input Property Required Fields and Platform Extensions

For `input_schema`: the root node (depth = 0) is not checked for private fields; **every property under `properties`** (and properties nested under objects) must satisfy the table below.  
Element schemas inside `items` are **not required** to have `description` / `location` (but `items` must not be an array).

### 3.1 Standard / Platform-shared Fields

| Field | Required (input property) | Description |
|------|----------------------|------|
| `type` | Required | See Section 2 |
| `description` | **Required and non-empty** | Parameter description; missing yields error `02401002` |
| `location` | **Required** | Only allowed: `Body` / `Headers` / `Query` / `Path` (case-sensitive, first letter capitalized) |
| `default` | Optional | When present the **content** must match the type: format checks apply to `number` / `integer` / `boolean` via the value's text representation (`asText()`), so a JSON string `"1"` also passes `integer` validation; `file/*` defaults are accepted as strings |
| `properties` | Required when `type=object` | Must contain at least 1 property; `additionalProperties` cannot substitute |
| `items` | Required when `type=array` | Element type may be scalar, `object`, or `file/*`; **must not** be an `array` |
| `required` | Optional | Array of strings listing the required property names at this level |

### 3.2 Platform-private Fields (Non-standard JSON Schema)

These fields sit on property nodes and are used for UI validation, Chinese name display, workflow binding, etc. **The backend `JsonSchemaUtils` enforces `description` + `location` (plus type/structure) during tool creation/update**; the private fields below do not participate in the 02401002 structural validation but are used by the UI / runtime.

| Field | Meaning | Common values |
|------|------|----------|
| `name_cn` | Chinese parameter name (display) | String, may be empty; UI "Chinese Name" |
| `validated` | Whether parameter validation is enabled | `true` / `false`; UI "Parameter Validation" checkbox |
| `validate_type` | Validation type | See table below; empty string when validation is disabled |
| `validate_rule` | Validation rule content | Varies with `validate_type`; may be empty |
| `env_var_ref` | Bound environment variable name | When present, the workflow side can auto-bind the same-named environment variable (common for Path etc.) |

**`validate_type` (create-tool UI)**

| `validate_type` | Applies to parameter `type` | `validate_rule` meaning (UI) |
|-----------------|-----------------|---------------------------|
| `CHAR` | `string` (default) | Character-class rule; usually empty, or length/regex configured by the product |
| `ENUM` | `string` | List of allowed enum values (edited in UI) |
| `DATE` | `string` | Date/time format constraint |
| `NUM` | `number` / `integer` | Numeric rule (range etc., edited in UI) |

When the parameter type changes, the UI resets the default `validate_type` (string → `CHAR`, numeric → `NUM`; `object` / `array` / `file/*` usually clear validation-related fields).

Output parameters (`output_schema`) do **not** require `description` / `location` and generally do not carry the input-only private fields above.

### 3.3 `location` vs UI / OpenAPI Export Notes

| location | UI create tool | Notes |
|----------|-----------|------|
| `Body` | string / number / integer / boolean / object / array&lt;*&gt; / file/* | Nested objects and arrays mainly go in Body |
| `Headers` / `Query` / `Path` | Basic scalars only; object / array / file are disabled in the UI | Path is commonly used for URL path variables |

When exporting OpenAPI, Header / Query / Path parameters currently become **string schemas** (type information may be narrowed). Put complex structures in `Body` to preserve them.

---

## 4. Array and Nesting Rules

### 4.1 Valid Example: Array of Scalars

```json
{
  "type": "object",
  "properties": {
    "tags": {
      "type": "array",
      "description": "Tag list",
      "location": "Body",
      "name_cn": "标签",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": "",
      "items": { "type": "string" }
    }
  },
  "required": ["tags"]
}
```

### 4.2 Valid Example: Array of Objects

```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "description": "Detail rows",
      "location": "Body",
      "name_cn": "明细",
      "validated": false,
      "validate_type": "",
      "validate_rule": "",
      "items": {
        "type": "object",
        "properties": {
          "sku": {
            "type": "string",
            "description": "SKU code",
            "location": "Body",
            "name_cn": "SKU",
            "validated": false,
            "validate_type": "CHAR",
            "validate_rule": ""
          },
          "qty": {
            "type": "integer",
            "description": "Quantity",
            "location": "Body",
            "name_cn": "数量",
            "validated": false,
            "validate_type": "NUM",
            "validate_rule": ""
          }
        },
        "required": ["sku", "qty"]
      }
    }
  }
}
```

### 4.3 Invalid: Array Nested in Array under a Property

Nested-array validation applies when `depth > 0`. Input properties hang under `properties` where depth ≥ 1, so the following fails:

```json
{
  "type": "object",
  "properties": {
    "matrix": {
      "type": "array",
      "description": "2D matrix",
      "location": "Body",
      "items": {
        "type": "array",
        "items": { "type": "string" }
      }
    }
  },
  "required": ["matrix"]
}
```

The error detail looks like: `The parameter [matrix] cannot be nested array.`

Note: if the **root node** itself is `type: array` with `items` being another `array` (no outer object properties), the items depth remains 0 in the current implementation and the nested-array validation above is **not** triggered (historical behavior). Real tool inputs are almost always a root `object` + `properties`; use the property-level example in this section as the reference.

### 4.4 Nesting Depth and Property Count

Configuration items (`studio-manager`):

| Config | Environment variable | Default | Meaning |
|------|----------|--------|------|
| `tool.jsonschema.max-prop-num` | `tool_jsonschema_max_prop_num` | `1000` | Max property count per `properties` level |
| `tool.jsonschema.max-prop-depth` | `tool_jsonschema_max_prop_depth` | `4` | Max nesting depth |

Exceeding the limits raises an error during validation (see Section 7 for error codes).

---

## 5. Full Input Example

```json
{
  "type": "object",
  "properties": {
    "Authorization": {
      "type": "string",
      "description": "Bearer Token",
      "location": "Headers",
      "name_cn": "鉴权头",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": ""
    },
    "page": {
      "type": "integer",
      "description": "Page number",
      "location": "Query",
      "default": "1",
      "name_cn": "页码",
      "validated": false,
      "validate_type": "NUM",
      "validate_rule": ""
    },
    "orderId": {
      "type": "string",
      "description": "Order ID",
      "location": "Path",
      "name_cn": "订单ID",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": ""
    },
    "payload": {
      "type": "object",
      "description": "Request body",
      "location": "Body",
      "name_cn": "请求体",
      "validated": false,
      "validate_type": "",
      "validate_rule": "",
      "properties": {
        "name": {
          "type": "string",
          "description": "Name",
          "location": "Body",
          "name_cn": "名称",
          "validated": true,
          "validate_type": "CHAR",
          "validate_rule": ""
        }
      },
      "required": ["name"]
    }
  },
  "required": ["orderId", "payload"]
}
```

When submitting, the object above must be **serialized as a whole string** and assigned to `input_schema`.

---

## 6. Output Example

Outputs do not require `location` / `description`; the structure is closer to standard JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "integer",
      "description": "Business code"
    },
    "data": {
      "type": "object",
      "description": "Business data",
      "properties": {
        "id": { "type": "string", "description": "Primary key" }
      },
      "required": ["id"]
    }
  },
  "required": ["code"]
}
```

Streaming tools (`intf_type = streaming`) may skip `output_schema` format validation.

---

## 7. Validation Failures and Error Codes

On tool creation / update, the Manager validates schemas via `ToolManagementService.checkToolInfo` → `JsonSchemaUtils`:

- **v1** standalone tools: invoked directly on create / update  
- **v2** plugin tools: `PluginService.addTool` / `updateTool` (including batch creation) invoke it as well, aligned with v1  

Therefore, submitting a schema missing `description` via API bypassing the frontend returns `02401002` for **both v1 and v2**. The "input cannot be empty" message in the UI parameter table's "Description" column is frontend form validation — same rule, different layer.

| External error code | Meaning | Common causes |
|------------|------|----------|
| `openjiuwen.02401002` | Input format error (`TOOL_INPUT_SCHEMA_INVALID`) | Missing `description` / `location` / `type` / `properties` / `items`, invalid type, nesting over limit, nested array, `additionalProperties` present, invalid JSON, `input_schema` parse failure, etc. |
| `openjiuwen.02401003` | Output format error (`TOOL_OUTPUT_SCHEMA_INVALID`) | Invalid output JSON / type / structure (e.g. empty root `properties`) |

**External messages include the specific reason** (i18n placeholder `{0}` + response `details`), e.g.:

- `Input format error: The parameter [age] is missing required field [description].`
- `The parameter [age] is missing required field [location] (must be one of: Body, Headers, Query, Path).`
- `The parameter [age] is missing required field [type].`
- `The parameter [matrix] cannot be nested array.`
- `The schema root is missing required field [properties].` / `The schema root field [properties] cannot be empty.`
- `The schema is not valid JSON.`

When troubleshooting, look first at the parameter name `[...]` and the missing field named in the error message.

---

## 8. Quick Reference: Differences from Standard JSON Schema

| Aspect | This platform |
|----|--------|
| Root form | Usually `object` + `properties` |
| Input properties | `description` + `location` enforced |
| Private extensions | `name_cn`, `validated`, `validate_type`, `validate_rule`, `env_var_ref`, etc. |
| Map-like objects | `additionalProperties` not supported |
| Nested arrays | Not supported |
| Enum / range | Not via standard `enum` / `minimum`; string side mostly uses `validate_type` + `validate_rule` |
| Transport form | Field values are JSON **strings**, not nested objects in the request body |

---

## 9. Self-check Checklist

**Request body**

- [ ] Right endpoint: standalone tools use **v1**; tools under a plugin use **v2** with `plugin_id`
- [ ] `tool_display_name` / `tool_desc` (plus the v2 Chinese name) meet length and character constraints
- [ ] `request_info.url` + `method` valid; intranet URLs may be blocked

**Schema**

- [ ] `input_schema` / `output_schema` are valid JSON and serialized to string as required
- [ ] Root node has a `type`; `object` has non-empty `properties`
- [ ] Every input property has a non-empty `description`, and its `location` is one of `Body` / `Headers` / `Query` / `Path`
- [ ] `array` has `items`, and `items` is not an `array`
- [ ] `additionalProperties` not used
- [ ] Nesting depth and per-level property count within configured limits
- [ ] Complex structures / `file/*` in `Body`; Query / Header / Path use scalars only (consistent with the UI)
- [ ] On `02401002` / `02401003`, check the parameter name `[...]` and missing field in the message / `details`

---

## 10. Implementation References (Code Locations)

| Module | Path |
|------|------|
| Backend validation | `backend/studio-manager-service/.../utils/JsonSchemaUtils.java` |
| Type enums | `.../enums/JsonSchemaType.java`, `ToolParamLocation.java` |
| v1 create/update validation | `.../service/ToolManagementService.java` → `checkToolInfo` / `buildToolEntity` |
| v2 plugin tool create/update validation | `.../service/plugin/PluginService.java` → `validatePluginToolSchemas` (`addTool` / `updateTool`) |
| Request DTOs | `.../dto/CreateToolReq.java`, `CreatePluginToolReq.java`, `RequestInfo.java` |
| Frontend assembly / parsing | `frontend/.../app-plugin/utils.ts` (`view2Schema` / `schema2View`) |
| Create-tool UI (type / validation dropdowns) | `frontend/.../app-plugin/create-tool/create-tool.ts` |

This document stays consistent with the implementation above; if behavior changes, update it accordingly.
