The openJiuwen framework provides the `WorkflowAgent` built-in agent. Developers create `WorkflowAgent` objects. Then, they call the `invoke` and `stream` external interfaces of the `WorkflowAgent` class to implement the batch and streaming invocation processes of the `WorkflowAgent`, respectively. At the same time, based on the framework's interrupt recovery function, the `WorkflowAgent` supports Human-in-the-Loop (HITL) scenarios. The specific process includes:

* Create and execute `WorkflowAgent`, execute the batch/stream invocation process, and the `WorkflowAgent` returns the corresponding batch output results/streaming data frames.
* Once the HITL process is triggered, the `WorkflowAgent` automatically records the state at the time of interruption; taking the information feedback from the user as input, when the `WorkflowAgent` object is executed again, it will continue execution from the interruption point based on the interruption state snapshot.

The following uses a `WorkflowAgent` bound to a workflow that asks the user questions as an example to help developers understand how to implement batch/stream invocation of the `WorkflowAgent` and implement HITL scenarios during batch/stream invocation.

## Creating Associated Workflow

Create a basic workflow: composed of a Start component, a Questioner component, and an End component connected in series. Its function is to extract user information such as name and age based on user input. Part of the example code is as follows:

```python
import os
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata, WorkflowInputsSchema
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.questioner_comp import QuestionerComponent, FieldInfo, QuestionerConfig

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")

def _build_workflow_with_questioner():
    id = "questioner_workflow"
    version = "0.0.1"
    name = "questioner_workflow"
    inputs_schema_dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "用户输入信息",
                "required": True
            }
        }
    }
    workflow_inputs_schema = WorkflowInputsSchema(**inputs_schema_dict)
    workflow_config = WorkflowConfig(metadata=WorkflowMetadata(name=name, id=id, version=version),
                                     workflow_inputs_schema=workflow_inputs_schema)
    flow = Workflow(workflow_config=workflow_config)

    model_config = ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=30  # 添加超时设置
        )
    )

    key_fields = [
        FieldInfo(field_name="name", description="用户姓名", required=True),
        FieldInfo(field_name="age", description="用户年龄", required=True)
    ]

    start_component = Start(
        {
            "inputs": [
                {"id": "query", "type": "String", "required": "true", "sourceType": "ref"}
            ]
        }
    )
    end_component = End({"responseTemplate": "姓名：{{name}} | 年龄：{{age}}"})

    questioner_config = QuestionerConfig(
        model=model_config,
        question_content="",
        extract_fields_from_response=True,
        field_names=key_fields,
        with_chat_history=False
    )
    questioner_component = QuestionerComponent(questioner_comp_config=questioner_config)

    flow.set_start_comp("s", start_component, inputs_schema={"query": "${query}"})
    flow.set_end_comp("e", end_component,
                      inputs_schema={"name": "${questioner.name}", "age": "${questioner.age}"})
    flow.add_workflow_comp("questioner", questioner_component, inputs_schema={"query": "${s.query}"})

    flow.add_connection("s", "questioner")
    flow.add_connection("questioner", "e")

    return flow
```

## Creating WorkflowAgent

Create a `WorkflowAgent` object, covering configuration parameter information related to `WorkflowAgent`, such as metadata information of the bound workflow, system prompt templates, and LLM configuration information.
The example code is as follows:

```python
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.agent.common.schema import WorkflowSchema

def _create_model():
    return ModelConfig(model_provider=MODEL_PROVIDER,
                       model_info=BaseModelInfo(
                           model=MODEL_NAME,
                           api_base=API_BASE,
                           api_key=API_KEY,
                           temperature=0.7,
                           top_p=0.9,
                           timeout=30
                       ))

def _create_prompt_template():
    return [
        dict(role="system", content="你是一个AI助手。请帮我调用工具解决问题。")
    ]

def _create_workflow_agent(workflow):
    """根据 workflow 实例化 WorkflowAgent。"""
    model_config = _create_model()
    prompt_template = _create_prompt_template()

    workflow_id = workflow.config().metadata.id
    workflow_name = workflow.config().metadata.name
    workflow_version = workflow.config().metadata.version
    schema = WorkflowSchema(
        id=workflow_id,
        name=workflow_name,
        version=workflow_version,
        description="用户信息收集工作流",
        inputs={"query": {"type": "string"}},
    )
    agent_config = WorkflowAgentConfig(
        id="workflow_agent_123",
        version="0.1.0",
        description="用户信息收集agent",
        workflows=[schema],
        model=model_config,
        prompt_template=prompt_template
    )
    agent = WorkflowAgent(agent_config)
    agent.add_workflows([workflow])
    return agent
```

## Running WorkflowAgent

By calling the `invoke` and `stream` external interfaces of the `WorkflowAgent` class, the batch and streaming execution processes of the `WorkflowAgent` are implemented respectively.

### Batch Execution

Call the `invoke` interface provided by `WorkflowAgent` to trigger the batch execution process of `WorkflowAgent` with one click.

```python
import asyncio

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)

    response = await workflow_agent.invoke(
        {"conversation_id": "12345", "query": "请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。"}
    )
    print(f"WorkflowAgent非流式调用的输出结果 >>> {response}")

if __name__ == '__main__':
    asyncio.run(main())
```

When the user request is `Please help me collect and organize user information. This user's name is Zhang San, and age is 25`, the `WorkflowAgent` object will first call the workflow named `name="questioner_workflow"`. The workflow can extract all required parameter information from the user request at once. The `WorkflowAgent` summarizes and generates the final answer based on the execution results of the workflow. An example of the result returned by the batch execution process is as follows:

```python
WorkflowAgent 非流式调用的输出结果 >>> {'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

The data structure of the batch output of the `WorkflowAgent` object is a dictionary, where specific field information includes:

* **result_type** (string): The type of result returned by the `WorkflowAgent`. In this example, the type of the batch execution result is `"answer"`, indicating that the `WorkflowAgent` returned the final result.
* **output** (string): The final return result of the `WorkflowAgent`. In this example, it is the final answer to the user request, i.e., `User information organization completed, name is Zhang San, age is 25`.

### Streaming Execution

Call the `stream` interface provided by `WorkflowAgent` to trigger the streaming invocation process of `WorkflowAgent` with one click.

```python
import asyncio

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)

    async for chunk in workflow_agent.stream(
        {"conversation_id": "12345", "query": "请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。"}
    ):
        print(f"WorkflowAgent 流式输出的结果 >>> {chunk}")

if __name__ == '__main__':
    asyncio.run(main())
```

When the user request is `Please help me collect and organize user information. This user's name is Zhang San, and age is 25`, the `WorkflowAgent` object will first call the workflow named `name="questioner_workflow"`. The workflow can extract all required parameter information from the user request at once. The `WorkflowAgent` summarizes and generates the final answer based on the execution results of the workflow. An example of the data frames returned by the streaming invocation execution process is as follows:

```python
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 222143), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'outputs': None, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 222143), 'endTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 222809), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'outputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 259972), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 259972), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'running', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 15, 259972), 'endTime': datetime.datetime(2025, 10, 27, 15, 41, 23, 371286), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁。'}, 'outputs': {'name': '张三', 'age': 25}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 23, 455565), 'endTime': None, 'inputs': {'name': '张三', 'age': 25}, 'outputs': None, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='tracer_workflow' payload={'traceId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'startTime': datetime.datetime(2025, 10, 27, 15, 41, 23, 455565), 'endTime': datetime.datetime(2025, 10, 27, 15, 41, 23, 456095), 'inputs': {'name': '张三', 'age': 25}, 'outputs': {'responseContent': '姓名：张三 | 年龄：25'}, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '88207e04-29ab-4b71-b4e6-6f9ddb9023a3', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 流式输出的结果 >>> type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

The difference between the return results of streaming invocation and batch invocation of the `WorkflowAgent` is that streaming invocation returns multiple data frames, while batch invocation returns a single output result. The streaming data frames involved in this example are data frames for trace information.

`type="tracer_workflow"`: Data frame for trace information. It records trace information such as input/output information and execution start/end times of various components involved in the workflow execution process, for developers to perform specific business analysis. Since the workflow in this example contains 3 components (Start component, Questioner component, End component), and each component generates one frame of trace information upon starting and ending execution respectively, there are a total of 7 such data frames.

## Human-in-the-Loop (HITL)

For a `WorkflowAgent` to trigger a Human-in-the-Loop (HITL) process, the following conditions must be met:

1.  First, the agent needs to bind and call a specific workflow.
2.  Second, the workflow must contain components supporting interrupt recovery (such as the built-in Questioner component).
3.  Finally, the component triggers a follow-up question operation during execution.

This section will use the Questioner component as an example for explanation.

### Batch Execution Trigger

When the user request is: Please help me collect and organize user information. This user's name is Zhang San. Call the `invoke` interface of `WorkflowAgent`:

```python
import asyncio

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)
    response = await workflow_agent.invoke(
        {"conversation_id": "12345", "query": "请帮我收集和整理用户信息。这名用户的姓名是张三。"}
    )
    print(f"WorkflowAgent 批调用的输出结果 >>> {response}")

if __name__ == '__main__':
    asyncio.run(main())
```

The `WorkflowAgent` object will first call the workflow named `name="questioner_workflow"` that asks the user questions. When the workflow executes to the Questioner component, since the user only provided name information, while age as a required piece of information still cannot be extracted, the Questioner triggers the mechanism to ask the user a follow-up question. The `WorkflowAgent` treats the interrupt data frame as a streaming output data frame for local invocation. An example of the data frame returned this time is as follows:

```python
WorkflowAgent 批调用的输出结果 >>> [OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供用户年龄相关的信息'))]
```
The output result of the `WorkflowAgent` batch invocation is a list summarizing several `OutputSchema` objects. When `type='__interaction__'`, it indicates interrupt information. Its `payload` field contains the specific component name of the interruption (in this example `"questioner"`) and the content of the follow-up question for the user (in this example `Please provide information related to user age`).
Therefore, developers judge whether an HITL scenario is triggered based on the return result of the `WorkflowAgent`. That is, when the agent output result is a list summarizing several `OutputSchema` objects, and it contains an object with `type='__interaction__'`.

```python
import asyncio
from typing import List
from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
from openjiuwen.core.stream.base import OutputSchema

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)
    response = await workflow_agent.invoke(
        {"conversation_id": "12345", "query": "请帮我收集和整理用户信息。这名用户的姓名是张三。"})
    print(f"WorkflowAgent 批调用的输出结果 >>> {response}")

    if isinstance(response, List):
        interactive_input = InteractiveInput()
        for item in response:
            if isinstance(item, OutputSchema) and item.type == '__interaction__':
                component_id = item.payload.id
                if component_id == "questioner":
                    # 针对提问器组件的用户反馈
                    interactive_input.update(component_id, "用户的年龄是25岁")
        result = await workflow_agent.invoke({"conversation_id": "12345", "query": interactive_input})
        print(f"WorkflowAgent 用户反馈后的批调用输出结果 >>> {result}")

if __name__ == '__main__':
    asyncio.run(main())
```

After the user feedbacks the age information, based on the same session ID (in this example `conversation_id=12345`), the `WorkflowAgent` is batch called again. The framework supports interrupt recovery, meaning the `WorkflowAgent` calls the workflow that was just interrupted again, and the workflow continues execution based on the `checkpointer` breakpoint recorded in the last execution, starting directly from the Questioner component rather than from the Start component. The final answer output by the `WorkflowAgent` is:

```python
WorkflowAgent 用户反馈后的批调用输出结果 >>> {'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

The data structure of the batch output of the `WorkflowAgent` object is a dictionary, where specific field information includes:

* **result_type** (string): The type of result returned by the `WorkflowAgent`. In this example, the type of the batch execution result is `"answer"`, indicating that the `WorkflowAgent` returned the final result.
* **output** (string): The final return result of the `WorkflowAgent`. In this example, it is the final answer to the user request—`WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}`.

### Streaming Execution Trigger

When the user request is: Please help me collect and organize user information. This user's name is Zhang San. Call the `stream` interface of `WorkflowAgent`:

```python
import asyncio
from openjiuwen.core.stream.base import OutputSchema

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)
    interaction_output_schema = []
    async for chunk in workflow_agent.stream({"conversation_id": "12345",
                                              "query": "请帮我收集和整理用户信息。这名用户的姓名是张三"}):  # 首次调用WorkflowAgent智能体对象
        print(f"WorkflowAgent 首次调用的输出结果 >>> {chunk}")
        if isinstance(chunk, OutputSchema) and chunk.type == "__interaction__":
            interaction_output_schema.append(chunk)

if __name__ == '__main__':
    asyncio.run(main())
```

The `WorkflowAgent` object will first call the workflow named `name="questioner_workflow"` that asks the user questions. When the workflow executes to the Questioner component, since the user only provided name information, while age as a required piece of information still cannot be extracted, the Questioner triggers the mechanism to ask the user a follow-up question. The workflow returns an interrupt data frame, and the `WorkflowAgent` treats the interrupt data frame as a streaming output data frame for local invocation. An example of the data frame returned by this invocation is as follows:

```python
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 748863), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 748863), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 749687), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 789839), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 789839), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'running', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='__interaction__' index=0 payload=InteractionOutput(id='questioner', value='请您提供用户年龄相关的信息')
```

The streaming data frames involved in this example mainly include two types:

* `type="tracer_workflow"`: Data frame for trace information. It records trace information such as input/output information and execution start/end times of various components involved in the workflow execution process, for developers to perform specific business analysis. In this example, since the workflow executes sequentially to the second component (the Questioner component named `questioner`), and each component generates one frame of trace information upon starting and ending execution respectively, there are a total of 4 such trace information data frames. Furthermore, it is worth noting that: since the Questioner component triggered the follow-up process and did not truly finish execution, the `status` field value in the second frame (fourth frame in total) of the Questioner's trace information is `"running"`, rather than the completed status `"finish"`.
* `type="__interaction__"`: Interrupt data frame. The `payload` field contains the interrupt data structure `InteractionOutput`, which includes the name of the interrupting component and the specific content of the follow-up question to the user. In this example, the workflow executes to the Questioner component named `questioner`, triggers the interrupt process, and asks the user for age information.

Developers judge whether an HITL process is triggered based on the `type` field of the result returned by calling the `WorkflowAgent` object, obtain specific information about the interruption, and thus provide corresponding user feedback. The example code is as follows:

```python
import asyncio
from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
from openjiuwen.core.stream.base import OutputSchema

async def main():
    my_workflow = _build_workflow_with_questioner()
    workflow_agent = _create_workflow_agent(my_workflow)
    interaction_output_schema = []
    async for chunk in workflow_agent.stream({"conversation_id": "12345",
                                              "query": "请帮我收集和整理用户信息。这名用户的姓名是张三"}):  # 首次调用WorkflowAgent智能体对象
        print(f"WorkflowAgent 首次调用的输出结果 >>> {chunk}")
        if isinstance(chunk, OutputSchema) and chunk.type == "__interaction__":
            interaction_output_schema.append(chunk)

    if interaction_output_schema:  # 若存在中断数据帧，则触发人机交互流程
        user_input = InteractiveInput()
        for item in interaction_output_schema:
            component_id = item.payload.id
            user_input.update(component_id, "用户的年龄是25岁")  # 针对提问器组件的用户反馈信息
        async for chunk in workflow_agent.stream({"conversation_id": "12345",
                                                  "query": user_input}):  # 再次调用WorkflowAgent智能体对象，输入为包含用户反馈信息的InteractiveInput对象
            print(f"WorkflowAgent 第二次输出结果 >>> {chunk}")

if __name__ == '__main__':
    asyncio.run(main())
```

After the user feedbacks the age information, based on the same session ID (in this example `conversation_id=12345`), the `WorkflowAgent` is called via stream again. The framework supports interrupt recovery, meaning the `WorkflowAgent` calls the workflow that was just interrupted again, and the workflow continues execution based on the `checkpointer` breakpoint recorded in the last execution, starting directly from the Questioner component rather than from the Start component. The final output result is:

```python
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'running', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 600135), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': {'age': 25, 'name': '张三'}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633531), 'endTime': None, 'inputs': {'name': '张三', 'age': 25}, 'outputs': None, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633531), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633948), 'inputs': {'name': '张三', 'age': 25}, 'outputs': {'responseContent': '姓名：张三 | 年龄：25'}, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

The streaming data frames involved in this example include data frames for trace information:

* `type="tracer_workflow"`: Data frame for trace information. It records trace information such as input/output information and execution start/end times of various components involved in the workflow execution process. Since the workflow in this example continues execution from the breakpoint of the last execution, and each component generates one frame of trace information upon starting and ending execution respectively, there are a total of 5 such data frames.