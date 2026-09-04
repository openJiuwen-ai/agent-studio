# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
LLMChain 完整工作流集成测试

将 LLMChain 放入完整工作流中测试，使用真实模型，配置从 memory_env 加载。

测试场景:
- Start → LLMChain(text) → End 非流式
- Start → LLMChain(json) → End 非流式
- Start → LLMChain(text) → End 流式
- Start → LLMChain1 → LLMChain2 → End 双节点串联
- WorkflowWrapper → Runner → Start → LLMChain → End 端到端（流式+批处理）
"""

import json
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.llm_chain import LLMChain
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


def _skip_if_no_model():
    if not os.getenv("LLM_API_KEY") or not os.getenv("LLM_MODEL_NAME"):
        pytest.skip("LLM_API_KEY / LLM_MODEL_NAME not configured in memory_env")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _llm_config(
    template: str = "请简短回答：{{query}}",
    response_type: str = "text",
    outputs: list = None,
    enable_history: bool = False,
    max_tokens: int = 512,
) -> dict:
    """构建 LLMChain 配置"""
    config = {
        "model": {
            "modelName": os.getenv("LLM_MODEL_NAME", ""),
            "modelType": "chat",
            "provider": os.getenv("LLM_PROVIDER", "SiliconFlow"),
            "apiBase": os.getenv("LLM_API_BASE", ""),
            "apiKey": os.getenv("LLM_API_KEY", ""),
            "hyperParameters": {
                "temperature": 0.5,
                "top_p": 0.5,
                "max_tokens": max_tokens,
            },
        },
        "deployMode": "online",
        "templateContent": [{"role": "user", "content": template}],
        "responseFormat": {"type": response_type},
        "enableHistory": enable_history,
        "userFields": {
            "outputs": outputs or [{"id": "answer", "type": "string"}],
        },
    }
    return config


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


def _end_config() -> dict:
    """构建 End 配置"""
    return {
        "name": "结束节点",
        "responseMode": "directResponse",
        "userFields": {
            "inputs": [{"id": "result", "type": "string", "required": False}],
            "outputs": [],
        },
        "responseTemplate": "{{result}}",
        "isStreamOut": False,
    }


# ===========================================================================
# 完整工作流测试
# ===========================================================================


@pytest.mark.asyncio
async def test_workflow_llm_text_invoke():
    """工作流: Start → LLMChain(text) → End  非流式调用"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → LLMChain(text) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm = LLMChain(
        _llm_config(
            template="请只回答数字：{{query}}",
            response_type="text",
        )
    )
    flow.add_workflow_comp(
        "llm",
        llm,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "result": "${llm.userFields.answer}",
        },
    )

    flow.add_connection("start", "llm")
    flow.add_connection("llm", "end")

    session = create_workflow_session()
    result = await flow.invoke(inputs={"query": "1+1等于几？"}, session=session)

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


@pytest.mark.asyncio
async def test_workflow_llm_json_invoke():
    """工作流: Start → LLMChain(json) → End  JSON 响应格式"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → LLMChain(json) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm = LLMChain(
        _llm_config(
            template='请以JSON格式回答 {"capital": "城市名"}，问题是：{{query}}',
            response_type="json",
            outputs=[{"id": "capital"}],
        )
    )
    flow.add_workflow_comp(
        "llm",
        llm,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
    )

    end_config = _end_config()
    end = End(end_config)
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "result": "${llm.userFields.capital}",
        },
    )

    flow.add_connection("start", "llm")
    flow.add_connection("llm", "end")

    session = create_workflow_session()
    result = await flow.invoke(inputs={"query": "法国的首都是哪里？"}, session=session)

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


@pytest.mark.asyncio
async def test_workflow_llm_text_stream():
    """工作流: Start → LLMChain(text) → End  流式调用"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流流式: Start → LLMChain(text) → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm = LLMChain(
        _llm_config(
            template="用一句话描述：{{query}}",
            response_type="text",
        )
    )
    flow.add_workflow_comp(
        "llm",
        llm,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
    )

    end = End(_end_config())
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "result": "${llm.userFields.answer}",
        },
    )

    flow.add_connection("start", "llm")
    flow.add_connection("llm", "end")

    session = create_workflow_session()
    chunks = []
    async for chunk in flow.stream(inputs={"query": "春天"}, session=session):
        chunks.append(chunk)
        workflow_logger.info(f"  stream chunk: {chunk}")

    workflow_logger.info(f"  总共收到 {len(chunks)} 个流式块")
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_workflow_llm_chain_two_nodes():
    """工作流: Start → LLMChain1(生成主题) → LLMChain2(展开描述) → End  双节点串联"""
    _skip_if_no_model()
    workflow_logger.info("=== 工作流: Start → LLM1 → LLM2 → End ===")

    flow = Workflow()

    start = Start(_start_config())
    flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm1 = LLMChain(
        _llm_config(
            template="请为一个关于{{query}}的主题生成一个简短的标题，只输出标题文本：",
            response_type="text",
            outputs=[{"id": "title"}],
        )
    )
    flow.add_workflow_comp(
        "llm1",
        llm1,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
    )

    llm2 = LLMChain(
        _llm_config(
            template="请根据以下标题写一句话的简介：{{title}}",
            response_type="text",
            outputs=[{"id": "description"}],
        )
    )
    flow.add_workflow_comp(
        "llm2",
        llm2,
        inputs_schema={
            "userFields": {"title": "${llm1.userFields.title}"},
        },
    )

    end_config = _end_config()
    end = End(end_config)
    flow.set_end_comp(
        "end",
        end,
        inputs_schema={
            "result": "${llm2.userFields.description}",
        },
    )

    flow.add_connection("start", "llm1")
    flow.add_connection("llm1", "llm2")
    flow.add_connection("llm2", "end")

    session = create_workflow_session()
    result = await flow.invoke(inputs={"query": "人工智能"}, session=session)

    workflow_logger.info(f"  state: {result.state}")
    workflow_logger.info(
        f"  result: {json.dumps(result.result, ensure_ascii=False) if result.result else None}"
    )

    assert result.state == WorkflowExecutionState.COMPLETED


# ===========================================================================
# WorkflowWrapper 端到端测试（真实模型）
# ===========================================================================


def _build_wrapper_streaming_workflow(workflow_id: str) -> Workflow:
    """构建流式工作流: Start → LLMChain(STREAM) → End(TRANSFORM)，注册到 Runner。"""
    card = WorkflowCard(
        id=workflow_id, name="llm_chain_test_stream", description="streaming test"
    )
    wf = Workflow(card=card)

    start = Start(_start_config())
    wf.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm = LLMChain(
        _llm_config(
            template="请简短回答：{{query}}",
            response_type="text",
            outputs=[{"id": "raw_output"}],
        )
    )
    wf.add_workflow_comp(
        "llm",
        llm,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
    )

    end = End({"responseTemplate": "{{answer}}"})
    wf.set_end_comp(
        "end",
        end,
        stream_inputs_schema={"answer": "${llm.userFields.raw_output}"},
        response_mode="streaming",
    )

    wf.add_connection("start", "llm")
    wf.add_stream_connection("llm", "end")
    return wf


def _build_wrapper_invoke_workflow(workflow_id: str) -> Workflow:
    """构建批处理工作流: Start → LLMChain(INVOKE) → End(INVOKE)，注册到 Runner。"""
    card = WorkflowCard(
        id=workflow_id, name="llm_chain_test_invoke", description="invoke test"
    )
    wf = Workflow(card=card)

    start = Start(_start_config())
    wf.set_start_comp("start", start, inputs_schema={"query": "${query}"})

    llm = LLMChain(
        _llm_config(
            template="请简短回答：{{query}}",
            response_type="text",
        )
    )
    wf.add_workflow_comp(
        "llm",
        llm,
        inputs_schema={
            "userFields": {"query": "${start.systemFields.query}"},
        },
        comp_ability=[ComponentAbility.INVOKE],
    )

    end = End({"responseTemplate": "{{answer}}"})
    wf.set_end_comp(
        "end",
        end,
        inputs_schema={
            "answer": "${llm.userFields.answer}",
        },
    )

    wf.add_connection("start", "llm")
    wf.add_connection("llm", "end")
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
async def test_wrapper_streaming_with_real_model(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端: 流式工作流，真实模型，验证 PARTIAL_CONTENT 输出。"""
    _skip_if_no_model()
    workflow_logger.info("=== WorkflowWrapper 端到端: 流式 (真实模型) ===")

    workflow_id = "test_llm_real_stream"
    agent_id = "test_agent_real_stream"
    wf = _build_wrapper_streaming_workflow(workflow_id)
    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="用一句话描述春天",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_real_stream",
        ):
            results.append(item)
            workflow_logger.info(f"  code={item.code}, data={item.data}")

        codes = [item.code for item in results]

        # 应有 PARTIAL_CONTENT
        assert StreamCode.PARTIAL_CONTENT.value in codes, (
            f"Missing PARTIAL_CONTENT in: {codes}"
        )

        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        for p in partial_items:
            assert isinstance(p.data, dict)
            assert "answer" in p.data

        full_answer = "".join(p.data["answer"] for p in partial_items)
        workflow_logger.info(f"  完整回答: {full_answer}")
        assert len(full_answer) > 0

    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_wrapper_invoke_with_real_model(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端: 批处理工作流，真实模型，验证 FINISH 输出。"""
    _skip_if_no_model()
    workflow_logger.info("=== WorkflowWrapper 端到端: 批处理 (真实模型) ===")

    workflow_id = "test_llm_real_invoke"
    agent_id = "test_agent_real_invoke"
    wf = _build_wrapper_invoke_workflow(workflow_id)
    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="1+1等于几？只回答数字",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_real_invoke",
        ):
            results.append(item)
            workflow_logger.info(f"  code={item.code}, data={item.data}")

        codes = [item.code for item in results]

        # 应有 FINISH
        assert StreamCode.FINISH.value in codes, f"Missing FINISH in: {codes}"

        # 不应有错误
        assert StreamCode.ERROR.value not in codes
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes

        finish_items = [r for r in results if r.code == StreamCode.FINISH.value]
        assert len(finish_items) >= 1
        workflow_logger.info(f"  FINISH data: {finish_items[0].data}")

    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_wrapper_full_params_with_real_model(setup_runner):  # noqa: redefined-outer-name
    """WorkflowWrapper 端到端: 携带完整 Controller 参数，真实模型，验证流程和 runtime_context。"""
    _skip_if_no_model()
    workflow_logger.info(
        "=== WorkflowWrapper 端到端: 完整 Controller 参数 (真实模型) ==="
    )

    workflow_id = "test_llm_real_full"
    agent_id = "test_agent_real_full"
    wf = _build_wrapper_streaming_workflow(workflow_id)
    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "global_variables": {
                "sys": {
                    "conversationHistory": [],
                    "conversationId": "conv_test",
                    "userId": "user_test",
                },
                "userId": "user_test",
                "query": "你好",
            },
            "conversation_history": [],
            "controller_mode_switch": True,
            "plugin_configs": {"default": {"headers": {"X-Auth-Token": "test"}}},
            "project_id": "proj_test",
        }

        results = []
        async for item in wrapper.astream(
            query="用一句话介绍你自己",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_real_full",
        ):
            results.append(item)
            workflow_logger.info(f"item={item}")

        # 验证工作流正常完成
        codes = [item.code for item in results]
        assert StreamCode.PARTIAL_CONTENT.value in codes
        assert StreamCode.ERROR.value not in codes

        # 验证 runtime_context 被正确设置
        ctx = wrapper.get_runtime_context()
        assert "global_variables" in ctx
        assert ctx["global_variables"]["userId"] == "user_test"

        workflow_logger.info("  端到端测试通过")

    finally:
        _unregister_workflow(workflow_id)


if __name__ == "__main__":
    import subprocess

    r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    sys.exit(r.returncode)
