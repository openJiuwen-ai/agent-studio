# openjiuwen.core.runner.Runner

## class openjiuwen.core.runner.Runner
Runner提供了Workflow、Agent、Tool和AgentGroup的统一执行接口，并提供了对Agent对象的生命周期管理能力。


### start
```python
async def start(self) -> bool
```
启动Runner。


**样例**：
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
关闭Runner。


**样例**：
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
注册agent实例或agent提供器。

**参数**：
* **agent_id**(str): agent唯一的ID。`agent_id`不可为`None`或`''`。
* **agent**(Agent|AgentProvider): agent实例或者agent的提供器。不可取值为`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：
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
...    # 创建工作流flow, 将flow注册到资源管理器
...    flow = Workflow(workflow_config=WorkflowConfig(
...        metadata=WorkflowMetadata(id="workflow_id", version="1", name="简单工作流",
...                                  description="this_is_a_demo")))
...    flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
...    flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
...    flow.add_connection("start", "end")
...
...    resource_mgr.workflow().add_workflow("workflow_id_1", flow)
...
...    # 创建Agent
...
...    workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                                workflows=[WorkflowSchema(
...                                                    id="workflow_id",
...                                                    version="1",
...                                                    name="简单工作流",
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
>>> # 1. 注册agent
>>> Runner.add_agent("agent_id", create_agent())
>>> 
>>> # 2. 调用agent
>>> print(asyncio.run(Runner.run_agent("agent_id", inputs={"conversion_id": "id1", "query": "哈哈"})))
{'output': WorkflowOutput(result={'output': {'result': '哈哈'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### remove_agent
指定ID删除对应的agent或者agent提供者。

```python
def remove_agent(self, agent_id) -> Union[Agent, AgentProvider]
```

**参数**：
* **agent_id**(str): agent唯一的ID。`agent_id`不可为`None`或`''`，否则报异常。

**返回**：

**Agent|AgentProvider**，被删除的Agent实例或Agent提供者实例，若不存在，则返回`None`。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
...    # 创建工作流flow, 将flow注册到资源管理器
...    flow = Workflow(workflow_config=WorkflowConfig(
...        metadata=WorkflowMetadata(id="workflow_id", version="1", name="简单工作流",
...                                  description="this_is_a_demo")))
...    flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
...    flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
...    flow.add_connection("start", "end")
... 
...    resource_mgr.workflow().add_workflow("workflow_id_1", flow)
... 
...    # 创建Agent
... 
...    workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                                workflows=[WorkflowSchema(
...                                                    id="workflow_id",
...                                                    version="1",
...                                                    name="简单工作流",
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
>>> # 1. 注册agent
>>> Runner.add_agent("agent_id", create_agent())
>>> # 2. 删除agent
>>> agent = Runner.remove_agent("agent_id")
>>> print(agent.config().get_agent_config().id)
agent_id
```

### run_agent

```python
async def run_agent(self, agent: Union[str, Agent], inputs: Any) -> Any
```
执行agent并返回其结果。

**参数**:

* **agent(str|Agent)**：agent的ID或agent实例。
* **inputs(Any)**：输入数据。

**返回**：

**Any**，agent执行结果。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
>>> # 创建工作流flow, 将flow注册到资源管理器
>>> flow = Workflow(workflow_config=WorkflowConfig(
...     metadata=WorkflowMetadata(id="workflow_id", version="1", name="简单工作流",
...                               description="this_is_a_demo")))
... 
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
>>> flow.add_connection("start", "end")
>>> 
>>> resource_mgr.workflow().add_workflow("workflow_id_1", flow)
>>> 
>>> # 创建Agent
>>> 
>>> workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                            workflows=[WorkflowSchema(
...                                                id="workflow_id",
...                                                version="1",
...                                                name="简单工作流",
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
>>> # 直接调用agent实例
>>> print(asyncio.run(Runner.run_agent(agent, inputs={"conversion_id": "id1", "query": "哈哈"})))
{'output': WorkflowOutput(result={'output': {'result': '哈哈'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
>>> 
>>> # 通过id，调用agent，需要首先将agent注册
>>> Runner.add_agent("agent_id", agent)
>>> print(asyncio.run(Runner.run_agent("agent_id", inputs={"conversion_id": "id1", "query": "哈哈"})))
{'output': WorkflowOutput(result={'output': {'result': '哈哈'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### run_agent_streaming

```python
async def run_agent_streaming(self, agent: Union[str, Agent], inputs: Any) -> AsyncGenerator
```
流式执行Agent并返回生成器。

**参数**:

* **agent(str|Agent)**：agent的ID或agent实例。
* **inputs(Any)**：输入数据。

**返回**:

**AsyncGenerator**，流式结果生成器。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
>>> # 创建工作流flow, 将flow注册到资源管理器
>>> flow = Workflow(workflow_config=WorkflowConfig(
...     metadata=WorkflowMetadata(id="workflow_id", version="1", name="简单工作流",
...                               description="this_is_a_demo")))
... 
>>> flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
>>> flow.add_connection("start", "end")
>>> 
>>> resource_mgr.workflow().add_workflow("workflow_id_1", flow)
>>> 
>>> # 创建Agent
>>> workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
...                                            workflows=[WorkflowSchema(
...                                                id="workflow_id",
...                                                version="1",
...                                                name="简单工作流",
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
...     result = Runner.run_agent_streaming(agent, inputs={"conversion_id": "id1", "query": "哈哈"})
...     async for chunk in result:
...         if isinstance(chunk, OutputSchema):
...             print(chunk)
... 
>>> asyncio.run(run_workflow())
type='workflow_final' index=0 payload={'output': {'result': '哈哈'}}
>>> 
>>> # 通过id，调用agent，需要首先将agent注册
>>> Runner.add_agent("agent_id", agent)
>>> async def run_workflow():
...     result = Runner.run_agent_streaming("agent_id", inputs={"conversion_id": "id1", "query": "哈哈"})
...     async for chunk in result:
...         if isinstance(chunk, OutputSchema):
...             print(chunk)
... 
>>> asyncio.run(run_workflow())
type='workflow_final' index=0 payload={'output': {'result': '哈哈'}}

```

### run_workflow

```python
async def run_workflow(self, workflow: Union[str, Workflow], inputs: Any, *, runtime: Union[Runtime, WorkflowRuntime] = None, context: Context = None) -> Any
```
执行工作流并返回其执行结果。

**参数**：

* **workflow(str|Workflow)**：工作流ID或者工作流实例。不可取值为`None`或`''`。
* **inputs(Any)**：执行工作流的输入数据。
* **runtime(Runtime|WorkflowRuntime)**：运行时实例。若提供的运行时来源于Agent的运行时，则`workflow`必须被Agent绑定。默认为`None`。
* **context(Context)**：用于存储用户对话信息的上下文引擎。默认为`None`，表示不开启上下文引擎功能。

**返回**：

**Any**，工作流执行结果。

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
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> from openjiuwen.core.runner.runner import Runner, resource_mgr
>>> 
>>> # 自定义组件Node
>>> class Node(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return inputs
...
>>> # 创建工作流
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
>>> # 直接运行workflow
>>> workflow = build_workflow("test_workflow", "test_workflow", "1")
>>> result = asyncio.run(Runner.run_workflow(workflow=workflow, inputs={"query": "query workflow"}, runtime=WorkflowRuntime()))
>>> print(result)
result={'output': {'result': 'query workflow'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
>>> # 指定workflow的id，执行工作流，首先需要将workflow添加到资源管理器中
>>> resource_mgr.workflow().add_workflow("test_workflow", workflow)
>>> result = asyncio.run(Runner.run_workflow(workflow="test_workflow", inputs={"query": "query workflow"}, runtime=WorkflowRuntime()))
>>> print(result)
result={'output': {'result': 'query workflow'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

### run_workflow_streaming

```python
async def run_workflow_streaming(self, workflow: Union[str, Workflow], inputs: Any, *, runtime: Union[Runtime, WorkflowRuntime] = None, stream_modes: list[BaseStreamMode] = None, context: Context = None) -> AsyncGenerator
```
流式执行工作流并返回其执行结果。

**参数**：

* **workflow(str|Workflow)**：工作流ID或者工作流实例。不可取值为`None`或`''`。
* **inputs(Any)**：执行工作流的输入数据。
* **runtime(Runtime|WorkflowRuntime)**：运行时实例。若提供的运行时来源于Agent的运行时，则入参中`workflow`必须被Agent绑定。默认为`None`。
* **stream_modes(list[BaseStreamMode])**：流式输出的类型。默认为`None`。
* **context(Context)**：用于存储用户对话信息的上下文引擎。默认为`None`，表示不开启上下文引擎功能。

**返回**：

**AsyncGenerator**，流式结果生成器。

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
>>> from openjiuwen.core.runner.runner import Runner
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import CustomSchema
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> # 自定义组件Node
>>> class Node(ComponentExecutable, WorkflowComponent):
...    def __init__(self):
...        super().__init__()
...
...    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...        await runtime.write_custom_stream({"1": "1"})
...        await runtime.write_custom_stream({"2": "2"})
...        return inputs
...
>>> # 创建工作流
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
>>> # 直接运行workflow
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
>>> # 指定id运行workflow, 前提必须将workflow添加到资源管理器
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

执行Tool并返回结果。

**参数**：

* **tool(str|Tool)**：ID或Tool实例。不可取值为`None`或`''`。
* **inputs**: 输入数据。
* **runtime(Runtime)**: 运行时实例。若提供的运行时来源于Agent的运行时，则入参中`tool`必须被Agent绑定。默认为`None`。

**返回**：

**Any**，Tool执行结果。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

```python
>>> from openjiuwen.core.utils.tool.function.function import LocalFunction
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # 创建本地工具
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
>>> # 1. 直接通过tool实例调用
>>> import asyncio
>>> from openjiuwen.core.runner.runner import Runner
>>> print(asyncio.run(Runner.run_tool(tool=add_plugin, inputs={'a':1, 'b':2})))
3
>>> # 2. 通过tool的id调用，前提必须将tool添加到资源管理器中
>>> from openjiuwen.core.runner.runner import resource_mgr
>>> resource_mgr.tool().add_tool("add", add_plugin)
>>> print(asyncio.run(Runner.run_tool(tool="add", inputs={'a':1, 'b':2})))
3
```

### run_tool_streaming

```python
async def run_tool_streaming(self, tool: Union[str, Tool], inputs, *, runtime: Runtime = None) -> AsyncGenerator
```
流式执行Tool并返回生成器。

**参数**：

* **tool(str|Tool)**：ID或Tool实例。不可取值为`None`或`''`。
* **inputs**: 输入数据。
* **runtime(Runtime)**: 运行时实例。若提供的运行时来源于Agent的运行时，则入参中`tool`必须被Agent绑定。默认为`None`。

**返回**：

**AsyncGenerator**，流式结果生成器。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.utils.tool.base import Tool
>>> from openjiuwen.core.utils.tool.constant import Input, Output
>>> 
>>> 
>>> # 自定义一个能流式输出的tool
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
>>> # 直接运行tool
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
>>> # 指定id运行tool，前提是先把tool添加到资源管理器
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
执行AgentGroup并返回结果。

**参数**：

* **agent_group(str|AgentGroup)**：ID或AgentGroup实例。不可取值为`None`或`''`。
* **inputs**: 输入数据。

**返回**：

**Any**，AgentGroup执行结果。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
...   """创建模型配置"""
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
...    """创建 Start 组件"""
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
...   构建金融业务工作流（带中断节点）
... 
...   Args:
...       workflow_id: 工作流ID
...       workflow_name: 工作流名称
...       workflow_desc: 工作流描述
...       field_name: 提问字段名
...       field_desc: 提问字段描述
... 
...   Returns:
...       Workflow: 包含 start -> questioner -> end 的工作流
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
...   # 创建组件
...   start = _create_start_component()
... 
...   # 创建提问器（中断节点）
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
...   # End 组件
...   end = End({"responseTemplate": f"{workflow_name}完成: {{{{{field_name}}}}}"})
... 
...   # 注册组件
...   flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
...   flow.add_workflow_comp(
...       "questioner", questioner, inputs_schema={"query": "${start.query}"}
...   )
...   flow.set_end_comp(
...       "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
...   )
... 
...   # 连接拓扑: start -> questioner -> end
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
...     """创建 WorkflowAgent"""
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
>>> # 创建金融业务工作流
>>> transfer_workflow = _build_financial_workflow(
...     workflow_id="transfer_flow",
...     workflow_name="转账服务",
...     workflow_desc="处理用户转账请求，支持转账到指定账户",
...     field_name="amount",
...     field_desc="转账金额（数字）"
... )
... 
>>> balance_workflow = _build_financial_workflow(
...     workflow_id="balance_flow",
...     workflow_name="余额查询",
...     workflow_desc="查询用户账户余额信息",
...     field_name="account",
...     field_desc="账户号码"
... )
... 
>>> invest_workflow = _build_financial_workflow(
...     workflow_id="invest_flow",
...     workflow_name="理财服务",
...     workflow_desc="提供理财产品推荐和购买服务",
...     field_name="product",
...     field_desc="理财产品名称"
... )
... 
>>> # 创建 WorkflowAgent
>>> transfer_agent = _create_workflow_agent(
...     agent_id="transfer_agent",
...     description="转账服务，处理用户的转账请求",
...     workflow=transfer_workflow
... )
... 
>>> balance_agent = _create_workflow_agent(
...     agent_id="balance_agent",
...     description="余额查询服务，查询用户账户余额",
...     workflow=balance_workflow
... )
... 
>>> invest_agent = _create_workflow_agent(
...     agent_id="invest_agent",
...     description="理财服务，提供理财产品推荐和购买",
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
...     description="金融服务主控制器，识别用户意图并分发任务"
... )
...
>>> main_controller = HierarchicalMainController()
>>> main_agent = ControllerAgent(main_config, controller=main_controller)
>>> 
>>> # 添加所有 agent 到 group
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
...     content="给张三转账",
...     conversation_id=conversation_id
... )
... 
>>> # 广播消息给所有订阅 test_query1主题的agent
>>> message1.message_type = "test_query1"
>>> result1 = asyncio.run(Runner.run_agent_group(hierarchical_group, message1))
>>> asyncio.run(Runner.stop())
>>> print(result1)
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供转账金额（数字）相关的信息'))]
```

### run_agent_group_streaming

```python
async def run_agent_group_streaming(self, agent_group: Union[str, AgentGroup], inputs: Any) -> AsyncGenerator
```
流式执行AgentGroup并返回结果。

**参数**：

* **agent_group(str|AgentGroup)**：ID或AgentGroup实例。不可取值为`None`或`''`。
* **inputs**: 输入数据。

**返回**：

**AsyncGenerator**，流式结果生成器。

**异常**：

- **JiuWenBaseException**：openJiuwen异常基类，具体详细信息和解决方法，参见[StatusCode](../common/exception/status_code.md)。

**样例**：

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
...     """创建模型配置"""
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
...     """创建 Start 组件"""
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
...     构建金融业务工作流（带中断节点）
... 
...     Args:
...         workflow_id: 工作流ID
...         workflow_name: 工作流名称
...         workflow_desc: 工作流描述
...         field_name: 提问字段名
...         field_desc: 提问字段描述
... 
...     Returns:
...         Workflow: 包含 start -> questioner -> end 的工作流
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
...     # 创建组件
...     start = _create_start_component()
... 
...     # 创建提问器（中断节点）
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
...     # End 组件
...     end = End({"responseTemplate": f"{workflow_name}完成: {{{{{field_name}}}}}"})
... 
...     # 注册组件
...     flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
...     flow.add_workflow_comp(
...         "questioner", questioner, inputs_schema={"query": "${start.query}"}
...     )
...     flow.set_end_comp(
...         "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
...     )
... 
...     # 连接拓扑: start -> questioner -> end
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
...     """创建 WorkflowAgent"""
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
>>> # 创建金融业务工作流
>>> transfer_workflow = _build_financial_workflow(
...     workflow_id="transfer_flow",
...     workflow_name="转账服务",
...     workflow_desc="处理用户转账请求，支持转账到指定账户",
...     field_name="amount",
...     field_desc="转账金额（数字）"
... )
... 
>>> balance_workflow = _build_financial_workflow(
...     workflow_id="balance_flow",
...     workflow_name="余额查询",
...     workflow_desc="查询用户账户余额信息",
...     field_name="account",
...     field_desc="账户号码"
... )
... 
>>> invest_workflow = _build_financial_workflow(
...     workflow_id="invest_flow",
...     workflow_name="理财服务",
...     workflow_desc="提供理财产品推荐和购买服务",
...     field_name="product",
...     field_desc="理财产品名称"
... )
... 
>>> # 创建 WorkflowAgent
>>> transfer_agent = _create_workflow_agent(
...     agent_id="transfer_agent",
...     description="转账服务，处理用户的转账请求",
...     workflow=transfer_workflow
... )
... 
>>> balance_agent = _create_workflow_agent(
...     agent_id="balance_agent",
...     description="余额查询服务，查询用户账户余额",
...     workflow=balance_workflow
... )
...  
>>> invest_agent = _create_workflow_agent(
...     agent_id="invest_agent",
...     description="理财服务，提供理财产品推荐和购买",
...     workflow=invest_workflow
... )
... 
>>> # 创建 HierarchicalGroup
>>> config = HierarchicalGroupConfig(
...     group_id="financial_group",
...     leader_agent_id="main_controller"
... )   
... 
>>> hierarchical_group = HierarchicalGroup(config)
>>> 
>>> # 创建主 agent（HierarchicalMainController）
>>> main_config = AgentConfig(
...     id="main_controller",
...     description="金融服务主控制器，识别用户意图并分发任务"
... )
... 
>>> main_controller = HierarchicalMainController()
>>> main_agent = ControllerAgent(main_config, controller=main_controller)
>>> 
>>> # 添加所有 agent 到 group
>>> hierarchical_group.add_agent("main_controller", main_agent)
>>> hierarchical_group.add_agent("transfer_agent", transfer_agent)
>>> hierarchical_group.add_agent("balance_agent", balance_agent)
>>> hierarchical_group.add_agent("invest_agent", invest_agent)
>>> 
>>> async def main():
...     # 启动Runner
...     await Runner.start()
...     message = Message.create_user_message(
...         content="给张三转账500元",
...         conversation_id="stream_session_test"
...     )
...     # 流式调用
...     async for chunk in Runner.run_agent_group_streaming(hierarchical_group, message):
...         print(f"输出结果：{chunk}")
...     # 停止Runner
...     await Runner.stop()
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
... 
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169086), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'query': '给张三转账500元'}, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 750914), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'amount': 500}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': None, 'inputs': {'amount': 500}, 'outputs': None, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752861), 'inputs': {'amount': 500}, 'outputs': {'responseContent': '转账服务完成: 500'}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 754020), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'responseContent': '转账服务完成: 500'}, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': '转账服务完成: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### release
```python
async def release(self, session_id: str)
```
清理指定`session_id`的缓存数据，如中断状态数据。

**参数**：
* **session_id(str)**: 对话ID。若为`None`，则不清理。

**样例**：

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
>>> # 创建自定义节点：带交互中断
>>> class InteractionNode(WorkflowComponent, ComponentExecutable):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         answer = inputs.get("answer")
...         query = await runtime.interact(answer)
...         return {"query": query}
... 
>>> # 创建工作流
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
>>> # 调用工作流，第一次中断
>>> from openjiuwen.core.runner.runner import Runner
>>> input1 = {"user_input": "天气"}
>>> result1 = asyncio.run(Runner.run_workflow(workflow, inputs=input1, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result1: {result1}')
result1: result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='interact_node', value='天气'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
>>> 
>>> # 传入交互式输入，继续工作流
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> # 这里需要为交互节点 'interact_node' 提供输入
>>> input2 = InteractiveInput()
>>> input2.update("interact_node", "晴天")
>>> result2 = asyncio.run(Runner.run_workflow(workflow, inputs=input2, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result2 after interactive input: {result2}')
result2 after interactive input: result={'result': '晴天'} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
>>> 
>>> # 清理session_1的数据
>>> asyncio.run(Runner.release(session_id="session_1"))
>>> 
>>> # 调用工作流，由于清理了session_1的数据，工作流从头执行
>>> # 注意：release后需要重新传入初始输入（字典格式），不能使用InteractiveInput
>>> result3 = asyncio.run(Runner.run_workflow(workflow, inputs=input1, runtime=WorkflowRuntime(session_id="session_1")))
>>> print(f'result3 after release: {result3}')
result3 after release: result=[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='interact_node', value='天气'))] state=<WorkflowExecutionState.INPUT_REQUIRED: 'INPUT_REQUIRED'>
```