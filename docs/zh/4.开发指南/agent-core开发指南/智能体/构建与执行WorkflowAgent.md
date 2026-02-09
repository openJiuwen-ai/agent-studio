openJiuwen框架提供了`WorkflowAgent`预置智能体。开发者创建`WorkflowAgent`智能体对象。然后，再调用`WorkflowAgent`类的对外接口`invoke`、`stream`，分别实现`WorkflowAgent`智能体的批、流调用流程。同时，`WorkflowAgent`智能体基于框架的中断恢复功能，支持人机交互场景。具体流程包括：

* 创建与执行`WorkflowAgent`，执行批/流的调用流程，`WorkflowAgent`返回相应的批输出结果/流式输出数据帧。
* 一旦触发人机交互流程，`WorkflowAgent`自动记录中断时的状态；将用户反馈的信息作为输入，再次执行`WorkflowAgent`智能体对象时，将基于中断状态快照从中断点继续执行。

以下以`WorkflowAgent`智能体绑定一个向用户提问的工作流为例，帮助开发者理解如何实现批/流调用`WorkflowAgent`智能体，并在批/流调用的同时实现人机交互场景。

## 创建关联工作流

创建一个基本工作流：由开始组件、提问器组件、结束组件先后串联构成，功能为根据用户输入、提取用户的姓名和年龄等信息。部分示例代码如下：

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

## 创建WorkflowAgent

创建`WorkflowAgent`对象，涵盖`WorkflowAgent`相关的配置参数信息，如绑定工作流的元数据信息、系统提示词模板及大模型配置信息等。
示例代码如下：

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

## 运行WorkflowAgent

通过调用`WorkflowAgent`类的对外接口`invoke`和`stream`，分别实现`WorkflowAgent`智能体的批、流执行流程。

### 批执行

调用`WorkflowAgent`提供的`invoke`接口，即可一键式触发`WorkflowAgent`的批执行流程。

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

当用户请求为`请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁`时，`WorkflowAgent`智能体对象将先调用`name="questioner_workflow"`的工作流，工作流能够从用户请求中一次性提取完整所有待提取参数信息，`WorkflowAgent`智能体根据工作流的执行结果总结生成最终答案。批执行流程返回的结果示例如下：

```python
WorkflowAgent 非流式调用的输出结果 >>> {'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

`WorkflowAgent`智能体对象批输出的数据结构是一个字典，其中具体的字段信息包括：

* ​**result_type**​(string)：`WorkflowAgent`智能体返回结果的类型，本例中批执行结果的类型为`"answer"`，表示`WorkflowAgent`智能体返回了最终结果。
* ​**output**​(string)：`WorkflowAgent`智能体的最终返回结果，本例中为针对用户请求的最终答案，即`用户信息整理完成，姓名为张三，年龄为25岁`。

### 流式执行

调用`WorkflowAgent`提供的`stream`接口，即可一键式触发`WorkflowAgent`的流式调用流程。

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

当用户请求为`请帮我收集和整理用户信息。这名用户的姓名是张三，年龄是25岁`时，`WorkflowAgent`智能体对象将先调用`name="questioner_workflow"`的工作流，工作流能够从用户请求中一次性提取完整所有待提取参数信息，`WorkflowAgent`智能体根据工作流的执行结果总结生成最终答案。流式调用执行流程返回的数据帧示例如下：

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

流式调用`WorkflowAgent`智能体的返回结果和批调用的区别在于：流式调用返回若干数据帧，而批调用返回单个输出结果。本示例涉及的流式数据帧为调测信息的数据帧。

type="tracer_workflow"：调测信息的数据帧。记录了工作流执行流程中涉及的各个组件的输入输出信息、执行开始/结束的时间等调测信息，供开发者做具体的业务分析。由于本例中的工作流包含开始组件、提问器组件、结束组件3个组件，每个组件开始执行和结束执行又各产生一帧调测信息，故此类数据帧共有7帧。

## 人机交互

WorkflowAgent智能体触发人机交互流程需满足以下条件：

1. 首先，智能体需绑定并调用一个特定的工作流。
2. 其次，该工作流中必须包含支持中断恢复的组件（如预置的提问器组件）。
3. 最后，该组件在执行过程中触发了追问操作。

本小节将以提问器组件为例进行说明。

### 批执行触发

当用户请求为：请帮我收集和整理用户信息。这名用户的姓名是张三。调用`WorkflowAgent`的`invoke`接口：

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

`WorkflowAgent`智能体对象将先调用`name="questioner_workflow"`的向用户提问的工作流。在工作流执行到提问器组件时，由于用户只提供了姓名信息，而年龄作为必需信息仍然无法提取其值，因此提问器触发了向用户追问机制，`WorkflowAgent`智能体将中断数据帧作为本地调用的流式输出数据帧。此次返回的数据帧示例如下：

```python
WorkflowAgent 批调用的输出结果 >>> [OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供用户年龄相关的信息'))]
```

`WorkflowAgent`智能体批调用的输出结果为若干OutputSchema对象汇总的列表，当`type='__interaction__'`，即表示中断信息，其`payload`字段包含了中断的具体组件名称（本例中为`"questioner"`）和用户追问的问题（本例中为`请您提供用户年龄相关的信息`）。
因此，开发者根据`WorkflowAgent`智能体的返回结果判断是否触发了人机交互场景。也就是当智能体输出结果为若干`OutputSchema`对象汇总的列表，且其中包含`type='__interaction__'`的对象。

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

用户反馈年龄信息后，基于同个会话id（本例中为`conversation_id=12345`），再次批调用`WorkflowAgent`智能体。框架支持中断恢复，即`WorkflowAgent`智能体再次调用刚刚执行中断的工作流，且工作流基于上次执行记录的checkpointer断点继续执行，直接从提问器组件开始执行，而不是从开始组件从头执行。`WorkflowAgent`智能体最终输出的答案为：

```python
WorkflowAgent 用户反馈后的批调用输出结果 >>> {'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

`WorkflowAgent`智能体对象批输出的数据结构是一个字典，其中具体的字段信息包括：

* **result_type**(string)：`WorkflowAgent`智能体返回结果的类型，本例中批执行结果的类型为`"answer"`，表示`WorkflowAgent`智能体返回了最终结果。
* **output**(string)：`WorkflowAgent`智能体的最终返回结果，本例中为针对用户请求的最终答案——`WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}`。

### 流式执行触发

当用户请求为：请帮我收集和整理用户信息。这名用户的姓名是张三。调用`WorkflowAgent`的`stream`接口：

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

`WorkflowAgent`智能体对象将先调用`name="questioner_workflow"`的向用户提问的工作流。在工作流执行到提问器组件时，由于用户只提供了姓名信息，而年龄作为必需信息仍然无法提取其值，因此提问器触发了向用户追问机制，工作流返回中断数据帧，`WorkflowAgent`智能体将中断数据帧作为本地调用的流式输出数据帧。此次调用返回的数据帧示例如下：

```python
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 748863), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 748863), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 749687), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'error': None, 'invokeId': 's', 'parentInvokeId': None, 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 's', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 789839), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='tracer_workflow' payload={'traceId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 21, 789839), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 's', 'executionId': '90e99326-819e-4b85-98d4-342fdf7419d7', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'running', 'parentNodeId': ''}
WorkflowAgent 第一次输出结果 >>> type='__interaction__' index=0 payload=InteractionOutput(id='questioner', value='请您提供用户年龄相关的信息')
```

本示例涉及的流式数据帧主要包含两种：

* type="tracer_workflow"：调测信息的数据帧。记录了工作流执行流程中涉及的各个组件的输入输出信息、执行开始/结束的时间等调测信息，供开发者做具体的业务分析。本例中，由于工作流顺序执行到第二个组件（名为`questioner`的提问器组件），且每个组件开始执行和结束执行又各产生一帧调测信息，此类调测信息数据帧共有4帧。此外，值得注意的是：由于提问器组件触发追问流程，并未真正执行完，提问器第二帧（总计第四帧）调测信息中的`status`字段值为`"running"`，而不是执行完成的状态`"finish"`。
* type="__interaction__"：中断数据帧。`payload`字段中包含了中断的数据结构`InteractionOutput`，其中包含了中断组件的名称和向用户追问的具体内容。而本例中，工作流执行到名为`questioner`的提问器组件触发了中断流程，并且向用户追问年龄信息。

开发者根据调用`WorkflowAgent`智能体对象返回结果的type字段，判断是否触发了人机交互流程，获取中断的具体信息，从而提供相应的用户反馈。示例代码如下：

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

用户反馈年龄信息后，基于同个会话id（本例中为`conversation_id=12345`），再次流调用`WorkflowAgent`智能体。框架支持中断恢复，即`WorkflowAgent`智能体再次调用刚刚执行中断的工作流，且工作流基于上次执行记录的checkpointer断点继续执行，直接从提问器组件开始执行，而不是从开始组件从头执行。最终输出结果为：

```python
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': None, 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'running', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 29, 957303), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 600135), 'inputs': {'query': '请帮我收集和整理用户信息。这名用户的姓名是张三'}, 'outputs': {'age': 25, 'name': '张三'}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': None, 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [{'on_invoke_data': 'extra trace data'}], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633531), 'endTime': None, 'inputs': {'name': '张三', 'age': 25}, 'outputs': None, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='tracer_workflow' payload={'traceId': '61546146-7098-42cd-b115-d20d235af829', 'startTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633531), 'endTime': datetime.datetime(2025, 10, 27, 15, 42, 36, 633948), 'inputs': {'name': '张三', 'age': 25}, 'outputs': {'responseContent': '姓名：张三 | 年龄：25'}, 'error': None, 'invokeId': 'e', 'parentInvokeId': 'questioner', 'executionId': '61546146-7098-42cd-b115-d20d235af829', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'e', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
WorkflowAgent 第二次输出结果 >>> type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': '姓名：张三 | 年龄：25'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

本示例涉及的流式数据帧包含调测信息的数据帧：

* type="tracer_workflow"：调测信息的数据帧。记录了工作流执行流程中涉及的各个组件的输入输出信息、执行开始/结束的时间等调测信息。由于本例中的工作流从上次执行的断点继续执行，且每个组件开始执行和结束执行又各产生一帧调测信息，故此类数据帧共有5帧。
