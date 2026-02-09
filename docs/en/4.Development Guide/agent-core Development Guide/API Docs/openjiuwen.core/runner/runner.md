# openjiuwen.core.runner.Runner

## class openjiuwen.core.runner.Runner
Runner provides a unified execution interface for Workflow, Agent, Tool, and AgentGroup, and manages the lifecycle of Agent objects.

### start
```python
async def start(self) -> bool
```
Start the Runner.


**Example**:
```python
>>> import asyncio
>>>
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> asyncio.run(Runner.start())
```

### stop
```python
async def stop(self)
```
Stop the Runner.

**Example**:
```python
>>> import asyncio
>>>
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> asyncio.run(Runner.stop())
```

### add_agent

```python
def add_agent(self, agent_id, agent: Union[Agent, AgentProvider])
```
Register an agent instance or agent provider.

**Parameters**:
- **agent_id** (str): Unique ID of the agent. agent_id must not be None or ''.
- **agent** (Agent | AgentProvider): An agent instance or an agent provider. Must not be None.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:
```python
>>> import asyncio
>>> 
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> def create_agent():
...    # Create a workflow and register it in the resource manager
...    flow = Workflow(workflow_config=WorkflowConfig(
...        metadata=WorkflowMetadata(id="workflow_id", version="1", name="Simple workflow",
...                                  description="this_is_a_demo")))
...    flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
...    flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
...    flow.add_connection("start", "end")
...
...    resource_mgr.workflow().add_workflow("workflow_id_1", flow)
...
...    # Create an Agent
...
...    workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                                workflows=[WorkflowSchema(
...                                                    id="workflow_id",
...                                                    version="1",
...                                                    name="Simple workflow",
...                                                    description="this_is_a_demo",
...                                                    inputs={"query": {"type": "string"}},
...                                                )],
...                                                controller_type=ControllerType.WorkflowController
...                                                )
...    agent = WorkflowAgent(agent_config=workflow_agent_config)
...    return agent
...
>>> 
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> # 1. Register the agent
>>> Runner.add_agent("agent_id", create_agent())
>>> 
>>> # 2. Invoke the agent
>>> print(asyncio.run(Runner.run_agent("agent_id", inputs={"conversion_id": "id1", "query": "haha"})))
{'output': WorkflowOutput(result={'output': {'result': 'haha'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### remove_agent
Remove the agent or agent provider with the specified ID.

```python
def remove_agent(self, agent_id) -> Union[Agent, AgentProvider]
```

**Parameters**:
- **agent_id** (str): Unique ID of the agent. Must not be None or '', otherwise an exception is raised.

**Returns**:
- **Agent | AgentProvider**, the removed Agent instance or AgentProvider instance; returns None if it does not exist.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> def create_agent():
...    # Create a workflow and register it in the resource manager
...    flow = Workflow(workflow_config=WorkflowConfig(
...        metadata=WorkflowMetadata(id="workflow_id", version="1", name="Simple workflow",
...                                  description="this_is_a_demo")))
...    flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
...    flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
...    flow.add_connection("start", "end")
... 
...    resource_mgr.workflow().add_workflow("workflow_id_1", flow)
... 
...    # Create an Agent
... 
...    workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                                workflows=[WorkflowSchema(
...                                                    id="workflow_id",
...                                                    version="1",
...                                                    name="Simple workflow",
...                                                    description="this_is_a_demo",
...                                                    inputs={"query": {"type": "string"}},
...                                                )],
...                                                controller_type=ControllerType.WorkflowController
...                                                )
...    agent = WorkflowAgent(agent_config=workflow_agent_config)
...    return agent
... 
>>> 
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> # 1. Register the agent
>>> Runner.add_agent("agent_id", create_agent())
>>> # 2. Remove the agent
>>> agent = Runner.remove_agent("agent_id")
>>> print(agent.config().get_agent_config().id)
agent_id
```

### run_agent

```python
async def run_agent(self, agent: Union[str, Agent], inputs: Any) -> Any
```
Execute an agent and return its result.

**Parameters**:
- **agent** (str | Agent): The agent ID or agent instance.
- **inputs** (Any): Input data.

**Returns**:
- **Any**, the agent execution result.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> # Create a workflow and register it in the resource manager
>>> flow = Workflow(workflow_config=WorkflowConfig(
...     metadata=WorkflowMetadata(id="workflow_id", version="1", name="Simple workflow",
...                               description="this_is_a_demo")))
... 
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
>>> flow.add_connection("start", "end")
>>> 
>>> resource_mgr.workflow().add_workflow("workflow_id_1", flow)
>>> 
>>> # Create an Agent
>>> 
>>> workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                            workflows=[WorkflowSchema(
...                                                id="workflow_id",
...                                                version="1",
...                                                name="Simple workflow",
...                                                description="this_is_a_demo",
...                                                inputs={"query": {"type": "string"}},
...                                            )],
...                                            controller_type=ControllerType.WorkflowController
...                                            )
...
>>> agent = WorkflowAgent(agent_config=workflow_agent_config)
>>> 
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> # Invoke the agent instance directly
>>> print(asyncio.run(Runner.run_agent(agent, inputs={"conversion_id": "id1", "query": "haha"})))
{'output': WorkflowOutput(result={'output': {'result': 'haha'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
>>> 
>>> # Invoke the agent by ID; you must register the agent first
>>> Runner.add_agent("agent_id", agent)
>>> print(asyncio.run(Runner.run_agent("agent_id", inputs={"conversion_id": "id1", "query": "haha"})))
{'output': WorkflowOutput(result={'output': {'result': 'haha'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### run_agent_streaming

```python
async def run_agent_streaming(self, agent: Union[str, Agent], inputs: Any) -> AsyncGenerator
```
Run an Agent in streaming mode and return a generator.

**Parameters**:
- **agent** (str | Agent): The agent ID or agent instance.
- **inputs** (Any): Input data.

**Returns**:
- **AsyncGenerator**, a streaming result generator.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> from openjiuwen.core.stream.base import OutputSchema
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> # Create a workflow and register it in the resource manager
>>> flow = Workflow(workflow_config=WorkflowConfig(
...     metadata=WorkflowMetadata(id="workflow_id", version="1", name="Simple workflow",
...                               description="this_is_a_demo")))
... 
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
>>> flow.add_connection("start", "end")
>>> 
>>> resource_mgr.workflow().add_workflow("workflow_id_1", flow)
>>> 
>>> # Create an Agent
>>> workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                            workflows=[WorkflowSchema(
...                                                id="workflow_id",
...                                                version="1",
...                                                name="Simple workflow",
...                                                description="this_is_a_demo",
...                                                inputs={"query": {"type": "string"}},
...                                            )],
...                                            controller_type=ControllerType.WorkflowController
...                                            )
... 
>>> agent = WorkflowAgent(agent_config=workflow_agent_config)
>>> 
>>> from openjiuwen.core.runner.runner import Runner
>>> async def run_workflow():
...     result = Runner.run_agent_streaming(agent, inputs={"conversion_id": "id1", "query": "haha"})
...     async for chunk in result:
...         if isinstance(chunk, OutputSchema):
...             print(chunk)
... 
>>> asyncio.run(run_workflow())
type='workflow_final' index=0 payload={'output': {'result': 'haha'}}
>>> 
>>> # Invoke by ID; register the agent first
>>> Runner.add_agent("agent_id", agent)
>>> async def run_workflow():
...     result = Runner.run_agent_streaming("agent_id", inputs={"conversion_id": "id1", "query": "haha"})
...     async for chunk in result:
...         if isinstance(chunk, OutputSchema):
...             print(chunk)
... 
>>> asyncio.run(run_workflow())
type='workflow_final' index=0 payload={'output': {'result': 'haha'}}

```

### run_workflow

```python
async def run_workflow(self, workflow: Union[str, Workflow], inputs: Any, *, runtime: Union[Runtime, WorkflowRuntime] = None, context: Context = None) -> Any
```
Execute a workflow and return its result.

**Parameters**:
- **workflow** (str | Workflow): Workflow ID or workflow instance. Must not be None or ''.
- **inputs** (Any): Input data to execute the workflow.
- **runtime** (Runtime | WorkflowRuntime): Runtime instance. If the runtime comes from an Agent, the workflow must be bound to that Agent. Default is None.
- **context** (Context): Context engine to store user conversation information. Default is None, which disables the context engine.

**Returns**:
- **Any**, the workflow execution result.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> from openjiuwen.core.runner.runner import Runner, resource_mgr
>>> 
>>> # Custom component Node
>>> class Node(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
...
>>> # Create a workflow
>>> def build_workflow(name, workflow_id, version):
...     workflow_config = WorkflowConfig(
...         metadata=WorkflowMetadata(
...             id=workflow_id,
...             version=version,
...             name=name,
...         )
...     )
...     flow = Workflow(workflow_config=workflow_config)
...     flow.set_start_comp("start", Start(),
...                         inputs_schema={
...                             "query": "${query}"})
...     flow.add_workflow_comp("node_a", Node(),
...                            inputs_schema={
...                                "output": "${start.query}"})
...     flow.set_end_comp("end", End(),
...                       inputs_schema={
...                           "result": "${node_a.output}"})
...     flow.add_connection("start", "node_a")
...     flow.add_connection("node_a", "end")
...     return flow
... 
>>> 
>>> # Run workflow directly
>>> workflow = build_workflow("test_workflow", "test_workflow", "1")
>>> result = asyncio.run(Runner.run_workflow(workflow=workflow, inputs={"query": "query workflow"}, runtime=WorkflowRuntime()))
>>> print(result)
result={'output': {'result': 'query workflow'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
>>> # Run by workflow ID (register the workflow in the resource manager first)
>>> resource_mgr.workflow().add_workflow("test_workflow", workflow)
>>> result = asyncio.run(Runner.run_workflow(workflow="test_workflow", inputs={"query": "query workflow"}, runtime=WorkflowRuntime()))
>>> print(result)
result={'output': {'result': 'query workflow'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

### run_workflow_streaming

```python
async def run_workflow_streaming(self, workflow: Union[str, Workflow], inputs: Any, *, runtime: Union[Runtime, WorkflowRuntime] = None, stream_modes: list[BaseStreamMode] = None, context: Context = None) -> AsyncGenerator
```
Execute a workflow in streaming mode and return its result.

**Parameters**:
- **workflow** (str | Workflow): Workflow ID or workflow instance. Must not be None or ''.
- **inputs** (Any): Input data to execute the workflow.
- **runtime** (Runtime | WorkflowRuntime): Runtime instance. If the runtime comes from an Agent, the provided workflow must be bound to that Agent. Default is None.
- **stream_modes** (list[BaseStreamMode]): Types of streaming outputs. Default is None.
- **context** (Context): Context engine to store user conversation information. Default is None, which disables the context engine.

**Returns**:
- **AsyncGenerator**, a streaming result generator.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runner.runner import Runner
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import CustomSchema
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> # Custom component Node
>>> class Node(ComponentExecutable, WorkflowComponent):
...    def __init__(self):
...        super().__init__()
...
...    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...        await runtime.write_custom_stream({"1": "1"})
...        await runtime.write_custom_stream({"2": "2"})
...        return inputs
...
>>> # Create a workflow
>>> def build_workflow(name, workflow_id, version):
...    workflow_config = WorkflowConfig(
...        metadata=WorkflowMetadata(
...            id=workflow_id,
...            version=version,
...            name=name,
...        )
...    )
...    flow = Workflow(workflow_config=workflow_config)
...    flow.set_start_comp("start", Start(),
...                        inputs_schema={
...                            "query": "${query}"})
...    flow.add_workflow_comp("node_a", Node(),
...                           inputs_schema={
...                               "output": "${start.query}"})
...    flow.set_end_comp("end", End(),
...                      inputs_schema={
...                          "result": "${node_a.output}"})
...    flow.add_connection("start", "node_a")
...    flow.add_connection("node_a", "end")
...    return flow
...
>>> # Run the workflow directly
>>> workflow = build_workflow("test_workflow", "test_workflow", "1")
>>> async def run_workflow():
...     result = Runner.run_workflow_streaming(workflow=workflow, inputs={"query": "query workflow"}, runtime=WorkflowRuntime())
...     async for chunk in result:
...         if isinstance(chunk, CustomSchema):
...             print(chunk)
...
>>> asyncio.run(run_workflow())
1='1'
2='2'
>>> 
>>> # Run by ID; register the workflow in the resource manager first
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> resource_mgr.workflow().add_workflow("test_workflow", workflow)
>>> async def run_workflow():
...     result = Runner.run_workflow_streaming(workflow="test_workflow", inputs={"query": "query workflow"}, runtime=WorkflowRuntime())
...     async for chunk in result:
...         if isinstance(chunk, CustomSchema):
...             print(chunk)
...
>>> asyncio.run(run_workflow())
1='1'
2='2'
```

### run_tool

```python
async def run_tool(self, tool: Union[str, Tool], inputs, *, runtime: Runtime = None) -> Any
```

Execute a Tool and return the result.

**Parameters**:
- **tool** (str | Tool): ID or Tool instance. Must not be None or ''.
- **inputs**: Input data.
- **runtime** (Runtime): Runtime instance. If the runtime comes from an Agent, the provided tool must be bound to that Agent. Default is None.

**Returns**:
- **Any**, the Tool execution result.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> from openjiuwen.core.utils.tool.function.function import LocalFunction
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # Create a local tool
>>> add_plugin = LocalFunction(
...     name="add",
...     description="Addition",
...     params=[
...         Param(name="a", description="first number", type="number", required=True),
...         Param(name="b", description="second number", type="number", required=True),
...     ],
...     func=lambda a, b: a + b
... )
... 
>>> # 1. Invoke via a Tool instance directly
>>> import asyncio
>>> from openjiuwen.core.runner.runner import Runner
>>> print(asyncio.run(Runner.run_tool(tool=add_plugin, inputs={'a':1, 'b':2})))
3
>>> # 2. Invoke by tool ID; register the tool in the resource manager first
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> resource_mgr.tool().add_tool("add", add_plugin)
>>> print(asyncio.run(Runner.run_tool(tool="add", inputs={'a':1, 'b':2})))
3
```

### run_tool_streaming

```python
async def run_tool_streaming(self, tool: Union[str, Tool], inputs, *, runtime: Runtime = None) -> AsyncGenerator
```
Execute a Tool in streaming mode and return a generator.

**Parameters**:
- **tool** (str | Tool): ID or Tool instance. Must not be None or ''.
- **inputs**: Input data.
- **runtime** (Runtime): Runtime instance. If the runtime comes from an Agent, the provided tool must be bound to that Agent. Default is None.

**Returns**:
- **AsyncGenerator**, a streaming result generator.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.utils.tool.base import Tool
>>> from openjiuwen.core.utils.tool.constant import Input, Output
>>> 
>>> 
>>> # Define a custom tool that supports streaming output
>>> class CustomTool(Tool):
...     def invoke(self, inputs: Input, **kwargs) -> Output:
...         pass
... 
...     async def ainvoke(self, inputs: Input, **kwargs) -> Output:
...         pass
... 
...     async def astream(self, inputs: Input, **kwargs):
...         for key, value in inputs.items():
...             yield {key: value}
... 
>>> # Run the tool directly
>>> from openjiuwen.core.runner.runner import Runner, resource_mgr
>>> tool = CustomTool()
>>> async def run_tool():
...     iter = Runner.run_tool_streaming(tool, inputs={"a": "a", "b": "b", "c": "c"})
...     async for chunk in iter:
...         print(chunk)
... 
>>> asyncio.run(run_tool())
{'a': 'a'}
{'b': 'b'}
{'c': 'c'}
>>> # Run by ID; register the tool in the resource manager first
>>> tool = CustomTool()
>>> resource_mgr.tool().add_tool("custom", tool)
>>> async def run_tool():
...   iter = Runner.run_tool_streaming("custom", inputs={"a": "a", "b": "b", "c": "c"})
...   async for chunk in iter:
...       print(chunk)
... 
>>> asyncio.run(run_tool())
{'a': 'a'}
{'b': 'b'}
{'c': 'c'}
```

### run_agent_group

```python
async def run_agent_group(self, agent_group: Union[str, AgentGroup], inputs: Any)-> Any
```
Execute an AgentGroup and return the result.

**Parameters**:
- **agent_group** (str | AgentGroup): ID or AgentGroup instance. Must not be None or ''.
- **inputs**: Input data.

**Returns**:
- **Any**, the AgentGroup execution result.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import os
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.questioner_comp import (
...     FieldInfo,
...     QuestionerComponent,
...     QuestionerConfig
... )
... 
>>> from openjiuwen.agent.config.base import AgentConfig
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> 
>>> def _create_model_config() -> ModelConfig:
...   """Create model config"""
...   return ModelConfig(
...       model_provider=MODEL_PROVIDER,
...       model_info=BaseModelInfo(
...           model=MODEL_NAME,
...           api_base=API_BASE,
...           api_key=API_KEY,
...           temperature=0.7,
...           top_p=0.9,
...           timeout=120,
...       ),
...   )
... 
>>> def _create_start_component():
...    """Create Start component"""
...    return Start({
...        "inputs": [
...            {
...                "id": "query",
...                "type": "String",
...                "required": "true",
...                "sourceType": "ref"
...            }
...        ]
...    })
... 
>>> 
>>> def _build_financial_workflow(
...         workflow_id: str,
...         workflow_name: str,
...         workflow_desc: str,
...         field_name: str,
...         field_desc: str
... ) -> Workflow:
...   """
...   Build a financial workflow (with an interrupt node)
... 
...   Args:
...       workflow_id: Workflow ID
...       workflow_name: Workflow name
...       workflow_desc: Workflow description
...       field_name: Field name to ask the user
...       field_desc: Field description
... 
...   Returns:
...       Workflow: A workflow consisting of start -> questioner -> end
...   """
...   workflow_config = WorkflowConfig(
...       metadata=WorkflowMetadata(
...           name=workflow_name,
...           id=workflow_id,
...           version="1.0",
...           description=workflow_desc,
...       )
...   )
...   flow = Workflow(workflow_config=workflow_config)
... 
...   # Create components
...   start = _create_start_component()
... 
...   # Create a questioner (interrupt node)
...   key_fields = [
...       FieldInfo(
...           field_name=field_name,
...           description=field_desc,
...           required=True
...       ),
...   ]
...   model_config = _create_model_config()
...   questioner_config = QuestionerConfig(
...       model=model_config,
...       question_content="",
...       extract_fields_from_response=True,
...       field_names=key_fields,
...       with_chat_history=False,
...   )
...   questioner = QuestionerComponent(questioner_config)
... 
...   # End component
...   end = End({"responseTemplate": f"{workflow_name} completed: {{{{{field_name}}}}}"})
... 
...   # Register components
...   flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
...   flow.add_workflow_comp(
...       "questioner", questioner, inputs_schema={"query": "${start.query}"}
...   )
...   flow.set_end_comp(
...       "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
...   )
... 
...   # Topology: start -> questioner -> end
...   flow.add_connection("start", "questioner")
...   flow.add_connection("questioner", "end")
... 
...   return flow
... 
>>> def _create_workflow_agent(
...         agent_id: str,
...         description: str,
...         workflow: Workflow
... ) -> WorkflowAgent:
...     """Create a WorkflowAgent"""
...     config = WorkflowAgentConfig(
...         id=agent_id,
...         version="1.0",
...         description=description,
...         workflows=[],
...         model=_create_model_config(),
...     )
...     agent = WorkflowAgent(config)
...     agent.add_workflows([workflow])
...     return agent
... 
>>> # Create financial workflows
>>> transfer_workflow = _build_financial_workflow(
...     workflow_id="transfer_flow",
...     workflow_name="Transfer Service",
...     workflow_desc="Handle user transfer requests, supporting transfers to specified accounts",
...     field_name="amount",
...     field_desc="Transfer amount (number)"
... )
... 
>>> balance_workflow = _build_financial_workflow(
...     workflow_id="balance_flow",
...     workflow_name="Balance Inquiry",
...     workflow_desc="Query user account balance information",
...     field_name="account",
...     field_desc="Account number"
... )
... 
>>> invest_workflow = _build_financial_workflow(
...     workflow_id="invest_flow",
...     workflow_name="Investment Service",
...     workflow_desc="Provide investment product recommendations and purchases",
...     field_name="product",
...     field_desc="Investment product name"
... )
... 
>>> # Create WorkflowAgents
>>> transfer_agent = _create_workflow_agent(
...     agent_id="transfer_agent",
...     description="Transfer service: handle user transfer requests",
...     workflow=transfer_workflow
... )
... 
>>> balance_agent = _create_workflow_agent(
...     agent_id="balance_agent",
...     description="Balance inquiry service: query account balance",
...     workflow=balance_workflow
... )
... 
>>> invest_agent = _create_workflow_agent(
...     agent_id="invest_agent",
...     description="Investment service: recommend and purchase products",
...     workflow=invest_workflow
... )
... 
>>> from openjiuwen.agent_group.hierarchical_group import (
...     HierarchicalGroup,
...     HierarchicalGroupConfig
... )
... 
>>> config = HierarchicalGroupConfig(
...     group_id="financial_group",
...     leader_agent_id="main_controller"
... )
... 
>>> hierarchical_group = HierarchicalGroup(config)
>>> 
>>> from openjiuwen.agent.config.base import AgentConfig
>>> from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController
>>> from openjiuwen.core.agent.agent import ControllerAgent
>>> 
>>> main_config = AgentConfig(
...     id="main_controller",
...     description="Financial services main controller: detect intent and dispatch tasks"
... )
...
>>> main_controller = HierarchicalMainController()
>>> main_agent = ControllerAgent(main_config, controller=main_controller)
>>> 
>>> # Add all agents to the group
>>> hierarchical_group.add_agent("main_controller", main_agent)
>>> hierarchical_group.add_agent("transfer_agent", transfer_agent)
>>> hierarchical_group.add_agent("balance_agent", balance_agent)
>>> hierarchical_group.add_agent("invest_agent", invest_agent)
>>> 
>>> from openjiuwen.core.agent.message.message import Message
>>> from openjiuwen.core.runner.runner import Runner
>>> import asyncio
>>> 
>>> asyncio.run(Runner.start())
>>> conversation_id = "session_001"
>>> hierarchical_group.group_controller.subscribe("test_query1", ["transfer_agent"])
>>> message1 = Message.create_user_message(
...     content="Transfer money to Zhang San",
...     conversation_id=conversation_id
... )
... 
>>> # Broadcast the message to all agents subscribed to the topic 'test_query1'
>>> message1.message_type = "test_query1"
>>> result1 = asyncio.run(Runner.run_agent_group(hierarchical_group, message1))
>>> asyncio.run(Runner.stop())
>>> print(result1)
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='Please provide information related to the transfer amount (number)'))]
```

### run_agent_group_streaming

```python
async def run_agent_group_streaming(self, agent_group: Union[str, AgentGroup], inputs: Any) -> AsyncGenerator
```
Execute an AgentGroup in streaming mode and return the result.

**Parameters**:
- **agent_group** (str | AgentGroup): ID or AgentGroup instance. Must not be None or ''.
- **inputs**: Input data.

**Returns**:
- **AsyncGenerator**, a streaming result generator.

**Exceptions**:
- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and remedies, see [StatusCode](../common/exception/status_code.md).

**Example**:

```python
>>> import os
>>> import asyncio
>>> 
>>> from openjiuwen.core.agent.message.message import Message
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.agent.agent import ControllerAgent
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.questioner_comp import (
...     FieldInfo,
...     QuestionerComponent,
...     QuestionerConfig
... )
... 
>>> from openjiuwen.agent.config.base import AgentConfig
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> from openjiuwen.agent_group.hierarchical_group import (
...     HierarchicalGroup,
...     HierarchicalGroupConfig
... )
... 
>>> from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController
>>> from openjiuwen.core.runner.runner import Runner
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> 
>>> def _create_model_config() -> ModelConfig:
...     """Create model config"""
...     return ModelConfig(
...         model_provider=MODEL_PROVIDER,
...         model_info=BaseModelInfo(
...             model=MODEL_NAME,
...             api_base=API_BASE,
...             api_key=API_KEY,
...             temperature=0.7,
...             top_p=0.9,
...             timeout=120,
...         ),
...     )
... 
>>> def _create_start_component():
...     """Create Start component"""
...     return Start({
...         "inputs": [
...             {
...                 "id": "query",
...                 "type": "String",
...                 "required": "true",
...                 "sourceType": "ref"
...             }
...         ]
...     })
... 
>>> 
>>> def _build_financial_workflow(
...         workflow_id: str,
...         workflow_name: str,
...         workflow_desc: str,
...         field_name: str,
...         field_desc: str
... ) -> Workflow:
...     """
...     Build a financial workflow (with an interrupt node)
... 
...     Args:
...         workflow_id: Workflow ID
...         workflow_name: Workflow name
...         workflow_desc: Workflow description
...         field_name: Field name to ask the user
...         field_desc: Field description
... 
...     Returns:
...         Workflow: A workflow consisting of start -> questioner -> end
...     """
...     workflow_config = WorkflowConfig(
...         metadata=WorkflowMetadata(
...             name=workflow_name,
...             id=workflow_id,
...             version="1.0",
...             description=workflow_desc,
...         )
...     )
...     flow = Workflow(workflow_config=workflow_config)
... 
...     # Create components
...     start = _create_start_component()
... 
...     # Create a questioner (interrupt node)
...     key_fields = [
...         FieldInfo(
...             field_name=field_name,
...             description=field_desc,
...             required=True
...         ),
...     ]
...     model_config = _create_model_config()
...     questioner_config = QuestionerConfig(
...         model=model_config,
...         question_content="",
...         extract_fields_from_response=True,
...         field_names=key_fields,
...         with_chat_history=False,
...     )
...     questioner = QuestionerComponent(questioner_config)
... 
...     # End component
...     end = End({"responseTemplate": f"{workflow_name} completed: {{{{{field_name}}}}}"})
... 
...     # Register components
...     flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
...     flow.add_workflow_comp(
...         "questioner", questioner, inputs_schema={"query": "${start.query}"}
...     )
...     flow.set_end_comp(
...         "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
...     )
... 
...     # Topology: start -> questioner -> end
...     flow.add_connection("start", "questioner")
...     flow.add_connection("questioner", "end")
... 
...     return flow
... 
>>> def _create_workflow_agent(
...         agent_id: str,
...         description: str,
...         workflow: Workflow
... ) -> WorkflowAgent:
...     """Create a WorkflowAgent"""
...     config = WorkflowAgentConfig(
...         id=agent_id,
...         version="1.0",
...         description=description,
...         workflows=[],
...         model=_create_model_config(),
...     )
...     agent = WorkflowAgent(config)
...     agent.add_workflows([workflow])
...     return agent
... 
>>> # Create financial workflows
>>> transfer_workflow = _build_financial_workflow(
...     workflow_id="transfer_flow",
...     workflow_name="Transfer Service",
...     workflow_desc="Handle user transfer requests, supporting transfers to specified accounts",
...     field_name="amount",
...     field_desc="Transfer amount (number)"
... )
... 
>>> balance_workflow = _build_financial_workflow(
...     workflow_id="balance_flow",
...     workflow_name="Balance Inquiry",
...     workflow_desc="Query user account balance information",
...     field_name="account",
...     field_desc="Account number"
... )
... 
>>> invest_workflow = _build_financial_workflow(
...     workflow_id="invest_flow",
...     workflow_name="Investment Service",
...     workflow_desc="Provide investment product recommendations and purchases",
...     field_name="product",
...     field_desc="Investment product name"
... )
... 
>>> # Create HierarchicalGroup
>>> config = HierarchicalGroupConfig(
...     group_id="financial_group",
...     leader_agent_id="main_controller"
... )   
... 
>>> hierarchical_group = HierarchicalGroup(config)
>>> 
>>> # Create the main agent (HierarchicalMainController)
>>> main_config = AgentConfig(
...     id="main_controller",
...     description="Financial services main controller: detect intent and dispatch tasks"
... )
... 
>>> main_controller = HierarchicalMainController()
>>> main_agent = ControllerAgent(main_config, controller=main_controller)
>>> 
>>> # Add all agents to the group
>>> hierarchical_group.add_agent("main_controller", main_agent)
>>> hierarchical_group.add_agent("transfer_agent", transfer_agent)
>>> hierarchical_group.add_agent("balance_agent", balance_agent)
>>> hierarchical_group.add_agent("invest_agent", invest_agent)
>>> 
>>> async def main():
...     # Start the Runner
...     await Runner.start()
...     message = Message.create_user_message(
...         content="Transfer 500 yuan to Zhang San",
...         conversation_id="stream_session_test"
...     )
...     # Stream invocation
...     async for chunk in Runner.run_agent_group_streaming(hierarchical_group, message):
...         print(f"Output: {chunk}")
...     # Stop the Runner
...     await Runner.stop()
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
... 
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169086), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': None, 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 750914), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'amount': 500}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': None, 'inputs': {'amount': 500}, 'outputs': None, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752861), 'inputs': {'amount': 500}, 'outputs': {'responseContent': 'Transfer Service completed: 500'}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 754020), 'inputs': {'query': 'Transfer 500 yuan to Zhang San'}, 'outputs': {'responseContent': 'Transfer Service completed: 500'}, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
Output: type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': 'Transfer Service completed: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### release
```python
async def release(self, session_id: str)
```
Clean up cached data for the specified session_id, such as interruption state.

**Parameters**:
- **session_id** (str): Conversation ID. If None, no cleanup is performed.

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> 
>>> # Create a custom node: with interactive interruption
>>> class InteractionNode(WorkflowComponent, ComponentExecutable):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         answer = inputs.get("answer")
...         query = await runtime.interact(answer)
...         return {"query": query}
... 
>>> # Create a workflow
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> workflow = Workflow()
>>> workflow.set_start_comp("start", Start(), inputs_schema={"answer": "${user_input}"})
>>> workflow.add_workflow_comp("interact_node", InteractionNode(), inputs_schema={"answer": "${start.answer}"})
>>> workflow.set_end_comp("end", End(), inputs_schema={"result": "${interact_node.query}"})
>>> workflow.add_connection("start", "interact_node")
>>> workflow.add_connection("interact_node", "end")
>>> 
>>> # First call: the workflow interrupts
>>> from openjiuwen.core.runner.runner import Runner
>>> input1 = {"user_input": "Weather"}
>>> result1 = asyncio.run(Runner.run_workflow(workflow, inputs=input1, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result1: {result1}')
result1: result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='interact_node', value='Weather'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
>>> 
>>> # Provide interactive input and continue the workflow
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> # Provide input for the interactive node 'interact_node'
>>> input2 = InteractiveInput()
>>> input2.update("interact_node", "Sunny")
>>> result2 = asyncio.run(Runner.run_workflow(workflow, inputs=input2, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result2 after interactive input: {result2}')
result2 after interactive input: result={'result': 'Sunny'} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
>>> 
>>> # Clean up data for session_1
>>> asyncio.run(Runner.release(session_id="session_1"))
>>> 
>>> # Call the workflow again; since session_1 was cleaned up, it starts from the beginning
>>> # Note: After release, you must pass the initial input (as a dict). Do not use InteractiveInput.
>>> result3 = asyncio.run(Runner.run_workflow(workflow, inputs=input1, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result3 after release: {result3}')
result3 after release: result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='interact_node', value='Weather'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
```