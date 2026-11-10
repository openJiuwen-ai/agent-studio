# coding: utf-8

"""KnowledgeRetrievalTool 控制器路径 retrieval 追踪接线。

能力门控约定（新 studio × 老 core 不崩）：
- _TracerAgentUtils 为 None（老 core 无该助手）时检索照常，只是无 retrieval span；
- session 未注入（kwargs 无 session）时同样跳过追踪；
- 追踪调用自身的异常被吞掉，绝不影响检索主流程。
"""

import asyncio

import pytest

from agent_runtime.extension.tool import knowledge_retrieval_tool as krt
from agent_runtime.extension.tool.knowledge_retrieval_tool import KnowledgeRetrievalTool
from jiuwen.plugin.common import constant
from openjiuwen.core.foundation.tool.base import ToolCard


class _FakeTracerUtils:
    """记录调用的 TracerAgentUtils 替身（.testenv 静态副本 core 里没有真身）。

    start 事件已不经 core helper（改走 _FakeSession/_FakeTracer 的本地路径）：
    本替身只承接 end/error 两个仍走 TracerAgentUtils 的事件。
    """

    def __init__(self):
        self.calls = []
        self.error_hang = False  # True 时 error 事件挂起，模拟真实取消落点

    async def trace_retriever_end(self, session, span, documents=None):
        self.calls.append(("end", session, documents))

    async def trace_retriever_error(self, session, span, error):
        self.calls.append(("error", session, error))
        if self.error_hang:
            await asyncio.sleep(3600)


class _FakeAgentSpan:
    def __init__(self, n: int):
        self.invoke_id = f"retr-{n}"


class _FakeTracer:
    """kwargs 会话 tracer 替身：登记/注销/事件全程可观测，trigger 行为可注入。"""

    def __init__(self, trigger=None):
        self.created = []
        self.popped = []
        self.events = []
        self._trigger = trigger
        outer = self

        class _Manager:
            # G.CLS.07：方法不碰 self（只经闭包 outer 观测），定义成 staticmethod
            @staticmethod
            def create_agent_span(*args, **kwargs):
                span = _FakeAgentSpan(len(outer.created))
                outer.created.append(span)
                return span

            @staticmethod
            def pop_span(invoke_id):
                outer.popped.append(invoke_id)

        self.tracer_agent_span_manager = _Manager()

    @staticmethod
    def agent_handler_valid() -> bool:
        return True

    async def trigger(self, handler, event, span=None, **payload):
        self.events.append((event, span, payload))
        if self._trigger is not None:
            return self._trigger(event, payload)


class _FakeSession:
    """kwargs 注入会话替身：tracer() 返回可观测的 _FakeTracer。"""

    def __init__(self, trigger=None):
        self.the_tracer = _FakeTracer(trigger)

    def tracer(self):
        return self.the_tracer


def _build_tool() -> KnowledgeRetrievalTool:
    return KnowledgeRetrievalTool(
        card=ToolCard(id="retrieval", name="retrieval", description=""),
        connection_id="conn-1",
        knowledge_base_ids=["kb-1"],
        retrieval_config={"topK": 5},
        tag_overrides={},
    )


def _canned_output() -> dict:
    return {
        constant.ERR_CODE: 0,
        constant.ERR_MESSAGE: "success",
        constant.RESTFUL_DATA: {
            "output_list": [
                # 携带与 document_name 不同的敏感正文：断言遥测载荷只含标识符
                {"document_name": "doc-a", "text": "机密正文-a", "content": "机密正文-a"},
                {"document_name": "doc-b", "text": "机密正文-b", "content": "机密正文-b"},
            ]
        },
    }


@pytest.mark.asyncio
async def test_invoke_emits_retriever_events_with_session(monkeypatch):
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    session = _FakeSession()
    tool = _build_tool()
    result = await tool.invoke({"query": "什么是九问"}, session=session)

    assert result == _canned_output()
    # start 经 kwargs 会话的 tracer 发射（inputs 携带 top_k / knowledge_base_ids）
    assert [e[0] for e in session.the_tracer.events] == ["on_retriever_start"]
    assert session.the_tracer.events[0][2]["inputs"]["query"] == "什么是九问"
    # end 仍经 core helper：只送标识符，机密正文不进遥测
    assert fake.calls == [("end", session, ["doc-a", "doc-b"])]
    assert "机密正文" not in str(fake.calls)


@pytest.mark.asyncio
async def test_invoke_error_emits_error_event_and_reraises(monkeypatch):
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    async def fake_run_retrieval(**kwargs):
        raise RuntimeError("kb down")

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    session = _FakeSession()
    with pytest.raises(RuntimeError, match="kb down") as excinfo:
        await tool.invoke({"query": "q"}, session=session)

    assert [e[0] for e in session.the_tracer.events] == ["on_retriever_start"]
    assert [call[0] for call in fake.calls] == ["error"]
    assert fake.calls[0][2] is excinfo.value  # error 对象原样透传给事件


@pytest.mark.asyncio
async def test_invoke_without_utils_still_retrieves(monkeypatch):
    # .testenv 的老 core 副本没有 TracerAgentUtils：模块级 import 失败即此形态
    monkeypatch.setattr(krt, "_TracerAgentUtils", None, raising=False)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    assert await tool.invoke({"query": "q"}, session=object()) == _canned_output()


@pytest.mark.asyncio
async def test_invoke_without_session_skips_tracing(monkeypatch):
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    assert await tool.invoke({"query": "q"}) == _canned_output()
    assert fake.calls == []


@pytest.mark.asyncio
async def test_invoke_empty_query_still_emits_event_pair(monkeypatch):
    # 空查询走 _run_retrieval 的短路返回：span 对表示"检索发生过"
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    async def fake_run_retrieval(**kwargs):
        return {
            constant.ERR_CODE: 0,
            constant.ERR_MESSAGE: "success",
            constant.RESTFUL_DATA: {"output_list": []},
        }

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    session = _FakeSession()
    tool = _build_tool()
    await tool.invoke({"query": ""}, session=session)

    assert [e[0] for e in session.the_tracer.events] == ["on_retriever_start"]
    assert session.the_tracer.events[0][2]["inputs"]["query"] == ""  # 空查询如实记录
    assert [call[0] for call in fake.calls] == ["end"]
    assert fake.calls[0][2] == []  # 空结果 documents 为空列表


@pytest.mark.asyncio
async def test_invoke_cancellation_still_emits_error_event(monkeypatch):
    # CancelledError 属 BaseException：except Exception 接不住，span 会悬空。
    # 取消/超时路径同样要发 error 事件收尾后原样抛出。
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    async def fake_run_retrieval(**kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    session = _FakeSession()
    with pytest.raises(asyncio.CancelledError) as excinfo:
        await tool.invoke({"query": "q"}, session=session)

    assert [e[0] for e in session.the_tracer.events] == ["on_retriever_start"]
    assert [call[0] for call in fake.calls] == ["error"]
    assert fake.calls[0][2] is excinfo.value  # 取消对象原样透传给事件


@pytest.mark.asyncio
async def test_invoke_skips_wrapper_when_ambient_tracer_alive(monkeypatch):
    # 双计守卫：ambient 会话上下文可达（controller 路径常态——agent 级
    # with_session 包装内执行工具）时，由 _run_retrieval 内建遥测发射，
    # kwargs 外壳必须静默，同一次检索只出一对 retriever 事件
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: object())

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    assert await tool.invoke({"query": "q"}, session=object()) == _canned_output()
    assert fake.calls == []


@pytest.mark.asyncio
async def test_invoke_cancellation_during_trace_start_propagates(monkeypatch):
    # 取消落在 start 事件 trigger 期间：CancelledError 穿透事件吞异常层，
    # _trace_retrieval_start 注销登记后原样上抛，再由 invoke 收尾伞接住
    # （span 未开启，error 收尾为 no-op）后重抛，检索本体不再执行
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    def cancel_trigger(event, payload):
        raise asyncio.CancelledError()

    session = _FakeSession(trigger=cancel_trigger)

    ran = []

    async def fake_run_retrieval(**kwargs):
        ran.append(1)
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    with pytest.raises(asyncio.CancelledError):
        await tool.invoke({"query": "q"}, session=session)

    assert ran == []  # 检索未执行
    assert fake.calls == []  # 未走到任何 core helper 事件
    tracer = session.the_tracer
    assert len(tracer.created) == 1  # 登记过一次
    assert tracer.popped == [s.invoke_id for s in tracer.created]  # 且已注销，无悬空


@pytest.mark.asyncio
async def test_real_task_cancel_during_error_event_drops_span(monkeypatch):
    # 真实取消（Task.cancel，非 monkeypatch 抛 CancelledError）：error 事件挂起期间
    # 任务被取消，except 块内的 await 再次收到 CancelledError——收尾不再依赖任何
    # 异步调用，同步尽力注销登记 + drop 半开 span 后取消原样上抛
    fake = _FakeTracerUtils()
    fake.error_hang = True
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    dropped = []
    monkeypatch.setattr(
        krt, "_drop_retrieval_span_by_session", lambda session, span: dropped.append(span)
    )

    async def failing_run_retrieval(**kwargs):
        raise RuntimeError("kb down")

    monkeypatch.setattr(krt, "_run_retrieval", failing_run_retrieval)

    session = _FakeSession()
    tool = _build_tool()
    task = asyncio.ensure_future(tool.invoke({"query": "q"}, session=session))
    await asyncio.sleep(0.05)  # 跑到 error 事件挂起处
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert [e[0] for e in session.the_tracer.events] == ["on_retriever_start"]
    assert [call[0] for call in fake.calls] == ["error"]  # 事件记录在案
    assert dropped and dropped[0] is not None  # 取消再投递时同步收尾已尽力


@pytest.mark.asyncio
async def test_invoke_start_trigger_exception_unregisters_span(monkeypatch):
    # codex 检视：kwargs 兜底路径 start 事件 trigger 抛 Exception。旧实现经
    # TracerAgentUtils.trace_retriever_start（create_agent_span 登记在前 +
    # trigger 无保护），异常被外壳吞掉后登记永久残留、污染 last_span。
    # 现要求：登记注销收尾、无后续 end/error 事件、检索照常返回
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    def boom_trigger(event, payload):
        raise RuntimeError("boom")

    session = _FakeSession(trigger=boom_trigger)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    result = await tool.invoke({"query": "q"}, session=session)

    assert result == _canned_output()  # 追踪失败绝不影响检索
    tracer = session.the_tracer
    assert len(tracer.created) == 1  # 登记过一次
    assert tracer.popped == [s.invoke_id for s in tracer.created]  # 已注销，无悬空
    assert [e[0] for e in tracer.events] == ["on_retriever_start"]  # 仅尝试过 start
    assert fake.calls == []  # span 未开启，无 end/error


def _patch_otel_drop_handler(monkeypatch, dropped):
    """把注册表 agent handlers 换成带 drop_agent_span 的替身，记录被 drop 的 invoke_id。"""
    from types import SimpleNamespace

    from openjiuwen.core.session.tracer.tracer import TracerHandlerRegistry

    otel_handler = SimpleNamespace(
        drop_agent_span=lambda invoke_id: dropped.append(invoke_id)
    )
    monkeypatch.setattr(
        TracerHandlerRegistry,
        "get_agent_handlers",
        staticmethod(lambda: {"otel": otel_handler}),
    )


@pytest.mark.asyncio
async def test_invoke_start_partial_delivery_exception_drops_opened_span(monkeypatch):
    # 部分送达：core trigger 逐 handler 裸 await 不隔离异常，第一个 handler
    # 已开启 otel span、第二个抛 Exception——只注销登记会漏半开 span，
    # 必须 drop 收口（对未开启 invoke_id 幂等 no-op）
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    session = _FakeSession()
    opened = []

    def partial_trigger(event, payload):
        # 第一个 handler 成功开启 otel span（替身已先记录事件三元组）
        opened.append(session.the_tracer.events[-1][1])
        raise RuntimeError("second handler boom")

    session.the_tracer._trigger = partial_trigger

    dropped = []
    _patch_otel_drop_handler(monkeypatch, dropped)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    result = await tool.invoke({"query": "q"}, session=session)

    assert result == _canned_output()  # 追踪失败绝不影响检索
    assert len(opened) == 1  # 确实发生过一次成功开启（部分送达前提）
    tracer = session.the_tracer
    assert tracer.popped == [s.invoke_id for s in tracer.created]  # 登记已注销
    assert dropped == [s.invoke_id for s in tracer.created]  # 已开的 span 被 drop
    assert fake.calls == []  # span 未开启成功，无 end/error


@pytest.mark.asyncio
async def test_invoke_start_partial_delivery_cancel_drops_opened_span(monkeypatch):
    # 取消落在 start trigger 的后继 handler：第一个 handler 已开 otel span。
    # CancelledError 穿透吞异常层走 BaseException 分支，同样注销 + drop 后
    # 原样上抛（drop 为同步原语，取消再投递打不断它）
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)
    monkeypatch.setattr(krt, "_resolve_retrieval_tracer", lambda: None)

    session = _FakeSession()
    opened = []

    def partial_cancel(event, payload):
        opened.append(session.the_tracer.events[-1][1])
        raise asyncio.CancelledError()

    session.the_tracer._trigger = partial_cancel

    dropped = []
    _patch_otel_drop_handler(monkeypatch, dropped)

    ran = []

    async def fake_run_retrieval(**kwargs):
        ran.append(1)
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    with pytest.raises(asyncio.CancelledError):
        await tool.invoke({"query": "q"}, session=session)

    assert ran == []  # 检索未执行
    assert len(opened) == 1  # 部分送达前提成立
    tracer = session.the_tracer
    assert tracer.popped == [s.invoke_id for s in tracer.created]  # 登记已注销
    assert dropped == [s.invoke_id for s in tracer.created]  # 已开的 span 被 drop
    assert fake.calls == []
