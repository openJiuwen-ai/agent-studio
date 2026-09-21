"""
智能工作流 (Smart Workflow - 天天盈)

完整流程：
开始 → 判断 → (continue==true → 提问器 → 意图识别 → 分支) / (default → 结束)

意图识别分支：
- branch_1 (感兴趣): 发短信 → 发送短信结束 → 代码_1_1 → 结束
- branch_0 (不确定/其他): 拒绝结束 → 代码 → 代码_1_1 → 结束

代码节点通过 MockCodeComponent 规避实现。
"""

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent

workflow_id = "5710b24a-490f-419a-96d4-7eff0da204be"
agent_id = "d4c90802-9243-4667-aaaa-e7ace9985b29"


class MockCodeComponent(WorkflowComponent):
    """
    Mock 代码组件，用于规避开源版本中不可用的代码节点。

    根据配置的默认输出值返回结果。
    """

    def __init__(self, conf: dict):
        super().__init__()
        self._default_outputs = conf.get("default_outputs", {})
        self._input_mapping = conf.get("input_mapping", {})

    def component_type(self) -> str:
        return "mock_code"

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        workflow_logger.debug(
            "MockCodeComponent invoke started",
            component_id=session.get_component_id(),
        )
        result = dict(self._default_outputs)
        if self._input_mapping and inputs:
            user_fields = inputs.get("userFields", {})
            for input_key, output_key in self._input_mapping.items():
                if input_key in user_fields:
                    result[output_key] = user_fields[input_key]
        workflow_logger.debug(
            "MockCodeComponent invoke completed",
            component_id=session.get_component_id(),
            outputs=result,
        )
        return {"userFields": result}


def create_smart_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建智能工作流（天天盈）

    完整结构:
    start -> branch -> (questioner -> intent_detection -> branches) / (mock_code_1_1 -> end)

    intent_detection branches:
    - branch_1 (感兴趣): message_sms -> message_sms_end -> mock_code_1_1 -> end
    - branch_0 (不确定): message_reject -> mock_code -> mock_code_1_1 -> end

    Returns:
        Workflow: 智能工作流实例
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="tiantianyingAgent517_1_1_2",
        version="0.6.0",
        description="517-GH智能外呼天天盈子Agent",
    )
    workflow = Workflow(workflow_card)

    start_conf = {
        "userFields": {
            "inputs": [
                {
                    "sourceType": "null",
                    "description": "客户ID",
                    "default_value": "",
                    "id": "dataId",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "话术选择结果",
                    "default_value": "",
                    "id": "huashu_result",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "xxx",
                    "default_value": "",
                    "id": "continue",
                    "type": "boolean",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "姓名",
                    "default_value": "",
                    "id": "name",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [
                {
                    "sourceType": "null",
                    "description": "客户ID",
                    "default_value": "",
                    "id": "dataId",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "话术选择结果",
                    "default_value": "",
                    "id": "huashu_result",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "null",
                    "description": "xxx",
                    "default_value": "",
                    "id": "continue",
                    "type": "boolean",
                    "required": False,
                },
                {
                    "sourceType": "null",
                    "description": "姓名",
                    "default_value": "",
                    "id": "name",
                    "type": "string",
                    "required": True,
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
        "preDefinedFields": {
            "inputs": [
                {
                    "schema": [
                        {
                            "storage_method": "auto",
                            "aging_level": "permanent",
                            "description": "xxx",
                            "default_value": "false",
                            "id": "is_inter1",
                            "type": "string",
                        },
                        {
                            "storage_method": "assignment",
                            "aging_level": "session",
                            "description": "",
                            "default_value": "false",
                            "id": "is_inter",
                            "type": "boolean",
                        },
                        {
                            "storage_method": "assignment",
                            "aging_level": "session",
                            "description": "",
                            "default_value": "",
                            "id": "action_after_completion",
                            "type": "string",
                        },
                    ],
                    "sourceType": "null",
                    "description": None,
                    "id": "memory",
                    "type": "object",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "schema": [
                        {
                            "storage_method": "auto",
                            "aging_level": "permanent",
                            "description": "xxx",
                            "default_value": "false",
                            "id": "is_inter1",
                            "type": "string",
                        },
                        {
                            "storage_method": "assignment",
                            "aging_level": "session",
                            "description": "",
                            "default_value": "false",
                            "id": "is_inter",
                            "type": "boolean",
                        },
                        {
                            "storage_method": "assignment",
                            "aging_level": "session",
                            "description": "",
                            "default_value": "",
                            "id": "action_after_completion",
                            "type": "string",
                        },
                    ],
                    "sourceType": "null",
                    "description": None,
                    "id": "memory",
                    "type": "object",
                    "required": True,
                }
            ],
        },
    }

    workflow.set_start_comp(
        "node_start",
        Start(start_conf),
        inputs_schema={"name": "", "huashu_result": "", "dataId": "", "continue": True},
    )

    branch_component = BranchComponent()
    branch_component.add_branch(
        "${node_start.userFields.continue} == True",
        ["node_1747193680786"],
        "node_1747663795634-if",
    )
    branch_component.add_branch("True", ["node_1752722330802"], "default")

    workflow.add_workflow_comp("node_1747663795634", branch_component, inputs_schema={})

    questioner_conf = {
        "model_name": "mock_model",
        "model_type": "Mock",
        "question_content": "#BDD#/本次致电，是邀请您体验我航'天天盈自动购买服务','天天盈'底层关联货币基金。您可设置自动购买频率及自动购买日，系统在约定购买日检索关联账户余额、计算购买金额并自动扣款购买天天盈。市场有风险，投资须谨慎。后续会有人工联系您介绍可以吗?",
        "with_chat_history": True,
        "extra_prompt_for_fields_extraction": "",
        "input_complement": False,
        "type_complement": "",
        "example_content": "",
        "rails_config": {},
        "extract_fields_from_response": False,
        "max_response": 3,
        "hyper_parameters": {"temperature": 0.2},
    }

    workflow.add_workflow_comp(
        "node_1747193680786", Questioner(questioner_conf), inputs_schema={}
    )

    intent_detection_conf = {
        "userFields": {"inputs": [], "outputs": []},
        "recallThreshold": 0.8,
        "chatHistoryMaxTurn": 0,
        "systemFields": {"inputs": [], "outputs": []},
        "enableKnowledge": False,
        "enableHistory": False,
        "overridable": False,
        "enableInput": True,
        "kg": {},
        "llm": {
            "model": {
                "modelName": "mock-model",
                "modelType": "Mock",
                "hyperParameters": {"temperature": 0.2},
                "extension": {
                    "api_key": "mock-api-key",
                    "api_base": "http://localhost:8080",
                },
            }
        },
        "branches": [
            {"catalog": "不确定，其他的意图", "id": "branch_0"},
            {"catalog": "感兴趣", "id": "branch_1"},
        ],
        "prompt": "你是一个功能分类器，你可以根据用户的请求提问，和相应的功能类别描述，选择正确的功能帮助用户解决问题。",
    }

    intent_detection = IntentDetection(intent_detection_conf)
    intent_detection.add_branch(
        "${node_1752918493583.classificationId} == 1",
        ["node_1747311246294"],
        "node_1752918493583_branch_1",
    )
    intent_detection.add_branch(
        "${node_1752918493583.classificationId} == 0",
        ["node_1747299525842"],
        "node_1752918493583_branch_0",
    )

    workflow.add_workflow_comp(
        "node_1752918493583",
        intent_detection,
        inputs_schema={"input": "${node_1747193680786.userFields.USER_RESPONSE}"},
    )

    message_sms_conf = {
        "template": "##",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "code",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "",
                    "id": "messageid",
                    "type": "string",
                    "required": True,
                },
                {
                    "sourceType": "input",
                    "description": "",
                    "id": "triggerNode",
                    "type": "string",
                    "required": True,
                },
            ],
            "outputs": [],
        },
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1747311246294",
        Message(message_sms_conf),
        inputs_schema={
            "userFields": {
                "code": "${node_start.userFields.dataId}",
                "messageid": "10101010",
                "triggerNode": "发送短信",
            }
        },
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    message_sms_end_conf = {
        "template": "#BDD#好的，请留意短信。",
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1747311022227",
        Message(message_sms_end_conf),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    message_reject_conf = {
        "template": "#BDD#好的。打扰了。",
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
    }

    workflow.add_workflow_comp(
        "node_1747299525842",
        Message(message_reject_conf),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    mock_code_conf = {"default_outputs": {"continue": True}, "input_mapping": {}}

    workflow.add_workflow_comp(
        "node_1747664673621",
        MockCodeComponent(mock_code_conf),
        inputs_schema={},
        comp_ability=[
            ComponentAbility.STREAM if is_streaming else ComponentAbility.INVOKE
        ],
    )

    mock_code_1_1_conf = {
        "default_outputs": {"continue": False},
        "input_mapping": {"code_continue": "continue"},
    }

    workflow.add_workflow_comp(
        "node_1752722330802",
        MockCodeComponent(mock_code_1_1_conf),
        inputs_schema={
            "userFields": {"code_continue": "${node_1747664673621.userFields.continue}"}
        },
    )

    end_conf = {
        "responseTemplate": "## 天天盈结束continue: {{temp}}",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "",
                    "id": "temp",
                    "type": "boolean",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "sourceType": "input",
                    "description": "",
                    "id": "continue",
                    "type": "boolean",
                    "required": True,
                }
            ],
        },
        "responseMode": "directResponse",
        "isStreamOut": True,
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={"temp": "${node_1752722330802.userFields.continue}"},
        response_mode="streaming" if is_streaming else "directResponse",
    )

    workflow.add_connection("node_start", "node_1747663795634")
    workflow.add_connection("node_1747193680786", "node_1752918493583")
    workflow.add_connection("node_1747311246294", "node_1747311022227")
    workflow.add_connection("node_1747311022227", "node_1752722330802")
    workflow.add_connection("node_1747299525842", "node_1747664673621")
    workflow.add_connection("node_1747664673621", "node_1752722330802")
    workflow.add_connection("node_1752722330802", "node_end")

    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


@pytest.mark.asyncio
async def test_smart_workflow():
    """
    测试智能工作流
    """
    workflow, workflow_id = create_smart_workflow(True)  # noqa: redefined-outer-name
    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []
    workflow_logger.info("=" * 50)
    workflow_logger.info("第一次请求：是本人")
    workflow_logger.info("=" * 50)
    async for chunk in workflow_wrapper.astream(
        query="",
        params={
            "global_variables": {
                "dataId": "test-data-id",
                "huashu_result": "test-huashu-result",
                "name": "测试用户",
                "continue": True,
                "sys": {
                    "conversationHistory": [],
                    "currentTime": "2024-01-01",
                    "userId": "test_user",
                    "conversationId": "3d29a10e-522c-4c74-a0cd-282160303328",
                },
            }
        },
        workflow_id=workflow_id,
        session_id="3d29a10e-522c-4c74-a0cd-282160303328",
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

    # ==================== 第二次请求：感兴趣 ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("第二次请求：感兴趣")
    workflow_logger.info("=" * 50)

    workflow_wrapper_resume = WorkflowWrapper()
    chunks_2 = []

    # 构建对话历史，包含第一次的交互（模拟 Handler 从 context_manager 获取的带 intent 历史）
    conversation_history = [
        {"role": "user", "content": "你好", "intent": [workflow_id]},
        {
            "role": "assistant",
            "content": "您好，这里是银行，请问你是tom先生吗？",
            "intent": [workflow_id],
        },
        {"role": "user", "content": "是本人", "intent": [workflow_id]},
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
                "conversationId": "3d29a10e-522c-4c74-a0cd-282160303328",
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
    resume_input.update(interrupt_node_id, "感兴趣")

    async for chunk in workflow_wrapper_resume.astream(
        query=resume_input,
        params=params_2,
        workflow_id=workflow_id,
        session_id="3d29a10e-522c-4c74-a0cd-282160303328",
        agent_id=agent_id,
    ):
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证第二次请求结果：工作流应该完成
    assert len(chunks_2) > 0
    workflow_logger.info(f"第二次请求完成，共收到 {len(chunks_2)} 个chunk")

    return chunks_1, chunks_2
