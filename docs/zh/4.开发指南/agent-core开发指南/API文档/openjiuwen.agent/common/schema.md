# openjiuwen.agent.common.schema

## class openjiuwen.agent.common.schema.WorkflowSchema

```python
openjiuwen.agent.common.schema.WorkflowSchema(id: str = "", name: str = "", description: str = "", version: str = "", inputs: Dict[str, Any] = {})
```

WorkflowSchema类用于定义工作流的元数据和配置信息。

**参数**：

- **id**(str)：工作流的唯一标识符。
- **name**(str)：工作流的名称。
- **description**(str)：工作流的描述信息，一般是工作流的功能描述。
- **version**(str)：工作流的版本号。
- **inputs**(Dict[str, Any], 可选)：工作流的输入参数定义。默认值：{}，表示工作流的运行不需要参数输入。输入参数可以为空、一个或者多个，包含以下字段：
  - **type**(str, 可选)：数据类型，通常为对象类型，用于描述入参的结构。默认值：`"object"`。
  - **description**(Dict[str, Any], 可选)：工具参数输入属性，键为参数名称，值为该参数的类型、约束、描述等。此项需要与工具函数的实际参数输入一一对应，默认值：`{}`。
  - **required**(bool, 可选)：输入字段是否为必选。默认值：`False`。

**样例**：

```python
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> 
>>> # 创建简单的工作流schema
>>> workflow_schema = WorkflowSchema(
...     id="weather_workflow",
...     name="weather",
...     description="天气查询工作流",
...     version="1.0"
... )
>>> 
>>> # 创建带输入参数的工作流schema
>>> workflow_schema_with_inputs = WorkflowSchema(
...     id="test_weather_agent",
...     name="weather",
...     description="天气查询工作流",
...     version="1.0",
...     inputs={
...         "query": {
...             "type": "string",
...             "description": "用户输入",
...             "required": True
...         }
...     }
... )
>>> 
>>> print(f"工作流ID: {workflow_schema_with_inputs.id}")
工作流ID: test_weather_agent
>>> print(f"工作流名称: {workflow_schema_with_inputs.name}")
工作流名称: weather
>>> print(f"工作流版本: {workflow_schema_with_inputs.version}")
工作流版本: 1.0
```

## class openjiuwen.agent.common.schema.PluginSchema

```python
openjiuwen.agent.common.schema.PluginSchema(id: str = "", version: str = "", name: str = "", description: str = "", inputs: Dict[str, Any] = {})
```

PluginSchema类用于定义插件的元数据和配置信息。

**参数**：

- **id**(str)：插件的唯一标识符。
- **name**(str)：插件的名称。
- **description**(str)：插件的描述信息，一般是插件的功能描述。
- **version**(str)：插件的版本号。
- **inputs**(Dict[str, Any], 可选)：插件的输入参数定义。默认值：{}，表示插件的运行不需要参数输入。输入参数可以为空、一个或者多个，包含以下字段：
  - **type**(str, 可选)：数据类型，通常为对象类型，用于描述入参的结构。默认值：`"object"`。
  - **description**(Dict[str, Any], 可选)：工具参数输入属性，键为参数名称，值为该参数的类型、约束、描述等。此项需要与工具函数的实际参数输入一一对应，默认值：`{}`。
  - **required**(bool, 可选)：输入字段是否为必选。默认值：`False`。

**样例**：

```python
>>> from openjiuwen.agent.common.schema import PluginSchema
>>> 
>>> # 创建天气查询插件schema
>>> weather_plugin_schema = PluginSchema(
...     name='WeatherReporter',
...     description='天气查询插件',
...     inputs={
...         "type": "object",
...         "properties": {
...             "location": {
...                 "type": "string",
...                 "description": "天气查询的地点。\n注意：地点名称必须为英文",
...                 "required": True
...             },
...             "date": {
...                 "type": "string",
...                 "description": "天气查询的时间，格式为YYYY-MM-DD",
...                 "required": True
...             }
...         }
...     }
... )
>>> 
>>> 
>>> print(f"插件名称: {weather_plugin_schema.name}")
插件名称: WeatherReporter
>>> print(f"插件描述: {weather_plugin_schema.description}")
插件描述: 天气查询插件
```

## class openjiuwen.agent.common.schema.McpSchema

```python
openjiuwen.agent.common.schema.McpSchema(id: str = "", name: str = "", description: str = "", inputs: Dict[str, Any] = {})
```

McpSchema类用于定义MCP（Model Context Protocol）的元数据和配置信息。

**参数**：

- **id**(str)：MCP的唯一标识符。
- **name**(str)：MCP的名称。
- **description**(str)：MCP的描述信息，一般是MCP的功能描述。
- **inputs**(Dict[str, Any], 可选)：MCP的输入参数定义。默认值：{}，表示MCP的运行不需要参数输入。输入参数可以为空、一个或者多个，包含以下字段：
  - **type**(str, 可选)：数据类型，通常为对象类型，用于描述入参的结构。默认值：`"object"`。
  - **description**(Dict[str, Any], 可选)：工具参数输入属性，键为参数名称，值为该参数的类型、约束、描述等。此项需要与工具函数的实际参数输入一一对应，默认值：`{}`。
  - **required**(bool, 可选)：输入字段是否为必选。默认值：`False`。

**样例**：

```python
>>> from openjiuwen.agent.common.schema import McpSchema
>>> 
>>> # 创建MCP schema
>>> mcp_schema = McpSchema(
...     id="mcp_001",
...     name="example_mcp",
...     description="示例MCP配置",
...     inputs={
...         "type": "object",
...         "properties": {
...             "query": {
...                 "type": "string",
...                 "description": "用户查询",
...                 "required": True
...             }
...         }
...     },
... )
>>> 
>>> print(f"MCP ID: {mcp_schema.id}")
MCP ID: mcp_001
>>> print(f"MCP名称: {mcp_schema.name}")
MCP名称: example_mcp
>>> print(f"MCP描述: {mcp_schema.description}")
MCP描述: 示例MCP配置
```
