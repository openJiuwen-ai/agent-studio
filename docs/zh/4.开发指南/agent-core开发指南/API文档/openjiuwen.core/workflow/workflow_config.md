# openjiuwen.core.workflow.workflow_config

## class openjiuwen.core.workflow.workflow_config.WorkflowSpec

负责工作流结构和组件关系的定义，内部graph结构，不建议用户手动设置。

* **comp_configs**(Dict[str，NodeSpec])：工作流中所有组件的配置信息，默认值：`{}`。
* **stream_edges**(Dict[str，list[str]])：工作流中组件之间的连接关系，定义数据流的边关系，默认值：`{}`。

## class openjiuwen.core.workflow.workflow_config.WorkflowMetadata

工作流元信息数据类，用于描述工作流的基本属性。

* **name**(str)：工作流名字。默认值：`""`。
* **id**(str)：工作流的id，唯一标识。默认值：`""`，此时系统会赋一个uuid。
* **version**(str)：工作流的版本号。默认值：`""`。
* **description**(str)：工作流的描述信息。默认值：`""`。

**样例**：

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowMetadata
>>> 
>>> metadata = WorkflowMetadata(id='fick_worklfow_id', name='工作流', version='version_1',  description='这是一个案例')
```

## class openjiuwen.core.workflow.workflow_config.ComponentAbility

工作流组件的能力枚举类。

- **INVOKE**：批数据处理成批数据的能力。
- **STREAM**：批数据处理成流数据的能力。
- **COLLECT**：流数据理成批数据的能力。
- **TRANSFORM**：流数据处理成流数据的能力。

## class openjiuwen.core.workflow.workflow_config.WorkflowInputsSchema

用于定义工作流工具插件的输入参数结构。此结构将工作流视为一个工具插件，并描述其输入参数的类型、约束和描述信息。

- **type**(str)：工具类型，必须为`object`类型。默认值：`""`。
- **properties**(Dict[str, Any])：定义工作流的输入参数描述，键为参数名称，值为该参数的类型`type`、描述`description`、是否必选`required`等。默认值：`{}`，表示无可选入参。
- **required**(List[str])：工作流的必选输入参数列表。默认值：`[]`，代表未给工作流工具传入参。注意：若工作流工具插件要求但未提供可能影响效果，

**样例**：

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowInputsSchema
>>> 
>>> workflow_inputs_schema = WorkflowInputsSchema(
...     type="object",
...     properties={
...         "query": {
...             "type": "string",  # 可为 string、integer、array、object、list、number
...             "description": "用户输入",
...             "required": True  # 标识该参数是否为三方插件的必填项。若为True，则要求LLM基于当前properties对象自动生成该插件的必需参数
...         }
...     },
...     required=['query']
... )
...
```

## class openjiuwen.core.workflow.workflow_config.WorkflowConfig

Workflow的配置结构数据类。

* **metadata**([WorkflowMetadata](./workflow_config.md#class-openjiuwencoreworkflowworkflow_configworkflowmetadata))：工作流的meta信息，例如id，version，type等。默认值：WorkflowMetadata()。
* **stream_timeout**(float)：流式消息帧间超时时间。单位：秒。默认值：0.2秒。
* **workflow_inputs_schema**(Optional[[WorkflowInputsSchema](./workflow_config.md#class-openjiuwencoreworkflowworkflow_configworkflowinputsschema)])：将工作流作为工具插件的输入参数结构信息。

**样例**：

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowInputsSchema, WorkflowConfig, WorkflowMetadata
>>> 
>>> # 定义工作流调用输入的
>>> workflow_inputs_schema = WorkflowInputsSchema(
...     type="object",
...     properties={
...         "query": {
...             "type": "string",
...             "description": "用户输入",
...             "required": True
...         }
...     },
...     required=['query']
... )
...
>>> # 创建WorkflowConfig
>>> workflow_config = WorkflowConfig(
...     metadata=WorkflowMetadata(id='fick_worklfow_id', name='工作流', version='version_1',  description='这是一个案例'), workflow_inputs_schema=workflow_inputs_schema)
```

## type alias openjiuwen.core.workflow.workflow_config.Transformer:Callable[[Any], Any]

`Transformer`为组件的输入或输出转换的方法。该函数接受任意类型的输入，并返回任意类型的输出。

**样例**:

```python
>>> from typing import Any
>>> from openjiuwen.core.runtime.state import Transformer
>>> 
>>> def demo_transformer(data: Any) -> Any:
...      return {'a': 'a', 'b': 'b'}
... 
>>> transformer: Transformer = demo_transformer
```


