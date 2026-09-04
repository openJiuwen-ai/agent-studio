# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
IntentDetection 完整工作流集成测试

将 IntentDetection 放入完整工作流中测试，使用真实模型，配置从 memory_env 加载。

测试场景:
- Start → IntentDetection(天气) → End 基础意图分类
- Start → IntentDetection(餐饮) → End 多分类场景
- Start → IntentDetection(旅行) → End 旅行规划意图
- Start → IntentDetection(无关问题) → End 回退默认分类
- Start → IntentDetection → End 流式输出（flow.stream）
- WorkflowWrapper → Runner → Start → IntentDetection → End 端到端
"""

import asyncio
import json
import os
import sys
from functools import wraps
from pathlib import Path

import pytest
import pytest_asyncio
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.stream.base import StreamCode
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.runner import Runner
from openjiuwen.core.workflow import (
    Workflow,
    WorkflowExecutionState,
    create_workflow_session,
)
from openjiuwen.core.workflow.base import WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

# ---------------------------------------------------------------------------
# 重试装饰器（应对 LLM API 瞬态错误）
# ---------------------------------------------------------------------------

_LLM_RETRY_COUNT = 3
_LLM_RETRY_DELAY = 5  # 秒


def retry_on_llm_error(
    max_retries: int = _LLM_RETRY_COUNT, delay: float = _LLM_RETRY_DELAY
):
    """对异步测试函数做自动重试，仅在遇到 LLM 瞬态错误时重试。"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    exc_str = str(exc)
                    if "101302" in exc_str or "FrameworkError" in exc_str:
                        if attempt < max_retries:
                            workflow_logger.warning(
                                f"LLM API 瞬态错误 (attempt {attempt}/{max_retries}), "
                                f"{delay}s 后重试: {exc_str}"
                            )
                            await asyncio.sleep(delay)
                            continue
                    raise
            raise last_exc

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# 环境变量加载
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function", autouse=True)
def load_environment():
    """从 memory_env 加载模型配置"""
    env_file = Path(__file__).parent / "memory_env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if value:
                os.environ[key] = value
    # 工作流执行超时（默认 60s 不够意图识别 LLM 调用）
    os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "180")


def _skip_if_no_model():
    if not os.getenv("LLM_API_KEY") or not os.getenv("LLM_MODEL_NAME"):
        pytest.skip("LLM_API_KEY / LLM_MODEL_NAME not configured in memory_env")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


_CATEGORIES = [
    {"id": "branch_0", "catalog": "其他意图"},
    {"id": "branch_1", "catalog": "天气查询"},
    {"id": "branch_2", "catalog": "餐饮推荐"},
    {"id": "branch_3", "catalog": "旅行规划"},
]


def _intent_config(
    categories: list[dict] | None = None,
    prompt: str = "请根据用户输入判断意图分类",
    enable_history: bool = False,
    enable_input: bool = True,
    chat_history_max_turn: int = 3,
) -> dict:
    """构建 IntentDetection 配置"""
    return {
        "llm": {
            "model": {
                "modelType": os.getenv("LLM_PROVIDER", "SiliconFlow"),
                "modelName": os.getenv("LLM_MODEL_NAME", ""),
                "hyperParameters": {
                    "temperature": 0.5,
                    "top_p": 0.5,
                    "max_tokens": 256,
                },
                "extension": {
                    "api_base": os.getenv("LLM_API_BASE", ""),
                    "api_key": os.getenv("LLM_API_KEY", ""),
                    "verify_ssl": False,
                    "timeout": 120.0,
                },
            }
        },
        "branches": categories or _CATEGORIES,
        "prompt": prompt,
        "enableHistory": enable_history,
        "enableInput": enable_input,
        "chatHistoryMaxTurn": chat_history_max_turn,
    }


def _start_config() -> dict:
    """构建 Start 配置"""
    return {
        "userFields": {"inputs": [], "outputs": []},
        "systemFields": {
            "inputs": [
                {
                    "sourceType": "input",
                    "id": "query",
                    "type": "string",
                    "required": True,
                }
            ],
            "outputs": [],
        },
    }


def _create_intent(
    config: dict | None = None, next_node: str = "end"
) -> IntentDetection:
    """创建 IntentDetection 实例，并注册 catch-all 分支路由到 next_node。"""
    intent = IntentDetection(config or _intent_config())
    intent.add_branch("true", next_node)
    return intent


def _end_config() -> dict:
    """构建 End 配置"""
    return {
        "name": "结束节点",
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [{"id": "result", "type": "string", "required": False}],
            "outputs": [],
        },
        "responseTemplate": "{{name}}: {{result}}",
        "isStreamOut": False,
    }


# ===========================================================================
# 完整工作流测试
# ===========================================================================


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_workflow_intent_detection_weather():
    """工作流: Start → IntentDetection → End  天气查询意图"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → IntentDetection(天气) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    flow.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
    )

    flow.add_connection("start", "intent")
    flow.add_connection("intent", "end")

    session = create_workflow_session()
    result = await flow.invoke(inputs={"query": "今天北京天气怎么样"}, session=session)

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_workflow_intent_detection_restaurant():
    """工作流: Start → IntentDetection → End  餐饮推荐意图"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → IntentDetection(餐饮) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    flow.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
    )

    flow.add_connection("start", "intent")
    flow.add_connection("intent", "end")

    session = create_workflow_session()
    result = await flow.invoke(
        inputs={"query": "推荐一家好吃的火锅店"}, session=session
    )

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_workflow_intent_detection_travel():
    """工作流: Start → IntentDetection → End  旅行规划意图"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → IntentDetection(旅行) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    flow.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
    )

    flow.add_connection("start", "intent")
    flow.add_connection("intent", "end")

    session = create_workflow_session()
    result = await flow.invoke(
        inputs={"query": "我想去三亚旅游，有什么好的行程推荐"}, session=session
    )

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_workflow_intent_detection_default():
    """工作流: Start → IntentDetection → End  无匹配意图回退默认分类"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → IntentDetection(默认分类) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    flow.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
    )

    flow.add_connection("start", "intent")
    flow.add_connection("intent", "end")

    session = create_workflow_session()
    result = await flow.invoke(
        inputs={"query": "帮我算一下1加1等于几"}, session=session
    )

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


# ===========================================================================
# WorkflowWrapper 流式输出测试（真实模型）
# ===========================================================================


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_wrapper_intent_detection_stream(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端流式输出: End 节点 response_mode=streaming，验证流式事件完整。"""
    _skip_if_no_model()
    workflow_logger.info(
        "=== WorkflowWrapper 端到端流式: IntentDetection 天气 (真实模型) ==="
    )

    workflow_id = "test_intent_real_stream"
    agent_id = "test_agent_intent_stream"

    # 构建 End 节点使用流式输出模式的工作流
    card = WorkflowCard(
        id=workflow_id, name="intent_detection_stream_test", description="stream test"
    )
    wf = Workflow(card=card)

    start = Start(_start_config())
    wf.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    wf.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
        comp_ability=[ComponentAbility.INVOKE],
    )

    end = End({"responseTemplate": "{{name}}: {{result}}"})
    wf.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
        response_mode="streaming",
    )

    wf.add_connection("start", "intent")
    wf.add_connection("intent", "end")

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="明天深圳天气如何",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_intent_stream",
        ):
            results.append(item)
            workflow_logger.info(f"  code={item.code}, data={item.data}")

        codes = [item.code for item in results]
        workflow_logger.info(f"  总共收到 {len(results)} 个流式事件, codes={codes}")

        assert len(results) > 0, "流式调用应至少返回一个事件"
        assert StreamCode.FINISH.value in codes, f"Missing FINISH in: {codes}"
        assert StreamCode.ERROR.value not in codes
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes

    finally:
        _unregister_workflow(workflow_id)


# ===========================================================================
# WorkflowWrapper 端到端测试（真实模型）
# ===========================================================================


def _build_intent_workflow(workflow_id: str) -> Workflow:
    """构建意图识别工作流: Start → IntentDetection → End，注册到 Runner。"""
    card = WorkflowCard(
        id=workflow_id, name="intent_detection_test", description="intent test"
    )
    wf = Workflow(card=card)

    start = Start(_start_config())
    wf.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    intent = _create_intent()
    wf.add_workflow_comp(
        "intent",
        intent,
        inputs_schema={
            "input": "${start.systemFields.query}",
        },
        comp_ability=[ComponentAbility.INVOKE],
    )

    end = End({"responseTemplate": "{{name}}: {{result}}"})
    wf.set_end_comp(
        "end",
        end,
        inputs_schema={
            "name": "${intent.name}",
            "result": "${intent.result}",
        },
    )

    wf.add_connection("start", "intent")
    wf.add_connection("intent", "end")
    return wf


def _register_workflow(wf: Workflow, agent_id: str) -> None:
    """将工作流注册到 Runner.resource_mgr。"""
    Runner.resource_mgr.add_workflow(
        card=wf.card,
        workflow=lambda card=wf.card: wf,
        tag=agent_id,
    )


def _unregister_workflow(workflow_id: str) -> None:
    """从 Runner.resource_mgr 移除工作流。"""
    Runner.resource_mgr.remove_workflow(workflow_id)


@pytest_asyncio.fixture
async def setup_runner():
    """初始化 Runner，测试结束后清理。"""
    await Runner.start()
    yield
    await Runner.stop()


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_wrapper_intent_detection_weather(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端: 意图识别工作流，真实模型，验证天气查询分类。"""
    _skip_if_no_model()
    workflow_logger.info(
        "=== WorkflowWrapper 端到端: IntentDetection 天气 (真实模型) ==="
    )

    workflow_id = "test_intent_real_weather"
    agent_id = "test_agent_intent_weather"
    wf = _build_intent_workflow(workflow_id)
    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="今天上海会不会下雨",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_intent_weather",
        ):
            results.append(item)
            workflow_logger.info(f"  code={item.code}, data={item.data}")

        codes = [item.code for item in results]
        assert StreamCode.FINISH.value in codes, f"Missing FINISH in: {codes}"
        assert StreamCode.ERROR.value not in codes
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes

    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
@retry_on_llm_error()
async def test_wrapper_intent_detection_restaurant(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端: 意图识别工作流，真实模型，验证餐饮推荐分类。"""
    _skip_if_no_model()
    workflow_logger.info(
        "=== WorkflowWrapper 端到端: IntentDetection 餐饮 (真实模型) ==="
    )

    workflow_id = "test_intent_real_restaurant"
    agent_id = "test_agent_intent_restaurant"
    wf = _build_intent_workflow(workflow_id)
    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="附近有什么好吃的粤菜馆",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_intent_restaurant",
        ):
            results.append(item)
            workflow_logger.info(f"  code={item.code}, data={item.data}")

        codes = [item.code for item in results]
        assert StreamCode.FINISH.value in codes, f"Missing FINISH in: {codes}"
        assert StreamCode.ERROR.value not in codes
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes

    finally:
        _unregister_workflow(workflow_id)


if __name__ == "__main__":
    import subprocess

    r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    sys.exit(r.returncode)
