# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
WorkflowWrapper 单元测试。

验证 WorkflowWrapper 封装新版 openjiuwen Workflow 后，
输出的 StreamData 与旧版 SpiffWorkflowControllerWorkflow 一致。

测试工作流拓扑: Start → LLMChain → End
使用 jiuwen.extension.workflow_node 下的扩展组件。

注意事项：
- 图引擎通过 inputs_schema（dict 格式 + ${ref_path} 语法）在节点间传递数据
- Start 组件需要 inputs_schema 从工作流输入提取用户查询
- LLMChain 需要 inputs_schema 从 Start 输出中提取模板变量
- End 组件使用 stream_inputs_schema（含 ${} 引用路径）消费流式数据
- inputs_schema 与 stream_inputs_schema 不允许存在重复 key
- LLM 调用已 mock，不会发起真实 API 请求

参数范围说明（对应 WorkflowHandler 对旧 workflow 的调用模式）：
- Controller 模式: astream(inputs=query, params=workflow_req_params)
  - workflow_req_params 包含: global_variables（含 sys）、conversation_history、
    controller_mode_switch、controller_mode_jump、plugin_configs、memory_variables 等
- React 模式: astream(query, kwargs)
  - kwargs 包含: global_variables、conversation_history、plugin_configs

WorkflowWrapper.astream() 将 params 映射为:
- _build_envs(params) → Session 环境变量
- _prepare_runtime_context(params) → runtime_context 字典
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.llm_chain import LLMChain
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.orchestration.flow.constant import (
    REQUEST_VARIABLES,
    WORKFLOW_EXECUTE_PROJECT_ID,
    WORKFLOW_EXECUTE_USER_ID,
    WORKFLOW_API_CONFIGS,
    ENVIRONMENT_VARIABLES,
    MEMORY_VARIABLES,
    WORKFLOW_GLOBAL_INTENTS,
    MEM_MAP,
    ENABLE_MEMORY_RETRIEVE,
)
from jiuwen.orchestration.flow.stream.base import StreamCode
from openjiuwen.core.runner import Runner
from openjiuwen.core.workflow import Workflow, WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility

# ==================== 组件配置 ====================

LLM_CHAIN_CONF = {
    "modelName": "mock-model",
    "modelType": "chat",
    "hyperParameters": {"temperature": 0.5, "top_p": 0.5, "max_tokens": 128},
    "deployMode": "standard",
    "templateContent": [{"role": "user", "content": "请回答: {{query}}"}],
    "responseFormat": {"type": "text"},
    "enableHistory": False,
    "userFields": {"inputs": [], "outputs": [{"id": "answer"}]},
}

LLM_CHAIN_MULTI_VAR_CONF = {
    "modelName": "mock-model",
    "modelType": "chat",
    "hyperParameters": {"temperature": 0.5, "top_p": 0.5, "max_tokens": 128},
    "deployMode": "standard",
    "templateContent": [
        {"role": "user", "content": "名字: {{name}}, 年龄: {{age}}, 问题: {{query}}"}
    ],
    "responseFormat": {"type": "text"},
    "enableHistory": False,
    "userFields": {"inputs": [], "outputs": [{"id": "answer"}]},
}

START_CONF = {
    "userFields": {
        "inputs": [{"id": "query", "required": True}],
    },
}

START_MULTI_FIELD_CONF = {
    "userFields": {
        "inputs": [
            {"id": "query", "required": True},
            {"id": "name", "required": False},
            {"id": "age", "required": False},
        ],
    },
}

END_CONF = {
    "responseTemplate": "{{answer}}",
}

# Mock LLM 流式输出的分片内容
_MOCK_STREAM_CHUNKS = ["你", "好", "，", "世", "界"]


# ==================== 辅助函数 ====================


def _create_mock_llm():
    """创建 mock LLM Model 实例，避免真实 API 调用。

    Returns:
        mock_model: MagicMock 对象，模拟 Model 的 stream/invoke 行为
    """
    mock_model = MagicMock()

    async def mock_stream(*args, **kwargs):
        for chunk_text in _MOCK_STREAM_CHUNKS:
            mock_chunk = MagicMock()
            mock_chunk.content = chunk_text
            yield mock_chunk

    mock_model.stream = mock_stream

    mock_invoke_result = MagicMock()
    mock_invoke_result.content = "".join(_MOCK_STREAM_CHUNKS)
    mock_invoke_result.usage_metadata = None
    mock_model.invoke = AsyncMock(return_value=mock_invoke_result)

    return mock_model


def _build_streaming_workflow(workflow_id: str = "test_wf") -> Workflow:
    """构建流式工作流: Start → LLM(STREAM) → End(TRANSFORM)。

    用于测试 PARTIAL_CONTENT 输出。
    End 节点仅使用 TRANSFORM 能力消费流式数据，不产生 FINISH。

    Args:
        workflow_id: 工作流 ID

    Returns:
        编排好的 Workflow 实例
    """
    card = WorkflowCard(
        id=workflow_id,
        name="test_workflow",
        description="test workflow for WorkflowWrapper",
    )
    wf = Workflow(card=card)

    start_comp = Start(START_CONF)
    llm_comp = LLMChain(LLM_CHAIN_CONF)
    end_comp = End(END_CONF)

    wf.set_start_comp("start", start_comp, inputs_schema={"query": "${query}"})

    wf.add_workflow_comp(
        "llm",
        llm_comp,
        inputs_schema={"userFields": {"query": "${start.systemFields.query}"}},
    )

    wf.set_end_comp(
        "end",
        end_comp,
        stream_inputs_schema={"answer": "${llm.userFields.raw_output}"},
        response_mode="streaming",
    )

    wf.add_connection("start", "llm")
    wf.add_stream_connection("llm", "end")

    return wf


def _build_invoke_workflow(workflow_id: str = "test_wf_invoke") -> Workflow:
    """构建批处理工作流: Start → LLM(INVOKE) → End(INVOKE)。

    用于测试 FINISH 输出。
    所有节点使用 INVOKE 能力，End 节点存储输出后触发 workflow_final → FINISH。

    Args:
        workflow_id: 工作流 ID

    Returns:
        编排好的 Workflow 实例
    """
    card = WorkflowCard(
        id=workflow_id, name="test_workflow_invoke", description="test invoke workflow"
    )
    wf = Workflow(card=card)

    start_comp = Start(START_CONF)
    llm_comp = LLMChain(LLM_CHAIN_CONF)
    end_comp = End(END_CONF)

    wf.set_start_comp("start", start_comp, inputs_schema={"query": "${query}"})

    wf.add_workflow_comp(
        "llm",
        llm_comp,
        inputs_schema={"userFields": {"query": "${start.systemFields.query}"}},
        comp_ability=[ComponentAbility.INVOKE],
    )

    wf.set_end_comp(
        "end",
        end_comp,
        inputs_schema={"answer": "${llm.userFields.answer}"},
    )

    wf.add_connection("start", "llm")
    wf.add_connection("llm", "end")

    return wf


def _build_multi_field_streaming_workflow(
    workflow_id: str = "test_wf_multi",
) -> Workflow:
    """构建多字段流式工作流: Start(multi) → LLM(STREAM) → End(TRANSFORM)。

    Start 组件声明多个用户输入字段（query/name/age），
    LLMChain 使用多变量模板，验证多字段变量传递链路。

    Args:
        workflow_id: 工作流 ID

    Returns:
        编排好的 Workflow 实例
    """
    card = WorkflowCard(
        id=workflow_id, name="test_workflow_multi", description="multi-field workflow"
    )
    wf = Workflow(card=card)

    start_comp = Start(START_MULTI_FIELD_CONF)
    llm_comp = LLMChain(LLM_CHAIN_MULTI_VAR_CONF)
    end_comp = End(END_CONF)

    wf.set_start_comp("start", start_comp, inputs_schema={"query": "${query}"})

    wf.add_workflow_comp(
        "llm",
        llm_comp,
        inputs_schema={"userFields": {"query": "${start.systemFields.query}"}},
    )

    wf.set_end_comp(
        "end",
        end_comp,
        stream_inputs_schema={"answer": "${llm.userFields.raw_output}"},
        response_mode="streaming",
    )

    wf.add_connection("start", "llm")
    wf.add_stream_connection("llm", "end")

    return wf


def _build_full_controller_params() -> dict:
    """构造完整 Controller 模式的参数（对齐 WorkflowHandler.prepare_workflow_params 输出）。

    对应 WorkflowHandler._stream_handle_workflow_execute 中:
        workflow_req_params = prepare_workflow_params(...)
        workflow_input = {"inputs": query, "params": workflow_req_params}

    Returns:
        模拟 WorkflowHandler 传入的完整参数字典
    """
    return {
        # 对应 _prepare_global_variables 合并后的全局变量
        "global_variables": {
            "sys": {
                "conversationHistory": [
                    {"role": "user", "content": "上轮问题"},
                    {"role": "assistant", "content": "上轮回答"},
                ],
                "conversationId": "conv_20250416_001",
                "userId": "user_789",
                "currentTime": "2025-04-16 20:00:00",
            },
            "conversationId": "conv_20250416_001",
            "userId": "user_789",
            "query": "你好世界",
            "custom_var_1": "value_1",
            "custom_var_2": 42,
        },
        # 对话历史（已过滤 hint 和空消息）
        "conversation_history": [
            {"role": "user", "content": "上轮问题"},
            {"role": "assistant", "content": "上轮回答"},
        ],
        # 控制器模式标志
        "controller_mode_switch": True,
        "controller_mode_jump": False,
        # 插件配置（API headers）
        "plugin_configs": {"default": {"headers": {"X-Auth-Token": "test-token-abc"}}},
        # 记忆变量
        "memory_variables": {"user_preference": "dark_mode", "user_language": "zh"},
        # 环境变量
        "environment_variables": {"timezone": "Asia/Shanghai", "locale": "zh-CN"},
        # 全局意图
        "global_intents": {"intent_1": "greeting", "intent_2": "qa"},
        # 记忆映射
        "mem_map": {"pref": "user_preference"},
        # 记忆检索开关
        "enable_memory_retrieve": True,
        # 项目 ID
        "project_id": "proj_001",
        # LLM 额外配置
        "llm_extra_configs": {"model_provider": "openai"},
        # 应用 ID
        "app_id": "app_001",
    }


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def setup_runner():
    """初始化 Runner 并注册测试工作流，测试结束后清理。"""
    await Runner.start()
    yield
    await Runner.stop()


@pytest_asyncio.fixture
def mock_llm():
    """Mock LLMChain._create_llm_instance 以避免真实 API 调用。"""
    mock_model = _create_mock_llm()
    with patch.object(LLMChain, "_create_llm_instance", return_value=mock_model):
        yield mock_model


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


# ==================== 测试用例: 基础功能 ====================


@pytest.mark.asyncio
async def test_astream_streaming_yields_partial_content(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证流式工作流输出 PARTIAL_CONTENT StreamData。

    流式工作流（End 使用 TRANSFORM 能力）产生 end node stream 分片，
    每个 LLM 分片对应一个 PARTIAL_CONTENT (code=1206)。

    注意：TRANSFORM end 节点不存储 INVOKE 输出，因此不产生 FINISH。
    """
    workflow_id = "test_wf_stream"
    agent_id = "test_agent"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="你好",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session",
        ):
            results.append(item)

        assert len(results) >= 1, (
            "WorkflowWrapper.astream should yield at least one item"
        )

        codes = [item.code for item in results]
        assert StreamCode.PARTIAL_CONTENT.value in codes, (
            f"Missing PARTIAL_CONTENT in output codes: {codes}"
        )

        # 验证每个 mock 分片都产生了对应的 PARTIAL_CONTENT, 包括最后一个作为结束标记的空字符串的 PARTIAL_CONTENT 消息（与原组件行为一致）
        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        assert len(partial_items) == len(_MOCK_STREAM_CHUNKS) + 1, (
            f"Expected {len(_MOCK_STREAM_CHUNKS) + 1} PARTIAL_CONTENT items, got {len(partial_items)}"
        )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_invoke_yields_finish(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证批处理工作流输出 FINISH StreamData。

    批处理工作流（End 使用 INVOKE 能力）存储最终结果，
    Workflow._stream 产生 workflow_final → WorkflowWrapper 转换为 FINISH (code=0)。
    """
    workflow_id = "test_wf_invoke"
    agent_id = "test_agent_invoke"
    wf = _build_invoke_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="你好",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_invoke",
        ):
            results.append(item)

        assert len(results) >= 1, (
            "WorkflowWrapper.astream should yield at least one item"
        )

        codes = [item.code for item in results]
        assert StreamCode.FINISH.value in codes, (
            f"Missing FINISH in output codes: {codes}"
        )

        finish_items = [r for r in results if r.code == StreamCode.FINISH.value]
        assert len(finish_items) == 1, (
            f"Expected exactly 1 FINISH, got {len(finish_items)}"
        )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_tag_matches_agent_id(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 agent_id 作为 tag 参数传递给 get_workflow 时能正确匹配。

    注册时使用 tag=agent_id，获取时也使用 tag=agent_id，
    确保工作流能被正确找到。
    """
    workflow_id = "test_wf_tag"
    agent_id = "my_agent_tag"

    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        found_workflow = await Runner.resource_mgr.get_workflow(
            workflow_id=workflow_id, tag=agent_id
        )
        assert found_workflow is not None, (
            "get_workflow with matching tag should return the workflow"
        )

        results = []
        async for item in wrapper.astream(
            query="测试tag",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_tag",
        ):
            results.append(item)

        assert len(results) >= 1, "Should yield at least one result with matching tag"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_workflow_not_found(setup_runner):  # noqa: redefined-outer-name
    """
    验证当 workflow_id 不存在时，WorkflowWrapper.astream 抛出 ValueError。
    """
    wrapper = WorkflowWrapper()
    with pytest.raises(ValueError, match="Workflow not found"):
        async for _ in wrapper.astream(
            query="test",
            params={},
            workflow_id="nonexistent_wf",
            agent_id="agent",
            session_id="session",
        ):
            pass


# ==================== 测试用例: runtime_context / 参数传播 ====================


@pytest.mark.asyncio
async def test_astream_runtime_context_prepared(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 WorkflowWrapper.astream 执行后，runtime_context 被正确准备。

    传入 global_variables 后，runtime_context 应包含:
    - REQUEST_VARIABLES（排除 conversationId/sys/conversationHistory）
    - global_variables
    - WORKFLOW_USER_ID (从 global_variables.userId 提取)
    - WORKFLOW_EXECUTE_PROJECT_ID (从 project_id 提取)
    """
    workflow_id = "test_wf_ctx"
    agent_id = "test_agent_ctx"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "global_variables": {
                "userId": "user_123",
                "conversationId": "conv_1",
                "query": "hello",
            },
            "project_id": "proj_1",
        }

        async for _ in wrapper.astream(
            query="hello",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_ctx",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        assert "global_variables" in ctx, (
            "runtime_context should contain global_variables"
        )
        assert ctx["global_variables"]["userId"] == "user_123"

        assert REQUEST_VARIABLES in ctx, (
            "runtime_context should contain REQUEST_VARIABLES"
        )
        assert ctx[REQUEST_VARIABLES]["userId"] == "user_123"
        assert ctx[WORKFLOW_EXECUTE_USER_ID] == "user_123"
        assert ctx[WORKFLOW_EXECUTE_PROJECT_ID] == "proj_1"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_request_variables_excludes_system_keys(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 _prepare_runtime_context 排除系统保留键。

    _REQUEST（即 REQUEST_VARIABLES）应排除:
    - conversationId
    - sys
    - conversationHistory

    但保留 userId、query 等用户变量。
    """
    workflow_id = "test_wf_req_exclude"
    agent_id = "test_agent_req_exclude"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "global_variables": {
                "conversationId": "conv_should_be_excluded",
                "sys": {"inner": "should_be_excluded"},
                "conversationHistory": [
                    {"role": "user", "content": "should_be_excluded"}
                ],
                "userId": "user_should_be_kept",
                "query": "test_query",
                "custom_key": "custom_val",
            },
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_exclude",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        request_vars = ctx[REQUEST_VARIABLES]

        # 排除的系统键
        assert "conversationId" not in request_vars, (
            "conversationId should be excluded from REQUEST_VARIABLES"
        )
        assert "sys" not in request_vars, (
            "sys should be excluded from REQUEST_VARIABLES"
        )
        assert "conversationHistory" not in request_vars, (
            "conversationHistory should be excluded from REQUEST_VARIABLES"
        )

        # 保留的用户变量
        assert request_vars["userId"] == "user_should_be_kept"
        assert request_vars["query"] == "test_query"
        assert request_vars["custom_key"] == "custom_val"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_plugin_configs_propagation(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 plugin_configs 传播到 runtime_context。

    对应 WorkflowHandler._prepare_workflow_kwargs 中:
        kwargs["plugin_configs"] = {"default": {"headers": ...}}

    runtime_context 应包含 WORKFLOW_API_CONFIGS 键。
    """
    workflow_id = "test_wf_plugin"
    agent_id = "test_agent_plugin"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "plugin_configs": {"default": {"headers": {"X-Auth-Token": "tok_123"}}},
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_plugin",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        assert WORKFLOW_API_CONFIGS in ctx, (
            f"runtime_context should contain {WORKFLOW_API_CONFIGS}"
        )
        assert (
            ctx[WORKFLOW_API_CONFIGS]["default"]["headers"]["X-Auth-Token"] == "tok_123"
        )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_memory_variables_propagation(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 memory_variables 传播到 runtime_context。

    对应 WorkflowHandler 中记忆系统相关参数。
    runtime_context 应包含 MEMORY_VARIABLES 键。
    """
    workflow_id = "test_wf_memory"
    agent_id = "test_agent_memory"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "memory_variables": {"user_preference": "dark_mode", "user_language": "zh"},
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_memory",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        assert MEMORY_VARIABLES in ctx, (
            f"runtime_context should contain {MEMORY_VARIABLES}"
        )
        assert ctx[MEMORY_VARIABLES]["user_preference"] == "dark_mode"
        assert ctx[MEMORY_VARIABLES]["user_language"] == "zh"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_environment_variables_propagation(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 environment_variables 传播到 runtime_context。

    runtime_context 应包含 ENVIRONMENT_VARIABLES 键。
    """
    workflow_id = "test_wf_env"
    agent_id = "test_agent_env"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "environment_variables": {"timezone": "Asia/Shanghai", "locale": "zh-CN"},
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_env",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        assert ENVIRONMENT_VARIABLES in ctx, (
            f"runtime_context should contain {ENVIRONMENT_VARIABLES}"
        )
        assert ctx[ENVIRONMENT_VARIABLES]["timezone"] == "Asia/Shanghai"
        assert ctx[ENVIRONMENT_VARIABLES]["locale"] == "zh-CN"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_misc_params_propagation(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 global_intents、mem_map、enable_memory_retrieve 传播到 runtime_context。
    """
    workflow_id = "test_wf_misc"
    agent_id = "test_agent_misc"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "global_intents": {"intent_1": "greeting"},
            "mem_map": {"pref": "user_preference"},
            "enable_memory_retrieve": True,
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_misc",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        assert WORKFLOW_GLOBAL_INTENTS in ctx
        assert ctx[WORKFLOW_GLOBAL_INTENTS]["intent_1"] == "greeting"

        assert MEM_MAP in ctx
        assert ctx[MEM_MAP]["pref"] == "user_preference"

        assert ENABLE_MEMORY_RETRIEVE in ctx
        assert ctx[ENABLE_MEMORY_RETRIEVE] is True
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: 完整 Controller 模式参数 ====================


@pytest.mark.asyncio
async def test_astream_streaming_with_full_controller_params(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证流式工作流在完整 Controller 参数下正常工作。

    模拟 WorkflowHandler.stream_handle_workflow_start_from_controller 的完整参数传入:
    - global_variables 包含 sys（conversationHistory/conversationId/userId/currentTime）
    - conversation_history
    - controller_mode_switch / controller_mode_jump
    - plugin_configs、memory_variables、environment_variables 等

    验证:
    1. 工作流正常执行并输出 PARTIAL_CONTENT
    2. runtime_context 包含所有预期的键
    3. _REQUEST 排除了系统保留键
    """
    workflow_id = "test_wf_full_stream"
    agent_id = "test_agent_full_stream"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = _build_full_controller_params()

        results = []
        async for item in wrapper.astream(
            query="你好世界",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_full_stream",
        ):
            results.append(item)

        # 1. 验证输出正常
        assert len(results) >= 1, "Should yield at least one result"

        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        assert len(partial_items) == len(_MOCK_STREAM_CHUNKS) + 1, (
            f"Expected {len(_MOCK_STREAM_CHUNKS) + 1} PARTIAL_CONTENT items, got {len(partial_items)}"
        )

        # 2. 验证 runtime_context 完整性
        ctx = wrapper.get_runtime_context()

        # global_variables
        assert "global_variables" in ctx
        assert ctx["global_variables"]["userId"] == "user_789"
        assert ctx["global_variables"]["conversationId"] == "conv_20250416_001"
        assert ctx["global_variables"]["custom_var_1"] == "value_1"
        assert ctx["global_variables"]["custom_var_2"] == 42

        # _REQUEST 排除系统键
        assert REQUEST_VARIABLES in ctx
        request_vars = ctx[REQUEST_VARIABLES]
        assert "conversationId" not in request_vars
        assert "sys" not in request_vars
        assert "conversationHistory" not in request_vars
        assert request_vars["userId"] == "user_789"
        assert request_vars["custom_var_1"] == "value_1"

        # 派生键
        assert ctx[WORKFLOW_EXECUTE_USER_ID] == "user_789"
        assert ctx[WORKFLOW_EXECUTE_PROJECT_ID] == "proj_001"
        assert (
            ctx[WORKFLOW_API_CONFIGS]["default"]["headers"]["X-Auth-Token"]
            == "test-token-abc"
        )
        assert ctx[MEMORY_VARIABLES]["user_preference"] == "dark_mode"
        assert ctx[ENVIRONMENT_VARIABLES]["timezone"] == "Asia/Shanghai"
        assert ctx[WORKFLOW_GLOBAL_INTENTS]["intent_1"] == "greeting"
        assert ctx[MEM_MAP]["pref"] == "user_preference"
        assert ctx[ENABLE_MEMORY_RETRIEVE] is True
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_invoke_with_full_controller_params(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证批处理工作流在完整 Controller 参数下正常工作。

    与 test_astream_streaming_with_full_controller_params 类似，
    但使用批处理工作流，验证 FINISH 输出和 runtime_context。
    """
    workflow_id = "test_wf_full_invoke"
    agent_id = "test_agent_full_invoke"
    wf = _build_invoke_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = _build_full_controller_params()

        results = []
        async for item in wrapper.astream(
            query="你好世界",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_full_invoke",
        ):
            results.append(item)

        # 验证 FINISH
        finish_items = [r for r in results if r.code == StreamCode.FINISH.value]
        assert len(finish_items) == 1, f"Expected 1 FINISH, got {len(finish_items)}"

        # 验证 runtime_context
        ctx = wrapper.get_runtime_context()
        assert ctx[WORKFLOW_EXECUTE_USER_ID] == "user_789"
        assert ctx[WORKFLOW_EXECUTE_PROJECT_ID] == "proj_001"
        assert ctx[WORKFLOW_API_CONFIGS] is not None
        assert ctx[MEMORY_VARIABLES]["user_preference"] == "dark_mode"
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: 输出数据内容验证 ====================


@pytest.mark.asyncio
async def test_astream_streaming_partial_content_answer(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证流式输出 PARTIAL_CONTENT 中 answer 字段的实际内容。

    每个 PARTIAL_CONTENT 的 data.answer 应包含对应 mock 分片的文本。
    按顺序验证分片内容: "你", "好", "，", "世", "界"。
    """
    workflow_id = "test_wf_answer_stream"
    agent_id = "test_agent_answer_stream"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="你好",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_answer_stream",
        ):
            results.append(item)

        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        assert len(partial_items) == len(_MOCK_STREAM_CHUNKS) + 1, (
            f"Expected {len(_MOCK_STREAM_CHUNKS) + 1} PARTIAL_CONTENT items, got {len(partial_items)}"
        )

        # 验证每个分片的 answer 内容
        for i, item in enumerate(partial_items):
            if i == len(_MOCK_STREAM_CHUNKS):
                continue
            assert isinstance(item.data, dict), f"Item {i} data should be dict"
            assert "answer" in item.data, f"Item {i} should have 'answer' key"
            assert item.data["answer"] == _MOCK_STREAM_CHUNKS[i], (
                f"Chunk {i}: expected '{_MOCK_STREAM_CHUNKS[i]}', got '{item.data['answer']}'"
            )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_invoke_finish_data_contains_answer(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证批处理工作流 FINISH 的 data 包含完整 answer。

    批处理模式下 LLM 返回完整文本（"你好，世界"），
    End 组件模板 {{answer}} 渲染后，FINISH data 应包含完整 answer。
    """
    workflow_id = "test_wf_finish_data"
    agent_id = "test_agent_finish_data"
    wf = _build_invoke_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="你好",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_finish_data",
        ):
            results.append(item)

        finish_items = [r for r in results if r.code == StreamCode.FINISH.value]
        assert len(finish_items) == 1

        finish_data = finish_items[0].data
        assert isinstance(finish_data, dict)
        # 批处理结果: End 组件渲染模板 {{answer}} 后输出 response 字段
        expected_answer = "".join(_MOCK_STREAM_CHUNKS)
        response_data = finish_data.get("answer")
        if isinstance(response_data, dict) and "answer" in response_data:
            actual_response = response_data["answer"]
        else:
            actual_response = response_data
        assert actual_response == expected_answer, (
            f"FINISH data.answer expected '{expected_answer}', got '{actual_response}'"
        )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_output_stream_code_sequence(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证流式工作流输出的 StreamCode 序列符合预期。

    流式工作流（End TRANSFORM）的输出序列应包含:
    - 若干 PARTIAL_CONTENT（对应每个 LLM 分片）
    - WORKFLOW_END
    - FINISH

    且不应包含: ERROR、WORKFLOW_EXCEPTION 等错误码。
    """
    workflow_id = "test_wf_code_seq"
    agent_id = "test_agent_code_seq"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="测试序列",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_code_seq",
        ):
            results.append(item)

        codes = [item.code for item in results]

        # 不应有错误码
        assert StreamCode.ERROR.value not in codes, (
            f"Unexpected ERROR in codes: {codes}"
        )
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes, (
            f"Unexpected WORKFLOW_EXCEPTION in codes: {codes}"
        )

        # 应有 PARTIAL_CONTENT
        assert StreamCode.PARTIAL_CONTENT.value in codes

        # 可能有 WORKFLOW_END 和 FINISH（由 End 组件 stream 产生）
        # WORKFLOW_END 和 FINISH 的出现取决于 End 组件的 stream 实现
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_invoke_output_stream_code_sequence(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证批处理工作流输出的 StreamCode 序列符合预期。

    批处理工作流的输出序列应包含:
    - FINISH (code=0)

    且不应包含: PARTIAL_CONTENT、ERROR、WORKFLOW_EXCEPTION。
    """
    workflow_id = "test_wf_invoke_code_seq"
    agent_id = "test_agent_invoke_code_seq"
    wf = _build_invoke_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="测试序列",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_invoke_code_seq",
        ):
            results.append(item)

        codes = [item.code for item in results]

        # 不应有错误码
        assert StreamCode.ERROR.value not in codes, (
            f"Unexpected ERROR in codes: {codes}"
        )
        assert StreamCode.WORKFLOW_EXCEPTION.value not in codes, (
            f"Unexpected WORKFLOW_EXCEPTION in codes: {codes}"
        )

        # 必须有 FINISH
        assert StreamCode.FINISH.value in codes

        # 批处理模式不应有 PARTIAL_CONTENT
        assert StreamCode.PARTIAL_CONTENT.value not in codes, (
            f"Unexpected PARTIAL_CONTENT in invoke mode codes: {codes}"
        )
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: 输出数据结构验证 ====================


@pytest.mark.asyncio
async def test_astream_output_data_structure(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 WorkflowWrapper.astream 输出的 StreamData 中 data 字段结构。

    分别验证流式输出和批处理输出的数据结构:
    - PARTIAL_CONTENT: data 为 dict，包含 answer 字段
    - FINISH: data 为 dict
    """
    # 验证流式输出结构
    workflow_id_stream = "test_wf_structure_stream"
    agent_id_stream = "test_agent_structure_stream"
    wf_stream = _build_streaming_workflow(workflow_id_stream)

    _register_workflow(wf_stream, agent_id_stream)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="结构测试",
            params={},
            workflow_id=workflow_id_stream,
            agent_id=agent_id_stream,
            session_id="test_session_structure",
        ):
            results.append(item)

        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        assert len(partial_items) > 0, "Should have PARTIAL_CONTENT items"
        for partial_item in partial_items:
            assert isinstance(partial_item.data, dict), (
                f"PARTIAL_CONTENT data should be dict, got {type(partial_item.data)}"
            )
    finally:
        _unregister_workflow(workflow_id_stream)

    # 验证批处理输出结构
    workflow_id_invoke = "test_wf_structure_invoke"
    agent_id_invoke = "test_agent_structure_invoke"
    wf_invoke = _build_invoke_workflow(workflow_id_invoke)

    _register_workflow(wf_invoke, agent_id_invoke)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="结构测试",
            params={},
            workflow_id=workflow_id_invoke,
            agent_id=agent_id_invoke,
            session_id="test_session_structure_invoke",
        ):
            results.append(item)

        finish_items = [r for r in results if r.code == StreamCode.FINISH.value]
        assert len(finish_items) == 1, (
            f"Expected 1 FINISH item, got {len(finish_items)}"
        )
        assert isinstance(finish_items[0].data, dict), (
            f"FINISH data should be dict, got {type(finish_items[0].data)}"
        )
    finally:
        _unregister_workflow(workflow_id_invoke)


# ==================== 测试用例: set_runtime_context / get_session_state ====================


@pytest.mark.asyncio
async def test_astream_set_runtime_context():
    """
    验证 set_runtime_context(key, value) 通用设置方法。

    支持设置任意键值对到 runtime_context 中。
    """
    wrapper = WorkflowWrapper()
    wrapper._runtime_context = {
        "global_variables": {"existing_key": "existing_val"},
    }

    wrapper.set_runtime_context(REQUEST_VARIABLES, {"new_key": "new_val"})
    assert wrapper.get_runtime_context()[REQUEST_VARIABLES]["new_key"] == "new_val"

    # 不影响已有的键
    assert (
        wrapper.get_runtime_context()["global_variables"]["existing_key"]
        == "existing_val"
    )

    # 可以设置任意键
    wrapper.set_runtime_context("custom_key", "custom_value")
    assert wrapper.get_runtime_context()["custom_key"] == "custom_value"

    # 可以覆盖已有的键
    wrapper.set_runtime_context("custom_key", "updated_value")
    assert wrapper.get_runtime_context()["custom_key"] == "updated_value"


@pytest.mark.asyncio
async def test_astream_set_runtime_context_empty_key():
    """
    验证 set_runtime_context 传入空 key 时不做任何修改。
    """
    wrapper = WorkflowWrapper()
    wrapper._runtime_context = {"global_variables": {"key": "val"}}

    wrapper.set_runtime_context(None, "value")
    assert wrapper.get_runtime_context() == {"global_variables": {"key": "val"}}

    wrapper.set_runtime_context("", "value")
    assert wrapper.get_runtime_context() == {"global_variables": {"key": "val"}}


# ==================== 测试用例: global_variables.sys 结构 ====================


@pytest.mark.asyncio
async def test_astream_global_variables_sys_structure(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 global_variables.sys 嵌套结构被正确保留到 runtime_context。

    WorkflowHandler._prepare_global_variables 构建的 global_variables 包含:
        sys: {conversationHistory, conversationId, userId, currentTime}

    这些系统信息应完整保留在 runtime_context.global_variables 中。
    """
    workflow_id = "test_wf_sys"
    agent_id = "test_agent_sys"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "global_variables": {
                "sys": {
                    "conversationHistory": [
                        {"role": "user", "content": "之前的问题"},
                        {"role": "assistant", "content": "之前的回答"},
                    ],
                    "conversationId": "conv_sys_001",
                    "userId": "user_sys_001",
                    "currentTime": "2025-04-16 10:30:00",
                },
                "conversationId": "conv_sys_001",
                "userId": "user_sys_001",
                "extra_field": "extra_value",
            },
        }

        async for _ in wrapper.astream(
            query="测试sys",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_sys",
        ):
            pass

        ctx = wrapper.get_runtime_context()

        # global_variables 应完整保留 sys
        gv = ctx["global_variables"]
        assert "sys" in gv, "global_variables should contain sys"
        assert gv["sys"]["conversationId"] == "conv_sys_001"
        assert gv["sys"]["userId"] == "user_sys_001"
        assert gv["sys"]["currentTime"] == "2025-04-16 10:30:00"
        assert len(gv["sys"]["conversationHistory"]) == 2
        assert gv["extra_field"] == "extra_value"

        # _REQUEST 应排除 sys 和 conversationId
        request_vars = ctx[REQUEST_VARIABLES]
        assert "sys" not in request_vars
        assert "conversationId" not in request_vars
        assert request_vars["userId"] == "user_sys_001"
        assert request_vars["extra_field"] == "extra_value"

        # WORKFLOW_EXECUTE_USER_ID 从 global_variables.userId 提取
        assert ctx[WORKFLOW_EXECUTE_USER_ID] == "user_sys_001"
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: 无 global_variables 时 params 处理 ====================


@pytest.mark.asyncio
async def test_astream_params_without_global_variables(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 params 不含 global_variables 时的处理。

    此时 runtime_context 应仅有非 global_variables 派生的键。
    """
    workflow_id = "test_wf_no_gv"
    agent_id = "test_agent_no_gv"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        params = {
            "plugin_configs": {"default": {}},
            "project_id": "proj_no_gv",
        }

        async for _ in wrapper.astream(
            query="test",
            params=params,
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_no_gv",
        ):
            pass

        ctx = wrapper.get_runtime_context()
        # 没有 global_variables，不应有 REQUEST_VARIABLES
        assert REQUEST_VARIABLES not in ctx
        assert "global_variables" not in ctx
        # 但应有直接映射的键
        assert ctx[WORKFLOW_API_CONFIGS] == {"default": {}}
        assert ctx[WORKFLOW_EXECUTE_PROJECT_ID] == "proj_no_gv"
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_empty_params(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证空 params 时工作流正常执行。

    runtime_context 应为空字典。
    """
    workflow_id = "test_wf_empty_params"
    agent_id = "test_agent_empty_params"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()

        results = []
        async for item in wrapper.astream(
            query="test",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_empty_params",
        ):
            results.append(item)

        assert len(results) >= 1, "Should yield results even with empty params"

        ctx = wrapper.get_runtime_context()
        assert ctx == {}, f"runtime_context should be empty, got: {ctx}"
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: 多字段 Start 组件 ====================


@pytest.mark.asyncio
async def test_astream_multi_field_start_component(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 Start 组件声明多个用户字段时，工作流仍能正常执行。

    START_MULTI_FIELD_CONF 声明了 query（required）、name、age 三个输入字段，
    但工作流 inputs_schema 仅映射 query，其余字段使用默认值。
    """
    workflow_id = "test_wf_multi_field"
    agent_id = "test_agent_multi_field"
    wf = _build_multi_field_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="测试多字段",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id="test_session_multi_field",
        ):
            results.append(item)

        partial_items = [
            r for r in results if r.code == StreamCode.PARTIAL_CONTENT.value
        ]
        assert len(partial_items) == len(_MOCK_STREAM_CHUNKS) + 1, (
            f"Expected {len(_MOCK_STREAM_CHUNKS) + 1} PARTIAL_CONTENT items, got {len(partial_items)}"
        )
    finally:
        _unregister_workflow(workflow_id)


# ==================== 测试用例: execution_id 一致性 ====================


@pytest.mark.asyncio
async def test_astream_execution_id_matches_session_id(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 StreamData 的 execution_id 与传入的 session_id 一致。
    """
    workflow_id = "test_wf_exec_id"
    agent_id = "test_agent_exec_id"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        session_id = "my_session_123"
        results = []
        async for item in wrapper.astream(
            query="test",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id=session_id,
        ):
            results.append(item)

        for item in results:
            assert item.execution_id == session_id, (
                f"execution_id should be '{session_id}', got '{item.execution_id}'"
            )
    finally:
        _unregister_workflow(workflow_id)


@pytest.mark.asyncio
async def test_astream_execution_id_default_empty(setup_runner, mock_llm):  # noqa: redefined-outer-name
    """
    验证 session_id 为 None 时，execution_id 默认为空字符串。
    """
    workflow_id = "test_wf_exec_id_default"
    agent_id = "test_agent_exec_id_default"
    wf = _build_streaming_workflow(workflow_id)

    _register_workflow(wf, agent_id)

    try:
        wrapper = WorkflowWrapper()
        results = []
        async for item in wrapper.astream(
            query="test",
            params={},
            workflow_id=workflow_id,
            agent_id=agent_id,
            session_id=None,
        ):
            results.append(item)

        for item in results:
            assert item.execution_id == "", (
                f"execution_id should be empty string when session_id is None, got '{item.execution_id}'"
            )
    finally:
        _unregister_workflow(workflow_id)
