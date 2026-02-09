openJiuwen stores both workflow and Agent configuration information in the Runtime. It supports retrieving and loading the corresponding configuration items in real time via the `Runtime` interfaces, enabling configuration management.

- **Workflow configuration**: Refers to the workflow's meta configuration information, including the workflow name, workflow ID, workflow version, and model configuration, obtained via `runtime.get_workflow_config()`.
- **Agent configuration**: Refers to the Agent's configuration, such as the agent ID, agent version, and model/tool configuration, obtained via `runtime.get_agent_config()`.

Below is an introduction based on a `openjiuwen.agent.workflow_agent.WorkflowAgent` that contains a workflow, showing how to obtain workflow configuration and Agent configuration via `runtime` within WorkflowAgent's workflow components.

# Retrieve workflow configuration

Use the `runtime.get_workflow_config` method to obtain the configuration information of a workflow by its workflow ID:

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
workflow_config = runtime.get_workflow_config(workflow_id="test_weather_agent")
print(workflow_config.metadata.id)
print(workflow_config.metadata.name)
print(workflow_config.metadata.version)
```

The obtained id, name, and version are as follows:

```python
test_weather_agent
weather
1.0
```

For the full code, refer to the [Complete Example](Configuration%20Management.md#complete-example) section.

# Retrieve Agent configuration

Use `runtime.get_agent_config` to obtain the Agent configuration:

```python
# Note: This code snippet depends on full runtime initialization and context configuration, and cannot run independently. Please refer to the complete code example.
agent_config = runtime.get_agent_config()
print(agent_config.id)
print(agent_config.version)
```

The obtained id and version are as follows:

```python
test_weather_agent
0.1.0
```

For the full code, refer to the [Complete Example](#complete-example) section.

# Complete Example

```python
import asyncio

from openjiuwen.agent.common.enum import ControllerType
from openjiuwen.agent.common.schema import WorkflowSchema
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

# Build a custom component
class CustomComponent(WorkflowComponent, ComponentExecutable):
    def __init__(self, workflow_id):
        super().__init__()
        self._workflow_id = workflow_id

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        # Print workflow_config information
        workflow_config: WorkflowConfig = runtime.get_workflow_config(self._workflow_id)
        print(workflow_config.metadata.id)
        print(workflow_config.metadata.name)
        print(workflow_config.metadata.version)
        workflow_metadata = workflow_config.metadata


        # Print agent_config information
        agent_config: AgentConfig = runtime.get_agent_config()
        print(agent_config.id)
        print(agent_config.version)
        agent_profile = f'{agent_config.id}-{agent_config.version}-{agent_config.description}'
        workflow_profile = f'{workflow_metadata.name}-{workflow_metadata.version}-{workflow_metadata.description}'
        return {"agent_profile": agent_profile, "workflow_profile": workflow_profile,
                "execution_id": runtime.executable_id(), "session_id": runtime.session_id()}



flow = Workflow(workflow_config=WorkflowConfig(
        metadata=WorkflowMetadata(id="test_weather_agent", version="1.0", name="weather",
                                  description="this_is_a_demo")))
flow.set_start_comp("start", Start())
flow.add_workflow_comp("com", CustomComponent("test_weather_agent"))
flow.set_end_comp("end", End(), inputs_schema={"profile": "${com}"})
flow.add_connection("start", "com")
flow.add_connection("com", "end")
test_workflow_schema = WorkflowSchema(
        id="test_weather_agent",
        version="1.0",
        name="weather",
        description="this_is_a_demo",
        inputs={"query": {"type": "string"}},
    )
workflow_agent_config = WorkflowAgentConfig(id="test_weather_agent", version="0.1.0", description="this_is_a_demo",
                                            workflows=[test_workflow_schema],
                                            controller_type=ControllerType.WorkflowController)
agent = WorkflowAgent(agent_config=workflow_agent_config)

agent.bind_workflows([flow])

if __name__ == "__main__":
    result = asyncio.run(agent.invoke(inputs={"conversation_id": "12345", "query": "demo"}))
    print(result)
```

Output

```python
test_weather_agent
weather
1.0
test_weather_agent
0.1.0
{'output': WorkflowOutput(result={'output': {'profile': {'agent_profile': 'test_weather_agent-0.1.0-this_is_a_demo', 'workflow_profile': 'weather-1.0-this_is_a_demo', 'execution_id': 'com', 'session_id': '12345'}}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```