# openjiuwen.core.component.tool_comp

## class openjiuwen.core.component.tool_comp.ToolComponentConfig

Configuration information for the Tool (plugin) component. Currently, this class does not define any concrete configuration fields and exists as a placeholder.

## class openjiuwen.core.component.tool_comp.ToolComponent

```python
class openjiuwen.core.component.tool_comp.ToolComponent(config: ToolComponentConfig)
```

The Tool component is used to invoke tools (including external APIs and local functions). It passes input parameters to the tool, executes the tool logic, and outputs the final execution result. This enables capabilities such as information search, web browsing, image generation, and file processing, thereby extending the capabilities of agents and workflows.

When invoking this component, the following constraints apply:

* **Input**:  
  The Tool component does not have fixed input parameters. Developers must ensure that the provided input parameters match the actual requirements of the bound tool.  
  Note:
  - The Tool component supports validating input parameter types based on the `params` (List[Param]) defined in the bound tool (`Tool`).  
  - If an input parameter cannot be converted to the type specified by `Param.type`, an exception is raised.
  - The Tool component also supports filling default values for required input parameters, based on the `params` definition of the bound tool. If a parameter is required but not provided to the Tool component, `Param.default_value` is used as the actual input value.

* **Output**:  
  The output includes a return code, an error message, and the execution result:
  - **error_code** (int): Return code of the tool execution. `0` indicates success; non-zero values indicate tool-specific execution errors.
  - **error_message** (str): Error message of the tool execution. Empty string on success; contains the corresponding error message on failure.
  - **data** (Any): The final execution result returned by the tool upon successful execution.

**Parameters**:

* **config** ([ToolComponentConfig](#class-openjiuwencorecomponenttool_comptoolcomponentconfig)): Configuration for the Tool component.

**Example**:

```python
>>> from openjiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
>>> tool_component = ToolComponent(ToolComponentConfig())
```

**Exceptions**:

* **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and resolution methods, see  
  [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

### bind_tool

```python
bind_tool(tool: Tool)
```

Bind exactly one tool (including an external API or a local function) to the Tool component.

**Parameters**:

* **tool** ([Tool](../utils/tool/base.md#class-openjiuwencoreutilstoolbasetool)): A tool object (external API or local function) that implements the actual business logic executed by the Tool component.

**Example**:

After creating a Tool component, bind a tool to it (using a third-party plugin service as an example):

```python
>>> import asyncio
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.utils.tool.param import Param
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> workflow = Workflow()
>>> start_component = Start()
>>> end_component = End()
>>> 
>>> tool_component = ToolComponent(ToolComponentConfig())
>>> weather_tool = RestfulApi(
...     name="WeatherReporter",
...     description="Weather query plugin",
...     params=[
...         Param(name="location", description="Location", type="string", required=True),
...         Param(name="date", description="Date", type="string", required=True),
...     ],
...     path="<url of restful api>",
...     headers={},
...     method="GET",
...     response=[],
... )
>>> tool_component = tool_component.bind_tool(weather_tool)
>>> # Add the Tool component to the workflow via Workflow.add_workflow_comp.
>>> # The component is named "tool", and its input parameters include the plugin inputs `location` and `date`.
>>> workflow.set_start_comp("start", start_component, inputs_schema={"location": "${location}", "date": "${date}"})
>>> workflow.set_end_comp("end", end_component, inputs_schema={"output": "${tool.data}"})
>>> workflow.add_workflow_comp(
...     "tool",
...     tool_component,
...     inputs_schema={"location": "${start.location}", "date": "${start.date}"},
... )
>>> workflow.add_connection("start", "tool")
>>> workflow.add_connection("tool", "end")
>>> result = asyncio.run(
...     workflow.invoke(
...         {"location": "hangzhou", "date": "2025-08-01", "conversation_id": "c123"},
...         WorkflowRuntime()
...     )
... )
```

If the plugin service executes successfully, the Tool component output has `error_code` set to `0`, an empty `error_message`, and `data` containing the execution result:
```json
{
    "error_code": 0,
    "error_message": "",
    "data": {
        "city": "Shanghai",
        "country": "CN",
        "feels_like": 36.21,
        "humidity": 86,
        "temperature": 29.21,
        "weather": "Cloudy",
        "wind_speed": 5.81
    }
}
```

If the plugin service execution fails, the Tool component outputs the corresponding tool-specific error code and error message:
```json
{
    "error_code": 10000,
    "error_message": "plugin service unavailable",
    "data": ""
}
```