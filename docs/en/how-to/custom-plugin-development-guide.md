# Custom Plugin Development Guide

> This guide is for plugin developers. It explains how to develop and integrate a custom plugin from scratch.

## Table of Contents

- [1. What is a Custom Plugin](#1-what-is-a-custom-plugin)
- [2. Plugin Development](#2-plugin-development)
- [3. Plugin Integration](#3-plugin-integration)
- [4. Implemented Plugins Reference](#4-implemented-plugins-reference)
- [Appendix: Self-Check Checklist](#appendix-self-check-checklist)

---

## 1. What is a Custom Plugin

### 1.1 When to Use a Custom Plugin

The platform supports two plugin types:

| Type | `call_mode` | Use Case | How to Develop |
|------|-------------|----------|----------------|
| **HTTP API Plugin** | `api` | Integrating with external HTTP endpoints (RESTful APIs) | Configure URL/method/headers/auth in the UI. No code required. |
| **Custom Plugin** | `custom` | Non-HTTP scenarios: direct database access, file processing, canvas interaction, local computation, etc. | Write Python code implementing custom execution logic. |

**Quick decision**: If your requirement can be solved through HTTP API integration, use an HTTP API plugin. If you need Python code (e.g., querying a database and processing results, reading local files, complex computations), you need a custom plugin.

### 1.2 Advantages of Custom Plugins

A custom plugin requires only **Python code + JSON configuration** to gain full platform capabilities:

- **Schema-driven forms**: Parameter configuration UI is auto-generated from `input_schema`. No frontend code needed.
- **Workflow + Agent support**: One plugin works in both workflow canvas and agent calls.

### 1.3 Lifecycle

A custom plugin goes through three stages from development to user availability:

1. **Plugin Development** → See [Chapter 2](#2-plugin-development)
2. **Plugin Integration** → See [Chapter 3](#3-plugin-integration)
3. **Plugin Usage** → Platform handles automatically. After integration, users can discover and use the plugin in both workflow canvas and agent configuration.

---

## 2. Plugin Development

### 2.1 Directory Structure

One plugin = one directory, placed under `agent-runtime/extensions/components/`:

```
agent-runtime/extensions/components/
├── my-plugin/
│   ├── component.json
│   ├── my_plugin.py
│   ├── init.sql
│   └── requirements.txt
└── ...
```

File responsibilities:

| File | Filename | Purpose | Required | Details |
|------|----------|---------|----------|---------|
| `component.json` | Fixed | Declares component type and entry class | Yes | [2.2](#22-componentjson) |
| `my_plugin.py` | Customizable | Python execution component, extends `PluginBase`, implements `invoke()` | Yes | [2.3](#23-python-component) |
| `init.sql` | Fixed | Standard `INSERT` statement to register the plugin in the `t_tool` table | Yes | [2.4](#24-initsql) |
| `requirements.txt` | Fixed | Declares third-party Python dependencies for the plugin | Yes | [2.5](#25-dependency-declaration) |

> `component.json` is the recommended fixed name. At runtime startup, the system scans the plugin directory for `.json` files to load component declarations — each plugin directory should contain only one `.json` file.

### 2.2 component.json

| Field | Type | Description | Constraint |
|-------|------|-------------|------------|
| `type` | string | Component type identifier | Use `custom.` prefix |
| `classInfo.className` | string | Python class name | Must match the class name in the `.py` file |
| `classInfo.filePath` | string | Python file relative path | Relative to app root, must not contain `..`, must not be an absolute path |

Example:

```json
{
  "type": "custom.my_plugin",
  "classInfo": {
    "className": "MyPlugin",
    "filePath": "extensions/components/my-plugin/my_plugin.py"
  }
}
```

### 2.3 Python Component

#### PluginBase Base Class

`PluginBase` is the base class for all custom plugins:

| Method/Attribute | Signature | Description |
|-----------------|-----------|-------------|
| `__init__` | `(self, params: List[Param] = None, **config)` | Framework automatically passes parameter definitions and runtime config |
| `params` | `@property → List[Param]` | Parameter definition list; access parameter names, types, descriptions via `self.params` |
| `config` | `@property → dict` | Framework-provided configuration, use as needed |
| `invoke` | `async def invoke(self, inputs: dict, **kwargs) -> dict` | **Must implement**. Receives input parameters, returns result dict. |
| `stream` | `async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]` | Optional override. Default calls `invoke()` and yields a single JSON string. |

> `invoke` is an abstract method that must be implemented, otherwise the plugin cannot be instantiated.

#### Development Example

```python
from jiuwen.extension.wrapper.plugin_base import PluginBase

class MyPlugin(PluginBase):
    """Custom plugin example"""

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        # inputs come from the frontend Schema form, keys match parameter ids in input_schema
        query = inputs.get("query", "")
        result = self._process(query)
        return {"output": result}

    def _process(self, query):
        # Business logic
        return f"processed: {query}"
```

> For streaming output, override the `stream()` method:
>
> ```python
> async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]:
>     query = inputs.get("query", "")
>     yield f"Processing: {query}...\n"
>     result = self._process(query)
>     yield json.dumps({"output": result}, ensure_ascii=False)
> ```

#### Return Value Convention

- Returned dict **without** `errCode` key → Framework wraps as `{"data": result, "errCode": 0, "errMessage": ""}`
- Returned dict **with** `errCode` key → Framework passes through as-is
- `invoke()` raises exception → Framework catches and wraps as `{"data": None, "errCode": 105001, "errMessage": str(e)}`

> It is recommended to handle expected business exceptions inside `invoke()`, returning a dict with error information rather than raising exceptions directly.

> **LLM String Input Compatibility**: When plugin parameter types are `array` or `object`, the LLM may pass them as JSON strings (instead of native Python objects). It is recommended to add type checking in `invoke()`:
> ```python
> coordinates = inputs.get("coordinates", [])
> if isinstance(coordinates, str):
>     coordinates = json.loads(coordinates)
> ```

### 2.4 init.sql

#### t_tool Table Field Requirements

| Field | Value | Description |
|-------|-------|-------------|
| `call_mode` | `custom` | Distinguishes HTTP API plugins (`api`) from custom plugins |
| `metadata` | `{"component_type": "custom.xxx"}` | JSON string; `component_type` must match `type` in `component.json` |
| `input_schema` | JSON | Parameter declarations for frontend form rendering; parameter ids must match the `inputs.get()` keys in Python `invoke()` |
| `output_schema` | JSON | Output parameter declarations. **All `type: "object"` parameters must include a `properties` field**, otherwise runtime validation fails |
| `tool_chinese_name` | Chinese name | Keep consistent with `tool_display_name` |

#### SQL Syntax

Use standard `INSERT` statement with a fixed primary key. No database-specific idempotent syntax (`ON DUPLICATE KEY UPDATE` / `ON CONFLICT DO UPDATE`) is required, compatible with MySQL, PostgreSQL, and all other databases. `init.sql` and `dml.sql` use the same syntax — just copy directly when merging. During development iteration, developers can add `DELETE` as needed.

> **Key Field Notes**:
> - `type`: Use `'inner'` for preset plugins (visible across workspaces); use `'custom'` for user-created plugins (filtered by workspace).
> - `project_id`: Empty string `''` when `type='inner'`; actual project ID when `type='custom'`.
> - `call_mode`: `'custom'` for custom Python component execution, `'api'` for HTTP API execution. This is a different dimension from `type`.
> - `icon`: Recommended to provide an SVG icon in `data:image/svg+xml;base64,...` format.

The following uses the DrawBox Demo as an example (see `agent-runtime/extensions/components/draw-box/init.sql` for the full implementation):

```sql
INSERT INTO t_tool (tool_id, project_id, tool_display_name, tool_chinese_name, tool_desc, icon, type, metadata, call_mode, input_schema, output_schema, visibility, published, customize_node, creator, creator_id, is_share)
VALUES (
    'draw-box',
    '',
    'Box Selection Plugin',
    'Box Selection Plugin',
    'Canvas box selection interaction plugin, supports area calculation, overlap detection, and box merge operations',
    'data:image/svg+xml;base64,PHN2ZyB3...',
    'inner',
    '{"component_type": "custom.draw_box"}',
    'custom',
    '{"type":"object","properties":{"operation":{"type":"string","enum":["calculate_area","find_overlaps","merge_boxes"],"description":"Box data operation type: calculate_area=calculate area, find_overlaps=detect overlaps, merge_boxes=merge boxes","default":"calculate_area"},"coordinates":{"type":"array","description":"List of coordinate points (for calculate_area: array of points [{x,y},...]; for find_overlaps/merge_boxes: array of point arrays [[{x,y},...],...])","items":{"type":"object","properties":{"x":{"type":"number","description":"X coordinate"},"y":{"type":"number","description":"Y coordinate"}},"required":["x","y"]}}},"required":["coordinates"]}',
    '{"type":"object","properties":{"output":{"type":"object","description":"Processing result","properties":{"operation":{"type":"string","description":"Executed operation type"},"area":{"type":"number","description":"Box selection area (calculate_area)"},"center":{"type":"object","description":"Center point coordinates (calculate_area)","properties":{"x":{"type":"number","description":"X coordinate"},"y":{"type":"number","description":"Y coordinate"}}},"bounds":{"type":"object","description":"Boundary range (calculate_area)","properties":{"min_x":{"type":"number","description":"Min X coordinate"},"max_x":{"type":"number","description":"Max X coordinate"},"min_y":{"type":"number","description":"Min Y coordinate"},"max_y":{"type":"number","description":"Max Y coordinate"}}},"point_count":{"type":"integer","description":"Number of coordinate points (calculate_area)"},"overlap_pairs":{"type":"array","description":"List of overlap pairs (find_overlaps)","items":{"type":"object","properties":{"box_a":{"type":"integer","description":"Box group A index"},"box_b":{"type":"integer","description":"Box group B index"}}}},"overlap_count":{"type":"integer","description":"Number of overlap pairs (find_overlaps)"},"merged_boxes":{"type":"array","description":"List of merged box regions (merge_boxes)","items":{"type":"object","properties":{"min_x":{"type":"number","description":"Min X coordinate"},"max_x":{"type":"number","description":"Max X coordinate"},"min_y":{"type":"number","description":"Min Y coordinate"},"max_y":{"type":"number","description":"Max Y coordinate"}}}},"box_count":{"type":"integer","description":"Number of merged box regions (merge_boxes)"}}}}}',
    'global',
    1,
    1,
    'system',
    'system',
    0
);
```

> **Important**: All `type: "object"` parameters in `output_schema` must include a `properties` field. Otherwise, runtime validation will report `The schema field is missing for object parameter` error, causing plugin registration failure.

### 2.5 Dependency Declaration

Third-party Python dependencies used by the plugin must be declared during development (`requirements.txt`). During integration, modify the build configuration based on this declaration. See [Chapter 3](#3-plugin-integration).

Example (`requirements.txt`):

```
requests>=2.28.0
pandas>=1.5.0
```

> After development is complete, please check each item in the [Appendix Self-Check Checklist](#appendix-self-check-checklist).

---

## 3. Plugin Integration

### 3.1 Choosing an Integration Method

The platform supports two integration methods:

| | Source Code Integration | Image Integration |
|---|---|---|
| **Use Case** | General-purpose, stable, long-term maintained plugins | Narrow scope, testing, or temporary needs |
| **Code Location** | `agent-runtime/extensions/components/` | Customer-built image layer overlay |
| **Python Dependencies** | Added to repo `requirements.txt` and `pyproject.toml` | `pip install` in customer Dockerfile |
| **SQL Registration** | Merged into `dml.sql`, auto-executed at manager startup | Manual `init.sql` execution against database |
| **Upgrade Path** | Released with platform versions | After verification, can be submitted to community for source code integration |
| **Details** | [3.2](#32-source-code-integration) | [3.3](#33-image-integration) |

### 3.2 Source Code Integration

1. Place the plugin directory in `agent-runtime/extensions/components/`

2. Append plugin Python dependencies to `agent-runtime/requirements.txt` and `agent-runtime/pyproject.toml`

3. Merge `init.sql` content into `backend/studio-manager-service/src/main/resources/sql/dml.sql`

4. Start manager and runtime locally to verify: manager executes `dml.sql` at startup to register the plugin, runtime scans `extensions/components/` to load plugin code. After startup, create an agent in the platform UI, add the plugin, and test via chat. Once verified, merge code and build packages

### 3.3 Image Integration

1. Write a `Dockerfile.runtime.custom` to overlay plugin code onto the base image and install dependencies

   ```dockerfile
   FROM studio-runtime:<version>
   # Copy only your plugin directory — does not affect existing plugins in the base image
   COPY extensions/components/my-plugin/ /opt/cloud/agent-runtime/app/extensions/components/my-plugin/
   RUN pip install -r /opt/cloud/agent-runtime/app/extensions/components/my-plugin/requirements.txt
   ```

   > For multiple plugins, either COPY each plugin directory individually, or use `COPY extensions/components/ /opt/cloud/agent-runtime/app/extensions/components/` — but note this replaces all existing plugins in that directory.

2. Build the custom runtime image (execute from the parent directory of `extensions/` to ensure the build context includes `extensions/`)

   ```bash
   docker build -t studio-runtime-custom:<version> -f Dockerfile.runtime.custom .
   ```

3. Connect to the database and execute `init.sql` (run from the parent directory of `extensions/`, path points to the local init.sql file)

   ```bash
   mysql -h <db_host> -u <user> -p <db> < extensions/components/my-plugin/init.sql
   ```

4. Update the studio-runtime service image version to `studio-runtime-custom:<version>` and restart the service

5. Create an agent in the platform UI, add the plugin, and test via chat

After verification, you can submit to the community for inclusion in the next release, upgrading to source code integration.

> After integration is complete, please check each item in the [Appendix Self-Check Checklist](#appendix-self-check-checklist).

---

## 4. Implemented Plugins Reference

The following plugins have been developed and integrated following this guide:

| Plugin | component_type | Description | Source |
|--------|----------------|-------------|--------|
| DrawBox | `custom.draw_box` | Canvas box selection interaction plugin. Supports area calculation, overlap detection, and box merge operations. Schema-driven form + non-HTTP execution + end-to-end full chain validation. | `agent-runtime/extensions/components/draw-box/` |

> After adding a new plugin, append a row to this table and link to the corresponding implementation documentation.

---

## Appendix: Self-Check Checklist

### A.1 Development Self-Check

Before submitting, verify each item:

**File Integrity**:
- [ ] `component.json` exists and is valid JSON
- [ ] `.py` file exists and has no syntax errors
- [ ] `init.sql` exists and uses standard `INSERT` statement (fixed primary key, no database-specific idempotent syntax)

**Naming and Constraints**:
- [ ] `component.json` `type` uses `custom.` prefix
- [ ] `classInfo.className` matches the class name in the `.py` file
- [ ] `classInfo.filePath` does not contain `..` and is not an absolute path

**Interface Contract**:
- [ ] Python class extends `PluginBase`
- [ ] Implements `async def invoke(self, inputs: dict, **kwargs) -> dict`
- [ ] If streaming output is needed, overrides `async def stream(self, inputs: dict, **kwargs)` returning `AsyncIterator[str]`
- [ ] `invoke()` return value is a `dict` type
- [ ] `invoke()` includes `isinstance(str)` + `json.loads()` compatibility handling for `array`/`object` type parameters

**Database Registration**:
- [ ] `t_tool` table fields are complete: `call_mode` set to `custom`, `metadata` contains `{"component_type": "custom.xxx"}`
- [ ] `input_schema` parameter ids match the `inputs.get()` keys in Python `invoke()`
- [ ] All `type: "object"` parameters in `output_schema` include a `properties` field

### A.2 Integration Self-Check

Before submitting, verify each item:

- [ ] Integration method determined (source code integration / image integration)
- [ ] After service startup, plugin is visible in platform UI, can be added to agent, and chat invocation works correctly
- [ ] **If source code integration**: Plugin code placed in `agent-runtime/extensions/components/`, Python dependencies appended to repo `requirements.txt` and `pyproject.toml`, `init.sql` content merged into `dml.sql`
- [ ] **If image integration**: `Dockerfile.runtime.custom` prepared (with `COPY` + `pip install`) and `init.sql` executed against database
