#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""End-to-end tests for TraceManager openjiuwen Tracer dual-write.

测试策略：
1. 集成测试：通过 TraceManager 触发事件，验证 openjiuwen Tracer 推送的 SSE 数据
2. 端到端测试：模拟完整 Agent 调用流程（Chain → LLM → Plugin → LLM）

注意：_oj_trigger 现在直接调用异步 trigger，在 @pytest.mark.asyncio 测试中
事件会同步完成，但仍建议 await asyncio.sleep(0) 确保事件循环处理完毕。
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from jiuwen.insight.manager import TraceManager, get_child_manager

from openjiuwen.core.session.tracer.tracer import Tracer
from openjiuwen.core.session.tracer.span import TraceAgentSpan, SpanManager
from openjiuwen.core.session.stream.emitter import StreamEmitter
from openjiuwen.core.session.stream.manager import StreamWriterManager


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_initialized_tracer() -> tuple:
    """创建一个完整初始化的 Tracer（含 StreamWriterManager）。

    Returns:
        (tracer, emitter)
    """
    tracer = Tracer()
    emitter = StreamEmitter()
    swm = StreamWriterManager(emitter)
    tracer.init(swm)
    return tracer, emitter


async def _collect_traces(emitter: StreamEmitter, timeout: float = 2.0) -> List[dict]:
    """从 StreamEmitter 中异步读取所有 trace 数据。

    Returns:
        list of TraceSchema 验证后的 dict，每个 dict 包含 type 和 payload。
    """
    traces = []
    while True:
        try:
            data = await asyncio.wait_for(
                emitter.stream_queue.receive(), timeout=timeout
            )
            if data == StreamEmitter.END_FRAME:
                break
            traces.append(data)
        except asyncio.TimeoutError:
            break
    return traces


def _extract_payloads(traces: list) -> List[dict]:
    """从 trace 列表中提取 payload dict。

    TraceSchema 验证后的数据是 Pydantic model，需要转为 dict。
    """
    payloads = []
    for t in traces:
        if hasattr(t, "payload"):
            payload = t.payload
            if hasattr(payload, "model_dump"):
                payload = payload.model_dump(by_alias=True)
            elif not isinstance(payload, dict):
                payload = dict(payload)
            payloads.append(payload)
        elif isinstance(t, dict):
            p = t.get("payload", {})
            if hasattr(p, "model_dump"):
                p = p.model_dump(by_alias=True)
            payloads.append(p)
    return payloads


def _find_by_invoke_type(payloads: List[dict], invoke_type: str) -> List[dict]:
    """从 payload 列表中筛选指定 invokeType 的记录。"""
    return [p for p in payloads if p.get("invokeType") == invoke_type]


async def _drain_pending_coroutines():
    """让出事件循环控制权，确保异步 trigger 完成执行。"""
    await asyncio.sleep(0.05)


def _make_child_manager(
    parent: TraceManager,
    instance_info: dict,
) -> TraceManager:
    """创建带 instance_info 的子 TraceManager。

    get_child_manager 不传递 instance_info，而 openjiuwen 的
    TraceAgentHandler._update_start_trace_data 需要 instance_info
    来设置 invoke_type 和 name，因此需要手动创建子 manager。
    """
    child = TraceManager(
        trace_handlers=[],
        parent_invoke_id=parent.invoke_id,
        instance_info=instance_info,
    )
    # 继承 openjiuwen 双写状态
    child._oj_tracer = parent._oj_tracer
    child._oj_span_map = parent._oj_span_map
    child._oj_root_span = parent._oj_root_span
    return child


# ── Test: Span 生命周期单元测试 ──────────────────────────────────────────────


class TestSpanLifecycle:
    """测试 Span 创建、invoke_id 覆盖、父子关系、清理。"""

    def setup_method(self):
        self.tracer, self.emitter = _create_initialized_tracer()
        self.tm = TraceManager(openjiuwen_tracer=self.tracer)

    def test_get_or_create_span_creates_new(self):
        span = self.tm._oj_get_or_create_span("invoke-001")
        assert isinstance(span, TraceAgentSpan)
        assert span.invoke_id == "invoke-001"

    def test_get_or_create_span_returns_existing(self):
        span1 = self.tm._oj_get_or_create_span("invoke-001")
        span2 = self.tm._oj_get_or_create_span("invoke-001")
        assert span1 is span2

    def test_get_or_create_span_parent_child(self):
        span_parent = self.tm._oj_get_or_create_span("invoke-parent")
        span_child = self.tm._oj_get_or_create_span("invoke-child", parent_invoke_id="invoke-parent")
        assert span_child.parent_invoke_id == span_parent.invoke_id

    def test_get_or_create_span_fallback_to_agent_root(self):
        span = self.tm._oj_get_or_create_span("invoke-001")
        # 没有 parent_invoke_id 时，parent 应该是 _oj_root_span
        assert span.parent_invoke_id == self.tm._oj_root_span.invoke_id

    def test_cleanup_span(self):
        self.tm._oj_get_or_create_span("invoke-001")
        assert "invoke-001" in self.tm._oj_span_map
        self.tm._oj_cleanup_span("invoke-001")
        assert "invoke-001" not in self.tm._oj_span_map

    def test_cleanup_span_idempotent(self):
        self.tm._oj_get_or_create_span("invoke-001")
        self.tm._oj_cleanup_span("invoke-001")
        self.tm._oj_cleanup_span("invoke-001")  # 不应抛异常
        assert "invoke-001" not in self.tm._oj_span_map


class TestAgentRootSpan:
    """测试 Agent 根 Span 的创建。"""

    def test_agent_root_span_created_on_init(self):
        tracer, _ = _create_initialized_tracer()
        tm = TraceManager(openjiuwen_tracer=tracer)
        assert tm._oj_root_span is not None
        assert tm._oj_root_span.invoke_type == "agent"
        assert tm._oj_root_span.name == "agent"

    def test_agent_root_span_is_in_span_manager(self):
        tracer, _ = _create_initialized_tracer()
        tm = TraceManager(openjiuwen_tracer=tracer)
        root_id = tm._oj_root_span.invoke_id
        span = tracer.tracer_agent_span_manager.get_span(root_id)
        assert span is not None
        assert span.invoke_type == "agent"

    def test_all_spans_without_parent_link_to_root(self):
        tracer, _ = _create_initialized_tracer()
        tm = TraceManager(openjiuwen_tracer=tracer)

        # 创建多个没有显式 parent 的 span
        span_a = tm._oj_get_or_create_span("a")
        span_b = tm._oj_get_or_create_span("b")

        # 都应该以 _oj_root_span 为 parent
        assert span_a.parent_invoke_id == tm._oj_root_span.invoke_id
        assert span_b.parent_invoke_id == tm._oj_root_span.invoke_id

    def test_no_tracer_no_root_span(self):
        """不传 openjiuwen_tracer 时，不应创建 root span。"""
        tm = TraceManager()
        assert tm._oj_root_span is None
        assert tm._oj_tracer is None


# ── Test: TraceManager 双写集成测试 ──────────────────────────────────────────


class TestTraceManagerDualWrite:
    """测试 TraceManager 的 openjiuwen Tracer 双写。"""

    def setup_method(self):
        self.tracer, self.emitter = _create_initialized_tracer()
        self.instance_info = {"class_name": "TestAgent", "type": "chain"}

    @pytest.mark.asyncio
    async def test_chain_start_end_triggers_tracer(self):
        """Chain start/end 事件应触发 openjiuwen tracer 并推送 SSE 数据。"""
        trace_manager = TraceManager(
            instance_info=self.instance_info,
            openjiuwen_tracer=self.tracer,
        )

        # 触发 chain start
        await trace_manager.on_chain_start(inputs={"query": "你好"})
        chain_invoke_id = trace_manager.invoke_id

        # 触发 chain end
        await trace_manager.on_chain_end(outputs={"content": "回复"})

        # 等待异步 trigger 完成
        await _drain_pending_coroutines()

        # 收集 trace 数据
        await self.emitter.close()
        traces = await _collect_traces(self.emitter)
        payloads = _extract_payloads(traces)

        # 验证：应该有 2 条 chain trace（start + end）
        chain_traces = _find_by_invoke_type(payloads, "chain")
        assert len(chain_traces) == 2

        # 验证 start
        start_trace = chain_traces[0]
        assert start_trace["status"] == "start"
        assert start_trace["name"] == "TestAgent"
        assert start_trace["inputs"] == {"inputs": {"query": "你好"}}
        assert start_trace["invokeId"] == chain_invoke_id

        # 验证 end
        end_trace = chain_traces[1]
        assert end_trace["status"] == "finish"
        assert end_trace["outputs"] == {"content": "回复"}
        assert end_trace["elapsedTime"] is not None

    @pytest.mark.asyncio
    async def test_llm_start_end_triggers_tracer(self):
        """LLM start/end 事件应触发 openjiuwen tracer。"""
        trace_manager = TraceManager(
            instance_info={"class_name": "OpenAI", "type": "llm"},
            openjiuwen_tracer=self.tracer,
        )

        await trace_manager.on_llm_start(inputs=[{"role": "user", "content": "hello"}])
        await trace_manager.on_llm_end(outputs={"content": "world"})

        await _drain_pending_coroutines()

        await self.emitter.close()
        traces = await _collect_traces(self.emitter)
        payloads = _extract_payloads(traces)

        llm_traces = _find_by_invoke_type(payloads, "llm")
        assert len(llm_traces) == 2

        start_trace = llm_traces[0]
        assert start_trace["invokeType"] == "llm"
        assert start_trace["name"] == "OpenAI"
        assert start_trace["inputs"] == {"inputs": [{"role": "user", "content": "hello"}]}

        end_trace = llm_traces[1]
        assert end_trace["outputs"] == {"content": "world"}

    @pytest.mark.asyncio
    async def test_plugin_start_end_triggers_tracer(self):
        """Plugin start/end 事件应触发 openjiuwen tracer。"""
        trace_manager = TraceManager(
            instance_info={"class_name": "weather_tool", "type": "plugin"},
            openjiuwen_tracer=self.tracer,
        )

        await trace_manager.on_plugin_start(inputs={"city": "北京"})
        await trace_manager.on_plugin_end(outputs={"temp": "28°C"})

        await _drain_pending_coroutines()

        await self.emitter.close()
        traces = await _collect_traces(self.emitter)
        payloads = _extract_payloads(traces)

        plugin_traces = _find_by_invoke_type(payloads, "plugin")
        assert len(plugin_traces) == 2

        start_trace = plugin_traces[0]
        assert start_trace["invokeType"] == "plugin"
        assert start_trace["name"] == "weather_tool"
        assert start_trace["inputs"] == {"inputs": {"city": "北京"}}

    @pytest.mark.asyncio
    async def test_error_triggers_tracer(self):
        """Error 事件应触发 openjiuwen tracer 并设置 error 字段。"""
        trace_manager = TraceManager(
            instance_info={"class_name": "TestLLM", "type": "llm"},
            openjiuwen_tracer=self.tracer,
        )

        await trace_manager.on_llm_start(inputs="test")
        await trace_manager.on_llm_error(error=RuntimeError("timeout"))

        await _drain_pending_coroutines()

        await self.emitter.close()
        traces = await _collect_traces(self.emitter)
        payloads = _extract_payloads(traces)

        llm_traces = _find_by_invoke_type(payloads, "llm")
        # start + error = 2 条
        assert len(llm_traces) == 2

        error_trace = llm_traces[1]
        assert error_trace["status"] == "error"
        assert error_trace["error"] is not None
        assert "timeout" in error_trace["error"]["message"]

    def test_no_tracer_no_dual_write(self):
        """不传 openjiuwen_tracer 时，不应初始化双写状态。"""
        trace_manager = TraceManager(instance_info=self.instance_info)
        assert trace_manager._oj_tracer is None
        assert trace_manager._oj_root_span is None


class TestTraceManagerGenerateManagerWithTracer:
    """测试 generate_manager 透传 session 并提取 tracer。"""

    @pytest.mark.asyncio
    async def test_generate_manager_with_session(self):
        """generate_manager 应从 session 中提取 tracer 并启用双写。"""
        tracer, emitter = _create_initialized_tracer()

        # 构造 mock session，其 _inner.tracer() 返回 tracer
        mock_session = MagicMock()
        mock_session._inner.tracer.return_value = tracer

        trace_manager = TraceManager.generate_manager(
            instance_info={"class_name": "Agent", "type": "chain"},
            session=mock_session,
        )

        # 验证双写已启用
        assert trace_manager._oj_tracer is tracer
        assert trace_manager._oj_root_span is not None

        # 触发事件验证可以正常打点
        await trace_manager.on_chain_start(inputs={"query": "test"})
        await trace_manager.on_chain_end(outputs={"result": "ok"})

        await _drain_pending_coroutines()

        await emitter.close()
        traces = await _collect_traces(emitter)
        payloads = _extract_payloads(traces)

        chain_traces = _find_by_invoke_type(payloads, "chain")
        assert len(chain_traces) == 2


class TestGetChildManagerInheritsDualWrite:
    """测试 get_child_manager 自动继承双写状态。"""

    def test_child_manager_inherits_dual_write(self):
        tracer, _ = _create_initialized_tracer()

        parent = TraceManager(
            instance_info={"class_name": "Agent", "type": "chain"},
            openjiuwen_tracer=tracer,
        )
        parent.get_run_id()

        child = get_child_manager(parent, name="llm_child")

        # 子 manager 应继承双写状态
        assert child._oj_tracer is tracer
        assert child._oj_span_map is parent._oj_span_map
        assert child._oj_root_span is parent._oj_root_span

        # 子 manager 的 parent_invoke_id 应等于 parent 的 invoke_id
        assert child.parent_invoke_id == parent.invoke_id


# ── Test: 端到端场景 ─────────────────────────────────────────────────────────


class TestEndToEndAgentScenario:
    """端到端场景：模拟 Agent 一次完整调用（Chain → LLM → Plugin → LLM）。"""

    @pytest.mark.asyncio
    async def test_full_agent_invocation_trace(self):
        """模拟完整 Agent 调用流程，验证所有 trace 数据正确推送。

        场景：用户查询北京天气
        流程：Chain(Agent入口) → LLM(推理) → Plugin(天气查询) → LLM(总结) → Chain(结束)
        """
        tracer, emitter = _create_initialized_tracer()

        # ── Step 1: Chain (Agent 入口) ──
        chain_manager = TraceManager(
            instance_info={"class_name": "ReActAgent", "type": "chain"},
            openjiuwen_tracer=tracer,
        )
        await chain_manager.on_chain_start(inputs={"query": "帮我查一下北京天气"})
        chain_invoke_id = chain_manager.invoke_id

        # ── Step 2: LLM 第一次推理 ──
        llm_manager = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "qwen-plus", "type": "llm"},
        )
        await llm_manager.on_llm_start(
            inputs=[{"role": "user", "content": "帮我查一下北京天气"}]
        )
        llm_1_invoke_id = llm_manager.invoke_id
        await llm_manager.on_llm_end(
            outputs={"content": "我需要调用天气插件", "tool_calls": [{"name": "weather"}]}
        )

        # ── Step 3: Plugin 调用 ──
        plugin_manager = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "weather_query", "type": "plugin"},
        )
        await plugin_manager.on_plugin_start(inputs={"city": "北京"})
        plugin_invoke_id = plugin_manager.invoke_id
        await plugin_manager.on_plugin_end(outputs={"temp": "28°C", "weather": "晴"})

        # ── Step 4: LLM 第二次推理 ──
        llm_manager_2 = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "qwen-plus", "type": "llm"},
        )
        await llm_manager_2.on_llm_start(
            inputs=[{"role": "user", "content": "帮我查一下北京天气"},
                    {"role": "assistant", "content": None, "tool_calls": [{"name": "weather"}]},
                    {"role": "tool", "content": '{"temp": "28°C", "weather": "晴"}'}]
        )
        llm_2_invoke_id = llm_manager_2.invoke_id
        await llm_manager_2.on_llm_end(
            outputs={"content": "北京今天28°C，天气晴朗。"}
        )

        # ── Step 5: Chain 结束 ──
        await chain_manager.on_chain_end(outputs={"answer": "北京今天28°C，天气晴朗。"})

        # 等待所有异步 trigger 完成
        await _drain_pending_coroutines()

        # ── 收集 trace 数据 ──
        await emitter.close()
        traces = await _collect_traces(emitter)
        payloads = _extract_payloads(traces)

        # ── 验证 trace 数据 ──

        # 1. 验证 chain trace（start + end = 2 条）
        chain_traces = _find_by_invoke_type(payloads, "chain")
        assert len(chain_traces) == 2
        assert chain_traces[0]["name"] == "ReActAgent"
        assert chain_traces[0]["status"] == "start"
        assert chain_traces[0]["inputs"] == {"inputs": {"query": "帮我查一下北京天气"}}
        assert chain_traces[1]["status"] == "finish"
        assert chain_traces[1]["outputs"] == {"answer": "北京今天28°C，天气晴朗。"}

        # 2. 验证 llm trace（2 次 × start+end = 4 条）
        llm_traces = _find_by_invoke_type(payloads, "llm")
        assert len(llm_traces) == 4
        assert llm_traces[0]["name"] == "qwen-plus"
        assert llm_traces[0]["status"] == "start"

        # 3. 验证 plugin trace（start + end = 2 条）
        plugin_traces = _find_by_invoke_type(payloads, "plugin")
        assert len(plugin_traces) == 2
        assert plugin_traces[0]["name"] == "weather_query"

        # 4. 验证 invokeId 对齐
        assert chain_traces[0]["invokeId"] == chain_invoke_id
        assert llm_traces[0]["invokeId"] == llm_1_invoke_id
        assert llm_traces[2]["invokeId"] == llm_2_invoke_id
        assert plugin_traces[0]["invokeId"] == plugin_invoke_id

        # 5. 验证 parentInvokeId
        # chain 的 parent 是 root，llm/plugin 的 parent 是 chain
        assert chain_traces[0]["parentInvokeId"] == chain_manager._oj_root_span.invoke_id
        assert llm_traces[0]["parentInvokeId"] == chain_invoke_id
        assert plugin_traces[0]["parentInvokeId"] == chain_invoke_id

        # 6. 验证 elapsedTime
        for end_trace in [chain_traces[1], llm_traces[1], llm_traces[3], plugin_traces[1]]:
            assert end_trace.get("elapsedTime") is not None

    @pytest.mark.asyncio
    async def test_error_scenario_trace(self):
        """模拟 LLM 调用失败场景，验证 error trace 正确推送。"""
        tracer, emitter = _create_initialized_tracer()

        chain_manager = TraceManager(
            instance_info={"class_name": "Agent", "type": "chain"},
            openjiuwen_tracer=tracer,
        )
        await chain_manager.on_chain_start(inputs={"query": "test"})

        llm_manager = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "qwen-plus", "type": "llm"},
        )
        await llm_manager.on_llm_start(inputs=[{"role": "user", "content": "test"}])
        await llm_manager.on_llm_error(error=RuntimeError("model timeout"))

        await chain_manager.on_chain_error(error=RuntimeError("agent failed"))

        await _drain_pending_coroutines()

        await emitter.close()
        traces = await _collect_traces(emitter)
        payloads = _extract_payloads(traces)

        # 验证 llm error trace
        llm_traces = _find_by_invoke_type(payloads, "llm")
        error_traces = [p for p in llm_traces if p.get("status") == "error"]
        assert len(error_traces) == 1
        assert error_traces[0]["error"] is not None
        assert "timeout" in error_traces[0]["error"]["message"]

        # 验证 chain error trace
        chain_traces = _find_by_invoke_type(payloads, "chain")
        chain_error = [p for p in chain_traces if p.get("status") == "error"]
        assert len(chain_error) == 1

    @pytest.mark.asyncio
    async def test_all_six_invoke_types(self):
        """验证 6 种 invoke_type 都能正确打点。"""
        tracer, emitter = _create_initialized_tracer()

        invoke_types = [
            ("prompt", "on_prompt_start", "on_prompt_end"),
            ("llm", "on_llm_start", "on_llm_end"),
            ("plugin", "on_plugin_start", "on_plugin_end"),
            ("chain", "on_chain_start", "on_chain_end"),
            ("retriever", "on_retriever_start", "on_retriever_end"),
            ("evaluator", "on_evaluator_start", "on_evaluator_end"),
        ]

        for invoke_type, start_method, end_method in invoke_types:
            tm = TraceManager(
                instance_info={"class_name": f"Test{invoke_type}", "type": invoke_type},
                openjiuwen_tracer=tracer,
            )
            await getattr(tm, start_method)(inputs={"test": "data"})
            await getattr(tm, end_method)(outputs={"result": "ok"})

        await _drain_pending_coroutines()

        await emitter.close()
        traces = await _collect_traces(emitter)
        payloads = _extract_payloads(traces)

        for invoke_type, _, _ in invoke_types:
            type_traces = _find_by_invoke_type(payloads, invoke_type)
            assert len(type_traces) == 2, (
                f"Expected 2 traces for {invoke_type}, got {len(type_traces)}"
            )

    @pytest.mark.asyncio
    async def test_span_tree_structure(self):
        """验证 span 树结构：root → chain → (llm, plugin)。"""
        tracer, emitter = _create_initialized_tracer()

        chain_manager = TraceManager(
            instance_info={"class_name": "Agent", "type": "chain"},
            openjiuwen_tracer=tracer,
        )
        await chain_manager.on_chain_start(inputs={"query": "test"})
        chain_id = chain_manager.invoke_id

        llm_manager = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "qwen-plus", "type": "llm"},
        )
        await llm_manager.on_llm_start(inputs="test")
        llm_id = llm_manager.invoke_id
        await llm_manager.on_llm_end(outputs="result")

        plugin_manager = _make_child_manager(
            chain_manager,
            instance_info={"class_name": "search", "type": "plugin"},
        )
        await plugin_manager.on_plugin_start(inputs={"x": 1})
        plugin_id = plugin_manager.invoke_id
        await plugin_manager.on_plugin_end(outputs={"y": 2})

        await chain_manager.on_chain_end(outputs={"done": True})

        await _drain_pending_coroutines()

        await emitter.close()
        traces = await _collect_traces(emitter)
        payloads = _extract_payloads(traces)

        # 获取 root span invoke_id
        root_id = chain_manager._oj_root_span.invoke_id

        # chain 的 parent 是 root
        chain_start = _find_by_invoke_type(payloads, "chain")[0]
        assert chain_start["parentInvokeId"] == root_id

        # llm 和 plugin 的 parent 是 chain
        llm_start = _find_by_invoke_type(payloads, "llm")[0]
        assert llm_start["parentInvokeId"] == chain_id

        plugin_start = _find_by_invoke_type(payloads, "plugin")[0]
        assert plugin_start["parentInvokeId"] == chain_id

        # root 的 childInvokes 应包含 chain
        root_span = tracer.tracer_agent_span_manager.get_span(root_id)
        assert chain_id in (root_span.child_invokes_id or [])


# ── Test: Facade 透传测试 ────────────────────────────────────────────────────


class TestFacadePassesSession:
    """测试 OpenJiuwenAgentFacade 透传 session。"""

    @pytest.mark.asyncio
    async def test_extract_runtime_kwargs_with_session(self):
        """_extract_runtime_kwargs 应提取 session。"""
        from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade

        mock_session = MagicMock()
        inputs = {
            "query": "hello",
            "_jiuwen_runtime_kwargs": {
                "stream": True,
                "session": mock_session,
            },
        }

        kwargs = OpenJiuwenAgentFacade._extract_runtime_kwargs(inputs)
        assert kwargs["session"] is mock_session

    @pytest.mark.asyncio
    async def test_extract_runtime_kwargs_without_session(self):
        """不传 session 时应为 None。"""
        from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade

        inputs = {
            "query": "hello",
            "_jiuwen_runtime_kwargs": {
                "stream": True,
            },
        }

        kwargs = OpenJiuwenAgentFacade._extract_runtime_kwargs(inputs)
        assert kwargs["session"] is None

    @pytest.mark.asyncio
    async def test_stream_passes_session_to_astream(self):
        """stream 方法应将 session 传递给 astream。"""
        from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade

        mock_session = MagicMock()

        class _FakeAgent:
            task_id = "t1"
            agent_id = "a1"

            async def astream(self, inputs, **kwargs):
                self.received_kwargs = kwargs
                yield "chunk"

        delegate = _FakeAgent()
        facade = OpenJiuwenAgentFacade(delegate)

        inputs = {
            "query": "hello",
            "_jiuwen_runtime_kwargs": {
                "stream": True,
                "session": mock_session,
            },
        }

        items = []
        async for item in facade.stream(inputs):
            items.append(item)

        assert delegate.received_kwargs["session"] is mock_session
