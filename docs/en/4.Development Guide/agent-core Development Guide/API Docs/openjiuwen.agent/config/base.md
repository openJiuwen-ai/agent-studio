

# openjiuwen.agent.config.base

## class openjiuwen.agent.config.base.AgentConfig

```python
openjiuwen.agent.config.base.AgentConfig(
    id: str = "",
    version: str = "",
    description: str = "",
    controller_type: ControllerType = ControllerType.Undefined,
    workflows: List[WorkflowSchema] = [],
    model: Optional[ModelConfig] = None,
    tools: List[str] = []
)
```

The **AgentConfig** class is the base class for all Agent configurations and defines the fundamental properties of an Agent.

### **Parameters**:

* **id** (str):
  The unique identifier of the agent.

* **version** (str):
  The version number of the agent.

* **description** (str):
  A description of the agent’s functionality or usage scenario.

* **controller_type** ([ControllerType](../common/enum.md#class-openjiuwenagentcommonenumcontrollertype), optional):
  The type of controller.
  Default value: `ControllerType.Undefined`, indicating that no controller type has been implemented.

* **workflows** (List[[WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema)], optional):
  A list of workflow descriptions used by the agent.
  Default value: `[]`, indicating that there are no callable workflows.

* **model** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig), optional):
  Model configuration.
  Default value: `None`, indicating that no large language model is configured.
  **Note**: If the model is not configured or is configured incorrectly, the component will raise an exception.

* **tools** (List[str], optional):
  A list of tool descriptions supported by the agent.
  Default value: `[]`, indicating that there are no callable tools.

### **Examples**:

```python
>>> from openjiuwen.agent.common.schema import WorkflowSchema, PluginSchema
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.config.base import AgentConfig
>>> 
>>> # Create a simple Agent configuration
>>> agent_config = AgentConfig(
...     id="test_agent_001",
...     version="1.0.0",
...     description="Test Agent",
...     controller_type=ControllerType.Undefined
... )
>>> 
>>> print(f"Agent ID: {agent_config.id}")
Agent ID: test_agent_001
>>> print(f"Agent Version: {agent_config.version}")
Agent Version: 1.0.0
>>> print(f"Controller Type: {agent_config.controller_type}")
Controller Type: ControllerType.Undefined
>>> 
>>> # Create an Agent configuration with plugins and workflows
>>> plugin_schema = PluginSchema(
...     name='WeatherReporter',
...     description='Weather query plugin'
... )
>>> 
>>> workflow_schema = WorkflowSchema(
...     id="workflow_001",
...     name="weather_workflow",
...     description="Weather query workflow",
...     version="1.0"
... )
>>> 
>>> agent_config_full = AgentConfig(
...     id="full_agent_001",
...     version="2.0.0",
...     description="Fully configured Agent",
...     controller_type=ControllerType.ReActController,
...     tools=["WeatherReporter"],
...     workflows=[workflow_schema]
... )
>>> 
>>> print(f"Number of plugins: {len(agent_config_full.tools)}")
Number of plugins: 1
>>> print(f"Number of workflows: {len(agent_config_full.workflows)}")
Number of workflows: 1
```

