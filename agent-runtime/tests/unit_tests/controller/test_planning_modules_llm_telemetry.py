# -*- coding: UTF-8 -*-
"""规划/理解/StepExecute LLM 调用遥测载荷单测（!2524 覆盖面补齐）。

task_plan_module / task_understanding_module 此前不经过 TraceManager，
PlanExecute StepExecute 的 _stream_llm_response 绕过 stream_function_call，
qwen._chat（ainvoke 落点）不打双时间戳——这些路径的 LLM span 均拿不到
用量/时延/finish_reason。本文件锁住补齐后的契约：

- task_plan / task_understanding：镜像 intention_detect 接线，on_llm_end
  载荷按 core handler 约定键名携带 usage_metadata / finish_reason；
- PlanExecute StepExecute：astream finish 块的 usage_metadata 进入载荷，
  内容块掐表产出 TPOT（inter-token，单位毫秒）；
- qwen._chat：requests_start_time / first_token_time 双时间戳打点，
  批式语义下 TTFT ≈ 整体请求时延（可换算、非负）；
- 遥测事件经 emit_trace_event 隔离发射：任一 trace handler 抛错不得
  改变业务语义（规划结果 / 复杂意图判断 / 步骤输出均保持成功路径）；
- 遥测初始化失败（create_trace_manager_safely 返回 None）停用事件不外传，
  业务行为与接线前一致；LLM 成功后的解析/构建错误按原语义裸抛，
  不在同一 trace 上补发 on_llm_error。
"""

import asyncio

import pytest

from jiuwen.common.llm_service.language_model import qwen as qwen_module
from jiuwen.common.llm_service.messages import AIMessage, HumanMessage, UsageMetadata
from jiuwen.controller.agent.control_mode import plan_execute_mode as pem
from jiuwen.controller.agent.control_mode.plan_execute_mode import PlanExecuteMode
from jiuwen.controller.task_planner.planning_modules import (
    task_plan_module as tpm,
)
from jiuwen.controller.task_planner.planning_modules import (
    task_understanding_module as tum,
)
from jiuwen.planner.common import stream_post_utils as spu
from jiuwen.planner.common.stream_post_utils import (
    FINISH_REASON,
    LATENCY,
    MODEL_USAGE,
    USAGE_METADATA,
    _iso_delta_ms,
)


def _usage(**overrides):
    """构造带完整字段的 UsageMetadata，按需覆盖。"""
    base = dict(
        model_name="qwen-max",
        finish_reason="stop",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        first_token_time="2026-10-23T10:00:00.200+08:00",
        requests_start_time="2026-10-23T10:00:00+08:00",
        cache_tokens=5,
        reasoning_tokens=7,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03,
    )
    base.update(overrides)
    return UsageMetadata(**base)


def _no_template_manager():
    """TemplateManager 替身：真实单例构造依赖 DB 配置，单测不触达。"""
    return None


class StubManager:
    """记录 TraceManager 事件的桩。"""

    def __init__(self):
        self.events = []

    async def on_llm_start(self, messages):
        self.events.append(("start", messages))

    async def on_llm_end(self, payload):
        self.events.append(("end", payload))

    async def on_llm_error(self, error):
        self.events.append(("error", error))


class RaisingManager:
    """所有事件都抛错的桩：验证遥测失败不污染业务语义。"""

    @staticmethod
    async def _boom(*args, **kwargs):
        raise RuntimeError("trace handler down")

    async def on_llm_start(self, messages):
        await self._boom(messages)

    async def on_llm_end(self, payload):
        await self._boom(payload)

    async def on_llm_error(self, error):
        await self._boom(error)


class _StubTaskPlanModule(tpm.TaskPlanModule):
    """固定提示词输出的规划模块：绕开模板加载，聚焦遥测契约。"""

    def _build_system_prompt(self):
        return "sys-prompt"

    def _build_user_prompt(self, query, matched_scene, filtered_tools):
        return "usr-prompt"


class _StubTaskUnderstandingModule(tum.TaskUnderstandingModule):
    """固定提示词输出的理解模块：绕开模板加载，聚焦遥测契约。"""

    def _build_system_prompt(self):
        return "sys-prompt"

    def _build_user_prompt(self, query, chat_history, available_intents):
        return "usr-prompt"


def _install_stub_manager(monkeypatch, namespace, stub_manager):
    """把 create_trace_manager_safely 打桩为返回给定 TraceManager 桩。"""
    monkeypatch.setattr(
        namespace, "create_trace_manager_safely", lambda *args, **kwargs: stub_manager
    )


def _broken_create(*args, **kwargs):
    """非法 trace_handlers 形态：模拟 generate_manager 初始化抛错。"""
    raise TypeError("bad trace_handlers shape")


class TestTaskPlanEmit:
    @staticmethod
    def test_plan_emits_usage_latency_finish_reason(monkeypatch):
        """plan() 经 TraceManager 发射：trace_handlers 取自 runtime_data。

        on_llm_end 载荷带约定键名的 usage_metadata / finish_reason。
        """
        stub_manager = StubManager()
        captured = {}

        def fake_create(*args, **kwargs):
            captured.update(kwargs)
            return stub_manager

        monkeypatch.setattr(tpm, "create_trace_manager_safely", fake_create)
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(
                    content='{"steps": [{"step_idx": 1, "step_name": "s1"}]}',
                    usage_metadata=_usage(),
                )

        stub_llm = StubLLM()
        module = _StubTaskPlanModule(llm=stub_llm, context_manager=None)

        handlers = object()
        plan = asyncio.run(
            module.plan(
                query="q",
                chat_history=[],
                matched_scene=None,
                filtered_tools=[],
                task_id="t1",
                runtime_data={"trace_handlers": handlers},
            )
        )

        # 接线参数：trace_handlers 从 runtime_data 透传
        assert captured["llm"] is stub_llm
        assert captured["functions"] == []
        assert captured["trace_handlers"] is handlers

        # 事件序列与载荷形状
        assert [e[0] for e in stub_manager.events] == ["start", "end"]
        start_msgs = stub_manager.events[0][1]
        assert start_msgs[0] == {"role": "system", "content": "sys-prompt"}
        payload = stub_manager.events[1][1]
        assert payload["content"].startswith('{"steps"')
        assert payload[LATENCY]["total_latency"] >= 0
        assert payload[MODEL_USAGE]["total_tokens"] == 30
        assert payload[USAGE_METADATA]["first_token_time"] == pytest.approx(0.2)
        assert payload[FINISH_REASON] == "stop"

        # 业务行为不因接线改变
        assert len(plan.steps) == 1

    @staticmethod
    def test_plan_without_runtime_data_passes_none(monkeypatch):
        """runtime_data 缺省（调用方兜底为 None）→ trace_handlers=None。

        正常发射，行为与既有 stream_function_call(trace_handlers=None) 一致。
        """
        stub_manager = StubManager()
        captured = {}

        def fake_create(*args, **kwargs):
            captured.update(kwargs)
            return stub_manager

        monkeypatch.setattr(tpm, "create_trace_manager_safely", fake_create)
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(content='{"steps": []}', usage_metadata=_usage())

        module = _StubTaskPlanModule(llm=StubLLM(), context_manager=None)

        asyncio.run(
            module.plan(
                query="q",
                chat_history=[],
                matched_scene=None,
                filtered_tools=[],
            )
        )
        assert captured["trace_handlers"] is None
        assert [e[0] for e in stub_manager.events] == ["start", "end"]

    @staticmethod
    def test_plan_llm_error_emits_error_event(monkeypatch):
        """LLM 调用失败 → on_llm_error 发射 + 原有 raise 行为保留。"""
        stub_manager = StubManager()
        _install_stub_manager(monkeypatch, tpm, stub_manager)
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                raise RuntimeError("llm down")

        module = _StubTaskPlanModule(llm=StubLLM(), context_manager=None)

        with pytest.raises(RuntimeError):
            asyncio.run(
                module.plan(
                    query="q", chat_history=[], matched_scene=None, filtered_tools=[]
                )
            )
        kinds = [e[0] for e in stub_manager.events]
        assert kinds == ["start", "error"]
        assert isinstance(stub_manager.events[-1][1], RuntimeError)

    @staticmethod
    def test_plan_parse_error_emits_no_llm_error(monkeypatch):
        """LLM 成功但计划解析失败 → 按原语义裸抛，不补发 on_llm_error。

        try 只罩 LLM 调用：同一 trace 上不得同时出现 on_llm_end 与
        on_llm_error 双终止事件，规划错误也不得误报为 LLM 调用错误。
        """
        stub_manager = StubManager()
        _install_stub_manager(monkeypatch, tpm, stub_manager)
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(content='{"steps": []}', usage_metadata=_usage())

        module = _StubTaskPlanModule(llm=StubLLM(), context_manager=None)

        def bad_parse(content, task_id):
            raise AttributeError("bad plan shape")

        monkeypatch.setattr(module, "_parse_plan_result", bad_parse)

        with pytest.raises(AttributeError):
            asyncio.run(
                module.plan(
                    query="q", chat_history=[], matched_scene=None, filtered_tools=[]
                )
            )
        # LLM 调用已成功终止（start/end），解析失败不得再叠加 error 事件
        assert [e[0] for e in stub_manager.events] == ["start", "end"]


class TestTaskUnderstandingEmit:
    @staticmethod
    def test_invoke_emits_usage_latency_finish_reason(monkeypatch):
        """invoke() 经 TraceManager 发射，复杂意图判断行为不变。"""
        stub_manager = StubManager()
        captured = {}

        def fake_create(*args, **kwargs):
            captured.update(kwargs)
            return stub_manager

        monkeypatch.setattr(tum, "create_trace_manager_safely", fake_create)
        monkeypatch.setattr(tum, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(content="1", usage_metadata=_usage())

        module = _StubTaskUnderstandingModule(llm=StubLLM(), context_manager=None)

        handlers = object()
        result = asyncio.run(
            module.invoke(
                query="还信用卡账单",
                chat_history=[],
                available_intents=["查余额"],
                task_id="t2",
                runtime_data={"trace_handlers": handlers},
            )
        )

        assert captured["trace_handlers"] is handlers
        assert [e[0] for e in stub_manager.events] == ["start", "end"]
        payload = stub_manager.events[1][1]
        assert payload["content"] == "1"
        assert payload[USAGE_METADATA]["first_token_time"] == pytest.approx(0.2)
        assert payload[MODEL_USAGE]["input_tokens"] == 10
        assert payload[FINISH_REASON] == "stop"
        # 业务行为不因接线改变
        assert result.is_complex is True

    @staticmethod
    def test_invoke_llm_error_emits_error_and_falls_back(monkeypatch):
        """LLM 调用失败 → on_llm_error 发射 + 原有兜底（is_complex=False）保留。"""
        stub_manager = StubManager()
        _install_stub_manager(monkeypatch, tum, stub_manager)
        monkeypatch.setattr(tum, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                raise RuntimeError("llm down")

        module = _StubTaskUnderstandingModule(llm=StubLLM(), context_manager=None)

        result = asyncio.run(
            module.invoke(query="q", chat_history=[], available_intents=[])
        )
        assert result.is_complex is False
        kinds = [e[0] for e in stub_manager.events]
        assert kinds == ["start", "error"]

    @staticmethod
    def test_invoke_list_content_single_termination(monkeypatch):
        """content 为 list（AIMessage 契约允许）→ 不得 end/error 双终止。

        on_llm_end 发射后若后处理（strip 等）仍在 try 内抛错，except 会
        补发 on_llm_error，同一 trace 双终止且业务落入错误分支；后处理
        须在 try 外、且非 str 内容按空串兜底（_parse_is_complex 判 False）。
        """
        stub_manager = StubManager()
        _install_stub_manager(monkeypatch, tum, stub_manager)
        monkeypatch.setattr(tum, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(
                    content=["非字符串内容"], usage_metadata=_usage()
                )

        module = _StubTaskUnderstandingModule(llm=StubLLM(), context_manager=None)

        result = asyncio.run(
            module.invoke(query="q", chat_history=[], available_intents=[])
        )
        assert result.is_complex is False
        kinds = [e[0] for e in stub_manager.events]
        assert kinds == ["start", "end"]
        # 载荷 content 按 str 兜底，不外泄 list 形态
        assert stub_manager.events[1][1]["content"] == ""


def make_stream_mode(monkeypatch, stub_manager, model):
    """装配 _stream_llm_response 依赖的最小 PlanExecuteMode。

    被测方法内部 from stream_post_utils import create_trace_manager_safely
    在调用时解析模块属性；这里打内层 create_trace_manager（safely 兜底
    保持真实），初始化失败用例可对其二次覆盖。多个测试类共用，置于
    模块级（类内受保护成员跨类访问会触 G.CLS.11）。
    """
    monkeypatch.setattr(
        spu, "create_trace_manager", lambda *args, **kwargs: stub_manager
    )
    mode = object.__new__(PlanExecuteMode)
    mode.task_id = "t-pe"
    mode.model = model
    monkeypatch.setattr(mode, "_trace_handlers", None, raising=False)
    return mode


class TestPlanExecuteStreamLlmEmit:
    @staticmethod
    def test_stream_llm_response_emits_payload(monkeypatch):
        """astream finish 块的 usage_metadata 进入 on_llm_end 载荷。"""

        class StubModel:
            # 生产链路 self.model.astream 同步返回异步生成器；无实例状态
            @staticmethod
            def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="he", usage_metadata=UsageMetadata())
                    yield AIMessage(content="llo", usage_metadata=UsageMetadata())
                    yield AIMessage(content="done", usage_metadata=_usage())

                return gen()

        stub_manager = StubManager()
        mode = make_stream_mode(monkeypatch, stub_manager, StubModel())

        # G.CLS.11：被测私有方法按字符串属性访问（测试直测内部路径）
        llm_output = asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )

        # 业务行为不变：finish 块内容覆盖拼装内容
        assert llm_output["content"] == "done"
        assert [e[0] for e in stub_manager.events] == ["start", "end"]
        payload = stub_manager.events[1][1]
        assert payload["content"] == "done"
        assert payload[LATENCY]["total_latency"] >= 0
        assert payload[MODEL_USAGE]["total_tokens"] == 30
        assert payload[USAGE_METADATA]["first_token_time"] == pytest.approx(0.2)
        assert payload[FINISH_REASON] == "stop"
        # 两个内容块 → TPOT 可算（真实掐表，只锁存在性与非负）
        assert payload[USAGE_METADATA]["inter_token_latency_ms"] >= 0

    @staticmethod
    def test_stream_tpot_unit_is_milliseconds(monkeypatch):
        """StepExecute TPOT 单位锁定：time.time() 秒差须 ×1000 入毫秒键。

        假钟每调用前进 0.1s：两内容块间隔 0.1s → TPOT 应为 100ms
        （若漏乘 1000 会得到 0.1）。
        """

        class _StepClock:
            def __init__(self):
                self._now = 1000.0

            def time(self):
                self._now += 0.1
                return self._now

        monkeypatch.setattr(pem.time, "time", _StepClock().time)

        class StubModel:
            @staticmethod
            def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="a", usage_metadata=UsageMetadata())
                    yield AIMessage(content="b", usage_metadata=UsageMetadata())
                    yield AIMessage(content="done", usage_metadata=_usage())

                return gen()

        stub_manager = StubManager()
        mode = make_stream_mode(monkeypatch, stub_manager, StubModel())

        asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )

        payload = stub_manager.events[-1][1]
        assert payload[USAGE_METADATA]["inter_token_latency_ms"] == pytest.approx(
            100.0
        )

    @staticmethod
    def test_stream_llm_response_error_emits_error_event(monkeypatch):
        """流式调用失败 → on_llm_error 发射 + 原有吞错（error 键）保留。"""

        class StubModel:
            @staticmethod
            def astream(inputs, **kwargs):
                raise RuntimeError("stream down")

        stub_manager = StubManager()
        mode = make_stream_mode(monkeypatch, stub_manager, StubModel())

        # G.CLS.11：被测私有方法按字符串属性访问（测试直测内部路径）
        llm_output = asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )
        assert llm_output["content"] == ""
        assert llm_output["error"] == "stream down"
        kinds = [e[0] for e in stub_manager.events]
        assert kinds == ["start", "error"]

    @staticmethod
    def test_trailing_empty_usage_does_not_drop_real_usage(monkeypatch):
        """带 "null" 标记的块不得覆盖 finish 块真实用量。

        qwen 中间/尾随信号块的 finish_reason 为 "null"（非空）：若暂存条件
        按"finish_reason 非空"判，逐块挂 usage 的实现或真实 finish 块之后的
        尾随块都会把真实用量静默替换成空值；暂存必须与 is_finish_block
        （仅 stop/function_call）同源。
        """
        class StubModel:
            @staticmethod
            def astream(inputs, **kwargs):
                async def gen():
                    # 中间块：finish_reason="null"（非空）+ 默认空 usage
                    yield AIMessage(
                        content="he",
                        usage_metadata=UsageMetadata(finish_reason="null"),
                    )
                    # finish 块：终止标记 + 真实用量
                    yield AIMessage(content="done", usage_metadata=_usage())
                    # 尾随信号块："null"（非空）+ 恒真默认空 usage
                    yield AIMessage(
                        content="",
                        usage_metadata=UsageMetadata(finish_reason="null"),
                    )

                return gen()

        stub_manager = StubManager()
        mode = make_stream_mode(monkeypatch, stub_manager, StubModel())

        llm_output = asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )

        assert llm_output["content"] == "done"
        payload = stub_manager.events[-1][1]
        # finish 块的真实用量不被 "null" 块覆盖丢弃
        assert payload[MODEL_USAGE]["total_tokens"] == 30
        assert payload[USAGE_METADATA]["input_tokens"] == 10
        assert payload[FINISH_REASON] == "stop"
        # 单内容块无 inter-token 间隔，TPOT 不产出
        assert "inter_token_latency_ms" not in payload[USAGE_METADATA]


class TestTelemetryFailureIsolation:
    """遥测 handler 抛错不得把成功的业务调用误判进失败分支。"""

    @staticmethod
    def test_task_plan_result_survives_handler_error(monkeypatch):
        """on_llm_start/on_llm_end 抛错 → 规划结果正常返回，不再重抛。"""
        _install_stub_manager(monkeypatch, tpm, RaisingManager())
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(
                    content='{"steps": [{"step_idx": 1, "step_name": "s1"}]}',
                    usage_metadata=_usage(),
                )

        module = _StubTaskPlanModule(llm=StubLLM(), context_manager=None)
        plan = asyncio.run(
            module.plan(query="q", chat_history=[], matched_scene=None, filtered_tools=[])
        )
        assert len(plan.steps) == 1

    @staticmethod
    def test_task_understanding_result_survives_handler_error(monkeypatch):
        """on_llm_start/on_llm_end 抛错 → 复杂意图判断不被兜底成简单意图。"""
        _install_stub_manager(monkeypatch, tum, RaisingManager())
        monkeypatch.setattr(tum, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(content="1", usage_metadata=_usage())

        module = _StubTaskUnderstandingModule(llm=StubLLM(), context_manager=None)
        result = asyncio.run(
            module.invoke(query="q", chat_history=[], available_intents=[])
        )
        assert result.is_complex is True

    @staticmethod
    def test_plan_execute_step_survives_handler_error(monkeypatch):
        """on_llm_start/on_llm_end 抛错 → 步骤输出正常，不落入 error 分支。"""

        class StubModel:
            @staticmethod
            def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="done", usage_metadata=_usage())

                return gen()

        mode = make_stream_mode(monkeypatch, RaisingManager(), StubModel())
        # G.CLS.11：被测私有方法按字符串属性访问（测试直测内部路径）
        llm_output = asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )
        assert llm_output["content"] == "done"
        assert "error" not in llm_output

    @staticmethod
    def test_task_plan_survives_manager_init_failure(monkeypatch):
        """create_trace_manager 抛错 → 遥测停用（无事件），规划照常返回。"""
        monkeypatch.setattr(spu, "create_trace_manager", _broken_create)
        monkeypatch.setattr(tpm, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(
                    content='{"steps": [{"step_idx": 1, "step_name": "s1"}]}',
                    usage_metadata=_usage(),
                )

        module = _StubTaskPlanModule(llm=StubLLM(), context_manager=None)
        plan = asyncio.run(
            module.plan(
                query="q", chat_history=[], matched_scene=None, filtered_tools=[]
            )
        )
        assert len(plan.steps) == 1

    @staticmethod
    def test_task_understanding_survives_manager_init_failure(monkeypatch):
        """create_trace_manager 抛错 → 复杂意图判断不被兜底成 False。"""
        monkeypatch.setattr(spu, "create_trace_manager", _broken_create)
        monkeypatch.setattr(tum, "TemplateManager", _no_template_manager)

        class StubLLM:
            async def ainvoke(self, messages):
                return AIMessage(content="1", usage_metadata=_usage())

        module = _StubTaskUnderstandingModule(llm=StubLLM(), context_manager=None)
        result = asyncio.run(
            module.invoke(query="q", chat_history=[], available_intents=[])
        )
        assert result.is_complex is True

    @staticmethod
    def test_plan_execute_step_survives_manager_init_failure(monkeypatch):
        """create_trace_manager 抛错 → 步骤输出正常，不落入 error 分支。"""
        class StubModel:
            @staticmethod
            def astream(inputs, **kwargs):
                async def gen():
                    yield AIMessage(content="done", usage_metadata=_usage())

                return gen()

        mode = make_stream_mode(monkeypatch, StubManager(), StubModel())
        monkeypatch.setattr(spu, "create_trace_manager", _broken_create)

        llm_output = asyncio.run(
            getattr(mode, "_stream_llm_response")(
                [{"role": "user", "content": "hi"}], []
            )
        )
        assert llm_output["content"] == "done"
        assert "error" not in llm_output


class TestQwenChatTimestamps:
    @staticmethod
    def test_chat_stamps_dual_timestamps(monkeypatch):
        """qwen._chat（ainvoke 落点）打双时间戳。

        批式语义下首 token 即完整响应到达，TTFT 可换算且非负
        （≈ 整体请求时延）。
        """

        def fake_request_params(messages, tools):
            return ({"model": "qwen-max"}, {})

        monkeypatch.setattr(
            qwen_module.Qwen, "_request_params", staticmethod(fake_request_params)
        )

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "id": "task-1",
                    "model": "qwen-max",
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": "hi"}}
                    ],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 4,
                        "total_tokens": 7,
                    },
                }

        captured = {}

        def fake_post(**kwargs):
            captured.update(kwargs)
            return FakeResponse()

        monkeypatch.setattr(qwen_module.requests, "post", fake_post)

        model = qwen_module.Qwen(
            api_key="unit-test", api_base="http://unit-test", model_name="qwen-max"
        )
        # 走公有入口 ainvoke（task_plan/task_understanding 的真实调用形态），
        # 其经 _achat 直通 _chat，被测路径不变
        result = asyncio.run(model.ainvoke([HumanMessage(content="hi")]))

        assert captured["json"]["model"] == "qwen-max"
        assert isinstance(result, AIMessage)
        usage = result.usage_metadata
        # 既有行为不回退：token 抽取与 finish_reason 保持
        assert (usage.input_tokens, usage.output_tokens, usage.total_tokens) == (3, 4, 7)
        assert usage.finish_reason == "stop"
        # 新增：双时间戳在位且可换算
        assert usage.requests_start_time
        assert usage.first_token_time
        delta_ms = _iso_delta_ms(usage.first_token_time, usage.requests_start_time)
        assert delta_ms is not None
        assert delta_ms >= 0
