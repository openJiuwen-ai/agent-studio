

# openjiuwen.agent.config.workflow_config

## class openjiuwen.agent.config.workflow_config.WorkflowAgentConfig

```python
openjiuwen.agent.config.workflow_config.WorkflowAgentConfig(
    id: str,
    version: str,
    description: str,
    workflows: List[WorkflowSchema] = [],
    model: Optional[ModelConfig] = None,
    tools: List[str] = [],
    controller_type: ControllerType = ControllerType.WorkflowController,
    start_workflow: WorkflowSchema = WorkflowSchema(),
    end_workflow: WorkflowSchema = WorkflowSchema(),
    global_variables: List[dict] = [],
    global_params: Dict[str, Any] = {},
    constrain: ConstrainConfig = ConstrainConfig()
)
```

The **WorkflowAgentConfig** class is used to configure all parameters of a WorkflowAgent.

### **Parameters**:

* **id** (str):
  The unique identifier of the agent.

* **version** (str):
  The version number of the agent.

* **description** (str):
  A description of the agent.

* **workflows** (List[[WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema)]):
  A list of workflow descriptions supported by the agent.

* **model** ([ModelConfig](../../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig), optional):
  Model configuration.
  Default value: `None`, indicating that no large language model is configured.
  **Note**: If the model is not configured or is configured incorrectly, the component will raise an exception.

* **tools** (List[str], optional):
  A list of tool descriptions supported by the agent.
  Default value: `[]`, indicating that there are no callable tools.

* **controller_type** ([ControllerType](../common/enum.md#class-openjiuwenagentcommonenumcontrollertype), optional):
  The controller type.
  This must be `ControllerType.WorkflowController`.
  Default value: `ControllerType.WorkflowController`.

* **start_workflow** ([WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema), optional):
  A reserved parameter for multi-level agents.
  Currently not in use.

* **end_workflow** ([WorkflowSchema](../common/schema.md#class-openjiuwenagentcommonschemaworkflowschema), optional):
  A reserved parameter for multi-level agents.
  Currently not in use.

* **global_variables** (List[dict], optional):
  A reserved parameter for multi-level agents.
  Currently not in use.

* **global_params** (Dict[str, Any], optional):
  A reserved parameter for multi-level agents.
  Currently not in use.

* **constrain** ([ConstrainConfig](react_config.md#class-openjiuwenagentconfigreact_configconstrainconfig), optional):
  Constraint configuration.
  Default value: `ConstrainConfig()`.

### **Examples**:

```python
>>> import os
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
...     return WorkflowSchema(
...         id=id,
...         name=name,
...         description="Weather query workflow",
...         version=version,
...         inputs={"query": {"type": "string"}}
...     )
>>> 
>>> workflow_id = "test_weather_agent"
>>> workflow_name = "weather"
>>> workflow_version = "1.0"
>>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
>>> 
>>> # Create a WorkflowAgentConfig
>>> config = WorkflowAgentConfig(
...     id="test_weather_agent",
...     version="0.1.0",
...     description="Test weather agent",
...     workflows=[schema]
... )
```

---

## is_single_workflow

```python
is_single_workflow(self) -> bool
```

Determines whether the current configuration contains only a single workflow.

### **Returns**:

* **bool**:
  Returns `True` if there is only one workflow; otherwise, returns `False`.

### **Examples**:

```python
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> 
>>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
...     return WorkflowSchema(
...         id=id,
...         name=name,
...         description="Weather query workflow",
...         version=version,
...         inputs={"query": {"type": "string"}}
...     )
>>> 
>>> # Create a configuration with a single workflow
>>> schema = _create_workflow_schema("workflow_1", "weather", "1.0")
>>> config = WorkflowAgentConfig(
...     id="test_agent",
...     version="0.1.0",
...     description="Test agent",
...     workflows=[schema]
... )
>>> 
>>> # Check whether it is a single-workflow configuration
>>> is_single = len(config.workflows) == 1
>>> print(f"Is single workflow: {is_single}")  # Output: True
Is single workflow: True
>>> 
>>> # Create a configuration with multiple workflows
>>> schema2 = _create_workflow_schema("workflow_2", "translate", "1.0")
>>> config_multi = WorkflowAgentConfig(
...     id="test_agent_multi",
...     version="0.1.0",
...     description="Test multi-workflow agent",
...     workflows=[schema, schema2]
... )
>>> 
>>> is_single_multi = len(config_multi.workflows) == 1
>>> print(f"Is single workflow: {is_single_multi}")  # Output: False
Is single workflow: False
```

