The orchestration and capability invocation of components within a workflow depend on the types of edges connected to their ends. The workflow automatically determines whether to run a component in `invoke`, `stream`, `transform`, or `collect` mode based on whether the component's inputs and outputs are stream edges or batch edges. Furthermore, in workflow orchestration, the method of data referencing between components directly influences the data transmission path and dependencies within the workflow. The following sections detail component connection methods and data transmission mechanisms.

# Component Connection Methods

In a workflow, the connection method of a component and its inherent capabilities mutually influence and constrain each other. The connection method dictates which specific capability of the component the workflow will invoke. Conversely, the capabilities supported by the component itself limit how it can be connected. The specific streaming I/O connection rules corresponding to different capabilities are as follows:

- When Component A implements the `invoke` capability, Component A uses `add_connection` to connect with predecessor and successor components.
- When Component A implements the `stream` capability, Component A uses `add_connection` to connect with predecessor components and `add_stream_connection` to connect with successor components.
- When Component A implements the `transform` capability, Component A uses `add_stream_connection` to connect with both predecessor and successor components.
- When Component A implements the `collect` capability, Component A uses `add_stream_connection` to connect with predecessor components and `add_connection` to connect with successor components.

The following section introduces three custom components: `StreamCompNode`, `TransformCompNode`, and `CollectCompNode`. Based on the different capabilities implemented by these components, distinct connection methods are selected to achieve streaming orchestration.

`StreamCompNode` implements the `stream` method (corresponding to `ComponentAbility.STREAM`), converting batch input into streaming output. Specifically, it receives a single input value (e.g., `{"value": 1}`) and generates two streaming data frames (`{"value": 1 * 1}` and `{"value": 1 * 2}`). `StreamCompNode` uses `add_connection` to connect with predecessors and `add_stream_connection` to connect with successors. The example code is as follows:

```python
import asyncio
from typing import AsyncIterator

from openjiuwen.core.common.logging import logger
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable
from openjiuwen.core.runtime.runtime import Runtime

class StreamCompNode(ComponentExecutable, WorkflowComponent):
    def __init__(self, node_id: str = ''):
        super().__init__()
        self.node_id = node_id

    async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
        logger.debug(f"===StreamCompNode[{self.node_id}], input: {inputs}")
        if inputs is None:
            yield 1
        else:
            for i in range(1, 3):
                yield {"value": i * inputs["value"]}
```

`TransformCompNode` implements the `transform` method (corresponding to `ComponentAbility.TRANSFORM`), processing stream data frame by frame. Specifically, it receives streaming input (e.g., `{"value":1}`, `{"value":2}`) and passes through each frame (logic for format conversion can be added in practice). `TransformCompNode` uses `add_stream_connection` to connect with both predecessors and successors. The example code is as follows:

```python
import asyncio
from typing import AsyncIterator
from openjiuwen.core.common.logging import logger
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable
from openjiuwen.core.runtime.runtime import Runtime

class TransformCompNode(ComponentExecutable, WorkflowComponent):
    def __init__(self, node_id: str = ''):
        super().__init__()
        self.node_id = node_id

    # inputs是generator字典
    async def transform(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[
        Output]:
        logger.debug(f"===TransformCompNode[{self.node_id}], input stream started")
        try:
            # 假设key是value，取对应generator
            value_generator = inputs.get("value")
            async for value in value_generator:
                logger.debug(f"===TransformCompNode[{self.node_id}], processed input: {value}")
                yield {"value": value}
        except Exception as e:
            logger.error(f"===TransformCompNode[{self.node_id}], critical error in transform: {e}")
            raise  # 重新抛出关键异常（如流中断）
```

`CollectCompNode` implements the `collect` method (corresponding to `ComponentAbility.COLLECT`), aggregating stream input into batch output. Specifically, it receives input stream data `[{"value":1}, {"value":2}]`, aggregates the calculation 1+2, and outputs the batch result `{"value":3}`. `CollectCompNode` uses `add_stream_connection` to connect with predecessors and `add_connection` to connect with successors. The example code is as follows:

```python
import asyncio
from typing import AsyncIterator
from openjiuwen.core.common.logging import logger
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable
from openjiuwen.core.runtime.runtime import Runtime

class CollectCompNode(ComponentExecutable, WorkflowComponent):
    def __init__(self, node_id: str = ''):
        super().__init__()
        self.node_id = node_id

    # inputs是generator字典
    async def collect(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        logger.info(f"===CollectCompNode[{self.node_id}], input stream started")
        result = 0
        try:
            # 假设key是value，取对应generator
            value_generator = inputs.get("value")
            async for value in value_generator:
                if value is None:
                    logger.warning(f"===CollectCompNode[{self.node_id}], missing 'value' in input: {input}")
                    continue
                result += value
                logger.info(f"===CollectCompNode[{self.node_id}], processed input: {input}")
            return {"value": result}
        except Exception as e:
            logger.error(f"===CollectCompNode[{self.node_id}], critical error in collect: {e}")
            raise  # 重新抛出关键异常，如流中断
```

Construct the workflow, set the start and end components, and add the three components above to the workflow:

```python
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.workflow.workflow_config import ComponentAbility

flow = Workflow()
flow.set_start_comp("start", Start({}), inputs_schema={"a": "${a}"})
# a: throw 2 frames: {value: 1}, {value: 2}
flow.add_workflow_comp("a", StreamCompNode("a"), inputs_schema={"value": "${start.a}"})
# b: transform 2 frames to c
flow.add_workflow_comp("b", TransformCompNode("b"), stream_inputs_schema={"value": "${a.value}"})
# c: value = sum(value of frames)
flow.add_workflow_comp("c", CollectCompNode("c"), stream_inputs_schema={"value": "${b.value}"})
flow.set_end_comp("end", End({}), inputs_schema={"result": "${c.value}"})
```

Connect the components; streaming components are connected using `add_stream_connection`:

```python
flow.add_connection("start", "a")
flow.add_stream_connection("a", "b")
flow.add_stream_connection("b", "c")
flow.add_connection("c", "end")
```

Execute the workflow:

```python
import asyncio
from openjiuwen.core.runtime.workflow import WorkflowRuntime
result = asyncio.run(flow.invoke({"a": 1}, WorkflowRuntime()))
print(f"{result}")
```

Execution result:

```python
result={'output': {'result': 3}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

# Data Transmission Methods Between Components

During the workflow construction process, data transmission between components can be achieved via reference expressions. Reference expressions can cite variables, input, or output values but do not support the addition of logic.

## Referencing Inputs in Successor Components

Assuming the input is `{"inputs": "test"}`, a successor component can reference the input via `${inputs}`.

```python
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.start_comp import Start

workflow = Workflow()
workflow.set_start_comp("start", Start(), inputs_schema={"query": "${inputs}"})
```

Assuming the input is `{"inputs": {"a": 1}}`, a successor component can reference the input via `${inputs.a}`.

```python
workflow.set_start_comp("start", Start(), inputs_schema={"query": "${inputs.a}"})
```

## Successor Components Referencing Predecessor Components

The output of a predecessor component can be referenced via `${<predecessor_component_id>.<output_value_id>}`. Assuming the predecessor component's output is `{"query": "result"}` and its ID added to the workflow is `start`, the successor component can reference it via `${start.query}`.

```python
workflow.set_end_comp("end", End(), inputs_schema={"query": "${start.query}"})
```
Below is a complete runnable example demonstrating how to use reference expressions for data transmission between components:

```python
import asyncio
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.runtime.workflow import WorkflowRuntime

# 创建工作流
workflow = Workflow()

# 设置Start组件，演示引用简单输入和嵌套输入
# inputs_schema中的${inputs}引用整个输入对象
# ${inputs.message}引用输入对象中的message字段
workflow.set_start_comp(
    "start", 
    Start(), 
    inputs_schema={
        "query": "${inputs.message}",  # 引用嵌套输入
        "metadata": "${inputs}"         # 引用整个输入
    }
)

# 设置End组件，演示引用前序组件的输出
# ${start.query}引用id为"start"的组件的query输出
# ${start.metadata}引用id为"start"的组件的metadata输出
workflow.set_end_comp(
    "end", 
    End({"responseTemplate": "处理结果: {{result}}, 元数据: {{meta}}"}),
    inputs_schema={
        "result": "${start.query}",      # 引用前序组件的输出
        "meta": "${start.metadata}"      # 引用前序组件的输出
    }
)

# 连接组件
workflow.add_connection("start", "end")

# 执行工作流
inputs = {
    "inputs": {
        "message": "Hello, openJiuwen!"
    }
}

result = asyncio.run(workflow.invoke(inputs=inputs, runtime=WorkflowRuntime()))
print(f"执行结果: {result.result}")
print(f"执行状态: {result.state}")
```

**Expected Output:**

```python
执行结果: {'responseContent': "处理结果: Hello, openJiuwen!, 元数据: {'message': 'Hello, openJiuwen!'}"}
执行状态: WorkflowExecutionState.COMPLETED
```