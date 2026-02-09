# openjiuwen.agent.config.react_config

## class openjiuwen.agent.config.react_config.ConstrainConfig

```python
openjiuwen.agent.config.react_config.ConstrainConfig(reserved_max_chat_rounds: int = 10, max_iteration: int = 5)
```

ConstrainConfig类用于配置Agent创建时的约束限制参数。

**参数**：

- **reserved_max_chat_rounds**(int, 可选)：保留的最大对话轮数。配置值必须大于0，默认值：10。
- **max_iteration**(int, 可选)：最大迭代次数。配置值必须大于0，默认值：5。

**样例**：

```python
>>> from openjiuwen.agent.config.react_config import ConstrainConfig
>>> 
>>> # 使用默认值创建约束配置
>>> constrain_config = ConstrainConfig()
>>> print(f"最大对话轮数: {constrain_config.reserved_max_chat_rounds}")  # 输出: 10
最大对话轮数: 10
>>> print(f"最大迭代次数: {constrain_config.max_iteration}")  # 输出: 5
最大迭代次数: 5
>>> 
>>> # 自定义约束配置
>>> custom_constrain = ConstrainConfig(
...     reserved_max_chat_rounds=20,
...     max_iteration=10
... )
>>> print(f"自定义最大对话轮数: {custom_constrain.reserved_max_chat_rounds}")  # 输出: 20
自定义最大对话轮数: 20
>>> print(f"自定义最大迭代次数: {custom_constrain.max_iteration}")  # 输出: 10
自定义最大迭代次数: 10
```

## class openjiuwen.agent.config.react_config.IntentDetectionConfig

```python
openjiuwen.agent.config.react_config.IntentDetectionConfig(intent_detection_template: List[Dict] = [], default_class: str = "分类1", enable_input: bool = True, enable_history: bool = False, chat_history_max_turn: int = 5, category_list: List[str] = [], user_prompt: str = "", example_content: List[str] = [])
```

IntentDetectionConfig为​**预留类**，用于配置意图检测功能的参数，当前为预留定义接口，当前还未使用。

## class openjiuwen.agent.config.react_config.ReActAgentConfig

```python
openjiuwen.agent.config.react_config.ReActAgentConfig(id: str, version: str, description: str, workflows: List[WorkflowSchema] = [], model: Optional[ModelConfig] = None, tools: List[str] = [], controller_type: ControllerType = ControllerType.ReActController, model: ModelConfig = None, prompt_template_name: str = "react_system_prompt", prompt_template: List[Dict] = [], constrain: ConstrainConfig = ConstrainConfig(), plugins: List[PluginSchema] = [], memory_config: MemoryConfig)
```

ReActAgentConfig类用于配置ReActAgent的所有参数。

**参数**：

- **id**(str)：agent的唯一标识符。
- **version**(str)：agent的版本号。
- **description**(str)：agent的描述信息。
- **workflows**(List[[WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema)], 可选)：预留配置项，注册到ReActAgent中的工作流描述信息列表。默认值：[]，表示没有可调用的workflow。
- **model**([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig), 可选)：模型配置。默认值：`None`，表示未配置大模型。注意：未配置大模型、或配置大模型错误，组件将抛出异常。
- **tools**(List[[str]], 可选)：agent支持的工具描述信息列表。默认值：[]，表示没有可调用的工具。
- **controller_type**([ControllerType](../common/enum.md#class-openjiuwenagentcommonenumcontrollertype), 可选)：控制器类型。此处必须是`ControllerType.ReActController`。默认值：`ControllerType.ReActController`。
- **prompt_template_name**(str, 可选)：提示词模板名称。默认值：`react_system_prompt`。
- **prompt_template**(List[Dict], 可选)：提示词模板列表。dict格式为`dict(role="system", content="你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！")`，role的取值可为`system`或`user`，为`system`时表示是系统提示词，为`user`时表示是用户提示词。默认值：[]。
- **constrain**([ConstrainConfig](#class-openjiuwenagentconfigreact_configconstrainconfig), 可选)：约束配置。默认值：`ConstrainConfig()`。
- **plugins**(List[[PluginSchema](../common/schema.md#class-openjiuwenagentcommonschemapluginschema)], 可选)：agent支持的插件描述信息列表。默认值：[]，表示没有可调用的插件。
- **memory_config**([MemoryConfig](../../openjiuwen.core/memory/config.md#openjiuwencorememoryconfig), 可选)：群组级记忆设置（如窗口大小、话题画像等）。默认值：`MemoryConfig()`。

**样例**：

```python
>>> import os
>>> from datetime import datetime
>>> from openjiuwen.agent.common.schema import PluginSchema
>>> from openjiuwen.agent.config.react_config import ReActAgentConfig, ConstrainConfig
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> def build_current_date():
...     current_datetime = datetime.now()
...     return current_datetime.strftime("%Y-%m-%d")
>>> 
>>> def _create_model():
...     return ModelConfig(model_provider=MODEL_PROVIDER,
...                        model_info=BaseModelInfo(
...                            model=MODEL_NAME,
...                            api_base=API_BASE,
...                            api_key=API_KEY,
...                            temperature=0.7,
...                            top_p=0.9,
...                            timeout=30
...                        ))
>>> 
>>> def _create_tool_schema():
...     tool_info = PluginSchema(
...         name='WeatherReporter',
...         description='天气查询插件',
...         inputs={
...             "type": "object",
...             "properties": {
...                 "location": {
...                     "type": "string",
...                     "description": "天气查询的地点。\n注意：地点名称必须为英文",
...                     "required": True
...                 },
...                 "date": {
...                     "type": "string",
...                     "description": "天气查询的时间，格式为YYYY-MM-DD",
...                     "required": True
...                 }
...             }
...         }
...     )
...     return tool_info
>>> 
>>> def _create_prompt_template():
...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
...     return [
...         dict(role="system", content=system_prompt.format(build_current_date()))
...     ]
>>> 
>>> tools_schema = [_create_tool_schema()]
>>> model_config = _create_model()
>>> prompt_template = _create_prompt_template()
>>> 
>>> # 使用默认约束配置
>>> react_agent_config = ReActAgentConfig(
...     id="react_agent_123",
...     version="0.0.1",
...     description="AI助手",
...     plugins=tools_schema,
...     workflows=[],
...     model=model_config,
...     prompt_template=prompt_template
... )
>>> 
>>> # 使用自定义约束配置
>>> custom_constrain = ConstrainConfig(
...     reserved_max_chat_rounds=20,
...     max_iteration=10
... )
>>> 
>>> react_agent_config_custom = ReActAgentConfig(
...     id="react_agent_456",
...     version="0.0.2",
...     description="自定义约束的AI助手",
...     plugins=tools_schema,
...     workflows=[],
...     model=model_config,
...     prompt_template=prompt_template,
...     constrain=custom_constrain
... )
>>> 
>>> print(f"Agent ID: {react_agent_config.id}")
Agent ID: react_agent_123
>>> print(f"最大对话轮数: {react_agent_config.constrain.reserved_max_chat_rounds}")
最大对话轮数: 10
>>> print(f"最大迭代次数: {react_agent_config.constrain.max_iteration}")
最大迭代次数: 5
```
