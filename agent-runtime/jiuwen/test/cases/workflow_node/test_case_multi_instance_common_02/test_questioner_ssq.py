"""
提问器-ssq 工作流 (Questioner-ssq Workflow)

根据 questioner_ssq.json 配置实现的工作流，包含以下节点：
- node_start: 开始节点
- node_5d8bd3c331a04: 提问器节点
- node_end: 结束节点

工作流功能：
1. 接收用户输入，通过提问器收集以下字段：
   - tel: 电话号码
   - time: 故障发生时间
   - switch: 移动开关
   - signals: 车机端显示信号
   - flow_rate: 车机端剩余流量
2. 收集完成后，通过结束节点输出收集到的信息

测试要点：
- 验证提问器多轮中断/恢复机制，以及字段收集完成后到达 End 节点的完整流程
- R1: 首次提问 → 中断（询问所有 5 个字段）
- R2: 恢复，提供部分信息 → 仍缺 4 字段 → 再次中断
- R3: 恢复，提供剩余信息 → 全部收集完成 → 到达 End 节点 → 输出模板结果
"""

import os

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.questioner import Questioner, FieldInfo
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.message_converter import WorkflowMessageConverter
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner.runner import Runner
from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
from openjiuwen.core.workflow import Workflow
from openjiuwen.core.workflow.base import WorkflowCard

# 设置环境变量
os.environ.setdefault("LLM_API_KEY", "mock-api-key-for-testing")
os.environ.setdefault("LLM_API_BASE", "https://api.siliconflow.cn/v1")
os.environ.setdefault("LLM_VERIFY_SSL", "False")

workflow_id = "117c6695dcd9139726dce28c83abe0e671ea76b4be270599"
agent_id = "0b34fea30e2a41b5af35b9b375edab99"


def create_questioner_ssq_workflow(is_streaming: bool = True) -> tuple[Workflow, str]:
    """
    创建提问器-ssq工作流

    结构: node_start -> node_5d8bd3c331a04 -> node_end

    Returns:
        Workflow: 工作流实例
        workflow_id: 工作流ID
    """
    workflow_card = WorkflowCard(
        id=workflow_id,
        name="提问器-ssq",
        version="0.6.0",
        description="自动化用例_ssq\n2024-09-24_14:44:41\n提问器，questioner，common_1727160281.871243\n\n车机故障\n电话号码是10000，故障发生在十点，移动开关开启，车机端有显示信号，车机端有剩余流量",
    )
    workflow = Workflow(workflow_card)

    # 1. 配置开始节点
    start_conf = {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "id": "query",
                    "type": "string",
                    "required": True,
                    "sourceType": "input",
                }
            ],
            "outputs": [{"id": "query", "type": "string", "description": "用户输入"}],
        },
    }

    workflow.set_start_comp("node_start", Start(start_conf), inputs_schema={})

    # 2. 配置提问器节点
    questioner_conf = {
        "model_name": "mock_model_name",
        "model_type": "Mock",
        "hyper_parameters": {"temperature": 0, "top_p": 0.9},
        "extra_prompt_for_fields_extraction": "",
        "prompt_template": None,
        "rails_config": None,
        "question_content": "",
        "input_complement": False,
        "with_chat_history": True,
        "extract_fields_from_response": True,
        "max_response": 3,
        "type_complement": "",
        "key_fields": [
            FieldInfo(
                field_name="tel",
                description="电话号码",
                cn_field_name="电话号码",
                required=True,
                type="string",
            ),
            FieldInfo(
                field_name="time",
                description="故障发生时间",
                cn_field_name="故障发生时间",
                required=True,
                type="string",
            ),
            FieldInfo(
                field_name="switch",
                description="移动开关",
                cn_field_name="移动开关",
                required=True,
                type="string",
            ),
            FieldInfo(
                field_name="signals",
                description="车机端显示信号",
                cn_field_name="车机端显示信号",
                required=True,
                type="string",
            ),
            FieldInfo(
                field_name="flow_rate",
                description="剩余流量",
                cn_field_name="剩余流量",
                required=True,
                type="string",
            ),
        ],
    }

    workflow.add_workflow_comp(
        "node_5d8bd3c331a04",
        Questioner(questioner_conf),
        inputs_schema={"input": "${node_start.systemFields.query}"},
    )

    # 3. 配置结束节点
    end_conf = {
        "responseTemplate": "电话号码：{{tel}}，故障发生时间：{{time}}，移动开关开启状态：{{switch}}，车机端信号状态：{{signals}}，车机端剩余流量：{{flow_rate}}",
        "responseMode": "directResponse",
        "isStreamOut": True,
        "userFields": {
            "inputs": [
                {"id": "tel", "type": "string", "required": True, "sourceType": "ref"},
                {"id": "time", "type": "string", "required": True, "sourceType": "ref"},
                {
                    "id": "switch",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                },
                {
                    "id": "signals",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                },
                {
                    "id": "flow_rate",
                    "type": "string",
                    "required": True,
                    "sourceType": "ref",
                },
            ],
            "outputs": [],
        },
    }

    workflow.set_end_comp(
        "node_end",
        End(end_conf),
        inputs_schema={
            "tel": "${node_5d8bd3c331a04.userFields.tel}",
            "time": "${node_5d8bd3c331a04.userFields.time}",
            "switch": "${node_5d8bd3c331a04.userFields.switch}",
            "signals": "${node_5d8bd3c331a04.userFields.signals}",
            "flow_rate": "${node_5d8bd3c331a04.userFields.flow_rate}",
        },
        response_mode="streaming" if is_streaming else "directResponse",
    )

    # 4. 添加连接
    workflow.add_connection("node_start", "node_5d8bd3c331a04")
    workflow.add_connection("node_5d8bd3c331a04", "node_end")

    # 5. 注册工作流到 Runner
    Runner.resource_mgr.remove_workflow(workflow_id=workflow_id, tag=agent_id)
    Runner.resource_mgr.add_workflow(workflow_card, lambda: workflow, tag=agent_id)

    return workflow, workflow_id


def _extract_interrupt_node_id(chunks) -> str | None:
    """从流式输出中提取中断节点的 node_id"""
    for chunk in chunks:
        if (
            hasattr(chunk, "data")
            and isinstance(chunk.data, dict)
            and chunk.data.get("should_interrupt", False)
        ):
            return chunk.data.get("node_id")
    return None


def _build_context(conversation_history: list):
    """从对话历史构建 ModelContext，模拟 WorkflowHandler 的 _build_context 行为。"""
    from openjiuwen.core.context_engine.context.context import SessionModelContext
    from openjiuwen.core.context_engine.schema.config import ContextEngineConfig

    model_context = SessionModelContext(
        context_id="test_context",
        session_id="test_session",
        config=ContextEngineConfig(),
        history_messages=[],
        processors=[],
    )
    WorkflowMessageConverter.conversation_messages_to_model_context(
        conversation_history, model_context
    )
    return model_context


def _extract_output_text(chunks) -> str:
    """从流式输出中提取最终输出文本"""
    texts = []
    for chunk in chunks:
        if hasattr(chunk, "data") and isinstance(chunk.data, dict):
            data = chunk.data
            if "answer" in data and not data.get("should_interrupt", False):
                answer = data["answer"]
                if isinstance(answer, str) and answer:
                    texts.append(answer)
    return "".join(texts)


@pytest.mark.asyncio
async def test_questioner_ssq_workflow():
    """
    测试提问器-ssq工作流的完整多轮字段收集流程

    测试流程：
    1. R1: "车机故障" → 提问器首次执行 → 所有字段缺失 → 中断（询问 5 个字段）
    2. R2: "电话号码是10000" → 恢复 → Mock LLM 提取 tel=10000 → 仍缺 4 字段 → 中断
    3. R3: "故障发生在十点，移动开关开启，车机端有显示信号，车机端有剩余流量"
       → 恢复 → Mock LLM 提取 time/switch/signals/flow_rate → 全部收集完成
       → 工作流正常完成 → 到达 End 节点 → 输出模板结果
    """
    workflow, workflow_id = create_questioner_ssq_workflow(True)  # noqa: redefined-outer-name
    session_id = "3f9c8dea-a5e2-467b-a9e1-b28c8ec968dc"

    # ==================== R1：车机故障（首次请求） ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("R1：车机故障（首次请求）")
    workflow_logger.info("=" * 50)

    workflow_wrapper = WorkflowWrapper()
    chunks_1 = []

    context_1 = _build_context([{"role": "user", "content": "车机故障"}])

    async for chunk in workflow_wrapper.astream(
        query="车机故障",
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
        context=context_1,
    ):
        chunks_1.append(chunk)
        workflow_logger.info(chunk)

    # 验证 R1：提问器应中断（所有 5 个字段缺失）
    assert len(chunks_1) > 0
    has_interrupt = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_1
    )
    workflow_logger.info(f"R1 是否中断: {has_interrupt}")
    assert has_interrupt is True

    # 从 R1 中提取中断节点 node_id
    interrupt_node_id_1 = _extract_interrupt_node_id(chunks_1)
    assert interrupt_node_id_1 is not None, "未找到 R1 的中断节点 node_id"

    # ==================== R2：电话号码是10000（恢复） ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("R2：电话号码是10000（恢复）")
    workflow_logger.info("=" * 50)

    # 构建中断恢复的 InteractiveInput，精确路由到中断节点
    resume_input_2 = InteractiveInput()
    resume_input_2.update(interrupt_node_id_1, "电话号码是10000")

    conversation_history_2 = [
        {"role": "user", "content": "车机故障"},
        {
            "role": "assistant",
            "content": "请您提供电话号码、故障发生时间、移动开关、车机端显示信号、剩余流量相关的信息",
        },
        {"role": "user", "content": "电话号码是10000"},
    ]

    params_2 = {
        "global_variables": {
            "sys": {
                "conversationHistory": conversation_history_2,
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            }
        },
        "conversation_history": conversation_history_2,
        "CONTROLLER_MODE_SWITCH": True,
    }

    workflow_wrapper_2 = WorkflowWrapper()
    chunks_2 = []
    context_2 = _build_context(conversation_history_2)
    async for chunk in workflow_wrapper_2.astream(
        query=resume_input_2,
        params=params_2,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
        context=context_2,
    ):
        chunks_2.append(chunk)
        workflow_logger.info(chunk)

    # 验证 R2：Mock LLM 提取 tel=10000，仍缺 4 个字段 → 再次中断
    assert len(chunks_2) > 0
    has_interrupt_2 = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_2
    )
    workflow_logger.info(f"R2 是否中断: {has_interrupt_2}")
    assert has_interrupt_2 is True

    # 从 R2 中提取中断节点 node_id
    interrupt_node_id_2 = _extract_interrupt_node_id(chunks_2)
    assert interrupt_node_id_2 is not None, "未找到 R2 的中断节点 node_id"

    # ==================== R3：提供剩余字段（恢复） ====================
    workflow_logger.info("=" * 50)
    workflow_logger.info("R3：提供剩余字段（恢复）")
    workflow_logger.info("=" * 50)

    # 构建中断恢复的 InteractiveInput
    resume_input_3 = InteractiveInput()
    resume_input_3.update(
        interrupt_node_id_2,
        "故障发生在十点，移动开关开启，车机端有显示信号，车机端有剩余流量",
    )

    conversation_history_3 = [
        {"role": "user", "content": "车机故障"},
        {
            "role": "assistant",
            "content": "请您提供电话号码、故障发生时间、移动开关、车机端显示信号、剩余流量相关的信息",
        },
        {"role": "user", "content": "电话号码是10000"},
        {
            "role": "assistant",
            "content": "请您提供故障发生时间、移动开关、车机端显示信号、剩余流量相关的信息",
        },
        {
            "role": "user",
            "content": "故障发生在十点，移动开关开启，车机端有显示信号，车机端有剩余流量",
        },
    ]

    params_3 = {
        "global_variables": {
            "sys": {
                "conversationHistory": conversation_history_3,
                "currentTime": "2024-09-24 14:44:41",
                "userId": "test_user",
                "conversationId": session_id,
            }
        },
        "conversation_history": conversation_history_3,
        "CONTROLLER_MODE_SWITCH": True,
    }

    workflow_wrapper_3 = WorkflowWrapper()
    chunks_3 = []
    context_3 = _build_context(conversation_history_3)
    async for chunk in workflow_wrapper_3.astream(
        query=resume_input_3,
        params=params_3,
        workflow_id=workflow_id,
        session_id=session_id,
        agent_id=agent_id,
        context=context_3,
    ):
        chunks_3.append(chunk)
        workflow_logger.info(chunk)

    # 验证 R3：Mock LLM 提取所有剩余字段 → 全部收集完成 → 不再中断
    assert len(chunks_3) > 0
    has_interrupt_3 = any(
        hasattr(chunk, "data")
        and isinstance(chunk.data, dict)
        and chunk.data.get("should_interrupt", False)
        for chunk in chunks_3
    )
    workflow_logger.info(f"R3 是否中断: {has_interrupt_3}")
    assert has_interrupt_3 is False, "R3 应该完成字段收集，不再中断"

    # 验证 End 节点输出了模板结果（包含字段标签和字段值）
    output_text = _extract_output_text(chunks_3)
    workflow_logger.info(f"R3 输出文本: {output_text}")
    assert len(output_text) > 0, "R3 应输出 End 节点的模板结果"

    # 验证输出包含 End 节点的模板标签（电话号码、故障发生时间等）
    assert "电话号码" in output_text, "输出应包含电话号码标签"
    assert "故障发生时间" in output_text, "输出应包含故障发生时间标签"
    assert "移动开关开启状态" in output_text, "输出应包含移动开关开启状态标签"

    # 验证输出包含实际字段值（证明字段值成功传递到 End 节点模板渲染）
    assert "10000" in output_text, "输出应包含电话号码值 10000"
    assert "十点" in output_text, "输出应包含故障发生时间值 十点"
    assert "开启" in output_text, "输出应包含移动开关值 开启"

    return chunks_1, chunks_2, chunks_3


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_questioner_ssq_workflow())
