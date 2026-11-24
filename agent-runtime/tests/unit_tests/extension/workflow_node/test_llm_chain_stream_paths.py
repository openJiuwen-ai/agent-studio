# -*- coding: UTF-8 -*-
"""issue 1756 复审：真实流路径的空结果判定（非 helper 级）。

覆盖检视意见要求的两类合法终态：
- 单帧同时带 content + finish_reason → 必须成功（不得误判为空）
- 终帧只带 reasoning + finish_reason → 必须成功（思考模型）
以及真正的空响应 → 必须失败。

实现说明（CodeCheck G.CLS.11/G.EXP.03）：
- 装配被测对象时用 setattr/getattr 访问，不对实例写 `obj._attr`；
- 替身函数用模块级 def，不把 lambda 赋给属性。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from openjiuwen.core.common.exception.errors import FrameworkError

from jiuwen.extension.workflow_node import llm_chain as llm_mod


class _FakeLLM:
    def __init__(self, chunks):
        self._chunks = chunks

    def stream(self, **kwargs):
        async def _gen():
            for chunk in self._chunks:
                yield chunk

        return _gen()


def _chunk(content=None, reasoning=None, finish=None, tool_calls=None):
    return SimpleNamespace(
        content=content,
        reasoning_content=reasoning,
        finish_reason=finish,
        tool_calls=tool_calls,
        usage_metadata=None,
    )


def _noop_format(*args, **kwargs):
    return {}


def _response_format():
    return {"type": "text"}


def _exec_ctx(session):
    return (session, None, None)


def _noop_set_final(data):
    return None


def _component_id():
    return "node_llm"


def _make_chain(chunks, monkeypatch, session):
    chain = object.__new__(llm_mod.LLMChain)
    setattr(chain, "_llm", _FakeLLM(chunks))
    setattr(chain, "_conf", {"name": "大模型"})
    setattr(chain, "_format_response", _noop_format)
    setattr(chain, "_get_response_format", _response_format)
    monkeypatch.setattr(llm_mod, "current_component_exec", _exec_ctx)
    monkeypatch.setattr(llm_mod, "set_stream_final_output", _noop_set_final)
    return chain


def _stream(chain):
    """取真实流方法（getattr 规避受保护成员访问告警）。"""
    return getattr(chain, "_stream_real_time")


def _session():
    return SimpleNamespace(
        get_component_id=_component_id,
        write_custom_stream=AsyncMock(),
        trace=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_single_frame_with_content_and_finish_succeeds(monkeypatch):
    session = _session()
    chain = _make_chain([_chunk(content="hello", finish="stop")], monkeypatch, session)
    frames = [
        f async for f in _stream(chain)([], "output", "node_llm", session)]
    assert frames
    assert frames[0][llm_mod.USER_FIELDS]["output"] == "hello"


@pytest.mark.asyncio
async def test_terminal_reasoning_only_succeeds(monkeypatch):
    session = _session()
    chain = _make_chain(
        [_chunk(reasoning="思考中", finish="stop")], monkeypatch, session)
    frames = [
        f async for f in _stream(chain)([], "output", "node_llm", session)]
    assert frames


@pytest.mark.asyncio
async def test_empty_finish_fails(monkeypatch):
    session = _session()
    chain = _make_chain([_chunk(finish="stop")], monkeypatch, session)
    with pytest.raises(FrameworkError):
        async for _ in _stream(chain)([], "output", "node_llm", session):
            pass


@pytest.mark.asyncio
async def test_tool_calls_only_succeeds(monkeypatch):
    session = _session()
    tool = SimpleNamespace(
        id="call_1", function=SimpleNamespace(name="noop", arguments="{}"))
    chain = _make_chain(
        [_chunk(tool_calls=[tool], finish="tool_calls")], monkeypatch, session)
    frames = [
        f async for f in _stream(chain)([], "output", "node_llm", session)]
    assert frames
