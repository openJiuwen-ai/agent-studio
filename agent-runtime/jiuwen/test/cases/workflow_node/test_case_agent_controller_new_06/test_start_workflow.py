"""
开始工作流 (Start Workflow)

根据 JSON 配置实现的工作流，包含以下节点：
- 开始节点
- 提问器节点
- 意图识别节点
- 结束节点

注意：code 组件已规避，end 组件固定 continue=True, age_temp=25
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

workflow_id = "dfac616f-95d5-425a-aa52-e5432f24624a"
agent_id = "d4c90802-9243-4667-aaaa-e7ace9985b29"
workflow_name = "xxxtest_3_2_1"


def create_start_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建开始工作流

    结构: start -> questioner -> intent_detection -> end
    code 组件已规避，end 组件固定 continue=True, age_temp=25

    Returns:
        Workflow: 开始工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="xxxtest_3_2_1",
        version="0.6.0",
        description="LL开始工作流",
    )
    workflow = Workflow(workflow_card)

    # 1. 配置开始节点
    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "名字",
                    "default_value": "",
                    "id": "name",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "感兴趣",
                    "default_value": "true",
                    "id": "continue",
                    "type": "boolean",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "年龄",
                    "default_value": "",
                    "id": "age",
                    "type": "integer",
                    "required": False,
                },
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "名字",
                    "default_value": "",
                    "id": "name",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "感兴趣",
                    "default_value": "true",
                    "id": "continue",
                    "type": "boolean",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "年龄",
                    "default_value": "",
                    "id": "age",
                    "type": "integer",
                    "required": False,
                },
            ],
        },
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "schema": [
                        {
                            "schema": {
                                "schema": [
                                    {
                                        "description": "角色",
                                        "id": "role",
                                        "type": "string",
                                    },
                                    {
                                        "description": "消息内容",
                                        "id": "content",
                                        "type": "string",
                                    },
                                ],
                                "id": "",
                                "type": "object",
                            },
                            "description": "会话历史消息",
                            "id": "conversationHistory",
                            "type": "array",
                        },
                        {
                            "description": "当前系统时间",
                            "id": "currentTime",
                            "type": "string",
                        },
                        {
                            "description": "使用该工作流的唯一标识",
                            "id": "userId",
                            "type": "string",
                        },
                        {
                            "description": "工作流对话id",
                            "id": "conversationId",
                            "type": "string",
                        },
                    ],
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "query",
                    "type": "string",
                    "required": True,
                },
                {
                    "schema": [
                        {
                            "schema": {
                                "schema": [
                                    {
                                        "description": "角色",
                                        "id": "role",
                                        "type": "string",
                                    },
                                    {
                                        "description": "消息内容",
                                        "id": "content",
                                        "type": "string",
                                    },
                                ],
                                "id": "",
                                "type": "object",
                            },
                            "description": "会话历史消息",
                            "id": "conversationHistory",
                            "type": "array",
                        },
                        {
                            "description": "当前系统时间",
                            "id": "currentTime",
                            "type": "string",
                        },
                        {
                            "description": "使用该工作流的唯一标识",
                            "id": "userId",
                            "type": "string",
                        },
                        {
                            "description": "工作流对话id",
                            "id": "conversationId",
                            "type": "string",
                        },
                    ],
                    "sourceType": "input",
                    "description": "系统变量",
                    "id": "sys",
                    "type": "object",
                    "required": True,
                },
            ],
        },
    }

    workflow.set_start_comp(
        "node_start", Start(start_conf), inputs_schema={"name": "Tom"}
    )

    # 2. 配置提问器节点
    questioner_conf = {
        "model_name": "mock_model",
        "model_type": "Mock",
        "hyper_parameters": {"temperature": 0.2},
        "question_content": "您好，这里是银行，请问你是{{name}}先生吗？",
        "with_chat_history": True,
        "extract_fields_from_response": False,
        "max_response": 10,
        "key_fields": [
            {
                "field_name": "name",
                "description": "用户名字",
                "type": "string",
                "required": True,
            }
        ],
    }

    workflow.add_workflow_comp(
        "node_1747663017657",
        Questioner(questioner_conf),
        inputs_schema={"name": "${node_start.userFields.name}"},
    )

    # 3. 配置意图识别节点
    intent_conf = {
        "branches": [
            {"catalog": "不确定，其他的意图", "id": "branch_0"},
            {"catalog": "是本人", "id": "branch_1"},
        ],
        "llm": {
            "model": {
                "modelName": "mock_model",
                "modelType": "Mock",
                "hyperParameters": {"temperature": 0.2},
                "extension": {
                    "api_key": "mock-api-key",
                    "api_base": "mock-api-base",
                    "verify_ssl": False,
                },
            }
        },
        "kg": {},
        "chatHistoryMaxTurn": 0,
        "enableKnowledge": False,
        "enableHistory": False,
        "overridable": False,
        "enableInput": True,
        "prompt": "你是一个功能分类器，你可以根据用户的请求提问，和相应的功能类别描述，选择正确的功能帮助用户解决问题。",
    }

    intent_component = IntentDetection(intent_conf)
    intent_component.add_branch(
        "${node_1752919177920.classificationId} == 0", ["node_end"], "branch_0"
    )
    intent_component.add_branch(
        "${node_1752919177920.classificationId} == 1", ["node_end"], "branch_1"
    )

    workflow.add_workflow_comp(
        "node_1752919177920",
        intent_component,
        inputs_schema={"input": "${node_1747663017657.userFields.USER_RESPONSE}"},
    )

    # 4. 配置结束节点
    # 固定 continue=True, age_temp=25
    end_conf = {
        "responseTemplate": "##开始工作流 continue：{{continue}};age_temp: {{age_temp}}，age改为 10",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "continue",
                    "type": "boolean",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "age_temp",
                    "type": "integer",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "",
                    "id": "age",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "continue",
                    "type": "boolean",
                    "value": "${node_1752717342114.userFields.continue}",
                    "required": True,
                },
            ],
        },
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"continue": True, "age_temp": 25},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 5. 添加连接
    workflow.add_connection("node_start", "node_1747663017657")
    workflow.add_connection("node_1747663017657", "node_1752919177920")

    # 6. 注册工作流到 Runner
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_start_workflow_interrupt():
    """
    测试开始工作流的中断处理

    第一次请求：发送"你好"，提问器会中断等待用户回复
    第二次请求：发送"是本人"，工作流继续执行到结束节点
    """
    workflow, workflow_id = create_start_workflow(True)  # noqa: redefined-outer-name
    session_id = "2f9c8dea-a5e2-467b-a9e1-b28c8ec968dc"

    # ==================== 第一次请求：你好 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：你好")
    workflow_logger.info("=" * 50)

    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    # 模拟 Handler 的 prepare_workflow_params() 传入的参数：
    # conversation_history 由 Handler 从 context_manager 获取（包含 intent），CONTROLLER_MODE_SWITCH=True
    params_1 = {
        "global_variables": {
            "name": "tom",
            "age": 25,
            "continue": True,
            "sys": {
                "conversationHistory": [],
                "currentTime": "2024-01-01",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        "conversation_history": [
            {"role": "user", "content": "你好", "intent": [workflow_name]}
        ],
        "CONTROLLER_MODE_SWITCH": True,
    }

    async for chunk in workflow_wrapper.astream(
        query="你好",
        params=params_1,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    # 验证第一次请求结果：提问器应该中断
    assert len(chunks_1) > 0
    # 检查是否有中断信号：WorkflowWrapper 不再返回 Message(WORKFLOW_INTERRUPT)，
    # 而是通过 StreamData.data.should_interrupt=True 标记，由 Handler 检测并生成中断消息
    has_interrupt = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_1
    )
    workflow_logger.info(f"第一次请求是否中断: {has_interrupt}")
    assert has_interrupt is True

    # ==================== 第二次请求：是本人 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：是本人")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

    # 构建对话历史，包含第一次的交互（模拟 Handler 从 context_manager 获取的带 intent 历史）
    conversation_history = [
        {"role": "user", "content": "你好", "intent": [workflow_name]},
        {
            "role": "assistant",
            "content": "您好，这里是银行，请问你是tom先生吗？",
            "intent": [workflow_name],
        },
        {"role": "user", "content": "是本人", "intent": [workflow_name]},
    ]

    params_2 = {
        "global_variables": {
            "name": "tom",
            "age": 25,
            "continue": True,
            "sys": {
                "conversationHistory": conversation_history,
                "currentTime": "2024-01-01",
                "userId": "test_user",
                "conversationId": session_id,
            },
        },
        "conversation_history": conversation_history,
        "CONTROLLER_MODE_SWITCH": True,
    }

    # 从第一次请求的中断 chunk 中提取 node_id
    interrupt_node_id = None
    for chunk in chunks_1:
        if (
            hasattr(chunk, "data")
            and isinstance(chunk.data, dict)
            and chunk.data.get("should_interrupt", False)
        ):
            interrupt_node_id = chunk.data.get("node_id")
            break
    assert interrupt_node_id is not None, "未找到中断节点的 node_id"

    # 构建中断恢复的 InteractiveInput，精确路由到中断节点
    resume_input = InteractiveInput()
    resume_input.update(interrupt_node_id, "是本人")

    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
        params=params_2,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
    ):
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果：工作流应该完成
    assert len(chunks_2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks_2)} 个chunk")

    return chunks_1, chunks_2
