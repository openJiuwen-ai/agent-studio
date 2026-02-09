
# openjiuwen.agent.common.schema

## class openjiuwen.agent.common.schema.WorkflowSchema

```python
openjiuwen.agent.common.schema.WorkflowSchema(
    id: str = "",
    name: str = "",
    description: str = "",
    version: str = "",
    inputs: Dict[str, Any] = {}
)
```

The `WorkflowSchema` class is used to define the metadata and configuration information of a workflow.

### Parameters

* **id** (str):
  A unique identifier for the workflow.

* **name** (str):
  The name of the workflow.

* **description** (str):
  A description of the workflow, usually explaining its functionality.

* **version** (str):
  The version number of the workflow.

* **inputs** (Dict[str, Any], optional):
  Definitions of the workflow input parameters.
  Default value: `{}`, indicating that the workflow does not require input parameters at runtime.

  Input parameters can be empty, or include one or more fields, each containing the following attributes:

  * **type** (str, optional):
    The data type, usually `"object"`, used to describe the structure of the input.
    Default value: `"object"`.

  * **description** (Dict[str, Any], optional):
    Describes the properties of the tool input parameters.
    The keys are parameter names, and the values define their types, constraints, descriptions, etc.
    This must correspond one-to-one with the actual input parameters of the tool function.
    Default value: `{}`.

  * **required** (bool, optional):
    Indicates whether the input field is required.
    Default value: `False`.

### Example

```python
from openjiuwen.agent.common.schema import WorkflowSchema

# Create a simple workflow schema
workflow_schema = WorkflowSchema(
    id="weather_workflow",
    name="weather",
    description="Weather query workflow",
    version="1.0"
)

# Create a workflow schema with input parameters
workflow_schema_with_inputs = WorkflowSchema(
    id="test_weather_agent",
    name="weather",
    description="Weather query workflow",
    version="1.0",
    inputs={
        "query": {
            "type": "string",
            "description": "User input",
            "required": True
        }
    }
)

print(f"Workflow ID: {workflow_schema_with_inputs.id}")
# Workflow ID: test_weather_agent
print(f"Workflow Name: {workflow_schema_with_inputs.name}")
# Workflow Name: weather
print(f"Workflow Version: {workflow_schema_with_inputs.version}")
# Workflow Version: 1.0
```

---

## class openjiuwen.agent.common.schema.PluginSchema

```python
openjiuwen.agent.common.schema.PluginSchema(
    id: str = "",
    version: str = "",
    name: str = "",
    description: str = "",
    inputs: Dict[str, Any] = {}
)
```

The `PluginSchema` class is used to define the metadata and configuration information of a plugin.

### Parameters

* **id** (str):
  A unique identifier for the plugin.

* **name** (str):
  The name of the plugin.

* **description** (str):
  A description of the plugin, usually explaining its functionality.

* **version** (str):
  The version number of the plugin.

* **inputs** (Dict[str, Any], optional):
  Definitions of the plugin input parameters.
  Default value: `{}`, indicating that the plugin does not require input parameters to run.

  Input parameters can be empty, or include one or more fields, each containing the following attributes:

  * **type** (str, optional):
    The data type, usually `"object"`, used to describe the structure of the input.
    Default value: `"object"`.

  * **description** (Dict[str, Any], optional):
    Describes the properties of the tool input parameters.
    The keys are parameter names, and the values define their types, constraints, descriptions, etc.
    This must correspond one-to-one with the actual input parameters of the tool function.
    Default value: `{}`.

  * **required** (bool, optional):
    Indicates whether the input field is required.
    Default value: `False`.

### Example

```python
from openjiuwen.agent.common.schema import PluginSchema

# Create a weather query plugin schema
weather_plugin_schema = PluginSchema(
    name='WeatherReporter',
    description='Weather query plugin',
    inputs={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Location for the weather query.\nNote: The location name must be in English",
                "required": True
            },
            "date": {
                "type": "string",
                "description": "Date of the weather query, in YYYY-MM-DD format",
                "required": True
            }
        }
    }
)

print(f"Plugin Name: {weather_plugin_schema.name}")
# Plugin Name: WeatherReporter
print(f"Plugin Description: {weather_plugin_schema.description}")
# Plugin Description: Weather query plugin
```

---

## class openjiuwen.agent.common.schema.McpSchema

```python
openjiuwen.agent.common.schema.McpSchema(
    id: str = "",
    name: str = "",
    description: str = "",
    inputs: Dict[str, Any] = {}
)
```

The `McpSchema` class is used to define the metadata and configuration information of MCP (Model Context Protocol).

### Parameters

* **id** (str):
  A unique identifier for the MCP.

* **name** (str):
  The name of the MCP.

* **description** (str):
  A description of the MCP, usually explaining its functionality.

* **inputs** (Dict[str, Any], optional):
  Definitions of the MCP input parameters.
  Default value: `{}`, indicating that the MCP does not require input parameters to run.

  Input parameters can be empty, or include one or more fields, each containing the following attributes:

  * **type** (str, optional):
    The data type, usually `"object"`, used to describe the structure of the input.
    Default value: `"object"`.

  * **description** (Dict[str, Any], optional):
    Describes the properties of the tool input parameters.
    The keys are parameter names, and the values define their types, constraints, descriptions, etc.
    This must correspond one-to-one with the actual input parameters of the tool function.
    Default value: `{}`.

  * **required** (bool, optional):
    Indicates whether the input field is required.
    Default value: `False`.

### Example

```python
from openjiuwen.agent.common.schema import McpSchema

# Create an MCP schema
mcp_schema = McpSchema(
    id="mcp_001",
    name="example_mcp",
    description="Example MCP configuration",
    inputs={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "User query",
                "required": True
            }
        }
    },
)

print(f"MCP ID: {mcp_schema.id}")
# MCP ID: mcp_001
print(f"MCP Name: {mcp_schema.name}")
# MCP Name: example_mcp
print(f"MCP Description: {mcp_schema.description}")
# MCP Description: Example MCP configuration
```


