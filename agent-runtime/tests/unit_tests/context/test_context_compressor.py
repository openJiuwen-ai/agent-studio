# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""超长上下文压缩测试（issue #1475）

覆盖：token 估算、分层边界切分、condition 触发、arun/run 压缩（摘要/截断/
回退）、update_compressed_history handler、ContextConfig 解析校验、
ContextEngine 接线（调度/竞态保护/并发新增不丢失）。
"""

import asyncio
from types import SimpleNamespace
from typing import List, Optional

import pytest

from jiuwen.common.exception import JiuWenBaseException
from jiuwen.context.base import ContextConfig
from jiuwen.context.engine import ContextEngine
from jiuwen.context.accessor.handler import ContextHandler
from jiuwen.context.base import ContextHandleType, ContextWindow
from jiuwen.context.history import ConversationHistory, ConversationMessage
from jiuwen.context.memory import MemoryContext
from jiuwen.context.processor.compressor import (
    SUMMARY_MESSAGE_PREFIX,
    CompressProcessor,
    CompressProcessorConfig,
    estimate_text_tokens,
    estimate_history_tokens,
    split_compress_boundary,
)


def _msg(role: str, content: str, intent: Optional[List[str]] = None, name: str = None):
    return ConversationMessage(role=role, content=content, intent=intent, name=name)


def _stub_history() -> List[ConversationMessage]:
    """锚点 1 条 user + 2 轮可压缩 + 最后 1 轮保护层。"""
    return [
        _msg("user", "任务目标：审查合同风险", intent=["goal"]),
        _msg("user", "turn2-question " + "x" * 200, intent=["a"]),
        _msg("assistant", "turn2-answer " + "y" * 200),
        _msg("user", "turn3-question " + "x" * 200, intent=["b"]),
        _msg("assistant", "turn3-answer " + "y" * 200),
        _msg("user", "latest-question"),
        _msg("assistant", "latest-answer"),
    ]


class _StubModel:
    """摘要模型桩：记录调用，可注入失败/延迟。"""

    def __init__(self, content: str = "这是压缩后的摘要", fail: bool = False, delay: float = 0.0):
        self.content = content
        self.fail = fail
        self.delay = delay
        self.calls: List[str] = []

    async def ainvoke(self, prompt):
        self.calls.append(prompt)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("model boom")
        return SimpleNamespace(content=self.content)

    def invoke(self, prompt):
        self.calls.append(prompt)
        if self.fail:
            raise RuntimeError("model boom")
        return SimpleNamespace(content=self.content)


def _processor(model=None, **overrides) -> CompressProcessor:
    config = CompressProcessorConfig(
        trigger_token_num=overrides.pop("trigger_token_num", 1),
        keep_recent_turns=overrides.pop("keep_recent_turns", 1),
        **overrides,
    )
    return CompressProcessor(config, model)


# ─── token 估算 ────────────────────────────────────────────────────────


class TestTokenEstimation:
    def test_ascii_and_cjk_ratio(self):
        ascii_tokens = estimate_text_tokens("abcdefgh")  # 8 ascii -> ~2
        cjk_tokens = estimate_text_tokens("你好世界")  # 4 cjk -> ~3
        assert ascii_tokens == 2
        assert cjk_tokens == 3

    def test_empty_text(self):
        assert estimate_text_tokens("") == 0
        assert estimate_text_tokens(None) == 0

    def test_history_tokens_sums_messages(self):
        history = [_msg("user", "abcdefgh"), _msg("assistant", "你好世界")]
        assert estimate_history_tokens(history) == 2 + 3


# ─── 分层边界 ──────────────────────────────────────────────────────────


class TestSplitBoundary:
    def test_anchor_and_protected_layer(self):
        history = _stub_history()
        anchor_end, boundary = split_compress_boundary(history, keep_recent_turns=1)
        assert anchor_end == 1  # 首条 user 保留
        assert history[boundary].role == "user"
        assert history[boundary].content == "latest-question"
        # 压缩层 = msgs[1:boundary]，含 turn2/turn3
        assert boundary == 5

    def test_no_anchor_when_first_message_not_user(self):
        history = [
            _msg("assistant", "hi"),
            _msg("user", "q1"),
            _msg("assistant", "a1"),
        ]
        anchor_end, boundary = split_compress_boundary(history, keep_recent_turns=1)
        assert anchor_end == 0
        assert history[boundary].content == "q1"

    def test_leading_function_messages_join_compressible_layer(self):
        history = [
            _msg("user", "q1"),
            _msg("assistant", "a1"),
            _msg("function", "tool-result", name="search"),
            _msg("user", "q2"),
            _msg("assistant", "a2"),
        ]
        anchor_end, boundary = split_compress_boundary(history, keep_recent_turns=1)
        # 保护层从 q2 开始，其前的孤立 function 消息划入压缩层
        assert history[boundary].content == "q2"

    def test_fewer_turns_than_keep_means_nothing_compressible(self):
        history = [_msg("user", "q1"), _msg("assistant", "a1")]
        anchor_end, boundary = split_compress_boundary(history, keep_recent_turns=5)
        assert boundary == 0
        assert boundary <= anchor_end


# ─── condition / arun / run ───────────────────────────────────────────


class TestCompressProcessor:
    @pytest.mark.asyncio
    async def test_condition_requires_threshold_and_compressible_layer(self):
        processor = _processor(trigger_token_num=10_000, keep_recent_turns=1)
        below = ContextWindow(chat_history=_stub_history())
        assert await processor.condition(below) is False

        processor = _processor(trigger_token_num=1, keep_recent_turns=1)
        above = ContextWindow(chat_history=_stub_history())
        assert await processor.condition(above) is True

    @pytest.mark.asyncio
    async def test_condition_false_when_all_turns_protected(self):
        processor = _processor(trigger_token_num=1, keep_recent_turns=10)
        window = ContextWindow(chat_history=_stub_history())
        assert await processor.condition(window) is False

    @pytest.mark.asyncio
    async def test_arun_summarize_keeps_anchor_summary_and_recent(self):
        model = _StubModel(content="保留关键结论")
        processor = _processor(model=model, keep_recent_turns=1)
        history = _stub_history()
        window = ContextWindow(chat_history=history)

        new_window = await processor.arun(window)

        new_msgs = new_window.chat_history
        # 锚点层
        assert new_msgs[0].content == "任务目标：审查合同风险"
        # 摘要消息（assistant + 前缀 + 合并 intent）
        assert new_msgs[1].role == "assistant"
        assert new_msgs[1].content.startswith(SUMMARY_MESSAGE_PREFIX)
        assert "保留关键结论" in new_msgs[1].content
        assert sorted(new_msgs[1].intent) == ["a", "b"]
        # 保护层
        assert [m.content for m in new_msgs[2:]] == [
            "latest-question",
            "latest-answer",
        ]
        # 压缩层内容进入摘要 prompt
        assert "turn2-question" in model.calls[0]
        assert "turn3-answer" in model.calls[0]
        # 输入窗口不被修改
        assert len(window.chat_history) == 7

    @pytest.mark.asyncio
    async def test_arun_model_failure_falls_back_to_truncate(self):
        model = _StubModel(fail=True)
        processor = _processor(model=model, keep_recent_turns=1)
        window = ContextWindow(chat_history=_stub_history())

        new_window = await processor.arun(window)

        contents = [m.content for m in new_window.chat_history]
        assert contents == ["任务目标：审查合同风险", "latest-question", "latest-answer"]
        assert model.calls  # 确实尝试过摘要

    @pytest.mark.asyncio
    async def test_arun_truncate_strategy_never_calls_model(self):
        model = _StubModel()
        processor = _processor(model=model, keep_recent_turns=1, strategy="truncate")
        window = ContextWindow(chat_history=_stub_history())

        new_window = await processor.arun(window)

        assert model.calls == []
        assert len(new_window.chat_history) == 3

    @pytest.mark.asyncio
    async def test_arun_without_model_truncates(self):
        processor = _processor(model=None, keep_recent_turns=1)
        window = ContextWindow(chat_history=_stub_history())

        new_window = await processor.arun(window)

        assert len(new_window.chat_history) == 3

    @pytest.mark.asyncio
    async def test_arun_returns_same_window_when_nothing_compressible(self):
        processor = _processor(trigger_token_num=1, keep_recent_turns=10)
        window = ContextWindow(chat_history=_stub_history())

        assert await processor.arun(window) is window

    def test_run_sync_summarize(self):
        model = _StubModel(content="同步摘要")
        processor = _processor(model=model, keep_recent_turns=1)

        new_window = processor.run(ContextWindow(chat_history=_stub_history()))

        assert "同步摘要" in new_window.chat_history[1].content
        assert len(new_window.chat_history) == 4

    @pytest.mark.asyncio
    async def test_summary_timeout_falls_back_to_truncate(self):
        model = _StubModel(delay=1.0)
        processor = CompressProcessor(
            CompressProcessorConfig(
                trigger_token_num=1,
                keep_recent_turns=1,
                summary_timeout_seconds=0.01,
            ),
            model,
        )

        new_window = await processor.arun(ContextWindow(chat_history=_stub_history()))

        assert len(new_window.chat_history) == 3


# ─── handler ──────────────────────────────────────────────────────────


class TestUpdateCompressedHistoryHandler:
    def test_handler_replaces_history(self):
        history = ConversationHistory()
        history.add_messages([{"role": "user", "content": "old"}])
        handler = ContextHandler(history, MemoryContext())

        update = handler.get_handler(ContextHandleType.UPDATE_COMPRESSED_HISTORY)
        assert update is not None
        update(ContextWindow(chat_history=[_msg("assistant", "compressed")]))

        assert [m.content for m in history.msgs] == ["compressed"]


# ─── ContextConfig 解析 ───────────────────────────────────────────────


class TestContextConfigParsing:
    def test_defaults_keep_compression_off(self):
        conf = ContextConfig.from_config_dict({})
        assert conf.enable_compression is False
        assert conf.compress_config == {}

    def test_open_compress_with_config(self):
        conf = ContextConfig.from_config_dict(
            {
                "openCompress": True,
                "compressConfig": {
                    "triggerTokenNum": 512,
                    "keepRecentTurns": 2,
                    "strategy": "truncate",
                },
            }
        )
        assert conf.enable_compression is True
        assert conf.compress_config == {
            "trigger_token_num": 512,
            "keep_recent_turns": 2,
            "strategy": "truncate",
        }

    def test_compress_config_defaults(self):
        conf = ContextConfig.from_config_dict({"openCompress": True})
        assert conf.compress_config["trigger_token_num"] == 4096
        assert conf.compress_config["keep_recent_turns"] == 5
        assert conf.compress_config["strategy"] == "summarize"

    def test_invalid_open_compress_type_raises(self):
        with pytest.raises(JiuWenBaseException):
            ContextConfig.from_config_dict({"openCompress": "yes"})

    def test_invalid_trigger_token_num_raises(self):
        with pytest.raises(JiuWenBaseException):
            ContextConfig.from_config_dict(
                {"openCompress": True, "compressConfig": {"triggerTokenNum": 0}}
            )

    def test_invalid_strategy_raises(self):
        with pytest.raises(JiuWenBaseException):
            ContextConfig.from_config_dict(
                {"openCompress": True, "compressConfig": {"strategy": "drop_all"}}
            )

    def test_invalid_summary_prompt_raises(self):
        with pytest.raises(JiuWenBaseException):
            ContextConfig.from_config_dict(
                {"openCompress": True, "compressConfig": {"summaryPrompt": 123}}
            )


# ─── ContextEngine 接线 ───────────────────────────────────────────────


def _engine(model, **compress_kwargs) -> ContextEngine:
    conf = ContextConfig(
        enable_compression=True,
        compress_config={
            "trigger_token_num": compress_kwargs.pop("trigger_token_num", 1),
            "keep_recent_turns": compress_kwargs.pop("keep_recent_turns", 1),
            **compress_kwargs,
        },
    )
    return ContextEngine(context_config=conf, model=model)


class TestContextEngineCompression:
    @pytest.mark.asyncio
    async def test_add_message_schedules_background_compression(self):
        model = _StubModel(content="后台摘要")
        engine = _engine(model)

        engine.add_messages(_stub_history())
        engine.add_message(_msg("user", "new-turn"))
        await asyncio.sleep(0.05)

        contents = [m.content for m in engine.history.msgs]
        assert any(c.startswith(SUMMARY_MESSAGE_PREFIX) for c in contents)
        assert contents[0] == "任务目标：审查合同风险"
        assert "new-turn" in contents

    @pytest.mark.asyncio
    async def test_acompress_history_explicit_call(self):
        model = _StubModel(content="显式摘要")
        engine = _engine(model)
        engine.add_messages(_stub_history())

        await engine.acompress_history()

        assert len(engine.history.msgs) == 4
        assert engine.history.msgs[1].content.startswith(SUMMARY_MESSAGE_PREFIX)

    @pytest.mark.asyncio
    async def test_compression_disabled_by_default(self):
        engine = ContextEngine()
        engine.add_messages(_stub_history())
        await asyncio.sleep(0.02)

        assert len(engine.history.msgs) == 7

    @pytest.mark.asyncio
    async def test_enabled_without_model_disables_compressor(self):
        engine = ContextEngine(
            context_config=ContextConfig(enable_compression=True), model=None
        )
        assert engine._compressor is None
        engine.add_messages(_stub_history())
        await engine.acompress_history()
        assert len(engine.history.msgs) == 7

    @pytest.mark.asyncio
    async def test_below_threshold_not_compressed(self):
        model = _StubModel()
        engine = _engine(model, trigger_token_num=10_000)
        engine.add_messages(_stub_history())

        await engine.acompress_history()

        assert len(engine.history.msgs) == 7
        assert model.calls == []

    @pytest.mark.asyncio
    async def test_messages_added_during_compression_are_preserved(self):
        model = _StubModel(delay=0.05)
        engine = _engine(model)
        # 直接写 history，避免 add_messages 的后台调度干扰时序
        engine.history.add_messages(_stub_history())

        task = asyncio.create_task(engine.acompress_history())
        await asyncio.sleep(0.01)  # 快照完成、摘要进行中
        engine.history.add(_msg("user", "并发新增"))
        await task

        contents = [m.content for m in engine.history.msgs]
        # 并发新增消息保留且不重复
        assert contents.count("并发新增") == 1
        # 压缩层确实被压缩
        assert not any("turn2-question" in c for c in contents)

    @pytest.mark.asyncio
    async def test_prefix_changed_during_compression_skips_apply(self):
        model = _StubModel(delay=0.05)
        engine = _engine(model)
        # 直接写 history，避免 add_messages 的后台调度干扰时序
        engine.history.add_messages(_stub_history())

        task = asyncio.create_task(engine.acompress_history())
        await asyncio.sleep(0.01)
        # 压缩进行中改写前缀（模拟竞态：替换首条消息对象）
        engine.history.msgs[0] = _msg("user", "被改写的锚点")
        await task

        # 前缀变化 -> 放弃应用，历史保持原样
        assert engine.history.msgs[0].content == "被改写的锚点"
        assert len(engine.history.msgs) == 7
