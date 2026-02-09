# openjiuwen.core.runtime.base

## class openjiuwen.core.runtime.base.ComponentExecutable

```python
openjiuwen.core.runtime.base.ComponentExecutable()
```

ComponentExecutable is the abstract executor for components. When implementing a custom component, you should inherit from the ComponentExecutable base class and provide custom logic. Depending on the component’s functional definition and its streaming input/output connections in the workflow, different methods of ComponentExecutable may be called during workflow execution.

- If a component A has a streaming connection to downstream components but has no streaming connection from upstream components, A’s execution will call invoke and stream.
- If a component A has a streaming connection to downstream components and also has a streaming connection from upstream components, A’s execution will call invoke, stream, and transform.
- If a component A has no streaming connection to downstream components but has a streaming connection from upstream components, A’s execution will call invoke and collect.
- If a component A has neither streaming connections to downstream components nor from upstream components, A’s execution will call only invoke.

### invoke

```python
async invoke(self, inputs: Input,  runtime: Runtime, context: Context) -> Output
```

The batch processing interface of the component. It processes the entire batch at once and outputs batch data.

**Parameters**:

- **inputs** (Input): Batch input for the component.
- **runtime** (Runtime): Execution context that provides resource management, state, and configuration.
- **context** (Context, optional): A context engine object that stores user conversation information.

**Returns**:

- **Output**: The batch processing result.

**Example**:

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
>>> # Create a custom component `InvokeDemoComponent` and implement `invoke` to perform addition.
>>> # 1. Custom component for addition
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
>>> # 2. Build a workflow and run it to trigger the custom component's `invoke` method
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

The component's batch-to-stream interface. Use this when the component needs real-time or step-by-step processing and should emit streaming data.

**Parameters**:

- **inputs** (Input): Batch input for the component.
- **runtime** (Runtime): Execution context that provides resource management, state, and configuration.
- **context** (Context, optional): A context engine object that stores user conversation information.

**Returns**:

- **AsyncIterator[Output]**: An iterator that yields streaming data.

**Example**:

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
>>> # Implement a custom node `StreamDemoComponent` with `stream` to perform addition and emit the calculation steps.
>>> # Create the custom component and implement the stream logic
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
>>> # Build the workflow and trigger the custom component's `stream` method
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

The component's streaming data processing interface that aggregates streaming data into a batch result. Implement this when the component needs to summarize, aggregate, or produce a final result from streaming outputs.

**Parameters**:

- **inputs** (Input): A dictionary of streaming inputs. Its shape matches the component's stream_inputs_schema. The references defined in stream_inputs_schema are materialized as async iterators in the inputs dictionary.
- **runtime** (Runtime): Execution context that provides resource management, state, and configuration.
- **context** (Context, optional): A context engine object that stores user conversation information.

**Returns**:

- **Output**: The batch processing result.

**Example**:

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
>>> # 1. Create a custom `CollectDemoComponent` and implement `collect` to compute all additions in one go
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
>>> # 2. To trigger `collect`, define a streaming component `StreamDemoComponent2` that streams each addition input
>>> class StreamDemoComponent2(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
...         datas = inputs.get("data")
...         for data in datas:
...             yield {'data': data}
... 
>>> # 3. Build the workflow and trigger the collect capability
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

The component's streaming data processing interface that transforms streaming data item-by-item into new streaming data. Implement this when you need to format a model's streaming output frame-by-frame before emitting it downstream.

**Parameters**:

- **inputs** (Input): A dictionary of streaming inputs. Its shape matches the component's stream_inputs_schema. The references defined in stream_inputs_schema are materialized as async iterators in the inputs dictionary.
- **runtime** (Runtime): Execution context that provides resource management, state, and configuration.
- **context** (Context, optional): A context engine object that stores user conversation information.

**Returns**:

- **AsyncIterator[Output]**: An iterator that yields transformed streaming data.

**Example**:

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
>>> # 1. Define `TransformDemoComponent` and implement `transform` for multi-round additions
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
>>> # 2. To trigger `transform`, define a streaming component `StreamDemoComponent2` that streams each addition input
>>> class StreamDemoComponent2(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
...         datas = inputs.get("data")
...         for data in datas:
...             yield {'data': data}
... 
>>> # 3. Build the workflow and trigger the custom node's `transform` method
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