# -*- coding: UTF-8 -*-
"""issue #1756：LLM 空结果判定（口径 A）。

分支→场景反向核对：
- received=0                    → 零帧（网关 200+JSON 未被客户端识别）
- 全空 + stop                   → 空响应
- 全空 + length/content_filter  → 截断/拒答
- 仅 reasoning                  → 合法（思考模型）
- 仅 tool_calls                 → 合法
- 有 content                    → 合法
"""
import pytest

from openjiuwen.core.common.exception.errors import FrameworkError

from jiuwen.extension.workflow_node.llm_chain import _validate_llm_output


def _call(**kwargs):
    params = dict(received=1, content="", reasoning="", has_tool_calls=False,
                  finish_reasons=set())
    params.update(kwargs)
    return _validate_llm_output(**params)


def test_zero_chunks_fails():
    with pytest.raises(FrameworkError) as exc:
        _call(received=0)
    assert "未收到任何流式数据" in str(exc.value)


def test_empty_content_fails():
    with pytest.raises(FrameworkError) as exc:
        _call(finish_reasons={"stop"})
    assert "未返回任何内容" in str(exc.value)


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_empty_with_truncation_reason_fails(reason):
    with pytest.raises(FrameworkError) as exc:
        _call(finish_reasons={reason})
    assert reason in str(exc.value)


def test_reasoning_only_is_allowed():
    _call(reasoning="思考中", finish_reasons={"stop"})


def test_tool_calls_only_is_allowed():
    _call(has_tool_calls=True, finish_reasons={"tool_calls"})


def test_content_is_allowed():
    _call(content="hello", finish_reasons={"stop"})
