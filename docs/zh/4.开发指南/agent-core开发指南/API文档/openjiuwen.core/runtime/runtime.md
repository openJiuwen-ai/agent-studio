# openjiuwen.core.runtime.runtime

## class Runtime

```python
class openjiuwen.core.runtime.runtime.Runtime()
```

Agent、Workflow运行时核心操作类，封装了状态管理、配置管理、流式输出、调测信息追踪、资源管理多个能力。

### executable_id

```python
executable_id(self) -> str
```

获取当前执行单元的全局唯一标识符。若在Agent任务中获取，返回为Agent的ID。若在工作流的组件中获取，返回为组件的ID。

**返回**：

**str**，当前工作流节点/Agent任务的唯一ID。

**样例**：

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

获取本次工作流执行的唯一会话标识。

**返回**：

**str**，当前工作流的唯一会话标识。

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

更新**当前执行单元**的状态数据，若不存在字段会新增。

- 若在Agent执行过程中更新状态，表示更新当前Agent的状态数据，并且立即生效。
- 若在Workflow执行过程中更新状态，表示更新当前组件的状态数据，在组件执行完生效。

**参数**：

- **data**(dict)：新增或更新的键值对字典。若data为None或{}，表示不更新。

**样例**：

更新状态信息

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
>>> # 2.  创建工作流并执行，工作流中含有loop组件，loop中包含自定义组件
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
>>> # 3. 执行工作流
>>> runtime = WorkflowRuntime()
>>> asyncio.run(flow.invoke({"user_inputs": {"query": "你好", "loop_number": 3}}, runtime))
[a] current state is {'recall_times': 1, 'messages': ['你好']}
[a] current state is {'recall_times': 2, 'messages': ['你好', '你好']}
[a] current state is {'recall_times': 3, 'messages': ['你好', '你好', '你好']}
```

### get_state

```python
get_state(self, key: Union[str, list, dict] = None) -> Any
```

读取**当前执行单元**的状态数据，支持灵活的数据提取。

- 若在Agent执行过程中获取状态信息，表示获取本Agent的状态信息。
- 若在Workflow执行过程中获取状态信息，表示获取当前组件的状态信息。

**参数**：

- **key** (Union[str, list, dict], 可选)：查询状态数据中对应value的key，默认`None`，表示获取全部的状态信息。根据`key`的取值类型，支持多种方式获取状态数据。
  - 当`key`为`str`类型，表示获取`key`路径下的状态数据，key可以为嵌套路径结构，例如`"user_inputs.query"`。
  - 当`key`为`dict`\ `list`类型，表示获取多个状态数据，该`dict`\ `list`中存在多个用`"${}"`包裹的变量，每个变量都是一个状态数据的路径。

**返回**：

**Any**，返回的状态值。根据`key`的类型的不同，返回结果为：

- 当`key`为`str`类型，返回为该路径下的状态信息，若不存在，则返回`None`。
- 当`key`为`dict`\ `list`类型，该接口会将输入的`dict`\ `list`中所有`${}`内的变量替换成相应路径的变量的值，若对应变量路径不存在，则替换为`None`，最终返回为替换完的结果。

**样例**：

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
...        # 获取单个状态
...        recall_times = runtime.get_state("recall_times")
...        # 获取多个状态
...        my_state = runtime.get_state({"recall_times": "${recall_times}", "messages": "${messages}"})
...        # 获取列表状态
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
>>> # 2.  创建工作流并执行，工作流中含有loop组件，loop中包含自定义组件
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
>>> # 3. 执行工作流
>>> runtime = WorkflowRuntime()
>>> 
>>> asyncio.run(flow.invoke({"user_inputs": {"query": "你好", "loop_number": 3}}, runtime))
recall_times: None, my_state: None, my_state_list: None
recall_times: 1, my_state: {'recall_times': 1, 'messages': ['你好']}, my_state_list: [1, ['你好']]
recall_times: 2, my_state: {'recall_times': 2, 'messages': ['你好', '你好']}, my_state_list: [2, ['你好', '你好']]
```

### update_global_state

```python
update_global_state(self, data: dict)
```

更新**全局共享**状态。**全局状态**表示Agent和Workflow之间共享的数据和变量。但是，在Agent中和Workflow中的更新生效时间有不同：

- 在Agent中，更新全局状态即可生效。
- 在Workflow中，更新全局状态生效时间为当前组件执行完。

**参数**：

- **data**(dict)：新增或更新的键值对字典。若入参为None或{}，表示不更新。

**样例**：

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
>>> # 1. 实现自定义组件, 用于全局状态每次进行+10的操作 
>>> class AddTenComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         call_times = runtime.get_state("call_times")
...         # 获取当前全局状态num
...         num = runtime.get_global_state("num")
...         if not num:
...             num = 0
...         if not call_times:
...             call_times = 0
...         call_times += 1
...         print(f"begin to invoke, call_times={call_times}, num={num}, operation: num = {num} + 10")
...         num += 10
...         runtime.update_global_state({"num": num})
...         # 更新当前全局状态
...         runtime.update_state({"call_times": call_times})
...         return inputs 
... 
>>> # 2. 自定义组件，用于工作流结束时读取全局状态num
>>> class CustomEnd(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'->[{self._node_id}] get num = {runtime.get_global_state("num")}')
...         return inputs
... 
>>> # 3. 创建工作流，并且执行工作流
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

读取全局共享状态数据，支持灵活的数据提取。

**参数**：

- **key** (Union[str, list, dict], 可选)：查询状态数据中对应value的key，默认`None`，表示获取全部的状态信息。根据`key`的取值类型，支持多种方式获取状态数据。
  - 当`key`为`str`类型，表示获取`key`路径下的状态数据，key可以为嵌套路径结构，例如`"user_inputs.query"`。
  - 当`key`为`dict`\ `list`类型，表示获取多个状态数据，该`dict`\ `list`中存在多个用`"${}"`包裹的变量，每个变量都是一个状态数据的路径。

**返回**：

根据`key`的类型的不同，返回结果为：

- 当`key`为`str`类型，返回为该路径下的状态信息，若不存在，则返回`None`。
- 当`key`为`dict`\ `list`类型，该接口会将输入的`dict`\ `list`中所有`${}`内的变量替换成相应路径的变量的值，若对应变量路径不存在，则替换为`None`，最终返回为替换完的结果。

**样例**：

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
>>> # 1. 实现自定义组件, 用于全局状态每次进行+10的操作
>>> class AddTenComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         call_times = runtime.get_state("call_times")
... 
...         # 获取当前全局状态num
...         num = runtime.get_global_state("num")
...         # 获取多个全局状态
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
...         # 更新当前全局状态
...         runtime.update_state({"call_times": call_times})
...         return inputs
... 
>>> # 2. 自定义组件，用于工作流结束时读取全局状态num
>>> class CustomEnd(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id):
...         super().__init__()
...         self._node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'->[{self._node_id}] get num = {runtime.get_global_state("num")}')
...         return inputs
...  
>>> # 3. 创建工作流，并且执行工作流
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

输出openJiuwen标准格式[OutputSchema](../stream/base.md#class-openjiuwencorestreambaseoutputschema)流式消息，并流出到Agent或者Workflow外。

**参数**：

- **data** (Union[dict, OutputSchema])：流式消息。该消息有严格的格式规定。
  - 直接提供`OutputSchema`对象，[OutputSchema](../stream/base.md#class-openjiuwencorestreambaseoutputschema)为openJiuwen内置的标准流式输出格式。
  - 可以提供`dict`类型的字段，但是必须包含[OutputSchema](../stream/base.md#class-openjiuwencorestreambaseoutputschema)中定义的字段`'type'`、`'index'`、`'payload'`，并且数据类型相同。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

创建自定义节点StreamNode，invoke中输出了两条流式消息

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
>>> # 创建简单工作流
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("a", StreamNode())
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>>  
>>> async def run_workflow():
...     # 获取流式消息
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

输出自定义格式[CustomSchema](../stream/base.md#class-openjiuwencorestreambasecustomschema)的流式消息，并流出到Agent或者Workflow外。

**参数**：

- **data** (dict)：流式消息内容。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

创建自定义节点StreamNode，invoke中输出了一条自定义格式的流式消息

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
>>> # 1. 自定义实现一个流式输出的组件
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.write_custom_stream(dict(content="这是一条流式消息", idx=1, message="消息"))
...         return inputs
... 
>>> # 2. 创建简单工作流
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start())
>>> flow.add_workflow_comp("a", StreamNode())
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>> # 3. 获取流式消息
>>> async def run_workflow():
...     async for chunk in flow.stream({}, WorkflowRuntime(), stream_modes=[BaseStreamMode.CUSTOM]):
...         print(chunk)
...
>>> asyncio.run(run_workflow())
content="这是一条流式消息" idx=1 message="消息"
type='workflow_final' index=0 payload={'output': None}
```

### get_agent_config

```python
get_agent_config(self) -> AgentConfig
```

获取当前Agent的config信息，若不存在，则返回`None`。Agent的config可参考 [ReActAgentConfig](../../openjiuwen.agent/config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig)和[WorkflowAgentConfig](../../openjiuwen.agent/config/workflow_config.md#class-openjiuwenagentconfigworkflow_configworkflowagentconfig)。

**返回**：

**AgentConfig**：当前Agent的config信息，若不存在，返回`None`。

**样例**：

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

获取指定工作流的config信息，若不存在，则返回`None`。工作流的config可参考[WorkflowConfig](../../openjiuwen.agent/config/workflow_config.md)。

**参数**：

- **workflow_id**(str, 可选)：指定workflow唯一标识ID。

**返回**：

**WorkflowConfig**，Workflow的config信息，若不存在，返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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

输出运行信息的流式消息，并以[TraceSchema](../stream/base.md#class-openjiuwencorestreambasetraceschema)格式的流式消息流出到Agent或者Workflow外，方便用户深入了解内部的运行机制，确保流程按照预期进行，同时能够快速找到问题所在，提高工作效率。

**参数**：

- **data**(dict)：需要溯源记录的运行数据。该数据将会填充到openJiuwen内置的流式消息格式[TraceSchema](../stream/base.md#class-openjiuwencorestreambasetraceschema)中payload结构中的`onInvokeData`字段，当为`None`时，表示没有运行数据。

**样例**：

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
>>> # 1. 自定义实现一个记录trace流信息的组件
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.trace(dict(content="记录trace信息"))
...         return inputs
... 
>>> # 2. 创建工作流
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"a": "${a}"})
>>> flow.add_workflow_comp("a", StreamNode(), inputs_schema={"aa": "${start.a}"})
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>> 
>>> async def run_workflow():
...     # 3. 执行工作流，并获取流式输出数据
...     async for chunk in flow.stream({"a": 1}, WorkflowRuntime(), stream_modes=[BaseStreamMode.TRACE]):
...         if 'onInvokeData' in chunk.payload and chunk.payload['onInvokeData'] and chunk.payload['status'] == 'running':
...             print(chunk.payload["onInvokeData"])
... 
>>> asyncio.run(run_workflow())
[{'content':'记录trace信息'}]
```

### trace_error

```python
trace_error(self, error: Exception)
```

输出运行过程中的错误信息，并以[TraceSchema](../stream/base.md#class-openjiuwencorestreambasetraceschema)格式的流式消息输出到Workflow或者Agent外。

**参数**：

- **error**(Exception)：错误异常信息。该数据将会填充到openJiuwen内置的流式消息格式[TraceSchema](../stream/base.md#class-openjiuwencorestreambasetraceschema)中payload结构中的`error`字段。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
>>> # 1. 创建自定义组件，并且流出一条trace error的流式消息
>>> class StreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
...     
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         await runtime.trace_error(JiuWenBaseException(error_code=-1, message="这是一条错误信息"))
...         return inputs
...     
>>> # 2. 创建工作流
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={"a": "${a}"})
>>> flow.add_workflow_comp("a", StreamNode(), inputs_schema={"aa": "${start.a}"})
>>> flow.set_end_comp("end", End())
>>> flow.add_connection("start", "a")
>>> flow.add_connection("a", "end")
>>>
>>> # 3. 执行工作流
>>> async def run_workflow():
...     async for chunk in flow.stream({"a": 1}, WorkflowRuntime(), stream_modes=[BaseStreamMode.TRACE]):
...         # 用于过滤带有error信息、且不为最后一帧的调测信息
...         if 'error' in chunk.payload and chunk.payload["error"] is not None and chunk.payload.get("outputs") is None:
...             print(chunk.payload["error"])
>>> 
>>> asyncio.run(run_workflow())
{'error_code': -1, 'message': '这是一条错误信息'}
```

### interact

```python
interact(self, value)
```

中断当前Agent或者Workflow执行，与用户进行交互，并等待用户补充输入[InteractionInput](./interaction.md#class-openjiuwencoreruntimeinteractioninteractive_inputinteractiveinput)后，从中断位置继续执行。该接口目前仅支持在组件的非流式输入模式下的`invoke`和`stream`接口中使用。
当工作流中具有提问节点，提问节点产生提问需求，可以调用该接口，并将问题信息作为value返回给用户，直到该用户输入新的回答，工作流从调用该接口的位置恢复执行。

**参数**：

- **value**(Any)：反馈给用户的中断提示信息，若取值为`None`，表示没有中断提示信息。根据中断发生的场景不同，该信息最终返回给用户的位置也有差异。
  - 当中断发生在工作流的`invoke`执行过程中，value会被填充到一个`WorkflowChunk`的`payload`(类型为`InteractionOutput`)中，并作为工作流执行结果`WorkflowOutput.result`列表的一个item返回。
  - 当中断发生在工作流的`stream`执行过程中，value会被填充到一帧`OutputSchema`格式的流式信息的`payload`(类型为`InteractionOutput`)中，并流出到工作流外，该流式信息的type为`INTERACTION`。

**返回**：

**Any**，用户补充输入[InteractionInput](./interaction.md#class-openjiuwencoreruntimeinteractioninteractive_inputinteractiveinput)中的`raw_inputs`或者`value`。

**样例**：

- 样例一：工作流的`invoke`执行过程中，出现中断交互。

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
>>> # 1.  创建一个带中断交互的节点
>>> class InteractiveNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         cmd = inputs.get("cmd")
...         # 向用户提问, 等待用户回答
...         result = await runtime.interact(f"Do you want to execute the command '{cmd}'?")
...         return {"confirm_result": result}
... 
>>> # 2. 创建简单工作流
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"command1": "${cmd1}"})
>>> flow.add_workflow_comp("interactive_node1", InteractiveNode(), inputs_schema={"cmd": "${start.command1}"}, outputs_schema={"result": "${confirm_result}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result1": "${interactive_node1.result}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> session_id = "session_id"
>>> #3.  执行工作流
>>> output = asyncio.run(flow.invoke({"cmd1": "delete all files"}, WorkflowRuntime(session_id=session_id)))
>>> 
>>> if isinstance(output.result[0].payload, InteractionOutput):
...     # 获取中断节点id
...     node_id = output.result[0].payload.id
...     print(f'node_id={output.result[0].payload.id}, value={output.result[0].payload.value}')
... 
node_id=interactive_node1, value=Do you want to execute the command 'delete all files'?
>>> 
>>> # 4. 用户向中断节点输入交互补充信息
>>> user_input = InteractiveInput()
>>> user_input.update(node_id, "Yes")
>>> 
>>> # 5. 执行invoke
>>> output = asyncio.run(flow.invoke(user_input, WorkflowRuntime(session_id=session_id)))
>>> print(output.result.get("output").get("result1"))
Yes
```

- 样例二：工作流的`stream`执行过程中，出现中断交互。

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
>>> # 1. 自定义交互节点
>>> class InteractiveStreamNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         # 中断执行，等待用户补充信息
...         result = await runtime.interact("Please enter any key")
... 
...         # 将用户补充的userInput信息作为一帧流式消息输出
...         await runtime.write_stream(OutputSchema(type="output", index=0, payload=result))
...         return result
... 
>>> # 2. 创建工作流, 并触发执行stream
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"a": "${inputs.a}",})
>>> flow.add_workflow_comp("interactive_node1", InteractiveStreamNode(),inputs_schema={ "aa": "${start.a}"},)
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${interactive_node1.aa}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> # 3. 执行stream
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

向runtime的资源管理器中增加一个提示词模板，如果template_id已经存在，则覆盖已有的template。

**参数**：

- **template_id**(str)：模板唯一id。
- **template**(Template)：模板实例。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> from openjiuwen.core.utils.prompt.template.template import Template
>>> user_prompt = """
...       {{user_prompt}}
...
...       当前可供选择的功能分类如下：
...       {{category_info}}
...
...       用户与助手的对话历史：
...       {{chat_history}}
...
...       当前输入：
...       {{input}}
...
...       请根据当前输入和对话历史分析并输出最适合的功能分类。输出格式为 JSON：
...       {"class": "分类xx"}
...       如果没有合适的分类，请输出 {{default_class}}。
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

向runtime的资源管理器中批量增加提示词模板，如果template_id已经存在，则覆盖已有的template。

**参数**：

- **templates**(List[Tuple[str, Template]])：模板列表，每个元素为template_id，template的元组。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

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

向runtime的资源管理器中删除一个提示词模板。

**参数**：

- **template_id**(str)：提示词模板id，若id为`None`，则直接返回`None`。

**返回**：

**Optional[Template]**，删除的template对象，若不存在，则返回`None`。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> runtime.remove_prompt("default_template")
>>> print(runtime.get_prompt("default_template"))
None
```

### get_prompt

```python
get_prompt(self, template_id: str) -> Optional[Template]
```

从runtime的资源管理器中查询指定id的提示词模板。

**参数**：

- **template_id**(str)：提示词模板id。

**返回**：

**Optional[Template]**，指定id的提示词模板实例，若不存在，则返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

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

向runtime的资源管理器中增加一个workflow实例，如果workflow_id已经存在，则覆盖已有的workflow。

**参数**：

- **workflow_id**(str)：workflow的id。
- **workflow**(Workflow)：workflow实例。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

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

向runtime的资源管理器中批量增加workflows，如果workflow_id已经存在，则覆盖已有的workflow。

**参数**：

- **workflows**(List[Tuple[str, Workflow]])：工作流实例列表，每个元素为workflow_id和workflow的元组。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> # 批量添加workflow
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

向runtime的资源管理器中删除一个workflow。

**参数**：

- **workflow_id**(str)：workflow的id，若id为`None`，则直接返回`None`。

**返回**：

**Optional[Workflow]**，被删除的workflow的实例，若不存在，则返回`None`。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> runtime.remove_workflow("2_2")
>>> print(await runtime.get_workflow("2_2"))
None
```

### get_workflow

```python
async def get_workflow(self, workflow_id: str) -> Optional[Workflow]
```

从runtime的资源管理器中查询指定id的workflow，若不存在，返回`None`。

**参数**：

- **workflow_id**(str)：workflow的id。

**返回**：

**Optional[Workflow]**，指定id的workflow实例，若不存在，则返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> # 批量添加workflow
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

向runtime的资源管理器中增加一个tool，如果tool已经存在，则覆盖已有的tool。

**参数**：

- **tool_id**(str)：工具id。
- **tool**(Tool)：工具实例。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="加法",
...     params=[
...         Param(name="a", description="加数", type="number", required=True),
...         Param(name="b", description="被加数", type="number", required=True),
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

向runtime的资源管理器中批量增加tools，如果tool_id已经存在，则覆盖已有的tool。

**参数**：

- **tools**(List[Tuple[str, Tool]])：tool列表，每个元素为tool_id，tool的元组。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="加法",
...     params=[
...         Param(name="a", description="加数", type="number", required=True),
...         Param(name="b", description="被加数", type="number", required=True),
...     ],
...     func=lambda a, b: a + b
... )
... 
>>> multiply_plugin = LocalFunction(
...     name="multiply",
...     description="乘法",
...     params=[
...         Param(name="a", description="乘数", type="number", required=True),
...         Param(name="b", description="被乘数", type="number", required=True),
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

向runtime的资源管理器中删除一个工具。

**参数**：

- **tool_id**(str)：工具id，当id为`None`，直接返回`None`。

**返回**：

**Optional[Tool]**，被删除的tool实例，若`tool_id`不存在，则返回`None`。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> runtime.remove_tool("add_plugin")
>>> print(runtime.get_tool("add_plugin"))
None
```

### get_tool

```python
get_tool(self, tool_id: str) -> Tool
```

从runtime的资源管理器中获取指定id的工具。

**参数**：

- **tool_id**(str)：工具id。

**返回**：

**Tool**，指定id的工具实例，若不存在，则返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> add_plugin = LocalFunction(
...     name="add",
...     description="加法",
...     params=[
...         Param(name="a", description="加数", type="number", required=True),
...         Param(name="b", description="被加数", type="number", required=True),
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

从runtime的资源管理器中获取工具的信息。

**参数**：

- **tool_id**(List[str], 可选)：工具id列表，默认为None，当`workflow_id`同时为`None`，表示获取全量的toolInfo，否则表示不获取工具的toolInfo。
- **workflow_id**(List[str]， 可选)：workflow工具id列表，默认为None，当`tool_id`同时为`None`，表示获取全量的toolInfo，否则表示不获取workflow的toolInfo。

**返回**：

**List[ToolInfo]**，按照提供的id返回tool信息列表。

**样例**：

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
...                                                                                  "description": "用户输入",
...                                                                                  "required": True
...                                                                              }
...                                                                          },
...                                                                          required=['query']
...                                                                      ))))
... 
...         add_plugin = LocalFunction(
...             name="add",
...             description="加法",
...             params=[
...                 Param(name="a", description="加数", type="number", required=True),
...                 Param(name="b", description="被加数", type="number", required=True),
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
type='function' function=Function(name='add', description='加法', parameters=Parameters(type='object', properties={'a': {'description': '加数', 'type': 'string'}, 'b': {'description': '被加数', 'type': 'string'}}, required=['a', 'b']))
type='function' function=Function(name='', description='', parameters=Parameters(type='object', properties={'query': {'type': 'string', 'description': '用户输入', 'required': True}}, required=['query']))
```

### add_model

```python
add_model(model_id: str, model: BaseChatModel)
```

向runtime的资源管理器中增加一个模型，如果`model_id`已经存在，则覆盖已有的模型。

**参数**：

- **model_id**(str)：模型唯一ID。
- **model**(BaseChatModel)：模型实例。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> model = self._get_model(timeout=10)
>>> runtime.add_model("model", model)
>>> saved_model = runtime.get_model("model")
>>> print(f"保存模型: {type(saved_model).__name__}")
保存模型: Siliconflow
```

### add_models

```python
add_models(models: List[Tuple[str, BaseChatModel]])
```

向runtime的资源管理器中批量增加模型，如果model_id已经存在，则覆盖已有的模型。

**参数**：

- **models**(List[Tuple[str, BaseChatModel]])：模型列表，每个元素为model_id和model的元组。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> model1 = self._get_model(timeout=1)
>>> model2 = self._get_model(timeout=2)
>>> runtime.add_models([("model_1", model1), ("model_2", model2)])
>>> print(f"model_1 存在: {runtime.get_model('model_1') is not None}")
model_1 存在: True
>>> print(f"model_2 存在: {runtime.get_model('model_2') is not None}")
model_2 存在: True
```

### remove_model

```python
remove_model(model_id: str) -> Optional[BaseChatModel]
```

向runtime的资源管理器中删除一个模型。

**参数**：

- **model_id**(str)：模型id，若id为`None`，则直接返回`None`。

**返回**：

**Optional[BaseChatModel]**，删除的模型对象，若不存在，则返回`None`。

**样例**：

完整代码参考[完整代码](runtime.md#完整代码)。

```python
>>> runtime.remove_model("model_1")
>>> print(runtime.get_model('model_1'))
None
```

### get_model

```python
get_model(self, model_id: str) -> Optional[BaseChatModel]
```

从runtime的资源管理器中查询指定id的模型。

**参数**：

- **model_id**(str)：模型id。

**返回**：

**Optional[BaseChatModel]**，指定id的模型实例，若不存在，则返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

完整代码参考[完整代码](#完整代码)。

```python
>>> model1 = self._get_model(timeout=1)
>>> model2 = self._get_model(timeout=2)
>>> runtime.add_models([("model_1", model1), ("model_2", model2)])
>>> print(f"model_1 存在: {runtime.get_model('model_1') is not None}")
model_1 存在: True
>>> print(f"model_2 存在: {runtime.get_model('model_2') is not None}")
model_2 存在: True
```

## 完整代码

prompt资源完整代码：

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
...              当前可供选择的功能分类如下：
...              {{category_info}}
...
...              用户与助手的对话历史：
...              {{chat_history}}
...
...              当前输入：
...              {{input}}
...
...              请根据当前输入和对话历史分析并输出最适合的功能分类。输出格式为 JSON：
...              {"class": "分类xx"}
...              如果没有合适的分类，请输出 {{default_class}}。
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

workflow资源完整代码：

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
...         # 添加1个workflow
...         workflow1 = self._create_workflow(workflow_config=WorkflowConfig(metadata=WorkflowMetadata(id="1", version="1")))
...         runtime.add_workflow("1_1", workflow1)
...         print((await runtime.get_workflow("1_1")).config().metadata)
... 
...         # 批量添加workflow
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

model资源完整代码：

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
...         # 需要修改替换 api_base 和 api_key 为真实地址与密钥
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
...         print(f"保存模型: {type(saved_model).__name__}")
... 
...         model1 = self._get_model(timeout=1)
...         model2 = self._get_model(timeout=2)
...         runtime.add_models([("model_1", model1), ("model_2", model2)])
...         print(f"model_1 存在: {runtime.get_model('model_1') is not None}")
...         print(f"model_2 存在: {runtime.get_model('model_2') is not None}")
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
保存模型: Siliconflow
model_1 存在: True
model_2 存在: True
None
```

tool管理完整代码：

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
...             description="加法",
...             params=[
...                 Param(name="a", description="加数", type="number", required=True),
...                 Param(name="b", description="被加数", type="number", required=True),
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
...             description="加法",
...             params=[
...                 Param(name="a", description="加数", type="number", required=True),
...                 Param(name="b", description="被加数", type="number", required=True),
...             ],
...             func=lambda a, b: a + b
...         )
... 
...         multiply_plugin = LocalFunction(
...             name="multiply",
...             description="乘法",
...             params=[
...                 Param(name="a", description="乘数", type="number", required=True),
...                 Param(name="b", description="被乘数", type="number", required=True),
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