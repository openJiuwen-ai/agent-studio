多Agent是openJiuwen框架为应对复杂任务场景设计的核心机制。当任务涉及多维度专业能力、需分步骤协同推进，或单一Agent难以覆盖全流程处理需求时，多Agent控制架构可通过合理的任务拆解，将不同模块分配给具备对应专业能力的Agent，借助Agent间的协同配合实现整体目标，最终达成高效协同、灵活响应的能力。
例如在金融转账场景中，当用户发起“我想转账”的请求时，系统通过意图识别自动匹配转账服务Agent并启动转账工作流；若检测到用户未提供金额参数，将触发工作流中断并向用户发起金额询问；待用户反馈具体金额后，系统会自动检测到有中断的Agent并恢复，持续推进转账全流程执行。

# 多Agent构建与执行流程

多Agent通过`HierarchicalGroup`实现系统管理和执行，能够对用户的查询进行意图识别，自动选择合适的Agent支持任务，也可以指定某个Agent来执行任务并支持Agent间的跳转与恢复。
多Agent的开发流程分为以下几步：

* 创建`WorkflowAgent`：创建`WorkflowAgent`智能体对象，然后根据场景需要为智能体绑定相关工作流。
* 创建`HierarchicalGroup`：先通过`ControllerAgent`初始化一个Leader Agent（作为整个多Agent系统的入口），再将该Leader Agent与先前创建的所有`WorkflowAgent`实例绑定到`HierarchicalGroup`中。
* 运行多Agent：多Agent场景支持批/流式调用。此外，任务执行提供灵活的调度策略：除支持多Agent自主选择合适的Agent执行任务外，还可直接指定特定Agent完成目标任务，或通过订阅消息广播机制触发相关Agent协同执行。

## 创建WorkflowAgent

用户可根据场景需要创建多个`WorkflowAgent`对象，并为每个对象绑定相关工作流。参考[构建工作流](../工作流/构建工作流.md)，[构建WorkflowAgent](../智能体/构建WorkflowAgent.md)

```python
import os
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.questioner_comp import (
    FieldInfo,
    QuestionerComponent,
    QuestionerConfig
)
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    """创建模型配置"""
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=120,
        ),
    )

def _create_start_component():
    """创建 Start 组件"""
    return Start({
        "inputs": [
            {
                "id": "query",
                "type": "String",
                "required": "true",
                "sourceType": "ref"
            }
        ]
    })


def _build_financial_workflow(
        workflow_id: str,
        workflow_name: str,
        workflow_desc: str,
        field_name: str,
        field_desc: str
) -> Workflow:
    """
    构建金融业务工作流（带中断节点）

    Args:
        workflow_id: 工作流ID
        workflow_name: 工作流名称
        workflow_desc: 工作流描述
        field_name: 提问字段名
        field_desc: 提问字段描述

    Returns:
        Workflow: 包含 start -> questioner -> end 的工作流
    """
    workflow_config = WorkflowConfig(
        metadata=WorkflowMetadata(
            name=workflow_name,
            id=workflow_id,
            version="1.0",
            description=workflow_desc,
        )
    )
    flow = Workflow(workflow_config=workflow_config)

    # 创建组件
    start = _create_start_component()

    # 创建提问器（中断节点）
    key_fields = [
        FieldInfo(
            field_name=field_name,
            description=field_desc,
            required=True
        ),
    ]
    model_config = _create_model_config()
    questioner_config = QuestionerConfig(
        model=model_config,
        question_content="",
        extract_fields_from_response=True,
        field_names=key_fields,
        with_chat_history=False,
    )
    questioner = QuestionerComponent(questioner_config)

    # End 组件
    end = End({"responseTemplate": f"{workflow_name}完成: {{{{{field_name}}}}}"})

    # 注册组件
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
    flow.add_workflow_comp(
        "questioner", questioner, inputs_schema={"query": "${start.query}"}
    )
    flow.set_end_comp(
        "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
    )

    # 连接拓扑: start -> questioner -> end
    flow.add_connection("start", "questioner")
    flow.add_connection("questioner", "end")

    return flow

def _create_workflow_agent(
        agent_id: str,
        description: str,
        workflow: Workflow
) -> WorkflowAgent:
    """创建 WorkflowAgent"""
    config = WorkflowAgentConfig(
        id=agent_id,
        version="1.0",
        description=description,
        workflows=[],
        model=_create_model_config(),
    )
    agent = WorkflowAgent(config)
    agent.add_workflows([workflow])
    return agent

# 创建金融业务工作流
transfer_workflow = _build_financial_workflow(
    workflow_id="transfer_flow",
    workflow_name="转账服务",
    workflow_desc="处理用户转账请求，支持转账到指定账户",
    field_name="amount",
    field_desc="转账金额（数字）"
)

balance_workflow = _build_financial_workflow(
    workflow_id="balance_flow",
    workflow_name="余额查询",
    workflow_desc="查询用户账户余额信息",
    field_name="account",
    field_desc="账户号码"
)

invest_workflow = _build_financial_workflow(
    workflow_id="invest_flow",
    workflow_name="理财服务",
    workflow_desc="提供理财产品推荐和购买服务",
    field_name="product",
    field_desc="理财产品名称"
)

# 创建 WorkflowAgent
transfer_agent = _create_workflow_agent(
    agent_id="transfer_agent",
    description="转账服务，处理用户的转账请求",
    workflow=transfer_workflow
)

balance_agent = _create_workflow_agent(
    agent_id="balance_agent",
    description="余额查询服务，查询用户账户余额",
    workflow=balance_workflow
)

invest_agent = _create_workflow_agent(
    agent_id="invest_agent",
    description="理财服务，提供理财产品推荐和购买",
    workflow=invest_workflow
)
```

## 创建HierarchicalGroup
`HierarchicalGroup`采用Leader-Worker架构的多Agent模式，开箱即用，内置一个Leader Agent与多个Worker Agent。
- Leader Agent：外部消息默认路由到Leader Agent，由Leader Agent将消息分发给对应Worker Agent
- Worker Agent：执行Leader Agent分配的任务

用户可根据具体场景，创建一个`HierarchicalGroup`对象来处理复杂的任务，并将上面创建的工作流智能体添加到创建好的`HierarchicalGroup`对象中。注意，在添加智能体时，必须首先添加Leader Agent。

```python
from openjiuwen.agent_group.hierarchical_group import (
    HierarchicalGroup,
    HierarchicalGroupConfig
)

config = HierarchicalGroupConfig(
    group_id="financial_group",
    leader_agent_id="main_controller"
)
hierarchical_group = HierarchicalGroup(config)
```
### 创建Leader Agent
Leader Agent是持有`HierarchicalMainController`的`ControllerAgent`，创建`HierarchicalGroup`必须要指定对应Leader Agent。`HierarchicalMainController`作为控制器，负责意图识别和任务分发，`HierarchicalGroup`默认会将消息直接路由到Leader Agent，基于LLM识别下一步处理的agent，然后将消息转发给对应的agent处理。
```python
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController
from openjiuwen.core.agent.agent import ControllerAgent

main_config = AgentConfig(
    id="main_controller",
    description="金融服务主控制器，识别用户意图并分发任务"
)
main_controller = HierarchicalMainController()
main_agent = ControllerAgent(main_config, controller=main_controller)
```

### 添加所有子agent
使用`add_agent`添加所有子`Agents`（Leader Agent和Worker Agents）到`Group`，完成`HierarchicalGroup`实例创建。

```python
# 添加所有 agent 到 group
hierarchical_group.add_agent("main_controller", main_agent)
hierarchical_group.add_agent("transfer_agent", transfer_agent)
hierarchical_group.add_agent("balance_agent", balance_agent)
hierarchical_group.add_agent("invest_agent", invest_agent)
```

## 运行多Agent
多Agent支持批调用和流式调用，同时提供3种消息路由方式。
### 消息路由
多Agent默认会根据用户的输入默认选择绑定的Agent来执行任务。也可以通过广播订阅和点对点调用的方式执行Agent执行任务。其中，点对点通信优先级最高，广播其次，默认路由到LeaderAgent消息处理。
#### 广播订阅
多Agent支持让绑定的Agent订阅主题，当输入的消息携带主题信息时，相关Agent会接收到消息并处理。
```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_001"
hierarchical_group.group_controller.subscribe("test_query1", ["transfer_agent"])
message1 = Message.create_user_message(
    content="给张三转账",
    conversation_id=conversation_id
)
# 广播消息给所有订阅 test_query1主题的agent
message1.message_type = "test_query1"
result1 = asyncio.run(hierarchical_group.invoke(message1))
print(result1)
```
预期输出
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供转账金额（数字）相关的信息'))]
```
#### 点对点通信
多Agent支持点对点的调用绑定的Agent处理相关消息。

```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_002"
message2 = Message.create_user_message(
    content="给张三转账",
    conversation_id=conversation_id
)
# receiver_id会指定绑定到group的agent_id对应的Agent执行任务
message2.receiver_id = "transfer_agent"
result2 = asyncio.run(hierarchical_group.invoke(message2))
print(result2)
```
预期输出
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供转账金额（数字）相关的信息'))]
```

#### 默认路由到Leader Agent
不指定消息路由方式，默认会直接将消息发送给LeaderAgent处理。

```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_003"
message3 = Message.create_user_message(
    content="给张三转账",
    conversation_id=conversation_id
)
result3 = asyncio.run(hierarchical_group.invoke(message3))
print(result3)
```
预期输出
```
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供转账金额（数字）相关的信息'))]
```

### 批调用
多Agent直接返回最终消息结果。
```python
from openjiuwen.core.agent.message.message import Message
import asyncio

conversation_id = "session_test"
message = Message.create_user_message(
    content="给张三转账500元",
    conversation_id=conversation_id,
)
# 批调用
result = asyncio.run(hierarchical_group.invoke(message))
print(result)
```
预期返回
```
{'output': WorkflowOutput(result={'responseContent': '转账服务完成: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

### 流式调用
多Agent支持流式返回中间结果。
```python
import asyncio
from openjiuwen.core.agent.message.message import Message

async def main():
    message = Message.create_user_message(
        content="给张三转账500元",
        conversation_id="stream_session_test"
    )

    # 流式调用
    async for chunk in hierarchical_group.stream(message):
        print(f"输出结果：{chunk}")

if __name__ == "__main__":
    asyncio.run(main())
```
预期返回
```
输出结果：type='tracer_agent' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167499), 'endTime': None, 'inputs': {'inputs': {'query': '给张三转账500元'}}, 'outputs': None, 'error': None, 'invokeId': '3f309daf-b9cb-40ca-b918-4aa738e534fd', 'parentInvokeId': 'b8127943-24af-4f89-8097-18cb3caf2e2f', 'childInvokes': [], 'invokeType': 'workflow', 'name': '转账服务', 'elapsedTime': None, 'metaData': {'class_name': '转账服务', 'type': 'workflow', 'metadata': {'name': '转账服务', 'id': 'transfer_flow', 'version': '1.0', 'description': '处理用户转账请求，支持转账到指定账户'}}}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 168923), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169086), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'query': '给张三转账500元'}, 'error': None, 'invokeId': 'start', 'parentInvokeId': 'transfer_flow', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'start', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': None, 'inputs': {'query': '给张三转账500元'}, 'outputs': None, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 169679), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 750914), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'amount': 500}, 'error': None, 'invokeId': 'questioner', 'parentInvokeId': 'start', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'questioner', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': None, 'inputs': {'amount': 500}, 'outputs': None, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'start', 'parentNodeId': ''}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752452), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 752861), 'inputs': {'amount': 500}, 'outputs': {'responseContent': '转账服务完成: 500'}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'end', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='end node stream' index=0 payload={'answer': '转账服务完成: 500'}
输出结果：type='tracer_workflow' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167805), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 754020), 'inputs': {'query': '给张三转账500元'}, 'outputs': {'responseContent': '转账服务完成: 500'}, 'error': None, 'invokeId': 'transfer_flow', 'parentInvokeId': None, 'executionId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'onInvokeData': [], 'componentId': '', 'componentName': '', 'componentType': 'transfer_flow', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
输出结果：type='tracer_agent' payload={'traceId': '78e2562a-dbbe-48a4-b9ef-6be622f6df69', 'startTime': datetime.datetime(2025, 12, 9, 15, 34, 41, 167499), 'endTime': datetime.datetime(2025, 12, 9, 15, 34, 44, 766519), 'inputs': {'inputs': {'query': '给张三转账500元'}}, 'outputs': {'outputs': [{'type': 'end node stream', 'index': 0, 'payload': {'answer': '转账服务完成: 500'}}, {'type': 'workflow_final', 'index': 0, 'payload': {'responseContent': '转账服务完成: 500'}}]}, 'error': None, 'invokeId': '3f309daf-b9cb-40ca-b918-4aa738e534fd', 'parentInvokeId': 'b8127943-24af-4f89-8097-18cb3caf2e2f', 'childInvokes': [], 'invokeType': 'workflow', 'name': '转账服务', 'elapsedTime': '3.60s', 'metaData': {'class_name': '转账服务', 'type': 'workflow', 'metadata': {'name': '转账服务', 'id': 'transfer_flow', 'version': '1.0', 'description': '处理用户转账请求，支持转账到指定账户'}}}
输出结果：type='workflow_final' index=0 payload={'output': WorkflowOutput(result={'responseContent': '转账服务完成: 500'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

# 完整示例代码

```python
import os
import asyncio

from openjiuwen.core.agent.message.message import Message
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.agent.agent import ControllerAgent
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.questioner_comp import (
    FieldInfo,
    QuestionerComponent,
    QuestionerConfig
)
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
from openjiuwen.agent_group.hierarchical_group import (
    HierarchicalGroup,
    HierarchicalGroupConfig
)
from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController

API_BASE = os.getenv("API_BASE", "your api base")
API_KEY = os.getenv("API_KEY", "your api key")
MODEL_NAME = os.getenv("MODEL_NAME", "")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")


def _create_model_config() -> ModelConfig:
    """创建模型配置"""
    return ModelConfig(
        model_provider=MODEL_PROVIDER,
        model_info=BaseModelInfo(
            model=MODEL_NAME,
            api_base=API_BASE,
            api_key=API_KEY,
            temperature=0.7,
            top_p=0.9,
            timeout=120,
        ),
    )

def _create_start_component():
    """创建 Start 组件"""
    return Start({
        "inputs": [
            {
                "id": "query",
                "type": "String",
                "required": "true",
                "sourceType": "ref"
            }
        ]
    })


def _build_financial_workflow(
        workflow_id: str,
        workflow_name: str,
        workflow_desc: str,
        field_name: str,
        field_desc: str
) -> Workflow:
    """
    构建金融业务工作流（带中断节点）

    Args:
        workflow_id: 工作流ID
        workflow_name: 工作流名称
        workflow_desc: 工作流描述
        field_name: 提问字段名
        field_desc: 提问字段描述

    Returns:
        Workflow: 包含 start -> questioner -> end 的工作流
    """
    workflow_config = WorkflowConfig(
        metadata=WorkflowMetadata(
            name=workflow_name,
            id=workflow_id,
            version="1.0",
            description=workflow_desc,
        )
    )
    flow = Workflow(workflow_config=workflow_config)

    # 创建组件
    start = _create_start_component()

    # 创建提问器（中断节点）
    key_fields = [
        FieldInfo(
            field_name=field_name,
            description=field_desc,
            required=True
        ),
    ]
    model_config = _create_model_config()
    questioner_config = QuestionerConfig(
        model=model_config,
        question_content="",
        extract_fields_from_response=True,
        field_names=key_fields,
        with_chat_history=False,
    )
    questioner = QuestionerComponent(questioner_config)

    # End 组件
    end = End({"responseTemplate": f"{workflow_name}完成: {{{{{field_name}}}}}"})

    # 注册组件
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
    flow.add_workflow_comp(
        "questioner", questioner, inputs_schema={"query": "${start.query}"}
    )
    flow.set_end_comp(
        "end", end, inputs_schema={field_name: f"${{questioner.{field_name}}}"}
    )

    # 连接拓扑: start -> questioner -> end
    flow.add_connection("start", "questioner")
    flow.add_connection("questioner", "end")

    return flow

def _create_workflow_agent(
        agent_id: str,
        description: str,
        workflow: Workflow
) -> WorkflowAgent:
    """创建 WorkflowAgent"""
    config = WorkflowAgentConfig(
        id=agent_id,
        version="1.0",
        description=description,
        workflows=[],
        model=_create_model_config(),
    )
    agent = WorkflowAgent(config)
    agent.add_workflows([workflow])
    return agent

# 创建金融业务工作流
transfer_workflow = _build_financial_workflow(
    workflow_id="transfer_flow",
    workflow_name="转账服务",
    workflow_desc="处理用户转账请求，支持转账到指定账户",
    field_name="amount",
    field_desc="转账金额（数字）"
)

balance_workflow = _build_financial_workflow(
    workflow_id="balance_flow",
    workflow_name="余额查询",
    workflow_desc="查询用户账户余额信息",
    field_name="account",
    field_desc="账户号码"
)

invest_workflow = _build_financial_workflow(
    workflow_id="invest_flow",
    workflow_name="理财服务",
    workflow_desc="提供理财产品推荐和购买服务",
    field_name="product",
    field_desc="理财产品名称"
)

# 创建 WorkflowAgent
transfer_agent = _create_workflow_agent(
    agent_id="transfer_agent",
    description="转账服务，处理用户的转账请求",
    workflow=transfer_workflow
)

balance_agent = _create_workflow_agent(
    agent_id="balance_agent",
    description="余额查询服务，查询用户账户余额",
    workflow=balance_workflow
)

invest_agent = _create_workflow_agent(
    agent_id="invest_agent",
    description="理财服务，提供理财产品推荐和购买",
    workflow=invest_workflow
)

# 创建 HierarchicalGroup
config = HierarchicalGroupConfig(
    group_id="financial_group",
    leader_agent_id="main_controller"
)
hierarchical_group = HierarchicalGroup(config)

# 创建主 agent（HierarchicalMainController）
main_config = AgentConfig(
    id="main_controller",
    description="金融服务主控制器，识别用户意图并分发任务"
)
main_controller = HierarchicalMainController()
main_agent = ControllerAgent(main_config, controller=main_controller)

# 添加所有 agent 到 group
hierarchical_group.add_agent("main_controller", main_agent)
hierarchical_group.add_agent("transfer_agent", transfer_agent)
hierarchical_group.add_agent("balance_agent", balance_agent)
hierarchical_group.add_agent("invest_agent", invest_agent)

async def main():
    message = Message.create_user_message(
        content="给张三转账500元",
        conversation_id="stream_session_test"
    )

    # 流式调用
    async for chunk in hierarchical_group.stream(message):
        print(f"输出结果：{chunk}")

if __name__ == "__main__":
    asyncio.run(main())
```
