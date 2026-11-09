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
    """记录调用的 TracerAgentUtils 替身（.testenv 静态副本 core 里没有真身）。"""

    def __init__(self):
        self.calls = []

    async def trace_retriever_start(self, session, query=None, instance_name=""):
        self.calls.append(("start", session, query, instance_name))
        return object()

    async def trace_retriever_end(self, session, span, documents=None):
        self.calls.append(("end", session, documents))

    async def trace_retriever_error(self, session, span, error):
        self.calls.append(("error", session, error))


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
                {"text": "doc-a", "content": "doc-a"},
                {"text": "doc-b", "content": "doc-b"},
            ]
        },
    }


@pytest.mark.asyncio
async def test_invoke_emits_retriever_events_with_session(monkeypatch):
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)

    async def fake_run_retrieval(**kwargs):
        return _canned_output()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    session = object()
    tool = _build_tool()
    result = await tool.invoke({"query": "什么是九问"}, session=session)

    assert result == _canned_output()
    assert fake.calls == [
        ("start", session, "什么是九问", "retrieval"),
        ("end", session, ["doc-a", "doc-b"]),
    ]


@pytest.mark.asyncio
async def test_invoke_error_emits_error_event_and_reraises(monkeypatch):
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)

    async def fake_run_retrieval(**kwargs):
        raise RuntimeError("kb down")

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    session = object()
    with pytest.raises(RuntimeError, match="kb down") as excinfo:
        await tool.invoke({"query": "q"}, session=session)

    assert [call[0] for call in fake.calls] == ["start", "error"]
    assert fake.calls[1][2] is excinfo.value  # error 对象原样透传给事件


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
    # 空查询走 _run_retrieval 的短路返回：span 对表示"检索发生过"，无 query 属性
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)

    async def fake_run_retrieval(**kwargs):
        return {
            constant.ERR_CODE: 0,
            constant.ERR_MESSAGE: "success",
            constant.RESTFUL_DATA: {"output_list": []},
        }

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    await tool.invoke({"query": ""}, session=object())

    assert [call[0] for call in fake.calls] == ["start", "end"]
    assert fake.calls[0][2] is None  # 空查询不传 query
    assert fake.calls[1][2] == []  # 空结果 documents 为空列表


@pytest.mark.asyncio
async def test_invoke_cancellation_still_emits_error_event(monkeypatch):
    # CancelledError 属 BaseException：except Exception 接不住，span 会悬空。
    # 取消/超时路径同样要发 error 事件收尾后原样抛出。
    fake = _FakeTracerUtils()
    monkeypatch.setattr(krt, "_TracerAgentUtils", fake)

    async def fake_run_retrieval(**kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(krt, "_run_retrieval", fake_run_retrieval)

    tool = _build_tool()
    session = object()
    with pytest.raises(asyncio.CancelledError) as excinfo:
        await tool.invoke({"query": "q"}, session=session)

    assert [call[0] for call in fake.calls] == ["start", "error"]
    assert fake.calls[1][2] is excinfo.value  # 取消对象原样透传给事件
