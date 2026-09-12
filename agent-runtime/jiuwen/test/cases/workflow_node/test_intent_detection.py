# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
IntentDetection 组件集成测试用例

测试工作流图:
    graph TD
        A[Start] --> B[IntentDetection]
        B --> C[End]

测试流程:
1. 用户输入："我想订一张去北京的机票"
2. Start 节点传递输入到 IntentDetection
3. IntentDetection 通过 LLM 识别意图为"机票预订"（分类1）
4. End 节点收集结果
5. 校验输出结果包含正确的意图分类

输入格式:
- Start: input: 用户输入
- IntentDetection: input: start.input
- End: intent_result: intent_detection.result, intent_name: intent_detection.name

输出格式:
- {"result": "分类1", "reason": "...", "classificationId": 1, "name": "机票预订"}
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.start import Start
from openjiuwen.core.context_engine.context.context import SessionModelContext
from openjiuwen.core.context_engine.schema.config import ContextEngineConfig
from openjiuwen.core.foundation.llm import BaseMessage
from openjiuwen.core.workflow import (
    Workflow,
    create_workflow_session,
    WorkflowExecutionState,
)

USER_INPUT = "我想订一张去北京的机票"


def _load_memory_env() -> dict:
    """从 memory_env 文件加载环境变量"""
    env_file = Path(__file__).parent / "memory_env"
    env_config = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_config[key.strip()] = value.strip()
    return env_config


_MEMORY_ENV = _load_memory_env()


def _create_test_model_context(
    messages: list[BaseMessage] = None,
) -> SessionModelContext:
    """创建测试用的 ModelContext"""
    config = ContextEngineConfig(
        max_context_message_num=100,
        default_window_message_num=50,
    )
    return SessionModelContext(
        context_id="test-context",
        session_id="test-session",
        config=config,
        history_messages=messages or [],
        processors=[],
    )


def _build_intent_config(
    model_name: str,
    model_type: str,
    hyper_parameters: dict = None,
    extension: dict = None,
) -> dict:
    """构建 IntentDetection 组件配置"""
    return {
        "llm": {
            "model": {
                "modelName": model_name,
                "modelType": model_type,
                "hyperParameters": hyper_parameters or {"temperature": 0.1},
                "extension": extension or {},
            }
        },
        "branches": [
            {"id": "branch_0", "catalog": "其他意图"},
            {"id": "branch_1", "catalog": "机票预订"},
            {"id": "branch_2", "catalog": "酒店预订"},
        ],
        "prompt": "请根据用户输入识别意图，从以下分类中选择最匹配的一个",
        "enableHistory": True,
        "enableInput": True,
        "chatHistoryMaxTurn": 3,
        "enableKnowledge": False,
        "kg": {},
        "memory": {},
        "overridable": False,
    }


def _build_workflow(intent_detection: IntentDetection) -> Workflow:
    """构建测试工作流: Start -> IntentDetection -> End"""
    wf = Workflow()

    start_config = {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "description": "用户输入",
                    "id": "input",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [],
        },
    }

    wf.set_start_comp(
        "start",
        Start(start_config),
        inputs_schema={"input": "${input}"},
    )

    wf.add_workflow_comp(
        "intent_detection",
        intent_detection,
        inputs_schema={"input": "${start.userFields.input}"},
    )

    end_config = {
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [
                {
                    "sourceType": "ref",
                    "description": "意图结果",
                    "id": "intent_result",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "意图名称",
                    "id": "intent_name",
                    "type": "string",
                    "required": False,
                },
                {
                    "sourceType": "ref",
                    "description": "意图原因",
                    "id": "intent_reason",
                    "type": "string",
                    "required": False,
                },
            ],
            "outputs": [],
        },
        "responseTemplate": '{"intent_result": "{{intent_result}}", "intent_name": "{{intent_name}}", "intent_reason": "{{intent_reason}}"}',
        "isStreamOut": False,
    }

    wf.set_end_comp(
        "end",
        End(end_config),
        inputs_schema={
            "intent_result": "${intent_detection.result}",
            "intent_name": "${intent_detection.name}",
            "intent_reason": "${intent_detection.reason}",
        },
    )

    wf.add_connection("start", "intent_detection")
    # wf.add_connection("intent_detection", "end")

    return wf


class TestIntentDetectionIntegrationWithMockLLM:
    """
    使用 Mock 大模型的集成测试

    测试流程:
    1. 用户输入："我想订一张去北京的机票"
    2. Start -> IntentDetection -> End
    3. Mock LLM 返回 {"class": "分类1", "reason": "用户想要预订机票"}
    4. 校验输出: intent_result="分类1", intent_name="机票预订"
    """

    @pytest.mark.asyncio
    async def test_workflow_intent_detection_with_mock_llm(self):
        """
        Mock LLM 测试：完整工作流测试

        流程:
        1. 用户输入："我想订一张去北京的机票"
        2. Mock LLM 返回 {"class": "分类1", "reason": "用户想要预订机票"}
        3. 校验输出中的意图分类为"分类1"，名称为"机票预订"
        """
        config = _build_intent_config(
            model_name="mock-model",
            model_type="mock",
        )

        # Mock LLM：invoke 返回带有 content 属性的对象
        mock_llm = MagicMock()
        mock_llm.invoke = AsyncMock(
            return_value=MagicMock(
                content='{"class": "分类1", "reason": "用户想要预订机票"}'
            )
        )

        # IntentDetection 在 __init__ 中创建 LLM，所以必须在构造前 patch
        with patch.object(IntentDetection, "_get_llm_instance", return_value=mock_llm):
            intent_detection = IntentDetection(conf=config)
            intent_detection.add_branch(
                condition="0 == ${intent_detection['classificationId']}",
                target="end",
                branch_id="branch_0",
            )
            intent_detection.add_branch(
                condition="1 == ${intent_detection['classificationId']}",
                target="end",
                branch_id="branch_1",
            )
            intent_detection.add_branch(
                condition="2 == ${intent_detection['classificationId']}",
                target="end",
                branch_id="branch_2",
            )

        wf = _build_workflow(intent_detection)
        session = create_workflow_session()
        context = _create_test_model_context()

        result = await wf.invoke(
            {"input": USER_INPUT},
            session,
            context=context,
        )

        # 验证工作流执行状态
        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED

        output = result.result
        assert output is not None
        assert "answer" in output, f"输出中应包含 'answer' 字段，实际输出: {output}"

        import json

        response_data = output["answer"]
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data["answer"]
        else:
            response_str = response_data
        output_data = json.loads(response_str)

        # 验证意图分类结果
        assert "intent_result" in output_data, (
            f"输出中应包含 'intent_result'，实际: {output_data}"
        )
        assert "intent_name" in output_data, (
            f"输出中应包含 'intent_name'，实际: {output_data}"
        )

        intent_result = output_data.get("intent_result", "")
        intent_name = output_data.get("intent_name", "")

        assert "分类1" in intent_result, (
            f"intent_result 应包含 '分类1'，实际值: {intent_result}"
        )
        assert "机票" in intent_name, (
            f"intent_name 应包含 '机票'，实际值: {intent_name}"
        )


class TestIntentDetectionIntegrationWithRealLLM:
    """
    使用真实大模型的集成测试

    测试流程:
    1. 用户输入："我想订一张去北京的机票"
    2. Start -> IntentDetection -> End
    3. 真实 LLM 识别意图
    4. 校验输出结果在预定义分类列表中
    """

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not _MEMORY_ENV.get("LLM_API_KEY"),
        reason="memory_env 文件中未配置 LLM_API_KEY，跳过真实 LLM 测试",
    )
    async def test_workflow_intent_detection_with_real_llm(self):
        """
        真实 LLM 测试：完整工作流测试

        流程:
        1. 用户输入："我想订一张去北京的机票"
        2. 真实 LLM 识别意图（预期为"机票预订"/分类1）
        3. 校验输出结果为有效分类
        """
        config = _build_intent_config(
            model_name=_MEMORY_ENV.get("LLM_MODEL_NAME", "Qwen/Qwen2.5-32B-Instruct"),
            model_type=_MEMORY_ENV.get("LLM_PROVIDER", "SiliconFlow"),
            hyper_parameters={"temperature": 0.1, "top_p": 0.15},
            extension={
                "api_key": _MEMORY_ENV.get("LLM_API_KEY"),
                "api_base": _MEMORY_ENV.get("LLM_API_BASE"),
                "verify_ssl": False,
            },
        )

        intent_detection = IntentDetection(conf=config)
        intent_detection.add_branch(
            condition="0 == ${intent_detection['classificationId']}",
            target="end",
            branch_id="branch_0",
        )
        intent_detection.add_branch(
            condition="1 == ${intent_detection['classificationId']}",
            target="end",
            branch_id="branch_1",
        )
        intent_detection.add_branch(
            condition="2 == ${intent_detection['classificationId']}",
            target="end",
            branch_id="branch_2",
        )

        wf = _build_workflow(intent_detection)
        session = create_workflow_session()
        context = _create_test_model_context()

        result = await wf.invoke(
            {"input": USER_INPUT},
            session,
            context=context,
        )

        # 验证工作流执行状态
        assert result is not None
        assert result.state == WorkflowExecutionState.COMPLETED

        output = result.result
        assert output is not None
        assert "answer" in output

        import json

        response_data = output["answer"]
        if isinstance(response_data, dict) and "answer" in response_data:
            response_str = response_data["answer"]
        else:
            response_str = response_data
        output_data = json.loads(response_str)

        # 验证意图分类结果
        assert "intent_result" in output_data, (
            f"输出中应包含 'intent_result'，实际: {output_data}"
        )
        assert "intent_name" in output_data, (
            f"输出中应包含 'intent_name'，实际: {output_data}"
        )

        intent_result = output_data.get("intent_result", "")
        valid_categories = ["分类0", "分类1", "分类2"]
        assert intent_result in valid_categories, (
            f"intent_result 应为 {valid_categories} 之一，实际值: {intent_result}"
        )
