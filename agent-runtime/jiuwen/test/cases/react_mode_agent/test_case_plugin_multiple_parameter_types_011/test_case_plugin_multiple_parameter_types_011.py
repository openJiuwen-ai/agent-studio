#!/usr/bin/env python
"""南向契约测试 -- ReAct 模式 AgentCoreRestfulLayer 路径 E2E 验证 (case 011)

场景：单轮 ReAct，LLM 调用 mock_plugin_header 插件（method=Headers），
      通过 USE_TOOL_WRAPPER=true 走 AgentCoreRestfulLayer 路径。
Mock 策略：
  - LLM: BaseChatModel.astream → _ScriptedLLM（按录制顺序返回 AIMessage）
  - Plugin: AgentCoreRestfulLayer.ainvoke → 返回录制的插件输出
验证：逐条 SSE 事件严格比对 resource/mock_e2e_output.txt 录制日志。
"""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("PLUGIN_SSL_API_CERT_KEY", "false")
os.environ["USE_TOOL_WRAPPER"] = "true"

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.insight.manager import TraceManager
from jiuwen.integration.agent_core_restful_new import AgentCoreRestfulLayer
from jiuwen.planner.common.plan_runtime_context import PlanRuntimeContext
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import (
    distribute_execution_request,
    prepare_params,
)
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[3]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
AGENT_DIR = CASE_DIR / "agent"
RESOURCE_DIR = CASE_DIR / "resource"

# ---------------------------------------------------------------------------
# Mock 基础设施
# ---------------------------------------------------------------------------
_mocks: dict = {"llm": None}
_plugin_calls: list = []  # [(inputs, kwargs), ...]


class _FallbackChatModel(BaseChatModel):
    """Patch 用的空壳 model，不会真正被调用。"""

    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _ScriptedLLM:
    """预设 LLM 返回值。astream yield AIMessage。"""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.call_count = 0

    async def astream(self, inputs, **kwargs):
        self.call_count += 1
        msg = self.outputs.pop(0) if self.outputs else AIMessage(content="0")
        yield AIMessage(
            content="",
            usage_metadata=UsageMetadata(code=0, errmsg="成功", finish_reason=""),
        )
        if not msg.usage_metadata:
            fr = "function_call" if msg.tool_calls else "stop"
            msg.usage_metadata = UsageMetadata(code=0, errmsg="成功", finish_reason=fr)
        yield msg


# ---------------------------------------------------------------------------
# 录制数据加载
# ---------------------------------------------------------------------------
def _load_recorded_plugin_output() -> dict:
    """从 resource/mock_react_plugin_input_and_output.txt 解析插件输出。"""
    txt = (RESOURCE_DIR / "mock_react_plugin_input_and_output.txt").read_text(
        encoding="utf-8"
    )
    # 找到 "mock 插件输出" 行之后的 dict
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("{") and "'errCode'" in line:
            # Python repr dict → 用 ast.literal_eval
            import ast

            return ast.literal_eval(line)
    raise ValueError("Cannot parse plugin output from resource file")


def _load_expected_sse_events() -> list:
    """从 resource/mock_e2e_output.txt 解析期望的 SSE 事件列表。"""
    txt = (RESOURCE_DIR / "mock_e2e_output.txt").read_text(encoding="utf-8")
    events = []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# Contract Runtime 初始化
# ---------------------------------------------------------------------------
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    os.environ["USE_TOOL_WRAPPER"] = "true"
    _mocks["llm"] = None
    _plugin_calls.clear()

    # Patch 1: ModelFactory → 空壳 model
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *a, **kw: _FallbackChatModel(),
    )

    # Patch 2: 初始化 prompt manager
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template dir not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    # Patch 3: BaseChatModel.astream → _mocks["llm"]
    original_astream = BaseChatModel.astream

    async def _patched_astream(self, inputs, **kwargs):
        llm = _mocks["llm"]
        if llm is not None and hasattr(llm, "astream"):
            async for item in llm.astream(inputs, **kwargs):
                yield item
            return
        async for item in original_astream(self, inputs, **kwargs):
            yield item

    monkeypatch.setattr(BaseChatModel, "astream", _patched_astream)

    # Patch 4: AgentCoreRestfulLayer.ainvoke → 记录调用 + 返回录制结果
    recorded_output = _load_recorded_plugin_output()

    async def _patched_layer_ainvoke(self, inputs, **kwargs):
        _plugin_calls.append((inputs, kwargs))
        return recorded_output

    monkeypatch.setattr(AgentCoreRestfulLayer, "ainvoke", _patched_layer_ainvoke)

    # Patch 5: create_workflow_instance → no-op
    async def _noop_create_workflow_instance(wf_ctx, conversation_id, user_id):
        return None

    monkeypatch.setattr(
        WorkflowHandler,
        "create_workflow_instance",
        staticmethod(_noop_create_workflow_instance),
    )


# ---------------------------------------------------------------------------
# IR 加载与执行
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_ir_to_tmp(tmp_path: Path) -> Path:
    """复制 Agent IR 到临时目录，修改 method=Body → Headers。"""
    agent_files = list(AGENT_DIR.glob("*.json"))
    if len(agent_files) != 1:
        raise AssertionError(
            f"Expected exactly one agent json in {AGENT_DIR}, found {len(agent_files)}"
        )
    agent_ir = _load_json(agent_files[0])

    # 修改参数传递方式为 Headers（与录制时一致）
    plugins = agent_ir.get("configs", {}).get("plugins", [])
    if plugins and plugins[0].get("arguments"):
        plugins[0]["arguments"][0]["method"] = "Headers"

    agent_dst = tmp_path / agent_files[0].name
    agent_dst.write_text(
        json.dumps(agent_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return agent_dst


async def _run_local_ir(
    *, ir_path, query, conversation_id, conversation_history=None, params=None
):
    if conversation_history is None:
        conversation_history = []
    if params is None:
        params = {}

    default_params = {
        "conversationHistory": conversation_history,
        "pluginConfigs": [],
        "llmExtraConfigs": {},
        "workflowSequence": [],
        "activeWorkflows": [],
        "globalVariables": {
            "sys": {
                "conversationHistory": [],
                "conversationId": conversation_id,
                "userId": None,
            },
            "conversationId": conversation_id,
            "userId": None,
        },
    }
    default_params.update(params)

    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id,
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": default_params,
            "headers": {
                "Content-Type": "application/json",
                "x-code": "123",
                "name": "Tom",
                "userid": "1212",
                "status": "123.1",
            },
        }
    )

    # 预处理：将 headers 合并到 plugin_configs（与真实服务端一致）
    req.params = prepare_params(req)

    from jiuwen.serve.controllers.execution.open_utils import async_ir_load

    ir_data = await async_ir_load(str(ir_path))
    ir_type = IRConverter.identify_ir(ir_data)

    if ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
        if hasattr(instance, "context_manager"):
            instance.context_manager.agent_config.agent_id = ir_data.get("agentId", "")
    else:
        raise AssertionError(f"Expected Agent IR type, got: {ir_type.name}")

    execution_data = ExecutionData(
        instance=instance, instance_type=ir_type, updated_time=int(time.time() * 1000)
    )
    fake_request = type("LocalRequest", (), {"headers": req.headers})()
    token = request_context.set(fake_request)
    try:
        response = await distribute_execution_request(req, execution_data)
    finally:
        request_context.reset(token)

    body = []
    async for chunk in response.body_iterator:
        body.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
    return "".join(body)


# ---------------------------------------------------------------------------
# SSE 解析 & 断言
# ---------------------------------------------------------------------------
def _parse_sse_events(response_text: str) -> list:
    events = []
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# 动态字段：每次运行都不同，跳过比对
_SKIP_KEYS = frozenset(
    {
        "createdTime",
        "executionId",
        "isStructMessage",
        "time_consumption",
        "overall_latency",
        "plugin_latency",
        "total_latency",
        "model_latency",
        "wait_latency",
        "tool_call_id",
        "id",
        "latency",
    }
)


def _strip_dynamic(obj):
    """递归移除动态字段，返回新对象用于比对。"""
    if isinstance(obj, dict):
        return {k: _strip_dynamic(v) for k, v in obj.items() if k not in _SKIP_KEYS}
    elif isinstance(obj, list):
        return [_strip_dynamic(item) for item in obj]
    return obj


def _assert_sse_strict(actual_events, expected_events):
    """逐条严格比对 SSE 事件（去除动态字段后）。"""
    # 先比对事件数量
    assert len(actual_events) == len(expected_events), (
        f"SSE event count mismatch: expected={len(expected_events)}, actual={len(actual_events)}\n"
        f"  expected types: {[e.get('event') for e in expected_events]}\n"
        f"  actual types:   {[e.get('event') for e in actual_events]}"
    )

    # 再比对事件类型序列
    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"SSE event type sequence mismatch:\n"
        f"  expected: {expected_types}\n"
        f"  actual:   {actual_types}"
    )

    # 逐条比对内容（去除动态字段）
    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        actual_clean = _strip_dynamic(actual)
        expected_clean = _strip_dynamic(expected)
        assert actual_clean == expected_clean, (
            f"SSE event[{i}] ({expected.get('event')}) content mismatch:\n"
            f"  expected: {json.dumps(expected_clean, ensure_ascii=False, indent=2)}\n"
            f"  actual:   {json.dumps(actual_clean, ensure_ascii=False, indent=2)}"
        )


def _assert_plugin_inputs(captured_inputs, captured_kwargs):
    """验证 AgentCoreRestfulLayer.ainvoke 收到的 inputs 和 kwargs 与录制一致。"""
    # 1. inputs 严格比对
    assert captured_inputs == {"query": "Jerry"}, (
        f"Plugin inputs mismatch: expected={{'query': 'Jerry'}}, actual={captured_inputs}"
    )

    # 2. kwargs 键集合
    expected_keys = {
        "task_id",
        "prompt_info",
        "plugins",
        "workflows",
        "contexts",
        "runtime_context",
        "multimodal_image",
        "mcps",
        "trace_handlers",
    }
    assert set(captured_kwargs.keys()) == expected_keys, (
        f"Plugin kwargs keys mismatch:\n"
        f"  expected: {sorted(expected_keys)}\n"
        f"  actual:   {sorted(captured_kwargs.keys())}"
    )

    # 3. 简单值字段（task_id 是动态生成的，测试环境未设置中间件所以为空，跳过）
    assert captured_kwargs["prompt_info"] is None, (
        f"prompt_info should be None, got: {captured_kwargs['prompt_info']!r}"
    )
    assert captured_kwargs["workflows"] == [], (
        f"workflows should be [], got: {captured_kwargs['workflows']!r}"
    )
    assert captured_kwargs["contexts"] is None, (
        f"contexts should be None, got: {captured_kwargs['contexts']!r}"
    )
    assert captured_kwargs["multimodal_image"] is None, (
        f"multimodal_image should be None, got: {captured_kwargs['multimodal_image']!r}"
    )
    assert captured_kwargs["mcps"] == [], (
        f"mcps should be [], got: {captured_kwargs['mcps']!r}"
    )

    # 4. plugins: list of 1 RestFulAPI instance
    plugins = captured_kwargs["plugins"]
    assert isinstance(plugins, list) and len(plugins) == 1, (
        f"plugins should be list of 1, got: {type(plugins).__name__} len={len(plugins)}"
    )
    assert isinstance(plugins[0], RestFulAPI), (
        f"plugins[0] should be RestFulAPI, got: {type(plugins[0]).__name__}"
    )

    # 5. trace_handlers: TraceManager instance
    assert isinstance(captured_kwargs["trace_handlers"], TraceManager), (
        f"trace_handlers should be TraceManager, got: "
        f"{type(captured_kwargs['trace_handlers']).__name__}"
    )

    # 6. runtime_context: PlanRuntimeContext with expected fields
    rc = captured_kwargs["runtime_context"]
    assert isinstance(rc, PlanRuntimeContext), (
        f"runtime_context should be PlanRuntimeContext, got: {type(rc).__name__}"
    )

    # 6a. api_config.headers 中的自定义 headers
    headers = rc.api_config.get("headers", {})
    assert headers.get("x-code") == "123", (
        f"runtime_context headers x-code mismatch: {headers.get('x-code')!r}"
    )
    assert headers.get("name") == "Tom", (
        f"runtime_context headers name mismatch: {headers.get('name')!r}"
    )
    assert headers.get("userid") == "1212", (
        f"runtime_context headers userid mismatch: {headers.get('userid')!r}"
    )
    assert headers.get("status") == "123.1", (
        f"runtime_context headers status mismatch: {headers.get('status')!r}"
    )
    assert "content-type" in headers or "Content-Type" in headers, (
        "runtime_context headers missing content-type"
    )

    # 6b. workflow_req_params
    wf_ctx = rc.agent_workflow_context or {}
    wf_params = wf_ctx.get("workflow_req_params", {})

    # global_variables（通过请求 globalVariables 传入，与录制一致）
    gv = wf_params.get("global_variables", {})
    assert gv.get("conversationId") == "conversation_BrcLnUez", (
        f"global_variables.conversationId mismatch: {gv.get('conversationId')!r}"
    )
    sys_vars = gv.get("sys", {})
    assert sys_vars.get("conversationId") == "conversation_BrcLnUez", (
        f"global_variables.sys.conversationId mismatch: {sys_vars.get('conversationId')!r}"
    )

    # plugin_configs（通过 prepare_params 预处理，headers 合并到 default）
    pc = wf_params.get("plugin_configs", {})
    assert isinstance(pc, dict), (
        f"plugin_configs should be dict after prepare_params, got: {type(pc).__name__}"
    )
    default_pc = pc.get("default", {})
    assert default_pc.get("x-code") == "123", (
        f"plugin_configs.default.x-code mismatch: {default_pc.get('x-code')!r}"
    )
    assert default_pc.get("name") == "Tom", (
        f"plugin_configs.default.name mismatch: {default_pc.get('name')!r}"
    )

    # 其他 workflow_req_params 字段
    assert wf_params.get("conversation_history") == [], (
        f"conversation_history should be [], got: {wf_params.get('conversation_history')!r}"
    )
    assert wf_params.get("workflow_sequence") == [], (
        f"workflow_sequence should be [], got: {wf_params.get('workflow_sequence')!r}"
    )
    assert wf_params.get("active_workflows") == [], (
        f"active_workflows should be [], got: {wf_params.get('active_workflows')!r}"
    )
    assert wf_params.get("enable_history") is True, (
        f"enable_history should be True, got: {wf_params.get('enable_history')!r}"
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("plugin_header_param_011")
    return _copy_ir_to_tmp(tmp_path)


# ===========================================================================
# 测试用例
# ===========================================================================
class TestCasePluginMultipleParameterTypes011:
    """ReAct 模式 AgentCoreRestfulLayer 路径 E2E 契约测试。

    单轮请求：LLM tool_call → plugin(mock_plugin_header) → LLM final answer
    通过 USE_TOOL_WRAPPER=true 走 AgentCoreRestfulLayer 路径。
    验证：SSE 事件序列严格比对 resource/mock_e2e_output.txt 录制日志。
    """

    def test_e2e_sse_output(self, local_ir_path):
        conversation_id = "conversation_BrcLnUez"

        # 插件返回值（与录制一致）
        PLUGIN_RESULT = (
            "Host: fakeIp:5003\r\n"
            "Query: Jerry\r\n"
            "X-Request-Id: f56a8045-d547-464a-aa03-2d91eb1d8316\r\n"
            "X-Execution-Id: 053e4bcb-2b36-4529-8c47-c0e4f2570401\r\n"
            "Accept: */*\r\n"
            "Accept-Encoding: gzip, deflate\r\n"
            "User-Agent: Python/3.11 aiohttp/3.13.3\r\n"
            "Content-Length: 2\r\n"
            "Content-Type: application/json\r\n\r\n"
        )
        PLUGIN_RESULT_JSON = json.dumps({"outname": PLUGIN_RESULT})

        # 设置 LLM mock（两次调用）
        llm = _ScriptedLLM(
            [
                # 第1次：tool_call
                AIMessage(
                    content='mock_plugin_header|{"query": "Jerry"}',
                    tool_calls=[
                        ToolCall(
                            name="mock_plugin_header", args={"query": "Jerry"}, id=""
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0, errmsg="成功", finish_reason="function_call"
                    ),
                ),
                # 第2次：final answer
                AIMessage(
                    content=PLUGIN_RESULT_JSON,
                    usage_metadata=UsageMetadata(
                        code=0, errmsg="成功", finish_reason="stop"
                    ),
                ),
            ]
        )
        _mocks["llm"] = llm

        # 执行
        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用mock_plugin_header输入Jerry",
                conversation_id=conversation_id,
            )
        )

        # 解析实际 SSE 事件
        actual_events = _parse_sse_events(response_text)

        # 加载期望 SSE 事件
        expected_events = _load_expected_sse_events()

        # 打印实际事件（调试用）
        print("\n--- Actual SSE Events ---")
        for i, ev in enumerate(actual_events):
            print(
                f"  [{i}] event={ev.get('event')} "
                f"data_keys={list(ev.get('data', {}).keys())}"
            )

        # 严格比对
        _assert_sse_strict(actual_events, expected_events)

        # 验证 plugin 被调用，inputs 和 kwargs 与录制一致
        assert len(_plugin_calls) == 1, (
            f"Expected 1 plugin call, got {len(_plugin_calls)}"
        )
        _assert_plugin_inputs(_plugin_calls[0][0], _plugin_calls[0][1])

        # 清理
        _mocks["llm"] = None
        _plugin_calls.clear()
