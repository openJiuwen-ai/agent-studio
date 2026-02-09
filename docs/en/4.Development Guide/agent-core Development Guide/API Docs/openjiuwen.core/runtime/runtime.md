# openjiuwen.core.runtime.runtime

## class Runtime

```python
class openjiuwen.core.runtime.runtime.Runtime()
```

Core runtime operations for Agents and Workflows, encapsulating capabilities such as state management, configuration management, streaming output, trace/debug info, and resource management.

### executable_id

```python
executable_id(self) -> str
```

Get the globally unique identifier of the current executable unit. Returns the Agent ID when called inside an Agent task, or the component ID when called inside a workflow component.

**Returns**:

- **str**, the unique ID for the current workflow node/Agent task.

**Example**:

```python
>>> import asyncio
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>>
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...    def __init__(self, workflow_id):
...        super().__init__()
...        self._workflow_id = workflow_id
...
...    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...        print(f"executable_id: {runtime.executable_id()}")
...        return {}
...
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>>
>>> if __name__ == "__main__":
...    asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
executable_id: custom
```

### session_id

```python
session_id(self) -> str
```

Get the unique session identifier for this workflow execution.

**Returns**:

- **str**, the unique session identifier for the current workflow.

```python
>>> import asyncio
>>> 
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...    def __init__(self, workflow_id):
...        super().__init__()
...        self._workflow_id = workflow_id
...
...    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...        print(f"session_id: {runtime.session_id()}")
...        return {}
...
>>> flow = Workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="demo_id", version="demo_version", name="demo_name", description="this_is_a_demo")))
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("com", CustomComponent("demo_id"))
>>> flow.set_end_comp("end", End(), inputs_schema={"profile": "${com}"})
>>> flow.add_connection("start", "com")
>>> flow.add_connection("com", "end")
>>> test_workflow_schema = WorkflowSchema(
...     id="demo_id",
...     version="demo_version",
...     name="demo_name",
...     description="this_is_a_demo",
...     inputs={"query": {"type": "string"}})
...
>>> workflow_agent_config = WorkflowAgentConfig(id="demo_agent", version="demo_version", description="this_is_a_demo",
...                                             workflows=[test_workflow_schema],
...                                             controller_type=ControllerType.WorkflowController)
...
>>> agent = WorkflowAgent(agent_config=workflow_agent_config)
>>> 
>>> agent.bind_workflows([flow])
>>> 
>>> asyncio.run(agent.invoke(inputs={"conversation_id": "12345", "query": "demo"}))
session_id: 12345
```

### update_state

```python
update_state(self, data: dict)
```

Update the state data of the current executable unit; adds new fields if they don't exist.

- In Agent execution, updates the current Agent's state and takes effect immediately.
- In Workflow execution, updates the current component's state and takes effect after the component finishes.

**Parameters**:

- **data** (dict): Key-value pairs to add or update. If data is None or {}, no update is performed.

**Example**:

Update state information

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> class CustomStateComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         my_state = runtime.get_state({"recall_times": "${recall_times}", "messages": "${messages}"})
...         if not my_state:
...             my_state = {}
...         if not my_state.get("recall_times"):
...             my_state["recall_times"] = 0
...         my_state["recall_times"] = my_state["recall_times"] + 1
...         if not my_state.get("messages"):
...             my_state["messages"] = []
...         my_state["messages"].append(inputs.get("query"))
...         print(f"[{self._node_id}] current state is {my_state}")
...         runtime.update_state(my_state)
...         return inputs
... 
>>> # 2. Create and run a workflow that contains a loop component which includes the custom component
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
>>> flow.set_end_comp("end", End())
>>> 
>>> loop_group = LoopGroup()
>>> loop_group.start_nodes(["s"])
>>> loop_group.end_nodes(["a"])
>>> loop_group.add_workflow_comp("s", Start(), inputs_schema={"query": "${l.query}"})
>>> loop_group.add_workflow_comp("a", CustomStateComponent("a"), inputs_schema={"query": "${start.query}"})
>>> loop_group.add_connection("s", "a")
>>> flow.add_workflow_comp("l", LoopComponent(loop_group, {}),inputs_schema={"loop_type": "number", "loop_number": "${user_inputs.loop_number}", "query": "${start.query}"})
>>> flow.add_connection("start", "l")
>>> flow.add_connection("l", "end")
>>> 
>>> # 3. Execute the workflow
>>> runtime = WorkflowRuntime()
>>> asyncio.run(flow.invoke({"user_inputs": {"query": "Hello", "loop_number": 3}}, runtime))
[a] current state is {'recall_times': 1, 'messages': ['Hello']}
[a] current state is {'recall_times': 2, 'messages': ['Hello', 'Hello']}
[a] current state is {'recall_times': 3, 'messages': ['Hello', 'Hello', 'Hello']}
```

### get_state

```python
get_state(self, key: Union[str, list, dict] = None) -> Any
```

Read the state data of the current executable unit with flexible extraction.

- In Agent execution, returns this Agent's state information.
- In Workflow execution, returns the state information of the current component.

**Parameters**:

- **key** (Union[str, list, dict], optional): Key path to retrieve values from the state, default None to fetch all. Depending on the key type, different extraction forms are supported.
  - If key is str, fetch the state at the given path; nested paths are supported (e.g., "user_inputs.query").
  - If key is dict or list, fetch multiple state values; all variables wrapped in ${} will be replaced with their corresponding values.

**Returns**:

- **Any**, the value(s) retrieved:
  - For str key, returns the value at the given path or None if it doesn't exist.
  - For dict/list key, returns the structure after replacing each ${} variable with its resolved value (or None if not found).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> class CustomStateComponent(ComponentExecutable, WorkflowComponent):
...    def __init__(self, node_id):
...        super().__init__()
...        self._node_id = node_id
...
...    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...        # Get a single state value
...        recall_times = runtime.get_state("recall_times")
...        # Get multiple state values
...        my_state = runtime.get_state({"recall_times": "${recall_times}", "messages": "${messages}"})
...        # Get a list of state values
...        my_state_list = runtime.get_state(["${recall_times}", "${messages}"])
...        print(f'recall_times: {recall_times}, my_state: {my_state}, my_state_list: {my_state_list}')
...        if not my_state:
...            my_state = {}
...        if not my_state.get("recall_times"):
...            my_state["recall_times"] = 0
...        my_state["recall_times"] = my_state["recall_times"] + 1
...        if not my_state.get("messages"):
...            my_state["messages"] = []
...        my_state["messages"].append(inputs.get("query"))
...        runtime.update_state(my_state)
...        return inputs
...
>>> # 2. Create and run a workflow with a loop component that contains the custom component
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
>>> flow.set_end_comp("end", End())
>>> 
>>> loop_group = LoopGroup()
>>> loop_group.start_nodes(["s"])
>>> loop_group.end_nodes(["a"])
>>> loop_group.add_workflow_comp("s", Start(), inputs_schema={"query": "${l.query}"})
>>> loop_group.add_workflow_comp("a", CustomStateComponent("a"), inputs_schema={"query": "${start.query}"})
>>> loop_group.add_connection("s", "a")
>>> flow.add_workflow_comp("l", LoopComponent(loop_group, {}),inputs_schema={"loop_type": "number", "loop_number": "${user_inputs.loop_number}", "query": "${start.query}"})
>>> flow.add_connection("start", "l")
>>> flow.add_connection("l", "end")
>>> 
>>> # 3. Execute the workflow
>>> runtime = WorkflowRuntime()
>>> 
>>> asyncio.run(flow.invoke({"user_inputs": {"query": "Hello", "loop_number": 3}}, runtime))
recall_times: None, my_state: None, my_state_list: None
recall_times: 1, my_state: {'recall_times': 1, 'messages': ['Hello']}, my_state_list: [1, ['Hello']]
recall_times: 2, my_state: {'recall_times': 2, 'messages': ['Hello', 'Hello']}, my_state_list: [2, ['Hello', 'Hello']]
```

### update_global_state

```python
update_global_state(self, data: dict)
```

Update the global shared state. Global state is shared between Agent and Workflow. The effective time differs by context:

- In Agent, global state updates take effect immediately.
- In Workflow, updates take effect after the current component finishes.

**Parameters**:

- **data** (dict): Key-value pairs to add or update. If None or {}, no update is performed.

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Output, Input
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 1. Custom component: each call adds +10 to the global state
>>> class AddTenComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         call_times = runtime.get_state("call_times")
...         # Read current global state 'num'
...         num = runtime.get_global_state("num")
...         if not num:
...             num = 0
...         if not call_times:
...             call_times = 0
...         call_times += 1
...         print(f"begin to invoke, call_times={call_times}, num={num}, operation: num = {num} + 10")
...         num += 10
...         runtime.update_global_state({"num": num})
...         # Update current state
...         runtime.update_state({"call_times": call_times})
...         return inputs 
... 
>>> # 2. Custom component to read the final global state 'num' at workflow end
>>> class CustomEnd(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'->[{self._node_id}] get num = {runtime.get_global_state("num")}')
...         return inputs
... 
>>> # 3. Create and run the workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.set_end_comp("end", CustomEnd("end"))
>>> flow.add_workflow_comp("a", AddTenComponent("a"))
>>> 
>>> sw = BranchComponent()
>>> sw.add_branch("${num} <= 30", ["a"], "1")
>>> sw.add_branch("${num} > 30", ["end"], "2")
>>> flow.add_workflow_comp("sw", sw)
>>> 
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "sw")
>>> asyncio.run(flow.invoke({"a": 2}, WorkflowRuntime()))
begin to invoke, call_times=1, num=0, operation: num = 0 + 10
begin to invoke, call_times=2, num=10, operation: num = 10 + 10
begin to invoke, call_times=3, num=20, operation: num = 20 + 10
begin to invoke, call_times=4, num=30, operation: num = 30 + 10
->[end] get num = 40
```

### get_global_state

```python
get_global_state(self, key: Union[str, list, dict] = None) -> Any
```

Read global shared state with flexible extraction.

**Parameters**:

- **key** (Union[str, list, dict], optional): Key path to retrieve values from the global state, default None to fetch all. Supports the same forms as get_state:
  - str for a single path,
  - dict/list for multiple values via ${} variables.

**Returns**:

- For str key, returns the value at the path or None if not found.
- For dict/list key, returns the structure after replacing ${} variables with their resolved values (or None if not found).

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Output, Input
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 1. Custom component: add +10 to the global state each time
>>> class AddTenComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         call_times = runtime.get_state("call_times")
... 
...         # Get the current global state 'num'
...         num = runtime.get_global_state("num")
...         # Get multiple global states
...         num_dict = runtime.get_global_state({"current_call_time": "${current_call_time}", "num": "${num}"})
...         num_list = runtime.get_global_state({"current_call_time": "${current_call_time}", "num": "${num}"})
...         print(f"get call times: {call_times}, num: {num}, num_list: {num_list}")
... 
...         if not num:
...             num = 0
...         if not call_times:
...             call_times = 0
...         call_times += 1
...         num += 10
...         runtime.update_global_state({"num": num, "current_call_times": call_times})
...         # Update current state
...         runtime.update_state({"call_times": call_times})
...         return inputs
... 
>>> # 2. Custom component to read final global state 'num' at workflow end
>>> class CustomEnd(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'->[{self._node_id}] get num = {runtime.get_global_state("num")}')
...         return inputs
...  
>>> # 3. Create and run the workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.set_end_comp("end", CustomEnd("end"))
>>> flow.add_workflow_comp("a", AddTenComponent("a"))
>>> 
>>> sw = BranchComponent()
>>> sw.add_branch("${num} <= 30", ["a"], "1")
>>> sw.add_branch("${num} > 30", ["end"], "2")
>>> flow.add_workflow_comp("sw", sw)
>>> 
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "sw")
>>> asyncio.run(flow.invoke({"a": 2}, WorkflowRuntime()))
get call times: None, num: None, num_list: {'current_call_time': None, 'num': None}
get call times: 1, num: 10, num_list: {'current_call_time': None, 'num': 10}
get call times: 2, num: 20, num_list: {'current_call_time': None, 'num': 20}
get call times: 3, num: 30, num_list: {'current_call_time': None, 'num': 30}
->[end] get num = 40
```

### write_stream

```python
write_stream(self, data: Union[dict, OutputSchema])
```

Emit an OutputSchema-formatted streaming message and stream it out to the Agent or Workflow host.

**Parameters**:

- **data** (Union[dict, OutputSchema]): The streaming message. Must follow OutputSchema's format.
  - You can pass an OutputSchema instance directly.
  - Or a dict that must include OutputSchema fields 'type', 'index', and 'payload' with matching types.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

Create a custom node StreamNode that outputs two streaming messages in invoke.

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import OutputSchema, BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.write_stream(OutputSchema(type='end node stream', index=0, payload='done'))
...         await runtime.write_stream(dict(type='end node stream', index=1, payload='done'))
...         return inputs
... 
>>> # Create a simple workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("a", StreamNode())
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>>  
>>> async def run_workflow():
...     # Read streaming messages
...     async for chunk in flow.stream({}, WorkflowRuntime(), stream_modes=[BaseStreamMode.OUTPUT]):
...         print(chunk)
... 
>>> asyncio.run(run_workflow())
type='end node stream' index=0 payload='done'
type='end node stream' index=1 payload='done'
```

### write_custom_stream

```python
write_custom_stream(self, data: dict)
```

Emit a custom-formatted streaming message (CustomSchema) and stream it out to the Agent or Workflow host.

**Parameters**:

- **data** (dict): Streaming message content.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

Create a custom node StreamNode that outputs one custom streaming message in invoke.

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 1. Custom streaming component
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.write_custom_stream(dict(content="This is a streaming message", idx=1, message="message"))
...         return inputs
... 
>>> # 2. Create a simple workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("a", StreamNode())
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>> # 3. Read streaming messages
>>> async def run_workflow():
...     async for chunk in flow.stream({}, WorkflowRuntime(), stream_modes=[BaseStreamMode.CUSTOM]):
...         print(chunk)
...
>>> asyncio.run(run_workflow())
content="This is a streaming message" idx=1 message="message"
type='workflow_final' index=0 payload={'output': None}
```

### get_agent_config

```python
get_agent_config(self) -> AgentConfig
```

Get the current Agent's config information, or None if not available. See ReActAgentConfig and WorkflowAgentConfig.

**Returns**:

- **AgentConfig**: The current Agent's config, or None.

**Example**:

```python
>>> import asyncio
>>>
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.base import AgentConfig
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>>
>>>
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
...
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         agent_config: AgentConfig = runtime.get_agent_config()
...         agent_profile = f'{agent_config.id}-{agent_config.version}-{agent_config.description}'
...         return {"agent_profile": agent_profile}
...
>>> async def run_workflow():
...     flow = Workflow(workflow_config=WorkflowConfig(
...         metadata=WorkflowMetadata(id="demo_id", version="demo_version", name="demo_name",
...                                   description="this_is_a_demo")))
...     flow.set_start_comp("start", Start())
...     flow.add_workflow_comp("com", CustomComponent("demo_id"))
...     flow.set_end_comp("end", End(), inputs_schema={"profile": "${com}"})
...     flow.add_connection("start", "com")
...     flow.add_connection("com", "end")
...     test_workflow_schema = WorkflowSchema(
...         id="demo_id",
...         version="demo_version",
...         name="demo_name",
...         description="this_is_a_demo",
...         inputs={"query": {"type": "string"}},
...     )
...     workflow_agent_config = WorkflowAgentConfig(id="demo_agent", version="demo_version", description="this_is_a_demo",
...                                                 workflows=[test_workflow_schema],
...                                                 controller_type=ControllerType.WorkflowController
...                                                 )
...     agent = WorkflowAgent(agent_config=workflow_agent_config)
...
...     agent.bind_workflows([flow])
...
...     result = await agent.invoke(inputs={"conversation_id": "12345", "query": "demo"})
...
...     return result.get("output").result
...
>>> if __name__ == "__main__":
...     print(asyncio.get_event_loop().run_until_complete(run_workflow()))
...
{'output': {'profile': {'agent_profile': 'demo_agent-demo_version-this_is_a_demo'}}}
```

### get_workflow_config

```python
get_workflow_config(self, workflow_id) -> WorkflowConfig
```

Get the config information of the specified workflow, or None if not available. See WorkflowConfig.

**Parameters**:

- **workflow_id** (str, optional): The unique workflow ID.

**Returns**:

- **WorkflowConfig**, or None if not found.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.agent.common.enum import ControllerType
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.config.base import AgentConfig
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         workflow_config: WorkflowConfig = runtime.get_workflow_config(self._workflow_id)
...         workflow_metadata = workflow_config.metadata
...         agent_config: AgentConfig = runtime.get_agent_config()
...         agent_profile = f'{agent_config.id}-{agent_config.version}-{agent_config.description}'
...         workflow_profile = f'{workflow_metadata.name}-{workflow_metadata.version}-{workflow_metadata.description}'
...         return {"agent_profile": agent_profile, "workflow_profile": workflow_profile,
...                 "execution_id": runtime.executable_id(), "session_id": runtime.session_id()}
... 
>>> async def run_workflow():
...     flow = Workflow(workflow_config=WorkflowConfig(
...         metadata=WorkflowMetadata(id="fick_id", version="fick_version", name="fick_name",
...                                   description="this_is_a_demo")))
...     flow.set_start_comp("start", Start())
...     flow.add_workflow_comp("com", CustomComponent("fick_id"))
...     flow.set_end_comp("end", End(), inputs_schema={"profile": "${com}"})
...     flow.add_connection("start", "com")
...     flow.add_connection("com", "end")
...     test_workflow_schema = WorkflowSchema(
...         id="fick_id",
...         version="fick_version",
...         name="fick_name",
...         description="this_is_a_demo",
...         inputs={"query": {"type": "string"}},
...     )
...     workflow_agent_config = WorkflowAgentConfig(id="fick_agent", version="fick_version", description="this_is_a_demo",
...                                                 workflows=[test_workflow_schema],
...                                                 controller_type=ControllerType.WorkflowController
...                                                 )
...     agent = WorkflowAgent(agent_config=workflow_agent_config)
... 
...     agent.bind_workflows([flow])
... 
...     result = await agent.invoke(inputs={"conversation_id": "12345", "query": "demo"})
... 
...     return result.get("output").result
...  
>>> if __name__ == "__main__":
...     print(asyncio.get_event_loop().run_until_complete(run_workflow()))
...
{'output': {'profile': {'agent_profile': 'fick_agent-fick_version-this_is_a_demo', 'workflow_profile': 'fick_name-fick_version-this_is_a_demo', 'execution_id': 'com', 'session_id': '12345'}}}
```

### trace

```python
trace(self, data: dict)
```

Emit runtime trace messages as TraceSchema-formatted streaming messages and stream them out to the Agent or Workflow host. This helps users understand internals, ensure flows behave as expected, and quickly locate issues.

**Parameters**:

- **data** (dict): The runtime data to be recorded for tracing. This will populate the onInvokeData field in the payload of TraceSchema. If None, indicates no runtime data.

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Output, Input
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 1. Custom component that outputs trace streaming info
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.trace(dict(content="Record trace information"))
...         return inputs
... 
>>> # 2. Create a workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"a": "${a}"})
>>> flow.add_workflow_comp("a", StreamNode(), inputs_schema={"aa": "${start.a}"})
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>> 
>>> async def run_workflow():
...     # 3. Execute the workflow and read streaming outputs
...     async for chunk in flow.stream({"a": 1}, WorkflowRuntime(), stream_modes=[BaseStreamMode.TRACE]):
...         if 'onInvokeData' in chunk.payload and chunk.payload['onInvokeData'] and chunk.payload['status'] == 'running':
...             print(chunk.payload["onInvokeData"])
... 
>>> asyncio.run(run_workflow())
[{'content':'Record trace information'}]
```

### trace_error

```python
trace_error(self, error: Exception)
```

Emit error information that occurs during execution as TraceSchema-formatted streaming messages and stream them out to the Workflow or Agent host.

**Parameters**:

- **error** (Exception): The exception to be traced. This will populate the error field in the payload of TraceSchema.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

```python
>>> import asyncio
>>>
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Output, Input
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.common.exception.exception import JiuWenBaseException
>>>
>>> # 1. Create a custom component and output a trace error streaming message
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
...     
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.trace_error(JiuWenBaseException(error_code=-1, message="This is an error message"))
...         return inputs
...     
>>> # 2. Create a workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"a": "${a}"})
>>> flow.add_workflow_comp("a", StreamNode(), inputs_schema={"aa": "${start.a}"})
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>>
>>> # 3. Execute the workflow
>>> async def run_workflow():
...     async for chunk in flow.stream({"a": 1}, WorkflowRuntime(), stream_modes=[BaseStreamMode.TRACE]):
...         # Filter trace info that contains error and is not the final frame
...         if 'error' in chunk.payload and chunk.payload["error"] is not None and chunk.payload.get("outputs") is None:
...             print(chunk.payload["error"])
>>> 
>>> asyncio.run(run_workflow())
{'error_code': -1, 'message': 'This is an error message'}
```

### interact

```python
interact(self, value)
```

Interrupt the current Agent or Workflow execution to interact with the user, waiting for the user to provide additional input (InteractionInput), then resume execution from where it stopped. Currently only supported in a component's invoke and stream methods in non-streaming input mode.

When a question node in the workflow needs user input, this API can be used to return a prompt (value) to the user. Execution resumes from the interruption point after the user provides an answer.

**Parameters**:

- **value** (Any): The interruption prompt shown to the user. If None, indicates no prompt. Depending on the context:
  - If the interruption occurs during workflow.invoke, the value will be placed in a WorkflowChunk's payload (InteractionOutput), and returned as one item in WorkflowOutput.result.
  - If the interruption occurs during workflow.stream, the value will be placed in the payload (InteractionOutput) of one OutputSchema streaming frame with type INTERACTION.

**Returns**:

- **Any**, the raw_inputs or value from the user's InteractionInput.

**Examples**:

- Example 1: Interruption occurs during workflow.invoke.

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.interaction.interaction import InteractionOutput
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>>  
>>> # 1. Create a node with an interruption/interaction
>>> class InteractiveNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         cmd = inputs.get("cmd")
...         # Ask the user; wait for the answer
...         result = await runtime.interact(f"Do you want to execute the command '{cmd}'?")
...         return {"confirm_result": result}
... 
>>> # 2. Create a simple workflow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"command1": "${cmd1}"})
>>> flow.add_workflow_comp("interactive_node1", InteractiveNode(), inputs_schema={"cmd": "${start.command1}"}, outputs_schema={"result": "${confirm_result}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result1": "${interactive_node1.result}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> session_id = "session_id"
>>> # 3. Execute the workflow
>>> output = asyncio.run(flow.invoke({"cmd1": "delete all files"}, WorkflowRuntime(session_id=session_id)))
>>> 
>>> if isinstance(output.result[0].payload, InteractionOutput):
...     # Get the ID of the node that interrupted
...     node_id = output.result[0].payload.id
...     print(f'node_id={output.result[0].payload.id}, value={output.result[0].payload.value}')
... 
node_id=interactive_node1, value=Do you want to execute the command 'delete all files'?
>>> 
>>> # 4. User provides the interaction input
>>> user_input = InteractiveInput()
>>> user_input.update(node_id, "Yes")
>>> 
>>> # 5. Execute invoke again
>>> output = asyncio.run(flow.invoke(user_input, WorkflowRuntime(session_id=session_id)))
>>> print(output.result.get("output").get("result1"))
Yes
```

- Example 2: Interruption occurs during workflow.stream.

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.common.constants.constant import INTERACTION
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode, OutputSchema
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # 1. Custom interaction node
>>> class InteractiveStreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         # Interrupt execution and wait for the user input
...         result = await runtime.interact("Please enter any key")
... 
...         # Output the user's input as a streaming message
...         await runtime.write_stream(OutputSchema(type="output", index=0, payload=result))
...         return result
... 
>>> # 2. Create a workflow and run stream
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"a": "${inputs.a}",})
>>> flow.add_workflow_comp("interactive_node1", InteractiveStreamNode(),inputs_schema={ "aa": "${start.a}"},)
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${interactive_node1.aa}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> # 3. Execute stream
>>> async def run_workflow():
...     interaction_node_id = None
...     interaction_msg = None
...     session_id = "ss"
...     async for res in flow.stream({"inputs": {"a": 1}}, WorkflowRuntime(session_id=session_id), stream_modes=[BaseStreamMode.OUTPUT]):
...         if res.type == INTERACTION:
...             interaction_node_id = res.payload.id
...             interaction_msg = res.payload.value
...             print(interaction_node_id)
...             print(interaction_msg)
...     user_input = InteractiveInput()
...     user_input.update(interaction_node_id, {"aa": "any key"})
...     async for res in flow.stream(user_input, WorkflowRuntime(session_id=session_id), stream_modes=[BaseStreamMode.OUTPUT]):
...         if res.type == "output":
...             print(res.payload)
... 
>>> asyncio.run(run_workflow())
interactive_node1
Please enter any key
{"aa": "any key"}
```

### add_prompt

```python
add_prompt(self, template_id: str, template: Template)
```

Add a prompt template to the runtime resource manager. If template_id already exists, it will be overwritten.

**Parameters**:

- **template_id** (str): Unique template ID.
- **template** (Template): Template instance.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> user_prompt = """
...       {{user_prompt}}
...
...       Available function categories:
...       {{category_info}}
...
...       Conversation history between the user and the assistant:
...       {{chat_history}}
...
...       Current input:
...       {{input}}
...
...       Based on the current input and the conversation history, analyze and output the most suitable function category. Output format in JSON:
...       {"class": "Category XX"}
...       If there is no suitable category, output {{default_class}}.
...       """
>>> intent_detection_template = Template(name="default", content=[{"role": "user", "content": user_prompt}])
>>> runtime.add_prompt("default_template", intent_detection_template)
>>>
>>> print(runtime.get_prompt("default_template").name)
default
```

### add_prompts

```python
add_prompts(self, templates: List[Tuple[str, Template]])
```

Add multiple prompt templates to the runtime resource manager. If a template_id already exists, it will be overwritten.

**Parameters**:

- **templates** (List[Tuple[str, Template]]): A list of tuples (template_id, template).

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> intent_detection_template_1 = Template(name="default_1", content=[{"role": "user", "content": "{{user_prompt}}"}])
>>> question_template = Template(name="ask", content=[{"role": "user", "content": "{{chat_history}}"}])
>>> runtime.add_prompts([("default_template", intent_detection_template_1), ("question_template", question_template)])
>>>
>>> print(runtime.get_prompt('default_template').name)
default_1 
>>> print(runtime.get_prompt('question_template').name)
ask
```

### remove_prompt

```python
remove_prompt(self, template_id: str) -> Optional[Template]
```

Remove a prompt template from the runtime resource manager.

**Parameters**:

- **template_id** (str): Template ID. If None, returns None directly.

**Returns**:

- **Optional[Template]**, the removed template instance, or None if not found.

**Example**:

See the Complete code section for full samples.

```python
>>> runtime.remove_prompt("default_template")
>>> print(runtime.get_prompt("default_template"))
None
```

### get_prompt

```python
get_prompt(self, template_id: str) -> Optional[Template]
```

Fetch a prompt template by ID from the runtime resource manager.

**Parameters**:

- **template_id** (str): Template ID.

**Returns**:

- **Optional[Template]**, the template instance if found, otherwise None.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> intent_detection_template_1 = Template(name="default_1", content=[{"role": "user", "content": "{{user_prompt}}"}])
>>> question_template = Template(name="ask", content=[{"role": "user", "content": "{{chat_history}}"}])
>>> runtime.add_prompts([("default_template", intent_detection_template_1), ("question_template", question_template)])
>>>
>>> print(runtime.get_prompt('default_template').name)
default_1
>>> print(runtime.get_prompt('question_template').name)
ask
```

### add_workflow

```python
add_workflow(self, workflow_id: str, workflow: Workflow)
```

Add a workflow instance to the runtime resource manager. If workflow_id already exists, it will be overwritten.

**Parameters**:

- **workflow_id** (str): Workflow ID.
- **workflow** (Workflow): Workflow instance.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> workflow1 = _create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="1", version="1")))
>>> runtime.add_workflow("1_1", workflow1)
>>> print((await runtime.get_workflow("1_1")).config().metadata)
name='' id='1' version='1' description=''
```

### add_workflows

```python
add_workflows(self, workflows: List[Tuple[str, Workflow]])
```

Add multiple workflows to the runtime resource manager. If a workflow_id already exists, it will be overwritten.

**Parameters**:

- **workflows** (List[Tuple[str, Workflow]]): List of (workflow_id, workflow) pairs.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> # Add multiple workflows
>>> workflow2 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="2", version="2")))
>>> workflow3 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="3", version="3")))
>>> runtime.add_workflows([("2_2", workflow2), ("3_3", workflow3)])
>>> 
>>> print((await runtime.get_workflow("2_2")).config().metadata)
name='' id='2' version='2' description=''
>>> print((await runtime.get_workflow("3_3")).config().metadata)
name='' id='3' version='3' description=''
```

### remove_workflow

```python
remove_workflow(self, workflow_id: str) -> Optional[Workflow]
```

Remove a workflow from the runtime resource manager.

**Parameters**:

- **workflow_id** (str): Workflow ID. If None, returns None directly.

**Returns**:

- **Optional[Workflow]**, the removed workflow instance, or None if not found.

**Example**:

See the Complete code section for full samples.

```python
>>> runtime.remove_workflow("2_2")
>>> print(await runtime.get_workflow("2_2"))
None
```

### get_workflow

```python
async def get_workflow(self, workflow_id: str) -> Optional[Workflow]
```

Fetch a workflow by ID from the runtime resource manager. Returns None if not found.

**Parameters**:

- **workflow_id** (str): Workflow ID.

**Returns**:

- **Optional[Workflow]**, the workflow instance if found, otherwise None.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> # Add multiple workflows
>>> workflow2 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="2", version="2")))
>>> workflow3 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="3", version="3")))
>>> runtime.add_workflows([("2_2", workflow2), ("3_3", workflow3)])
>>> print((await runtime.get_workflow("2_2")).config().metadata)
name='' id='2' version='2' description=''
>>> print((await runtime.get_workflow("3_3")).config().metadata)
name='' id='3' version='3' description=''
```

### add_tool

```python
add_tool(self, tool_id: str, tool: Tool)
```

Add a tool to the runtime resource manager. If the tool already exists, it will be overwritten.

**Parameters**:

- **tool_id** (str): Tool ID.
- **tool** (Tool): Tool instance.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="Addition",
...     params=[
...         Param(name="a", description="Addend", type="number", required=True),
...         Param(name="b", description="Augend", type="number", required=True),
...     ],
...     func=lambda a, b: a + b
... )
... 
>>> runtime.add_tool("add_plugin", add_plugin)            
>>> tool = runtime.get_tool("add_plugin")
>>> print(tool.name)
add
```

### add_tools

```python
add_tools(self, tools: List[Tuple[str, Tool]])
```

Add multiple tools to the runtime resource manager. If a tool_id already exists, it will be overwritten.

**Parameters**:

- **tools** (List[Tuple[str, Tool]]): A list of (tool_id, tool) pairs.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="Addition",
...     params=[
...         Param(name="a", description="Addend", type="number", required=True),
...         Param(name="b", description="Augend", type="number", required=True),
...     ],
...     func=lambda a, b: a + b
... )
... 
>>> multiply_plugin = LocalFunction(
...     name="multiply",
...     description="Multiplication",
...     params=[
...         Param(name="a", description="Multiplier", type="number", required=True),
...         Param(name="b", description="Multiplicand", type="number", required=True),
...     ],
...     func=lambda a, b: a * b
... )
... 
>>> runtime.add_tools([("add_plugin", add_plugin), ("multiply_plugin", multiply_plugin)])
>>> tool = runtime.get_tool("multiply_plugin")
>>> print(tool.name)
multiply
```

### remove_tool

```python
remove_tool(self, tool_id: str) -> Optional[Tool]
```

Remove a tool from the runtime resource manager.

**Parameters**:

- **tool_id** (str): Tool ID. If None, returns None directly.

**Returns**:

- **Optional[Tool]**, the removed tool instance, or None if not found.

**Example**:

See the Complete code section for full samples.

```python
>>> runtime.remove_tool("add_plugin")
>>> print(runtime.get_tool("add_plugin"))
None
```

### get_tool

```python
get_tool(self, tool_id: str) -> Tool
```

Get a tool by ID from the runtime resource manager.

**Parameters**:

- **tool_id** (str): Tool ID.

**Returns**:

- **Tool**, the tool instance, or None if not found.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="Addition",
...     params=[
...         Param(name="a", description="Addend", type="number", required=True),
...         Param(name="b", description="Augend", type="number", required=True),
...     ],
...     func=lambda a, b: a + b
... )
... 
>>> runtime.add_tool("add_plugin", add_plugin)            
>>> tool = runtime.get_tool("add_plugin")
>>> print(tool.name)
add
```

### get_tool_info

```python
get_tool_info(self, tool_id: List[str], workflow_id: List[str]) -> List[ToolInfo]
```

Retrieve tool information from the runtime resource manager.

**Parameters**:

- **tool_id** (List[str], optional): List of tool IDs. Default None. If workflow_id is also None, returns all tool info; otherwise, does not include tool info.
- **workflow_id** (List[str], optional): List of workflow tool IDs. Default None. If tool_id is also None, returns all tool info; otherwise, does not include workflow tool info.

**Returns**:

- **List[ToolInfo]**, a list of tool info corresponding to the provided IDs.

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
>>> from openjiuwen.core.utils.tool.function.function import LocalFunction
>>> from openjiuwen.core.utils.tool.param import Param
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata, WorkflowInputsSchema
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     def _create_workflow(self, workflow_config):
...         workflow = Workflow(workflow_config)
...         workflow.set_start_comp("start", Start())
...         workflow.set_end_comp("end", End())
...         workflow.add_connection("start", "end")
...         return workflow
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         runtime.add_workflow("workflow_id1",
...                              Workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="id1", version="1"),
...                                                                      workflow_inputs_schema=WorkflowInputsSchema(
...                                                                          type="object",
...                                                                          properties={
...                                                                              "query": {
...                                                                                  "type": "string",
...                                                                                  "description": "User input",
...                                                                                  "required": True
...                                                                              }
...                                                                          },
...                                                                          required=['query']
...                                                                      ))))
... 
...         add_plugin = LocalFunction(
...             name="add",
...             description="Addition",
...             params=[
...                 Param(name="a", description="Addend", type="number", required=True),
...                 Param(name="b", description="Augend", type="number", required=True),
...             ],
...             func=lambda a, b: a + b
...         )
... 
...         runtime.add_tool("add_plugin", add_plugin)
... 
...         tool_infos = runtime.get_tool_info(tool_id=["add_plugin"], workflow_id=["workflow_id1"])
...         print(len(tool_infos))
... 
...         print(tool_infos[0])
... 
...         print(tool_infos[1])
... 
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>> 
>>> asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
type='function' function=Function(name='add', description='Addition', parameters=Parameters(type='object', properties={'a': {'description': 'Addend', 'type': 'string'}, 'b': {'description': 'Augend', 'type': 'string'}}, required=['a', 'b']))
type='function' function=Function(name='', description='', parameters=Parameters(type='object', properties={'query': {'type': 'string', 'description': 'User input', 'required': True}}, required=['query']))
```

### add_model

```python
add_model(model_id: str, model: BaseChatModel)
```

Add a model to the runtime resource manager. If model_id already exists, it will be overwritten.

**Parameters**:

- **model_id** (str): Unique model ID.
- **model** (BaseChatModel): Model instance.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> model = self._get_model(timeout=10)
>>> runtime.add_model("model", model)
>>> saved_model = runtime.get_model("model")
>>> print(f"Saved model: {type(saved_model).__name__}")
Saved model: Siliconflow
```

### add_models

```python
add_models(models: List[Tuple[str, BaseChatModel]])
```

Add multiple models to the runtime resource manager. If a model_id already exists, it will be overwritten.

**Parameters**:

- **models** (List[Tuple[str, BaseChatModel]]): List of (model_id, model) pairs.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> model1 = self._get_model(timeout=1)
>>> model2 = self._get_model(timeout=2)
>>> runtime.add_models([("model_1", model1), ("model_2", model2)])
>>> print(f"model_1 exists: {runtime.get_model('model_1') is not None}")
model_1 exists: True
>>> print(f"model_2 exists: {runtime.get_model('model_2') is not None}")
model_2 exists: True
```

### remove_model

```python
remove_model(model_id: str) -> Optional[BaseChatModel]
```

Remove a model from the runtime resource manager.

**Parameters**:

- **model_id** (str): Model ID. If None, returns None directly.

**Returns**:

- **Optional[BaseChatModel]**, the removed model, or None if not found.

**Example**:

See the Complete code section for full samples.

```python
>>> runtime.remove_model("model_1")
>>> print(runtime.get_model('model_1'))
None
```

### get_model

```python
get_model(self, model_id: str) -> Optional[BaseChatModel]
```

Fetch a model by ID from the runtime resource manager.

**Parameters**:

- **model_id** (str): Model ID.

**Returns**:

- **Optional[BaseChatModel]**, the model instance if found, otherwise None.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. See StatusCode for details.

**Example**:

See the Complete code section for full samples.

```python
>>> model1 = self._get_model(timeout=1)
>>> model2 = self._get_model(timeout=2)
>>> runtime.add_models([("model_1", model1), ("model_2", model2)])
>>> print(f"model_1 exists: {runtime.get_model('model_1') is not None}")
model_1 exists: True
>>> print(f"model_2 exists: {runtime.get_model('model_2') is not None}")
model_2 exists: True
```

## Complete code

Complete code for prompt resource:

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
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         user_prompt = """
...              {{user_prompt}}
...
...              Available function categories:
...              {{category_info}}
...
...              Conversation history between the user and the assistant:
...              {{chat_history}}
...
...              Current input:
...              {{input}}
...
...              Based on the current input and the conversation history, analyze and output the most suitable function category. Output format in JSON:
...              {"class": "Category XX"}
...              If there is no suitable category, output {{default_class}}.
...              """
...         intent_detection_template = Template(name="default", content=[{"role": "user", "content": user_prompt}])
...         runtime.add_prompt("default_template", intent_detection_template)
...
...         print(runtime.get_prompt("default_template").name)
...
...         intent_detection_template_1 = Template(name="default_1", content=[{"role": "user", "content": "{{user_prompt}}"}])
...         question_template = Template(name="ask", content=[{"role": "user", "content": "{{chat_history}}"}])
...         runtime.add_prompts([("default_template", intent_detection_template_1), ("question_template", question_template)])
...
...         print(runtime.get_prompt('default_template').name)
...         print(runtime.get_prompt('question_template').name)
...
...         runtime.remove_prompt("default_template")
...         print(runtime.get_prompt("default_template"))
>>> 
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>> 
>>> asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))   
default
default_1
ask
None
```

Complete code for workflow resource:

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
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     def _create_workflow(self, workflow_config):
...         workflow = Workflow(workflow_config)
...         workflow.set_start_comp("start", Start())
...         workflow.set_end_comp("end", End())
...         workflow.add_connection("start", "end")
...         return workflow
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         # Add one workflow
...         workflow1 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="1", version="1")))
...         runtime.add_workflow("1_1", workflow1)
...         print((await runtime.get_workflow("1_1")).config().metadata)
... 
...         # Add multiple workflows
...         workflow2 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="2", version="2")))
...         workflow3 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="3", version="3")))
...         runtime.add_workflows([("2_2", workflow2), ("3_3", workflow3)])
... 
...         print((await runtime.get_workflow("2_2")).config().metadata)
...         print((await runtime.get_workflow("3_3")).config().metadata)
... 
...         runtime.remove_workflow("2_2")
...         print(await runtime.get_workflow("2_2"))
... 
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>> 
>>> asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
name='' id='1' version='1' description=''
name='' id='2' version='2' description=''
name='' id='3' version='3' description=''
None
```

Complete code for model resource:

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
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     def _get_model(self, timeout):
...         # You need to replace api_base and api_key with real endpoint and key
...         return ModelFactory().get_model(
...             model_provider="siliconflow",
...             api_key="sk-****************************",
...             api_base="https://api.siliconflow.cn/v1",
...             max_retries=1,
...             timeout=timeout,
...         )
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         model = self._get_model(timeout=10)
...         runtime.add_model("model", model)
...         saved_model = runtime.get_model("model")
...         print(f"Saved model: {type(saved_model).__name__}")
... 
...         model1 = self._get_model(timeout=1)
...         model2 = self._get_model(timeout=2)
...         runtime.add_models([("model_1", model1), ("model_2", model2)])
...         print(f"model_1 exists: {runtime.get_model('model_1') is not None}")
...         print(f"model_2 exists: {runtime.get_model('model_2') is not None}")
... 
...         runtime.remove_model("model_1")
...         print(runtime.get_model('model_1'))
... 
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>> 
>>> asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
Saved model: Siliconflow
model_1 exists: True
model_2 exists: True
None
```

Complete code for tool management:

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
>>> from openjiuwen.core.utils.tool.function.function import LocalFunction
>>> from openjiuwen.core.utils.tool.param import Param
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, workflow_id):
...         super().__init__()
...         self._workflow_id = workflow_id
... 
...     def _create_workflow(self, workflow_config):
...         workflow = Workflow(workflow_config)
...         workflow.set_start_comp("start", Start())
...         workflow.set_end_comp("end", End())
...         workflow.add_connection("start", "end")
...         return workflow
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         add_plugin = LocalFunction(
...             name="add",
...             description="Addition",
...             params=[
...                 Param(name="a", description="Addend", type="number", required=True),
...                 Param(name="b", description="Augend", type="number", required=True),
...             ],
...             func=lambda a, b: a + b
...         )
...         runtime.add_tool("add_plugin", add_plugin)
... 
...         tool = runtime.get_tool("add_plugin")
...         print(tool.name)
... 
...         add_plugin = LocalFunction(
...             name="add",
...             description="Addition",
...             params=[
...                 Param(name="a", description="Addend", type="number", required=True),
...                 Param(name="b", description="Augend", type="number", required=True),
...             ],
...             func=lambda a, b: a + b
...         )
... 
...         multiply_plugin = LocalFunction(
...             name="multiply",
...             description="Multiplication",
...             params=[
...                 Param(name="a", description="Multiplier", type="number", required=True),
...                 Param(name="b", description="Multiplicand", type="number", required=True),
...             ],
...             func=lambda a, b: a * b
...         )
... 
...         runtime.add_tools([("add_plugin", add_plugin), ("multiply_plugin", multiply_plugin)])
...         tool = runtime.get_tool("multiply_plugin")
...         print(tool.name)
... 
...         runtime.remove_tool("add_plugin")
...         print(runtime.get_tool("add_plugin"))
... 
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("custom", CustomComponent("custom"))
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "custom")
>>> flow.add_connection("custom", "end")
>>> 
>>> 
>>> asyncio.run(flow.invoke(inputs={}, runtime=WorkflowRuntime()))
add
multiply
None
```