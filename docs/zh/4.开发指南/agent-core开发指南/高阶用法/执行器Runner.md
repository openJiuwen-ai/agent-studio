Runner是openJiuwen执行所有核心组件（包括Workflow，Agent，AgentGroup和Tool）的统一入口和控制中心。它将复杂的执行逻辑抽象化，为开发者提供了一个简洁、一致且强大的编程接口。
Runner的主要功能包括：
- 提供Agent标准的异步调用（invoke）和异步流式调用（stream）两种执行入口。
- 提供Workflow标准的异步调用（invoke）和异步流式调用（stream）两种执行入口。
- 提供Tool标准的异步调用（invoke）和异步流式调用（stream）两种执行入口。
- 提供AgentGroup标准的异步调用（invoke）和异步流式调用（stream）两种执行入口。


## Agent执行

Runner支持所有Agent的单次输出执行和流式输出执行，包括ReActAgent、WorkflowAgent等内置Agent的执行，也包括用户自定义的Agent的执行。

下面以一个`WorkflowAgent`为例，介绍通过`Runner`执行`Agent`的过程。

首先，创建一个WorkflowAgent实例：
```python
from openjiuwen.agent.common.enum import ControllerType
from openjiuwen.agent.common.schema import WorkflowSchema
from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.runner.runner import resource_mgr
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

def create_agent():
   # 创建工作流flow, 将flow注册到资源管理器
   flow = Workflow(workflow_config=WorkflowConfig(
       metadata=WorkflowMetadata(id="workflow_id", version="1", name="简单工作流",
                                 description="this_is_a_demo")))
   flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
   flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
   flow.add_connection("start", "end")

   resource_mgr.workflow().add_workflow("workflow_id_1", flow)

   # 创建Agent
   workflow_agent_config = WorkflowAgentConfig(id="agent_id", version="1", description="this_is_a_demo",
                                               workflows=[WorkflowSchema(
                                                   id="workflow_id",
                                                   version="1",
                                                   name="简单工作流",
                                                   description="this_is_a_demo",
                                                   inputs={"query": {"type": "string"}},
                                               )],
                                               controller_type=ControllerType.WorkflowController
                                               )
   agent = WorkflowAgent(agent_config=workflow_agent_config)
   return agent

agent = create_agent()
```
然后，调用`Runner`的`run_agent`接口直接运行WorkflowAgent:
```python
import asyncio
from openjiuwen.core.runner.runner import Runner

print(asyncio.run(Runner.run_agent(agent=agent, inputs={"conversion_id": "id1", "query": "哈哈"})))
```
执行结果：
```python
{'output': WorkflowOutput(result={'output': {'result': '哈哈'}}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
```

## Workflow执行

Runner支持Workflow的单次输出执行和流式输出执行。

下面通过构建一个简单工作流为例，介绍`Runner`执行`Workflow`的过程。

首先，创建一个Workflow:
```python
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata

def build_workflow(name, workflow_id, version):
    flow = Workflow(workflow_config=WorkflowConfig(
        metadata=WorkflowMetadata(id=workflow_id, version=version, name=name,
                                  description="this_is_a_demo")))
    flow.set_start_comp("start", Start(), inputs_schema={"query": "${query}"})
    flow.set_end_comp("end", End(), inputs_schema={"result": "${start.query}"})
    flow.add_connection("start", "end")
    return flow

workflow = build_workflow("test_workflow", "test_workflow", "1")
```

然后，调用`Runner`的`run_workflow`直接运行`Workflow`：
```python
import asyncio
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.runtime.workflow import WorkflowRuntime

result = asyncio.run(Runner.run_workflow(workflow=workflow, inputs={"query": "query workflow"}, runtime=WorkflowRuntime()))
print(result)
```
执行结果：
```python
result={'output': {'result': 'query workflow'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

## Tool执行

Runner支持所有Tool的单次输出执行和流式输出执行，不仅包括内置的`RestfulApi`和`LocalFunction`，也支持用户自定义的任何Tool的执行。

下面构建一个用于加法计算的`LocalFunction`工具为例，介绍通过`Runner`执行`Tool`的过程。

首先，创建一个Tool：
```python
from openjiuwen.core.utils.tool.function.function import LocalFunction, Param

# 创建本地工具
add_plugin = LocalFunction(
    name="add",
    description="加法",
    params=[
        Param(name="a", description="加数", type="number", required=True),
        Param(name="b", description="被加数", type="number", required=True),
    ],
    func=lambda a, b: a + b
)
```
然后，使用`Runner`的`run_tool`执行工具：
```python
import asyncio
from openjiuwen.core.runner.runner import Runner

print(asyncio.run(Runner.run_tool(tool=add_plugin, inputs={'a':1, 'b':2})))
```
最后，执行结果：
```python
3
```

## AgentGroup执行

AgentGroup是用于管理多个智能体协作的核心组件。Runner支持AgentGroup的单次输出执行和流式输出执行。

下面以一个用于银行服务的`HierarchicalGroup`为例，介绍如何通过`Runner`执行`AgentGroup`。

首先，分别创建用于转账服务、余额查询和理财服务的三个`WorkflowAgent`，然后创建`HierarchicalGroup`，并将三个`WorkflowAgent`绑定到`HierarchicalGroup`中。

```python
import os

from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
from openjiuwen.core.component.end_comp import End
from openjiuwen.core.component.start_comp import Start
from openjiuwen.core.workflow.base import Workflow
from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
from openjiuwen.core.component.common.configs.model_config import ModelConfig
from openjiuwen.core.utils.llm.base import BaseModelInfo
from openjiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
from openjiuwen.agent.config.base import AgentConfig
from openjiuwen.agent_group.hierarchical_group.agents.main_controller import HierarchicalMainController
from openjiuwen.core.agent.agent import ControllerAgent
from openjiuwen.agent_group.hierarchical_group import (
    HierarchicalGroup,
    HierarchicalGroupConfig
)

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

config = HierarchicalGroupConfig(
    group_id="financial_group",
    leader_agent_id="main_controller"
)
hierarchical_group = HierarchicalGroup(config)


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
```

然后，启动Runner，并执行AgentGroup。

```python
import asyncio
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.agent.message.message import Message

asyncio.run(Runner.start())

conversation_id = "session_001"
hierarchical_group.group_controller.subscribe("test_query1", ["transfer_agent"])
message1 = Message.create_user_message(
    content="给张三转账",
    conversation_id=conversation_id
)
# 广播消息给所有订阅 test_query1主题的agent
message1.message_type = "test_query1"
result1 = asyncio.run(Runner.run_agent_group(hierarchical_group, message1))
print(result1)

asyncio.run(Runner.stop())
```

最终获得输出：
```python
[OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供转账金额（数字）相关的信息'))]
```
