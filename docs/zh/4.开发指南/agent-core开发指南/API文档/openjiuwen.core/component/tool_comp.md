# openjiuwen.core.component.tool_comp

## class openjiuwen.core.component.tool_comp.ToolComponentConfig

插件组件的配置信息，当前不涉及具体配置，仅作为预留。

## class openjiuwen.core.component.tool_comp.ToolComponent

```python
class openjiuwen.core.component.tool_comp.ToolComponent(config: ToolComponentConfig)
```

插件组件，可调用工具（包括外部API、本地函数）：向工具输入参数、执行工具逻辑、最终输出工具的执行结果。实现如搜索信息、浏览网页、生成图像、文件处理等功能，从而扩展智能体、工作流的能力。

调用该组件时需要遵循以下约束：

* 输入：插件组件的输入没有固定参数，由开发者根据插件的实际输入，保证正确的输入参数。注意：插件组件支持校验工具输入参数类型，校验依据是插件组件绑定工具(Tool)的params(List[Param])，如果插件组件的输入参数类型无法转化为`Param.type`指定的类型，则抛出异常；插件组件也支持填充必选输入参数的默认值，填充依据也是插件组件绑定工具(Tool)的params(List[Param])，如果输入参数是必选参数、但未输入插件组件，则插件组件用`Param.default_value`作为该输入参数的实际输入值。
* 输出：包含返回码、错误信息和执行结果。具体如下：
  
  * **error_code**(int)：插件组件的执行结果的返回码，执行成功为0，其他为插件执行的实际错误码。
  * **error_message**(str)：插件组件的执行结果的错误信息，如果执行成功，为空字符串；如果执行失败，为相应的错误码。
  * **data**(Any)：插件组件执行成功后，最终的执行结果。

**参数**：

* ​**config**([ToolComponentConfig](#class-openjiuwencorecomponenttool_comptoolcomponentconfig))​：插件组件的配置信息。

**样例**：

```python
>>> from openjiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
>>> tool_component = ToolComponent(ToolComponentConfig())
```

**异常：**

* **JiuWenBaseException**​：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

### bind_tool

```python
bind_tool(tool: Tool)
```

插件组件绑定唯一的一个工具（包括外部API、本地函数）。

**参数**：

* **tool**([Tool](../utils/tool/base.md#class-openjiuwencoreutilstoolbasetool))：工具对象（包括外部API、本地函数），实际执行插件组件的业务逻辑。

**样例**：

创建一个插件组件成功后，绑定一个工具（以调用三方插件服务对象为例）。

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
...             name="WeatherReporter",
...             description="天气查询插件",
...             params=[
...                 Param(name="location", description="地点", type="string", required=True),
...                 Param(name="date", description="日期", type="string", required=True),
...             ],
...             path="<url of restful api>",
...             headers={},
...             method="GET",
...             response=[],
...         )
>>> tool_component = tool_component.bind_tool(weather_tool)
>>> # 通过`Workflow`的`add_workflow_comp`方法将插件组件对象添加到工作流中，定义组件名称为"tool"，输入参数中包含了插件的入参`location`和`date`。
>>> workflow.set_start_comp("start", start_component, inputs_schema={"location": "${location}", "date": "${date}"})
>>> workflow.set_end_comp("end", end_component, inputs_schema={"output": "${tool.data}"})
>>> workflow.add_workflow_comp(
...             "tool",
...             tool_component,
...             inputs_schema={"location": "${start.location}", "date": "${start.date}"},
...         )
>>> workflow.add_connection("start", "tool")
>>> workflow.add_connection("tool", "end")
>>> result = asyncio.run(workflow.invoke({"location": "hangzhou", "date": "2025-08-01", "conversation_id": "c123"}, WorkflowRuntime()))

>>> # 若插件服务返回成功，则插件组件输出的执行错误码`error_code`为0，插件执行错误的原因`error_message`为空，`data`为插件运行结果
{
    "error_code": 0,
    "error_message": "",
    "data": {"city":"Shanghai","country":"CN","feels_like":36.21,"humidity":86,"temperature":29.21,"weather":"多云","wind_speed":5.81}
}

>>> # 若插件服务返回失败，则插件组件输出的返回具体的插件执行错误码`error_code`和插件执行错误的原因`error_message
{
    "error_code": 10000,  # 插件的自定义错误码
    "error_message": "plugin service unavailable",  # 插件的自定义错误错误信息
    "data": ""
}
```
