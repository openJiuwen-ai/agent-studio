# openjiuwen.agent.config.base

## class openjiuwen.agent.config.base.AgentConfig

```python
openjiuwen.agent.config.base.AgentConfig(id: str = "", version: str = "", description: str = "", controller_type: ControllerType = ControllerType.Undefined, workflows: List[WorkflowSchema] = [], model: Optional[ModelConfig] = None, tools: List[str] = [])
```

AgentConfig类是所有Agent配置的基础类，定义了Agent的基本属性。

**参数**：

- **id**(str)：agent的唯一标识符。
- **version**(str)：agent的版本号。
- **description**(str)：agent的功能或使用场景描述信息。
- **controller_type**([ControllerType](../common/enum.md#class-openjiuwenagentcommonenumcontrollertype), 可选)：控制器类型。默认值：`ControllerType.Undefined`，表示是没有实现的控制器类型。
- **workflows**(List[[WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema)], 可选)：agent使用的工作流描述信息列表。默认值：[]，表示没有可调用的工作流。
- **model**([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig), 可选)：模型配置。默认值：`None`，表示未配置大模型。注意：未配置大模型、或配置大模型错误，组件将抛出异常。
- **tools**(List[[str]], 可选)：agent支持的工具描述信息列表。默认值：[]，表示没有可调用的工具。

**样例**：

```python
>>> from openjiuwen.agent.common.schema import WorkflowSchema, PluginSchema
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.config.base import AgentConfig
>>> 
>>> # 创建简单的Agent配置
>>> agent_config = AgentConfig(
...     id="test_agent_001",
...     version="1.0.0",
...     description="测试Agent",
...     controller_type=ControllerType.Undefined
... )
>>> 
>>> print(f"Agent ID: {agent_config.id}")
Agent ID: test_agent_001
>>> print(f"Agent版本: {agent_config.version}")
Agent版本: 1.0.0
>>> print(f"控制器类型: {agent_config.controller_type}")
控制器类型: ControllerType.Undefined
>>> 
>>> # 创建带插件和工作流的Agent配置
>>> plugin_schema = PluginSchema(
...     name='WeatherReporter',
...     description='天气查询插件'
... )
>>> 
>>> workflow_schema = WorkflowSchema(
...     id="workflow_001",
...     name="weather_workflow",
...     description="天气查询工作流",
...     version="1.0"
... )
>>> 
>>> agent_config_full = AgentConfig(
...     id="full_agent_001",
...     version="2.0.0",
...     description="完整配置的Agent",
...     controller_type=ControllerType.ReActController,
...     tools=["WeatherReporter"],
...     workflows=[workflow_schema]
... )
>>> 
>>> print(f"插件数量: {len(agent_config_full.tools)}")
插件数量: 1
>>> print(f"工作流数量: {len(agent_config_full.workflows)}")
工作流数量: 1
```
