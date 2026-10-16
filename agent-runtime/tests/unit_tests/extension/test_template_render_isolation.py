# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件验证模板渲染按调用克隆、原 processor 的位置字段不被推进，判据的观测面
# 就是受保护成员（_processor/_template_processor/_current_position/_chunk_index/
# _count/_lock/_condition/_new_renderer）：渲染隔离性与同步原语是否按调用重建
# 没有公开入口可观测，故必须直接访问这些成员。
# pylint: disable=protected-access
"""Message/FlowCard 模板渲染位置并发隔离测试。

审计结论：两组件本体零执行期实例写入，但共享 ``self._processor`` /
``self._template_processor``（TemplateProcessor）的 ``render_stream`` 逐段推进
``_current_position/_chunk_index/_count``——并发执行渲染位置互踩（顺序复用可经
render_stream finally 的 reset 自愈，并发不行）。Message 无 ``set_mix``，引擎不会
帮它复位。

修复：渲染调用点先克隆 TemplateProcessor（浅拷贝隔离位置字段；浅拷贝会连
``_lock/_condition`` 一起共享，而父类 ``_render_stream`` 在持锁期间逐帧 yield，
故按调用重建同步原语，参照 end.py 的 ``_prepare_render_state``）。

核心断言：渲染后原 processor 的位置字段与渲染前一致 + 克隆确实发生 + 锁/条件不共享。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from openjiuwen.core.workflow.components.flow.end_comp import TemplateProcessor

from jiuwen.extension.workflow_node.flow_card import FlowCard, FlowCardConfig
from jiuwen.extension.workflow_node.flow_message import Message


def _mock_session(comp_id: str = "comp") -> MagicMock:
    """Message/FlowCard 渲染测试用 mock session（仅覆盖渲染路径所需接口）。"""
    session = MagicMock()
    session.get_component_id = MagicMock(return_value=comp_id)
    session.get_workflow_id = MagicMock(return_value="test_wf")
    session.get_session_id = MagicMock(return_value="test_sess")
    # 小超时：变量缺失时 render_stream 会 wait 超时后跳过，加速测试
    session.get_env = MagicMock(return_value=0.01)
    session.get_global_state = MagicMock(return_value=None)
    session.write_custom_stream = AsyncMock()
    return session


def _spy_render_stream(monkeypatch, seen: list) -> None:
    """记录 render_stream 实际被调用的 processor 实例（克隆断言用）。"""
    original = TemplateProcessor.render_stream

    def spy(self, inputs, session, timeout=0.2):
        seen.append(self)
        return original(self, inputs, session, timeout)

    monkeypatch.setattr(TemplateProcessor, "render_stream", spy)


def _spy_render(monkeypatch, seen: list) -> None:
    """记录 render 实际被调用的 processor 实例（克隆断言用）。"""
    original = TemplateProcessor.render

    def spy(self, inputs):
        seen.append(self)
        return original(self, inputs)

    monkeypatch.setattr(TemplateProcessor, "render", spy)


class TestMessageRenderIsolation:
    """Message 渲染调用点（invoke / stream）按调用克隆 TemplateProcessor。"""

    @pytest.mark.asyncio
    async def test_invoke_renders_on_clone_and_leaves_original_untouched(self, monkeypatch):
        """invoke 的 render_stream 使用克隆；原 processor 位置字段保持不变。"""
        seen: list = []
        _spy_render_stream(monkeypatch, seen)
        # 模板变量相对 userFields 展平（Message._resolve_user_fields 先解包 userFields）
        msg = Message({"template": "hello {{answer}}", "name": "m"})
        original = msg._processor

        session = _mock_session("msg_invoke")
        result = await msg.invoke({"userFields": {"answer": "world"}}, session, None)

        assert result == {"result": "hello world"}
        assert seen, "render_stream 未被调用"
        assert all(renderer is not original for renderer in seen), "渲染未使用克隆 processor"
        assert original._current_position == 0
        assert original._chunk_index == 0
        assert original._count == 0

    @pytest.mark.asyncio
    async def test_stream_renders_on_clone_and_leaves_original_untouched(self, monkeypatch):
        """stream 的 render_stream 使用克隆；原 processor 位置字段保持不变。"""
        seen: list = []
        _spy_render_stream(monkeypatch, seen)
        msg = Message({"template": "hi {{name}}"})
        original = msg._processor

        session = _mock_session("msg_stream")
        outputs = [chunk async for chunk in msg.stream({"userFields": {"name": "n"}}, session, None)]

        assert outputs, "stream 未产出帧"
        assert outputs[-1].payload.get("result") == "hi n"
        assert seen, "render_stream 未被调用"
        assert all(renderer is not original for renderer in seen), "渲染未使用克隆 processor"
        assert original._current_position == 0
        assert original._chunk_index == 0
        assert original._count == 0

    @pytest.mark.asyncio
    async def test_clone_rebuilds_sync_primitives(self):
        """克隆重建 _lock/_condition（render_stream 持锁逐帧 yield，共享会队头阻塞）。"""
        msg = Message({"template": "x{{userFields.a}}"})
        original = msg._processor

        renderer = msg._new_renderer()

        assert renderer is not original
        assert renderer._lock is not original._lock
        assert renderer._condition is not original._condition
        # 位置字段独立推进
        renderer.advance_position()
        assert renderer._current_position == 1
        assert original._current_position == 0
        assert renderer._segments is original._segments  # 模板 split 结果只读共享

    @pytest.mark.asyncio
    async def test_concurrent_invokes_do_not_interleave_positions(self):
        """并发渲染互踩复现：模板两变量段，两路各缺一个变量。

        共享 processor 时：先到者持锁渲染到缺失变量处释放锁等待，后到者从中间
        位置接管并 reset，先到者超时恢复后从头重渲染 → 输出重复/截断。
        """
        msg = Message({"template": "P{{x}}Q{{y}}R"})
        original = msg._processor

        result_a, result_b = await asyncio.gather(
            msg.invoke({"userFields": {"x": "ax"}}, _mock_session("a"), None),
            msg.invoke({"userFields": {"y": "by"}}, _mock_session("b"), None),
        )

        assert result_a == {"result": "PaxQR"}
        assert result_b == {"result": "PQbyR"}
        assert original._current_position == 0
        assert original._count == 0


class TestFlowCardRenderIsolation:
    """FlowCard 渲染调用点（invoke→render / stream→render_stream）按调用克隆。"""

    @pytest.mark.asyncio
    async def test_invoke_renders_on_clone(self, monkeypatch):
        """invoke 的 render 使用克隆；原 processor 位置字段保持不变。"""
        seen: list = []
        _spy_render(monkeypatch, seen)
        card = FlowCard(FlowCardConfig(template="你好，{{name}}！"))
        original = card._template_processor

        result = await card.invoke({"name": "张三"}, _mock_session("card_invoke"), None)

        assert result == {"result": "你好，张三！"}
        assert seen, "render 未被调用"
        assert all(renderer is not original for renderer in seen), "渲染未使用克隆 processor"
        assert original._current_position == 0

    @pytest.mark.asyncio
    async def test_stream_renders_on_clone_and_leaves_original_untouched(self, monkeypatch):
        """stream 的 render_stream 使用克隆；原 processor 位置字段保持不变。"""
        seen: list = []
        _spy_render_stream(monkeypatch, seen)
        card = FlowCard(FlowCardConfig(template="流式{{data}}"))
        original = card._template_processor

        session = _mock_session("card_stream")
        outputs = [chunk async for chunk in card.stream({"data": "内容"}, session, None)]

        assert outputs, "stream 未产出帧"
        assert seen, "render_stream 未被调用"
        assert all(renderer is not original for renderer in seen), "渲染未使用克隆 processor"
        assert original._current_position == 0
        assert original._chunk_index == 0
        assert original._count == 0
        # 渲染帧内容完整（克隆下逐段推进正常）
        responses = [
            (chunk.payload or {}).get("response")
            for chunk in outputs
            if hasattr(chunk, "payload")
        ]
        assert "内容" in responses

    @pytest.mark.asyncio
    async def test_clone_rebuilds_sync_primitives(self):
        """克隆重建 _lock/_condition；位置字段独立。"""
        card = FlowCard(FlowCardConfig(template="x{{a}}"))
        original = card._template_processor

        renderer = card._new_renderer()

        assert renderer is not original
        assert renderer._lock is not original._lock
        assert renderer._condition is not original._condition
        renderer.advance_position()
        assert renderer._current_position == 1
        assert original._current_position == 0
