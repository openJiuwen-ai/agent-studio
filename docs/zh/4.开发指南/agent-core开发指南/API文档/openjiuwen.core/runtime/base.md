# openjiuwen.core.runtime.base

## class openjiuwen.core.runtime.base.ComponentExecutable

```python
openjiuwen.core.runtime.base.ComponentExecutable()
```

`ComponentExecutable`为组件执行器的抽象类，开发者实现自定义组件时，需要继承`ComponentExecutable`这个基类进行定制化实现。根据组件本身功能的定义和注册到工作流中的**流式输入输出关系**不同，在工作流执行过程中，可能调用`ComponentExecutable`的不同方法。

* 当某组件A与后续组件**存在**流式连接，与前序组件**不存在**流式连接时，组件A执行时调用`invoke`方法和`stream`方法。
* 当某组件A与后续组件**存在**流式连接，与前序组件也**存在**流式连接时，组件A执行时调用`invoke`方法、`stream`方法和`transform`方法。
* 当某组件A与后续组件**不存在**流式连接，与前序组件**存在**流式连接时，组件A执行时调用`invoke`方法和`collect`方法。
* 当某组件A与后续组件**不存在**流式连接，与前序组件也**不存在**流式连接时，组件A执行时仅调用`invoke`方法。

### invoke

```python
async invoke(self, inputs: Input,  runtime: Runtime, context: Context) -> Output
```

组件的批处理接口，将批数据一次性处理完毕，输出为批数据。

**参数**：

* **inputs**(Input)：组件的批输入。
* **runtime**(Runtime)：执行过程的上下文，内置了资源管理、状态信息、配置信息。
* **context**(Context, 可选)：用于存储用户对话信息的上下文引擎对象。

**返回**：

**Output**，批处理结果。

**样例**：

```python
>>> import asyncio
>>> from typing import Any
>>>
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>>
>>> # 创建自定义组件`InvokeDemoComponent`，实现`invoke`方法用来进行加法运算。
>>> # 1. 自定义组件，用来做加法
>>> class InvokeDemoComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
...
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         a = int(inputs.get('a', 0))
...         b = int(inputs.get('b', 0))
...         return {'result': a + b}
...
>>>
>>> # 2. 创建工作流，并调用工作流，触发到自定义组件的`invoke`方法
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={'a': '${user_inputs.a}', 'b': '${user_inputs.b}'})
>>> flow.add_workflow_comp("invoke_node", InvokeDemoComponent(), inputs_schema={'a': '${start.a}', 'b': '${start.b}'})
>>> flow.set_end_comp('end', End(), inputs_schema={'result': '${invoke_node.result}'})
>>> 
>>> flow.add_connection('start', 'invoke_node')
>>> flow.add_connection('invoke_node', 'end')
>>> 
>>> workflow_output = asyncio.run(flow.invoke(inputs={'user_inputs':{'a': 1, 'b': 2}}, runtime=WorkflowRuntime()))
>>> 
>>> print(workflow_output.result["output"])
{'result': 3}
```

### stream

```python
async stream(self, inputs: Input, runtime: Runtime, context: Context)-> AsyncIterator[Output]
```

组件的批处理接口，并且将批数据转为流数据。当组件有实时或分步处理数据的场景的需求，可以实现该接口。

**参数**：

* **inputs**(Input)：组件的批输入。
* **runtime**(Runtime)：执行过程的上下文，内置了资源管理、状态信息、配置信息。
* **context**(Context, 可选)：用于存储用户对话信息的上下文引擎对象。

**返回**：

**AsyncIterator[Output]**，流数据的迭代器。

**样例**：

```python
>>> import asyncio
>>> from typing import AsyncIterator
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import ComponentAbility
>>> 
>>> # 实现自定义节点`StreamDemoComponent`，并实现了`stream`方法，用于进行加法运算，并输出了计算过程。
>>> # 创建自定义组件，并实现stream逻辑
>>> class StreamDemoComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
...         yield {"a" : inputs.get("a")}
...         yield {"op" : "+"}
...         yield {"b" : inputs.get("b")}
...         yield {"result": int(inputs.get("a")) + int(inputs.get("b"))}
... 
>>> # 创建工作流，并触发到自定义组件的`stream`方法
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={'a': '${user_inputs.a}', 'b': '${user_inputs.b}'})
>>> flow.add_workflow_comp("stream_node", StreamDemoComponent(), inputs_schema={'a': '${start.a}', 'b': '${start.b}'}, comp_ability=[ComponentAbility.STREAM], wait_for_all=True)
>>> flow.set_end_comp('end', End(), response_mode="streaming", stream_inputs_schema={'stream_node': '${stream_node}'})
>>> 
>>> flow.add_connection('start', 'stream_node')
>>> flow.add_stream_connection('stream_node', 'end')
>>> 
>>> async def run():
...    async for chunk in flow.stream(inputs={'user_inputs': {'a': 1, 'b': 2}}, runtime=WorkflowRuntime(),
...                                   stream_modes=[BaseStreamMode.OUTPUT]):
...        print(chunk.payload)
... 
>>> asyncio.run(run())
{'output': {'stream_node': {'a': 1}}}
{'output': {'stream_node': {'op': '+'}}}
{'output': {'stream_node': {'b': 2}}}
{'output': {'stream_node': {'result': 3}}}
```

### collect

```python
async collect(self, inputs: Input, runtime: Runtime, context: Context)->Output
```

组件的流数据处理接口，并将流数据处理成批数据。若组件需要对流式输出进行汇总、聚合或最终结果生成的场景的需求，可实现该接口。

**参数**：

* **inputs**(Input)：组件的流式输入的字典，字典的格式符合stream_inputs_schema（组件流式输入参数结构）的定义，stream_inputs_schema中的引用在inputs字典中实际填充的是异步迭代器。
* **runtime**(Runtime)：执行过程的上下文，内置了资源管理、状态信息、配置信息。
* **context**(Context，可选)：用于存储用户对话信息的上下文引擎对象。

**返回**：

**Output**，批处理结果。

**样例**：

```python
>>> import asyncio
>>> from typing import AsyncIterator
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import ComponentAbility
>>> 
>>> # 1. 创建自定义`CollectDemoComponent`, 并实现`collect`方法，用于一次加法计算所有的数据
>>> class CollectDemoComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def collect(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         result = []
...         data_generator = inputs.get('data')
...         async for data in data_generator:
...             a = int(data.get("a"))
...             b = int(data.get("b"))
...             result.append({"a": a, "b": b, "op": "add", "result": a + b})
...         return {'results': result}
... 
>>> # 2. 为了触发自定义组件的`collect`方法，需要自定义一个支持流式输出组件`StreamDemoComponent2`，用于流式输出每轮加法计算的数据
>>> class StreamDemoComponent2(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
...         datas = inputs.get("data")
...         for data in datas:
...             yield {'data': data}
... 
>>> # 3. 创建工作流，并触发transform能力
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={'data': '${user_inputs.data}'})
>>> flow.add_workflow_comp("stream_node", StreamDemoComponent2(), inputs_schema={'data': '${start.data}'},comp_ability=[ComponentAbility.STREAM], wait_for_all=True)
>>> flow.add_workflow_comp("collect_node", CollectDemoComponent(), stream_inputs_schema={'data': '${stream_node.data}'},comp_ability=[ComponentAbility.COLLECT], wait_for_all=True)
>>> flow.set_end_comp('end', End(), inputs_schema={"results": "${collect_node.results}"})
>>> 
>>> flow.add_connection('start', 'stream_node')
>>> flow.add_stream_connection('stream_node', 'collect_node')
>>> flow.add_connection('collect_node', 'end')
>>> 
>>> result = asyncio.run(flow.invoke(
...                     inputs={'user_inputs': {'data': [{'a': 1, 'b': 2}, {'a': 2, 'b': 3}, {'a': 4, 'b': 5}]}},
...                     runtime=WorkflowRuntime()))
...
>>> print(result.result)
{'output': {'results': [{'a': 1, 'b': 2, 'op': 'add', 'result': 3}, {'a': 2, 'b': 3, 'op': 'add', 'result': 5}, {'a': 4, 'b': 5, 'op': 'add', 'result': 9}]}}
```

### transform

```python
async transform(self, inputs: Input, runtime: Runtime, context: Context)-> AsyncIterator[Output]
```

组件的流数据处理接口，并且对流数据进行逐条处理成新的流数据。当组件存在对大模型的流式输出进行逐帧格式化后再输出的场景，可以实现该接口。

**参数**：

* **inputs**(Input)：组件的流式输入的字典，字典的格式符合stream_inputs_schema（组件流式输入参数结构）的定义，stream_inputs_schema中的引用在inputs字典中实际填充的是异步迭代器。
* **runtime**(Runtime)：执行过程的上下文，内置了资源管理、状态信息、配置信息。
* **context**(Context, 可选)：用于存储用户对话信息的上下文引擎对象。

**返回**：

**AsyncIterator[Output]**，转换完的流数据的迭代器。

**样例**：

```python
>>> import asyncio
>>> from typing import AsyncIterator
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.stream.base import BaseStreamMode
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import ComponentAbility
>>>
>>> # 1. 自定义`TransformDemoComponent`组件，并实现了`transform`方法，用于多轮加法计算
>>> class TransformDemoComponent(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def transform(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[
...         Output]:
...         data_generator = inputs.get('data')
...         async for data in data_generator:
...             a = int(data.get("a"))
...             b = int(data.get("b"))
...             yield {"a": a, "b": b, "op": "add", "result": a + b}
... 
>>> # 2. 为了触发自定义组件的`transform`方法，需要自定义一个支持流式输出组件`StreamDemoComponent2`，用于流式输出每轮加法计算的数据
>>> class StreamDemoComponent2(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
...         datas = inputs.get("data")
...         for data in datas:
...             yield {'data': data}
... 
>>> # 3. 构建工作流，并触发自定义节点的`transform`方法
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start(), inputs_schema={'data': '${user_inputs.data}'})
>>> flow.add_workflow_comp("stream_node", StreamDemoComponent2(), inputs_schema={'data': '${start.data}'}, comp_ability=[ComponentAbility.STREAM], wait_for_all=True)
>>> flow.add_workflow_comp("transform_node", TransformDemoComponent(), stream_inputs_schema={'data': '${stream_node.data}'},  comp_ability=[ComponentAbility.TRANSFORM], wait_for_all=True)
>>> flow.set_end_comp('end', End(), response_mode="streaming", stream_inputs_schema={'transform_node': '${transform_node}'})
>>> 
>>> flow.add_connection('start', 'stream_node')
>>> flow.add_stream_connection('stream_node', 'transform_node')
>>> flow.add_stream_connection('transform_node', 'end')
>>> 
>>> async def main():
...     async for chunk in flow.stream(inputs={'user_inputs': {'data': [{'a': 1, 'b': 2}, {'a': 2, 'b': 3}, {'a': 4, 'b': 5}]}}, runtime=WorkflowRuntime(), stream_modes=[BaseStreamMode.OUTPUT]):
...         print(chunk.payload)
... 
>>> asyncio.run(main())
{'output': {'transform_node': {'a': 1, 'b': 2, 'op': 'add', 'result': 3}}}
{'output': {'transform_node': {'a': 2, 'b': 3, 'op': 'add', 'result': 5}}}
{'output': {'transform_node': {'a': 4, 'b': 5, 'op': 'add', 'result': 9}}}
```
