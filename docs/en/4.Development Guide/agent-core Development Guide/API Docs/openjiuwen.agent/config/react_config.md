

# openjiuwen.agent.config.react_config

## class openjiuwen.agent.config.react_config.ConstrainConfig

```python
openjiuwen.agent.config.react_config.ConstrainConfig(
    reserved_max_chat_rounds: int = 10,
    max_iteration: int = 5
)
```

The **ConstrainConfig** class is used to configure constraint parameters when creating an Agent.

### **Parameters**:

* **reserved_max_chat_rounds** (int, optional):
  The maximum number of conversation rounds to retain.
  The value must be greater than 0.
  Default value: **10**.

* **max_iteration** (int, optional):
  The maximum number of iterations allowed.
  The value must be greater than 0.
  Default value: **5**.

### **Examples**:

```python
>>> from openjiuwen.agent.config.react_config import ConstrainConfig
>>> 
>>> # Create a constraint configuration using default values
>>> constrain_config = ConstrainConfig()
>>> print(f"Max chat rounds: {constrain_config.reserved_max_chat_rounds}")  # Output: 10
Max chat rounds: 10
>>> print(f"Max iterations: {constrain_config.max_iteration}")  # Output: 5
Max iterations: 5
>>> 
>>> # Create a custom constraint configuration
>>> custom_constrain = ConstrainConfig(
...     reserved_max_chat_rounds=20,
...     max_iteration=10
... )
>>> print(f"Custom max chat rounds: {custom_constrain.reserved_max_chat_rounds}")  # Output: 20
Custom max chat rounds: 20
>>> print(f"Custom max iterations: {custom_constrain.max_iteration}")  # Output: 10
Custom max iterations: 10
```

---

## class openjiuwen.agent.config.react_config.IntentDetectionConfig

```python
openjiuwen.agent.config.react_config.IntentDetectionConfig(
    intent_detection_template: List[Dict] = [],
    default_class: str = "分类1",
    enable_input: bool = True,
    enable_history: bool = False,
    chat_history_max_turn: int = 5,
    category_list: List[str] = [],
    user_prompt: str = "",
    example_content: List[str] = []
)
```

**IntentDetectionConfig** is a **reserved class** used to configure parameters for intent detection.
It is currently a placeholder interface and is not yet in use.

---

## class openjiuwen.agent.config.react_config.ReActAgentConfig

```python
openjiuwen.agent.config.react_config.ReActAgentConfig(
    id: str,
    version: str,
    description: str,
    workflows: List[WorkflowSchema] = [],
    model: Optional[ModelConfig] = None,
    tools: List[str] = [],
    controller_type: ControllerType = ControllerType.ReActController,
    model: ModelConfig = None,
    prompt_template_name: str = "react_system_prompt",
    prompt_template: List[Dict] = [],
    constrain: ConstrainConfig = ConstrainConfig(),
    plugins: List[PluginSchema] = [],
    memory_config: MemoryConfig
)
```

The **ReActAgentConfig** class is used to configure all parameters of a ReActAgent.

### **Parameters**:

* **id** (str):
  The unique identifier of the agent.

* **version** (str):
  The version number of the agent.

* **description** (str):
  A description of the agent.

* **workflows** (List[[WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema)], optional):
  A reserved configuration item.
  A list of workflow descriptions registered to the ReActAgent.
  Default value: `[]`, indicating that there are no callable workflows.

* **model** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig), optional):
  Model configuration.
  Default value: `None`, indicating that no large language model is configured.
  **Note**: If the model is not configured or is configured incorrectly, the component will raise an exception.

* **tools** (List[str], optional):
  A list of tool descriptions supported by the agent.
  Default value: `[]`, indicating that there are no callable tools.

* **controller_type** ([ControllerType](../common/enum.md#class-openjiuwenagentcommonenumcontrollertype), optional):
  The controller type.
  This must be `ControllerType.ReActController`.
  Default value: `ControllerType.ReActController`.

* **prompt_template_name** (str, optional):
  The name of the prompt template.
  Default value: `react_system_prompt`.

* **prompt_template** (List[Dict], optional):
  A list of prompt templates.
  Each dictionary has the format:
  `dict(role="system", content="You are an AI assistant...")`
  The value of `role` can be `system` or `user`.

  * `system`: system prompt
  * `user`: user prompt
    Default value: `[]`.

* **constrain** ([ConstrainConfig](#class-openjiuwenagentconfigreact_configconstrainconfig), optional):
  Constraint configuration.
  Default value: `ConstrainConfig()`.

* **plugins** (List[[PluginSchema](../common/schema.md#class-openjiuwenagentcommonschemapluginschema)], optional):
  A list of plugin descriptions supported by the agent.
  Default value: `[]`, indicating that there are no callable plugins.

* **memory_config** ([MemoryConfig](../../openjiuwen.core/memory/config.md#openjiuwencorememoryconfig), optional):
  Group-level memory configuration (e.g., window size, topic profiling, etc.).
  Default value: `MemoryConfig()`.

### **Examples**:

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
...     return ModelConfig(
...         model_provider=MODEL_PROVIDER,
...         model_info=BaseModelInfo(
...             model=MODEL_NAME,
...             api_base=API_BASE,
...             api_key=API_KEY,
...             temperature=0.7,
...             top_p=0.9,
...             timeout=30
...         )
...     )
>>> 
>>> def _create_tool_schema():
...     tool_info = PluginSchema(
...         name='WeatherReporter',
...         description='Weather query plugin',
...         inputs={
...             "type": "object",
...             "properties": {
...                 "location": {
...                     "type": "string",
...                     "description": "Location for the weather query.\nNote: The location name must be in English",
...                     "required": True
...                 },
...                 "date": {
...                     "type": "string",
...                     "description": "Date of the weather query, in YYYY-MM-DD format",
...                     "required": True
...                 }
...             }
...         }
...     )
...     return tool_info
>>> 
>>> def _create_prompt_template():
...     system_prompt = (
...         "You are an AI assistant. Call appropriate tools when necessary to help me complete tasks! "
...         "Today's date is: {}\n"
...         "Note: 1. If no specific date is provided in the user request, today will be used by default."
...     )
...     return [
...         dict(role="system", content=system_prompt.format(build_current_date()))
...     ]
>>> 
>>> tools_schema = [_create_tool_schema()]
>>> model_config = _create_model()
>>> prompt_template = _create_prompt_template()
>>> 
>>> # Use default constraint configuration
>>> react_agent_config = ReActAgentConfig(
...     id="react_agent_123",
...     version="0.0.1",
...     description="AI Assistant",
...     plugins=tools_schema,
...     workflows=[],
...     model=model_config,
...     prompt_template=prompt_template
... )
>>> 
>>> # Use custom constraint configuration
>>> custom_constrain = ConstrainConfig(
...     reserved_max_chat_rounds=20,
...     max_iteration=10
... )
>>> 
>>> react_agent_config_custom = ReActAgentConfig(
...     id="react_agent_456",
...     version="0.0.2",
...     description="AI Assistant with Custom Constraints",
...     plugins=tools_schema,
...     workflows=[],
...     model=model_config,
...     prompt_template=prompt_template,
...     constrain=custom_constrain
... )
>>> 
>>> print(f"Agent ID: {react_agent_config.id}")
Agent ID: react_agent_123
>>> print(f"Max chat rounds: {react_agent_config.constrain.reserved_max_chat_rounds}")
Max chat rounds: 10
>>> print(f"Max iterations: {react_agent_config.constrain.max_iteration}")
Max iterations: 5
```


