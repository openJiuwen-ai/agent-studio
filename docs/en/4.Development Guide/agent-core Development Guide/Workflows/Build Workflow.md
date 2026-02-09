In the openJiuwen framework, workflows are implemented by the `Workflow` type. A configured `Workflow` instance is in an executable state and can be called via the `invoke` method. For scenarios requiring real-time output, streaming calls are also supported via the `stream` method. During workflow execution, the state data and framework functions required by each workflow component are provided by the `WorkflowRuntime`, the scope of which is a single workflow invocation process.

The basic steps to create and execute a workflow are as follows:

1.  Create Workflow: Create a new workflow instance and initialize it, register components to the workflow, and connect the components.
2.  Execute Workflow: Create a workflow runtime for each execution, and call the workflow based on user input and the workflow runtime.

# Creating a Workflow

## Initializing a Workflow

Create and initialize a new workflow instance. Currently, two methods are supported: creation via default configuration and creation via custom configuration.

### Creation via Default Configuration

You can quickly create a workflow with a default configuration by directly creating a new workflow object:

```python
from openjiuwen.core.workflow.base import Workflow

workflow = Workflow()
```

### Creation via Custom Configuration

In some complex workflow construction scenarios, configuration information can be specified when creating a `Workflow`. Workflow configuration is represented by `WorkflowConfig`, which contains complete information about a workflow. `WorkflowConfig` supports default empty construction as well as construction specifying workflow ID, name, and version information.

```python
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

# 新建一个默认的空配置，组件与边默认为空
empty_workflow_config = WorkflowConfig()
workflow_with_empty_config = Workflow(workflow_config=empty_workflow_config)

# 新建一个工作流配置包含工作流的ID、名称、版本信息，组件与边默认为空
name = "test_workflow"
id = "test_workflow_id"
version = "1.0.0"
workflow_config = WorkflowConfig(metadata=WorkflowMetadata(name=name, id=id, version=version))
workflow = Workflow(workflow_config=workflow_config)
```

## Registering Components to Workflow

A workflow must contain a Start component and an End component; other components can be selected from built-in components or custom components. When registering a component to the workflow, `inputs_schema` usually uses reference expressions with the structure `${<predecessor_component_ID>.<output_value_ID>}`. The predecessor component ID is the ID name set by the user when registering to the workflow, and non-existent components cannot be referenced.

### Start Component

Register the built-in `Start` component to the workflow via the `set_start_comp` method, setting the component ID to `start`. The start component reads user input during workflow invocation via `${query}`, and successor components can retrieve the output of the start component via `${start.query}`. For more details on Start component configuration, please refer to the [Start Component](./Using%20Components/Using%20Preset%20Components.md#start-component) section.

```python
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.workflow.base import Workflow

workflow = Workflow()
workflow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
```

### Business Component

Taking an LLM component implementing Chinese-to-English translation as an example, register the `LLMComponent` to the workflow via the `add_workflow_comp` method. Here, the predecessor of the LLM component is `start`, so input can be retrieved from the start component via `${start.query}`. In the `output_config` of the LLM component, the output format is configured as `"query": {"type": "string", "description": "Rewritten query", "required": True}`. Successor components can also retrieve the LLM component's output via `${llm.query}`. For more details on LLM component configuration, please refer to the [LLM Component](./Using%20Components/Using%20Preset%20Components.md#llm-component) section.

```python
import os
from datetime import datetime

from openjiuwen.core.component.llm_comp import LLMComponent, LLMCompConfig
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo

API_BASE = os.getenv("API_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("API_KEY", "sk-fake")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")

SYSTEM_PROMPT_TEMPLATE = "你是一个query改写的AI助手。今天的日期是{}。"

def _create_model_config() -> ModelConfig:
    """根据环境变量构造模型配置。"""
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=120,  # 增加超时时间到120秒，避免网络问题
        ),
    )

def build_current_date():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d")

def _create_llm_component() -> LLMComponent:
    """创建 LLM 组件，仅用于抽取结构化字段（location/date）。"""
    model_config = _create_model_config()
    current_date = build_current_date()
    user_prompt = ("\n原始query为：{{query}}\n\n帮我改写原始query，要求：\n"
                   "1. 改为英文；\n"
                   "2. 改写后的query必须包含当前的日期，默认日期为今天；\n"
                   "3. 日期为YYYY-MM-DD格式。")
    config = LLMCompConfig(
        model=model_config,
        template_content=[{"role": "user", "content": SYSTEM_PROMPT_TEMPLATE.format(current_date) + user_prompt}],
        response_format={"type": "text"},
        output_config={
            "query": {"type": "string", "description": "改写后的query", "required": True}
        },
    )
    return LLMComponent(config)

llm = _create_llm_component()

# 注册大模型组件到工作流
workflow.add_workflow_comp("llm", llm, inputs_schema={"query": "${start.query}"})
```

### End Component

Register the `End` component to the workflow via the `set_end_comp` method, specifying the output template as `{"responseTemplate": "Result:{{final_output}}"}`, and setting the component ID to "end". The End component can retrieve input from the executed LLM component via `${llm.query}`. For more details on End component configuration, please refer to the [End Component](./Using%20Components/Using%20Preset%20Components.md#end-component)  section.

```python
from openjiuwen.core.component.end_comp import End
# 创建End组件（指定输出模板）
end = End({"responseTemplate": "结果:{{final_output}}"})

# 注册End组件到工作流（批输出模式）
workflow.set_end_comp("end", end, inputs_schema={"final_output": "${llm.query}"})
```

## Connecting Components

In a workflow, a connection represents the dependency relationship and execution path between components. Essentially, it is a directed connection used to define the sequence of tasks or the direction of data flow. All connections are unidirectional, ensuring the process executes according to the preset path, and support conditional judgment to achieve dynamic branching. Note that in some scenarios where dynamic jumps to the next component based on component logic output are required, explicit connection relationships do not necessarily need to be established between components.

### Normal Connection

A normal connection is the most basic form of connection in a workflow. It only represents a direct dependency or sequential relationship between two components without additional conditional constraints. It is used to implement linear or simple task transitions, ensuring that the successor component is automatically triggered after the predecessor node completes. Create a normal connection via the `workflow.add_connection()` method, where the first parameter is the source component ID and the second parameter is the target component ID. The execution order strictly follows the definition of the connection from left to right.

```python
# 添加普通连接：从"start"组件指向"llm"
workflow.add_connection("start", "llm")

# 添加普通连接：从"llm"指向"end"
workflow.add_connection("llm", "end")
```

### Conditional Connection

A conditional connection indicates that there is a conditional judgment on the connection between components. The result of the conditional judgment determines the selection of the target component. It is used to choose different execution paths based on specific conditions, achieving dynamic branching of the workflow. Create a conditional connection via the `workflow.add_conditional_connection()` method, where the first parameter is the source component ID and the second parameter is a conditional judgment function, which can receive current state variables for judgment and return the target component ID.

```python
from openjiuwen.core.runtime.runtime import Runtime

# 从Runtime中获取"start"组件输出的"query"字段值，基于query的大小决定下一执行的组件
def router(runtime: Runtime):
    num = runtime.get_global_state("start.query")
    if num == 0:
        return "a"
    elif num == 1:
        return "b"
    else:
        return "a"

# 增加条件连接 start -> a/b
workflow.add_conditional_connection("start", router=router)
# a -> end
workflow.add_connection("a", "end")
# b -> end
workflow.add_connection("b", "end")
```

Conditional connections are typically used in the following scenarios:

* Static Branching: In most scenarios, the range of selectable next components after a specific component is clear, and the executable conditions for each branch are defined.
* Loop Conditions: In certain workflow patterns (e.g., ReAct), the ability to jump back and cyclically execute parts of the workflow path is required.
* Dynamic Jumps: When constructing a workflow, users dynamically specify jump branches based on runtime state data.

**Static Branching**

All possible branch paths are determined during graph construction, and one is selected for execution through conditional judgment.

```python
from openjiuwen.core.runtime.runtime import Runtime

def router(runtime: Runtime):
    if runtime.get_global_state("start.value") < 1:
        return "a"
    else:
        return "b"

workflow.add_conditional_connection("start", router=router)
# a -> end
workflow.add_connection("a", "end")
# b -> end
workflow.add_connection("b", "end")
```

**Loop Conditions**

Conditional connections can point to previous nodes in the workflow, but care must be taken to avoid infinite loops.

```python
from openjiuwen.core.runtime.runtime import Runtime

def router(runtime: Runtime):
    if runtime.get_global_state("start.value") < 1:
        return "a"
    else:
        return "b"

# start -> a
workflow.add_connection("start", "a")
# a -> router, router->a/b
workflow.add_conditional_connection("a", router=router)
# b -> end
workflow.add_connection("b", "end")
```

**Dynamic Jumps**

Conditional connections can dynamically jump to other nodes in the workflow. When `start.value` is 'a', it jumps to node 'a'; when `start.value` is 'b', it jumps to node 'b'.

```python
from openjiuwen.core.runtime.runtime import Runtime

def router(runtime: Runtime):
    return runtime.get_global_state("start.value")

workflow.add_conditional_connection("start", router=router)
# a -> end
workflow.add_connection("a", "end")
# b -> end
workflow.add_connection("b", "end")

```

### Streaming Connection

When building workflows, the openJiuwen framework also provides streaming connection capabilities for components that support streaming output processing. This connection method allows streaming variables to be passed between two adjacent components. Create a streaming connection via the `Workflow.add_stream_connection` method. The first parameter is the ID of the producer component that outputs streaming messages (the corresponding component must implement the `stream` interface or `transform` interface), and the second parameter is the ID of the consumer component that accepts streaming input messages (the corresponding component must implement the `transform` or `collect` interface). Additionally, when registering a consumer component, a separate Schema definition `stream_inputs_schema` must be specified for the streaming connection, used in the same way as `inputs_schema`. Taking the streaming connection between an LLM component and an End component as an example (the usage is the same for streaming connections between components in other scenarios):

```python
# 注册end组件时，指定流式连接输入定义stream_inputs_schema
workflow.set_end_comp("end_stream", end, stream_inputs_schema={"data": "${llm.output}"})
# 添加流式连接：从"llm"指向"end"，其中大模型组件默认实现了`stream`接口，end组件默认实现了`transform`和`collect`接口
workflow.add_stream_connection("llm", "end_stream")
```

From the workflow perspective, to achieve real-time outflow of streaming messages from the LLM component, it is usually recommended to specify `response_mode="streaming"` when registering the End component to enable its streaming output. Then, use the `workflow.stream` streaming output call method to process the stream output results of the End component, thereby obtaining the streaming output results of the workflow.

```python
import asyncio

from openjiuwen.core.runtime.workflow import WorkflowRuntime
from openjiuwen.core.stream.base import BaseStreamMode
# 注册end组件时，指定流式连接输入定义stream_inputs_schema，并指定`response_mode="streaming"`来开启流式输出
workflow.set_end_comp("end_stream", end, stream_inputs_schema={"data": "${llm.output}"}, response_mode="streaming")
# 添加流式连接：从"llm"指向"end"，其中大模型组件默认实现了`stream`接口，end组件默认实现了`transform`和`collect`接口
workflow.add_stream_connection("llm", "end_stream")

# 采用workflow.stream的流式输出调用方式，会调用end组件的【`transform`接口】
async def run_stream():
    async for chunk in workflow.stream(
        {"query": "查询上海的天气"},
        WorkflowRuntime(),
        stream_modes=[BaseStreamMode.OUTPUT]
    ):
        print(chunk)

# 使用 asyncio.run 执行异步函数
if __name__ == "__main__":
    asyncio.run(run_stream())
```

# Executing Workflow

## Creating Workflow Runtime

`WorkflowRuntime` is used to manage workflow context information, encapsulating configurations, states, and other content required during workflow execution.

```python
from openjiuwen.core.runtime.workflow import WorkflowRuntime

runtime = WorkflowRuntime()
```

When creating `WorkflowRuntime`, you can specify the session ID of the current request to track multi-turn conversation scenarios. If not set, a temporary UUID is generated by default:

```python
session_id = "test_session"

runtime = WorkflowRuntime(session_id=session_id)
```

## Invoking Workflow

Generally, the latency of the Agent workflow execution process is mainly distributed in the access to LLM services and API calls to external tools. Therefore, from the perspective of performance and efficiency, the openJiuwen framework defaults to supporting calls only in an asynchronous context environment (based on Python's `asyncio` framework). If users wish to call the workflow in a synchronous environment, they can use common Python methods for synchronously calling asynchronous functions, such as `asyncio.run()`.

The workflow supports two invocation methods:

* `invoke`: Refers to a workflow execution method that processes a complete batch of data at once. It receives a set of complete data as input and returns the complete processing result at once after workflow processing. This mode is suitable for scenarios where the data volume is fixed and the processing result needs to be presented in full, such as data analysis and report generation.
* `stream`: Refers to a workflow execution method that processes data step-by-step in a data stream manner. It receives an input data stream, then processes it step-by-step and returns intermediate results. It is suitable for scenarios requiring real-time response or step-by-step processing, such as ultra-long text generation by LLMs.

### invoke

Based on the translation workflow mentioned above, input `"Query weather in Shanghai"` and `WorkflowRuntime`, call the `invoke` method, and print the output result:

```python
import asyncio

result = asyncio.run(workflow.invoke({"query": "查询上海的天气"}, runtime))
print(f"{result}")
```

The output result is as follows:

```python
{"responseContent": "结果:Check the weather in Shanghai on 2025-08-22"}
```

### stream

Executing the workflow via `stream` returns an asynchronous generator. Each message obtained by traversing the generator is a `chunk`. Each `chunk` is a fragment of the processing process, which may contain partial semantics, intermediate inference states, or the step-by-step construction of the final result. Users can see progress immediately upon receiving the first chunk and continue to receive supplementary content until the entire process ends.

openJiuwen provides **three streaming output modes** to offer customized output capabilities for streaming information. Since all streaming messages share the output pipeline within the workflow, distinguishing output modes improves the extensibility of streaming messages:

* `BaseStreamMode.OUTPUT`: Outputs only standard streaming data defined by the framework, with data of type `OutputSchema`.
* `BaseStreamMode.TRACE`: Outputs only debugging/trace streaming data defined by the framework, with data of type `TraceSchema`.
* `BaseStreamMode.CUSTOM`: Outputs only user-defined streaming data, with data of type `CustomSchema`.

The output type is specified via the parameter `stream_modes`. This parameter is a `List` and supports simultaneous output of multiple modes. If no output mode is currently specified, all information is printed by default. If modes are specified, only information related to the specified modes is printed. The output of the three modes is introduced below based on the translation workflow example above.

> **Note**
>
> When using the `stream` method for output, you need to specify `response_mode="streaming"` when registering the End component to enable streaming output, and connect the End component with the predecessor component using a streaming connection via the `Workflow.add_stream_connection` method.

#### BaseStreamMode.OUTPUT

In the `workflow.stream` method, specify `stream_modes=[BaseStreamMode.OUTPUT]` to indicate outputting only standard streaming data defined by the framework:

```python
# Simulate executing a workflow for a weather query.
async for chunk in workflow.stream({"query": "查询上海的天气"}, runtime, stream_modes=[BaseStreamMode.OUTPUT]):
    print(chunk)
```

The output data type is `OutputSchema`, and the output result is as follows:

```python
OutputSchema(type = 'end node stream', index = 0, payload = {'answer': '结果:'}),
OutputSchema(type = 'end node stream', index = 1, payload ={ 'answer': 'Check the weather in Shanghai on 2025-08-22' })
```

#### BaseStreamMode.TRACE

In the `workflow.stream` method, specify `stream_modes=[BaseStreamMode.TRACE]` to indicate outputting only debugging streaming data defined by the framework:

```python
# Simulate executing a workflow for a weather query.
async for chunk in workflow.stream({"query": "查询上海的天气"}, runtime, stream_modes=[BaseStreamMode.TRACE]):
    print(chunk)
```

The output data type is `TraceSchema`. The output is as follows (excerpting the trace output of the end node):

```python
...
# 组件的调测开始事件帧
TraceSchema(type = 'tracer_workflow', payload = {
    'traceId': '86b76988-5549-482b-8401-444b2621641e',
    'startTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 678133),
    'inputs': {
    'final_output': 'Check the weather in Shanghai on 2025-08-22',
    },
    'invokeId': 'end',
    'parentInvokeId': 'llm',
    'executionId': '86b76988-5549-482b-8401-444b2621641e',
    'componentId': 'end',
    'componentName': '',
    'componentType': 'llm_component',
    'status': 'start',
    'parentNodeId': ''
})
# 组件的调测结束事件帧
TraceSchema(type = 'tracer_workflow', payload = {
    'traceId': '86b76988-5549-482b-8401-444b2621641e',
    'startTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 678133),
    'endTime': datetime.datetime(2025, 8, 22, 14, 39, 9, 679167),
    'inputs': {
    'final_output': 'Check the weather in Shanghai on 2025-08-22',
    },
    'outputs': {
    'responseContent': '结果:Check the weather in Shanghai on 2025-08-22'
    },
    'invokeId': 'end',
    'parentInvokeId': 'llm',
    'executionId': '86b76988-5549-482b-8401-444b2621641e',
    'componentId': 'end',
    'componentName': '',
    'componentType': 'llm_component',
    'status': 'finish',
    'parentNodeId': '',
    'streamOutputs': []
})
...
```

#### BaseStreamMode.CUSTOM

To demonstrate user-defined streaming data, the following code is temporarily added to the used `LLMComponent`:

```python
from openjiuwen.core.component.base import WorkflowComponent
from openjiuwen.core.context_engine.base import Context
from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
from openjiuwen.core.runtime.runtime import Runtime


class LLMComponent(WorkflowComponent, ComponentExecutable):
    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        ...
        model_inputs = self._prepare_model_inputs(inputs)
        llm_response = await self._llm.ainvoke(model_inputs)
        # 若response为 {"role": "user", "content": "Check the weather in Shanghai on 2025-08-22"}
        response = llm_response.content
        await runtime.write_custom_stream(**dict(custom_output=response))
        ...
```

In the `workflow.stream` method, specify `stream_modes=[BaseStreamMode.CUSTOM]` to indicate outputting only user-defined streaming data:

```python
# Simulate executing a workflow for a weather query.
async for chunk in workflow.stream({"query": "查询上海的天气"}, runtime, stream_modes=[BaseStreamMode.CUSTOM]):
    print(chunk)
```

The output data type is `CustomSchema`, and the output is as follows:
```python
...
# LLM组件自定义输出内容
CustomSchema(custom_output = 'Check the weather in Shanghai on 2025-08-22')
...
```