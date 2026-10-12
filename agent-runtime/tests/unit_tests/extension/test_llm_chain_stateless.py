# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""LLMChain 组件跨执行隔离测试（静态图复用前提，issue #1555 / Task 11）。

审计发现：实例复用后，执行期状态落在组件实例上——
`self._session` / `self._context`（invoke/stream 入口覆写，辅助方法回读）、
`self._stream_final_output`（流式末帧，引擎 `Vertex._post_stream` 经
`get_stream_output` 消费），以及 `_initialize_if_needed` 懒初始化无锁
（并发首调会重复建 Model，第二次结果覆盖第一次、旧 Model 泄漏）。

本测试钉住：
1. 实例上不再挂执行期 session/context/末帧字段（死代码 `_state` 一并删除）；
2. 末帧输出走 Task 1 的 ContextVar 通道（set/get 直连，不落实例）；
3. 懒初始化双检加锁：并发首调只建一次 Model；
4. invoke / stream 入口 set component_exec、退出后 reset（含嵌套 invoke 的
   JSON 模式 stream 路径，set/reset 同值幂等）。
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.foundation.llm import UserMessage

from jiuwen.extension.workflow import execution_session_ctx as ctx
from jiuwen.extension.workflow_node.llm_chain import LLMChain


@pytest.fixture(autouse=True)
def _clean_exec_channels():
    """两个执行期 ContextVar 通道进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_component_exec(None, None)
    ctx.set_stream_final_output(None)
    yield
    ctx.set_component_exec(None, None)
    ctx.set_stream_final_output(None)


def _conf(response_type="text"):
    return {
        "name": "llm",
        "model": {
            "modelName": "test-model",
            "modelType": "LLM",
            "hyperParameters": {"thinking": {"type": "disabled"}},
            "extension": {},
        },
        "deployMode": "workflow",
        "templateContent": [{"content": "{{query}}", "role": "user"}],
        "responseFormat": {"type": response_type},
        "userFields": {
            "inputs": [],
            "outputs": [{"sourceType": "input", "id": "raw_output", "type": "string"}],
        },
        "enableHistory": False,
        "memory": {"enable": False},
    }


class _FakeLLMOutput:
    """最小 LLM 输出桩（不触发 MagicMock 的 usage_metadata 自动属性）。"""

    def __init__(self, content="hi"):
        self.content = content
        self.reasoning_content = None
        self.usage_metadata = None


class TestLLMChainStateless:
    def test_no_exec_state_instance_fields(self):
        """实例不再持有执行期 session/context/末帧字段（死代码 _state 亦删除）。"""
        chain = LLMChain({"name": "llm"})
        assert not hasattr(chain, "_session")
        assert not hasattr(chain, "_context")
        assert not hasattr(chain, "_stream_final_output")
        assert not hasattr(chain, "_state")

    def test_stream_final_output_via_contextvar(self):
        chain = LLMChain({"name": "llm"})
        ctx.set_stream_final_output({"userFields": "a"})
        assert chain.get_stream_output() == {"userFields": "a"}
        ctx.set_stream_final_output({"userFields": "b"})
        assert chain.get_stream_output() == {"userFields": "b"}
        ctx.set_stream_final_output(None)

    @pytest.mark.asyncio
    async def test_lazy_init_lock_dedupes_concurrent_first_calls(self):
        """并发首调只建一次 Model（锁双检）。

        side_effect 内 sleep(0) 让出事件循环制造真交错：无锁时两个协程都会
        通过 `if not self._initialized` 检查，重复建 Model。
        """
        chain = LLMChain({"name": "llm"})

        async def _slow_create():
            await asyncio.sleep(0)
            return MagicMock()

        chain._create_llm_instance = AsyncMock(side_effect=_slow_create)
        await asyncio.gather(
            chain._initialize_if_needed(), chain._initialize_if_needed()
        )
        assert chain._create_llm_instance.call_count == 1

    def test_get_chat_history_reads_component_exec_channel(self):
        """辅助方法经 ContextVar 读 context：设通道有历史，复位后为空。"""
        chain = LLMChain(_conf())
        context = MagicMock()
        context.get_messages = MagicMock(return_value=[UserMessage(content="u1")])

        token = ctx.set_component_exec(None, context)
        try:
            assert chain._get_chat_history() == [{"role": "user", "content": "u1"}]
        finally:
            ctx.reset_component_exec(token)
        assert chain._get_chat_history() == []

    @pytest.mark.asyncio
    async def test_invoke_sets_and_resets_component_exec(self):
        """invoke 期间通道可见 (session, context)，返回后复位。"""
        chain = LLMChain(_conf())
        chain._initialized = True
        chain._llm = MagicMock()
        session = MagicMock()
        context = MagicMock()
        context.get_messages = MagicMock(return_value=[UserMessage(content="u1")])

        seen = {}

        async def _capture(**kwargs):
            seen["exec"] = ctx.current_component_exec()
            return _FakeLLMOutput()

        chain._llm.invoke = AsyncMock(side_effect=_capture)
        result = await chain.invoke(
            {"userFields": {"query": "q"}}, session=session, context=context
        )

        assert seen["exec"] == (session, context)
        assert result["userFields"] == {"raw_output": "hi"}
        assert ctx.current_component_exec() == (None, None)

    @pytest.mark.asyncio
    async def test_invoke_resets_component_exec_on_error(self):
        """invoke 异常路径同样复位通道（finally）。"""
        chain = LLMChain(_conf())
        chain._initialized = True
        chain._llm = MagicMock()
        chain._llm.invoke = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(Exception):
            await chain.invoke(
                {"userFields": {"query": "q"}},
                session=MagicMock(),
                context=MagicMock(),
            )
        assert ctx.current_component_exec() == (None, None)

    @pytest.mark.asyncio
    async def test_stream_json_mode_nested_invoke_keeps_channel(self):
        """JSON 模式 stream 内嵌 invoke（嵌套 set/reset 同值幂等）：
        末帧写入 ContextVar 通道，generator 耗尽后通道复位。"""
        chain = LLMChain(_conf(response_type="json"))
        chain._initialized = True
        chain._llm = MagicMock()
        chain._llm.invoke = AsyncMock(return_value=_FakeLLMOutput(content='{"raw_output": "hi"}'))
        session = MagicMock()
        session.get_component_id = MagicMock(return_value="llm_node")
        session.write_custom_stream = AsyncMock()

        frames = []
        async for frame in chain.stream(
            {"userFields": {"query": "q"}}, session=session, context=MagicMock()
        ):
            frames.append(frame)

        assert len(frames) == 1
        assert chain.get_stream_output() == frames[0]
        assert ctx.current_component_exec() == (None, None)

    @pytest.mark.asyncio
    async def test_stream_entry_reset_clears_stale_final_output_on_failure(self):
        """入口复位末帧通道：上一执行的末帧不串入本执行（判别用例）。

        预置 stale 末帧后驱动 stream 在**写末帧之前**失败（非 JSON 路径
        `_llm.stream` 抛错）。成功路径会写新末帧、掩盖入口复位，故必须用
        「写末帧前失败」路径判别：删掉入口 `set_stream_final_output(None)`
        时本用例读到 stale 值转红。
        """
        ctx.set_stream_final_output({"stale": True})

        chain = LLMChain(_conf())
        chain._initialized = True
        chain._llm = MagicMock()
        chain._llm.stream = MagicMock(side_effect=RuntimeError("boom"))
        session = MagicMock()
        session.get_component_id = MagicMock(return_value="llm_node")

        with pytest.raises(BaseError, match="LLM stream failed"):
            async for _ in chain.stream(
                {"userFields": {"query": "q"}}, session=session, context=MagicMock()
            ):
                pass

        assert chain.get_stream_output() is None
        assert ctx.current_component_exec() == (None, None)

    @pytest.mark.asyncio
    async def test_stream_aclose_resets_component_exec(self):
        """消费方提前 aclose（中断迭代）同样走 finally 复位 component_exec。"""
        chain = LLMChain(_conf(response_type="json"))
        chain._initialized = True
        chain._llm = MagicMock()
        chain._llm.invoke = AsyncMock(return_value=_FakeLLMOutput(content='{"raw_output": "hi"}'))
        session = MagicMock()
        session.get_component_id = MagicMock(return_value="llm_node")
        session.write_custom_stream = AsyncMock()
        context = MagicMock()

        gen = chain.stream(
            {"userFields": {"query": "q"}}, session=session, context=context
        )
        assert await gen.__anext__() is not None
        # 迭代期间通道生效（generator 体与消费者同 context）
        assert ctx.current_component_exec() == (session, context)
        await gen.aclose()
        assert ctx.current_component_exec() == (None, None)
