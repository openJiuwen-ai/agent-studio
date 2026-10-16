# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# 本文件是 FlowInput / Extractor / FlowKnowledgeRetrieval 跨执行状态清理的白盒验收：
# 判据的观测面就是组件的私有实现细节（懒初始化锁、初始化入口、LLM 调用桩、加载后的
# 知识库配置缓存），这些成员没有公开入口可读写，断言必须直接钉住“并发首调只初始化
# 一次”“末帧输出不再落实例”这类内部不变量，故按测试需要直接访问。
# 用例 docstring 均写在 def 下一行并缩进 4 空格；多行正文的续行与首行对齐、
# 收尾三引号随末行正文，为本文件统一写法。
# pylint: disable=protected-access,function-docstring-indents-four
"""FlowInput / Extractor / FlowKnowledgeRetrieval 执行期状态清理钉住测试
（issue #1555 / Task 18）。

Task 17 全量审计（spec 附录 A）裁定三型组件仍有执行期残留：

1. FlowInput：末帧输出落实例字段 ``_stream_output``（写点 :464/:531，读点
   ``get_stream_output``，invoke/stream 入口均无复位）；``_node_state``
   执行期多点写实例（原 :399/:447/:453/:478/:520/:546）——实例跨执行复用后
   上一执行残留会被本执行读到（``should_interrupt`` / ``get_state`` 读点）。
2. Extractor：``inputs`` / ``user_response`` 执行期写实例（原 :846/:852）并被
   invoke 链回读（原 :630 / :801）；``node_field.extracted_key_fields`` 为实例级
   累积容器（``update_key_fields`` 写 → ``reply_key_fields`` 整体写入输出），
   跨执行累积；``init`` 名为初始化、实为 invoke 首调的懒初始化且无锁（并发首调
   重复建 Model）。
3. FlowKnowledgeRetrieval：``ensure_kb_config`` check-then-act 无锁（并发首调
   重复从 OBS 加载）。

本测试钉住的修复（源码由 Task 18 前任实现者完成、经 stash 恢复；测试为本任
补写）：

- FlowInput：末帧走 ``execution_session_ctx`` 的 ContextVar 通道（invoke/stream
  入口复位、出口不 reset 供引擎 ``Vertex._post_stream`` 读取）；``_node_state``
  每执行入口从 session 重建（session 恢复型写点保留、覆写型写点删除，实例残留
  被本次执行覆盖）。
- Extractor：``inputs`` / ``user_response`` 不落实例（局部变量 + 参数在 invoke
  链内传递）；``extracted_key_fields`` 随返回值传递（``update_key_fields`` 返回
  → ``reply_key_fields`` 写入输出），实例级累积容器与 ``ExtractorField`` 死字段
  一并删除；``_ensure_initialized`` 双检加锁，并发首调只执行一次 ``init``。
- FlowKnowledgeRetrieval：``ensure_kb_config`` 双检加锁，并发首调只加载一次。
"""
import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from jiuwen.extension.workflow import execution_session_ctx as ctx


@pytest.fixture(autouse=True)
def _clean_exec_channels():
    """末帧 ContextVar 通道进程内共享，用例前后复位避免互相串扰。"""
    ctx.set_stream_final_output(None)
    yield
    ctx.set_stream_final_output(None)


# =============================================================================
# FlowInput
# =============================================================================


def _flow_input(conf=None):
    from jiuwen.extension.workflow_node.flow_input import FlowInput

    return FlowInput(conf if conf is not None else {"name": "flow_input"})


def _flow_input_session(saved_state=None, user_response=None):
    """最小 session 桩。

    ``spec_set`` 限定 API 面：``_inner`` 解析为 None（无父工作流），
    ``_build_custom_data`` 不产生 parentNodeId。
    """
    session = MagicMock(
        spec_set=[
            "get_state",
            "update_state",
            "get_component_id",
            "write_custom_stream",
            "interact",
        ]
    )
    session.get_state = MagicMock(return_value=saved_state or {})
    session.update_state = MagicMock()
    session.get_component_id = MagicMock(return_value="flow_input_node")
    session.write_custom_stream = AsyncMock()
    session.interact = AsyncMock(
        return_value=user_response if user_response is not None else {}
    )
    return session


class TestFlowInputResidualState:
    @staticmethod
    def test_no_instance_stream_output_field():
        """实例不再持有末帧字段 ``_stream_output``（源码级 + 实例级）。"""
        from jiuwen.extension.workflow_node.flow_input import FlowInput

        src = inspect.getsource(FlowInput)
        assert "self._stream_output" not in src
        assert not hasattr(_flow_input(), "_stream_output")

    @pytest.mark.asyncio
    async def test_final_output_entry_reset_discards_stale_channel(self):
        """入口复位判别：上一执行末帧不经本执行（resume 路径不写新末帧）。

        预置 stale 末帧后驱动 USER_INTERACT（session 恢复）路径成功返回——该
        路径不写新末帧，若 invoke 入口无 ``set_stream_final_output(None)``，
        ``get_stream_output`` 会读到上一执行的 stale 值（引擎
        ``Vertex._post_stream`` 会将其写入本次 io_state）。删掉入口复位本用例
        转红。
        """
        from jiuwen.extension.workflow_node.flow_input import FLOW_INPUT_STATE_KEY

        ctx.set_stream_final_output({"stale": True})
        fi = _flow_input()
        session = _flow_input_session(
            saved_state={
                FLOW_INPUT_STATE_KEY: {
                    "status": "user_interact",
                    "question": "q1",
                }
            },
            user_response={"field": "value"},
        )

        result = await fi.invoke({}, session, MagicMock())

        assert result == {"userFields": {}}
        assert ctx.get_stream_final_output() is None
        assert fi.get_stream_output() is None

    @pytest.mark.asyncio
    async def test_final_output_new_value_overrides_stale(self):
        """START 路径末帧写入通道：新值覆盖 stale，形态为 custom_data 原样。"""
        from jiuwen.extension.workflow_node.flow_input import FlowInputUtils

        ctx.set_stream_final_output({"stale": True})
        fi = _flow_input({"name": "flow_input"})
        session = _flow_input_session()

        await fi.invoke({}, session, MagicMock())

        query = FlowInputUtils.build_inputs_message(fi.config)
        expected = {
            "answer": query,
            "result": query,
            "node_id": "flow_input_node",
            "node_name": "flow_input",
            "node_type": "jiuwen.input",
            "should_interrupt": True,
        }
        assert session.interact.await_args.args == (query,)
        assert ctx.get_stream_final_output() == expected
        assert fi.get_stream_output() == expected

    @pytest.mark.asyncio
    async def test_stream_path_writes_final_output_to_channel(self):
        """stream 入口复位 + START 路径末帧写通道（引擎在流耗尽后读取）。"""
        ctx.set_stream_final_output({"stale": True})
        fi = _flow_input()
        session = _flow_input_session()

        frames = [frame async for frame in fi.stream({}, session, MagicMock())]

        assert frames == []  # START 路径 interact 后 return，无流式帧
        out = ctx.get_stream_final_output()
        assert out is not None
        assert out["node_type"] == "jiuwen.input"
        assert out["node_id"] == "flow_input_node"
        assert "stale" not in out

    @pytest.mark.asyncio
    async def test_stale_node_state_overwritten_by_session_rebuild(self):
        """实例残留概念已消除（评审 Suggestion-1 通道迁移）：无 _node_state
        实例字段，行为等价于"入口重建覆盖残留"。

        判定表（迁移后）：invoke/stream 入口从 session 恢复（session 为真源）；
        执行期状态为局部变量，逃逸面经 component_state 通道读取——invoke
        结束通道复位，get_state 回退初始状态（不再反映上次执行）。
        本用例验证：空 session 执行走 START 路径（interact 携带 fresh query）、
        实例无字段可残留、invoke 外逃逸面为初始状态。
        """
        from jiuwen.extension.workflow_node.flow_input import (
            ExecutionStatus,
            FlowInputState,
            FlowInputUtils,
        )

        fi = _flow_input()
        # 实例上已无 _node_state 字段可预置残留（注入也不影响行为）
        assert not hasattr(fi, "_node_state")
        session = _flow_input_session()

        await fi.invoke({}, session, MagicMock())

        fresh_query = FlowInputUtils.build_inputs_message(fi.config)
        assert session.interact.await_args.args == (fresh_query,)
        # invoke 外通道已复位：逃逸面回退初始状态（不反映上次执行）
        assert isinstance(fi.get_state(), FlowInputState)
        assert fi.get_state().status == ExecutionStatus.START
        assert fi.should_interrupt() is False

    @pytest.mark.asyncio
    async def test_session_saved_state_wins_over_instance_residue(self):
        """session 恢复型保留：恢复态以 session 为准（真源），逃逸面 invoke
        外回退初始状态（执行期状态经通道，结束即复位）。"""
        from jiuwen.extension.workflow_node.flow_input import (
            FLOW_INPUT_STATE_KEY,
        )

        fi = _flow_input()
        session = _flow_input_session(
            saved_state={
                FLOW_INPUT_STATE_KEY: {
                    "status": "user_interact",
                    "question": "from-session-q",
                }
            },
            user_response={},
        )

        await fi.invoke({}, session, MagicMock())

        assert session.interact.await_args.args == ("from-session-q",)
        # invoke 外通道已复位：逃逸面为初始状态（恢复态只活在执行窗口内）
        assert fi.should_interrupt() is False


# =============================================================================
# Extractor
# =============================================================================


class _RecordingPrompt:
    """记录 ``format`` 入参的 prompt 桩（``to_messages`` 返回空列表即可驱动链）。"""

    def __init__(self):
        self.inputs = []

    def format(self, template_input):
        self.inputs.append(template_input)
        return SimpleNamespace(to_messages=lambda: [])


def _extractor():
    from jiuwen.extension.workflow_node.flow_extractor import Extractor

    return Extractor()


def _extractor_ready(llm_response='{"name": "小明"}'):
    """最小可运行 Extractor：绕过懒初始化，注入最小配置与 prompt 桩。"""
    from jiuwen.extension.workflow_node.flow_extractor import ExtractorConfig

    ext = _extractor()
    ext.llm = MagicMock()
    ext.extractor_config = ExtractorConfig(
        cn_fields_name={"name": "姓名"},
        key_fields=[{"name": "name", "desc": "名字"}],
        with_chat_history=True,
        chat_history_max_rounds=2,
    )
    ext.prompt = _RecordingPrompt()
    ext._invoke_llm = AsyncMock(return_value=llm_response)
    return ext


def _extractor_two_fields(llm_response='{"name": "小明"}'):
    """双字段配置的 Extractor（用于 key_fields 跨执行累积判别）。"""
    ext = _extractor_ready(llm_response)
    ext.extractor_config.cn_fields_name = {"name": "姓名", "city": "城市"}
    ext.extractor_config.key_fields = [
        {"name": "name", "desc": "名字"},
        {"name": "city", "desc": "城市"},
    ]
    return ext


def _extractor_session():
    """session 桩：``trace`` 真让出事件循环（sleep），用于制造执行期交错。"""
    session = MagicMock(spec_set=["trace", "get_session_id"])

    async def _slow_trace(payload):
        await asyncio.sleep(0.02)

    session.trace = _slow_trace
    session.get_session_id = MagicMock(return_value="sess-1")
    return session


def _ctx_with_user(content):
    context = MagicMock()
    context.get_messages = MagicMock(
        return_value=[
            SimpleNamespace(role="user", content=content, enable_history=True)
        ]
    )
    return context


class TestExtractorResidualState:
    @staticmethod
    def test_no_instance_exec_state_fields():
        """``inputs`` / ``user_response`` / ``node_field`` 不再落实例。

        源码级 + 实例级双断言（``node_field.extracted_key_fields`` 累积容器
        与 ``ExtractorField`` 死字段一并删除）。
        """
        from jiuwen.extension.workflow_node.flow_extractor import Extractor

        src = inspect.getsource(Extractor)
        assert "self.inputs" not in src
        assert "self.user_response" not in src
        assert "self.node_field" not in src

        ext = _extractor()
        assert not hasattr(ext, "inputs")
        assert not hasattr(ext, "user_response")
        assert not hasattr(ext, "node_field")

    @pytest.mark.asyncio
    async def test_concurrent_invokes_do_not_cross_read_user_response(self):
        """局部化判别：并发两次 invoke 各读各的 user_response。

        实例跨执行复用（静态图复用）下两执行在 ``session.trace`` 处真交错
        （sleep 让出事件循环）：旧实现把 user_response 写实例字段、在
        ``create_prompt_template_input`` 回读，先交错者读到后交错者的值
        （本用例断言 A 执行输出与提示词为自己消息即转红）。修复后
        user_response 随参数在 invoke 链内传递，互不串扰。
        """
        ext = _extractor_ready()
        session_a = _extractor_session()
        session_b = _extractor_session()

        results = await asyncio.gather(
            ext.invoke({}, session_a, _ctx_with_user("A-msg")),
            ext.invoke({}, session_b, _ctx_with_user("B-msg")),
        )

        assert results[0]["userFields"]["USER_RESPONSE"] == "A-msg"
        assert results[1]["userFields"]["USER_RESPONSE"] == "B-msg"

        dig_histories = [item["dig_history"] for item in ext.prompt.inputs]
        assert len(dig_histories) == 2
        a_dig = [d for d in dig_histories if "A-msg" in d]
        b_dig = [d for d in dig_histories if "B-msg" in d]
        assert len(a_dig) == 1 and len(b_dig) == 1
        assert "B-msg" not in a_dig[0]
        assert "A-msg" not in b_dig[0]

    @pytest.mark.asyncio
    async def test_second_invoke_reflects_own_context(self):
        """同实例第二次 invoke：输出与提示词只反映本次上下文（回归守卫）。"""
        ext = _extractor_ready()
        session = _extractor_session()

        first = await ext.invoke({}, session, _ctx_with_user("first-msg"))
        second = await ext.invoke({}, session, _ctx_with_user("second-msg"))

        assert first["userFields"]["USER_RESPONSE"] == "first-msg"
        assert second["userFields"]["USER_RESPONSE"] == "second-msg"
        first_dig, second_dig = (item["dig_history"] for item in ext.prompt.inputs)
        assert "first-msg" in first_dig and "second-msg" not in first_dig
        assert "second-msg" in second_dig and "first-msg" not in second_dig

    @pytest.mark.asyncio
    async def test_second_execution_output_excludes_previous_key_fields(self):
        """判别用例：第二次执行输出不含上一执行提取的 key_fields。

        旧实现 ``node_field.extracted_key_fields`` 为实例级累积容器
        （update_key_fields 写 → reply_key_fields 整体写入输出），静态图复用
        下上一执行的提取值会并入后续执行输出。本用例第二次 LLM 只返回 city，
        输出必须只有 city（含 name 即转红）。
        """
        ext = _extractor_two_fields('{"name": "小明"}')
        session = _extractor_session()

        first = await ext.invoke({}, session, _ctx_with_user("first-msg"))
        assert first["userFields"]["name"] == "小明"
        assert "city" not in first["userFields"]

        ext._invoke_llm = AsyncMock(return_value='{"city": "北京"}')
        second = await ext.invoke({}, session, _ctx_with_user("second-msg"))

        assert second["userFields"]["city"] == "北京"
        assert "name" not in second["userFields"]

    @pytest.mark.asyncio
    async def test_concurrent_executions_do_not_share_extracted_key_fields(self):
        """判别用例：并发两执行的输出互不含对方的 key_fields（不共享累积容器）。

        session.trace（sleep）真交错：旧实现共享 ``node_field`` 容器，后完成者
        把先完成者的字段并入自己的输出（本用例断言 B 输出无 A 的字段即转红）。
        ``responses.pop(0)`` 依赖 gather 下 A 先于 B 到达 ``_invoke_llm``（两执行
        await 序列一致，顺序确定）。
        """
        responses = ['{"name": "小明"}', '{"city": "北京"}']

        async def _llm_by_order(messages):
            await asyncio.sleep(0.01)
            return responses.pop(0)

        ext = _extractor_two_fields()
        ext._invoke_llm = _llm_by_order  # 按调用序返回不同响应
        session_a = _extractor_session()
        session_b = _extractor_session()

        results = await asyncio.gather(
            ext.invoke({}, session_a, _ctx_with_user("A-msg")),
            ext.invoke({}, session_b, _ctx_with_user("B-msg")),
        )

        assert set(results[0]["userFields"]) == {"USER_RESPONSE", "name"}
        assert set(results[1]["userFields"]) == {"USER_RESPONSE", "city"}

    @pytest.mark.asyncio
    async def test_init_lock_serializes_concurrent_first_calls(self, monkeypatch):
        """懒初始化双检加锁：init 在锁内执行且并发首调只执行一次（判别）。

        预置（外部持有）``_init_lock`` 后启动两个并发首调：修复实现两者都停在
        锁上（``init`` 未被调用）；若 init 不在锁内执行（旧实现直接调 init），
        第一个任务立即完成 init → ``calls`` 非空 → 转红。释放锁后仅一次 init。
        """
        ext = _extractor()
        calls = []

        def _fake_init(conf, session, context):
            calls.append(conf)
            ext.llm = MagicMock()

        monkeypatch.setattr(ext, "init", _fake_init)
        lock = ext._init_lock
        assert isinstance(lock, asyncio.Lock)

        await lock.acquire()
        tasks = [
            asyncio.create_task(
                ext._ensure_initialized({"k": 1}, MagicMock(), MagicMock())
            ),
            asyncio.create_task(
                ext._ensure_initialized({"k": 1}, MagicMock(), MagicMock())
            ),
        ]
        await asyncio.sleep(0.02)
        assert calls == []  # 两协程都停在锁上，init 未执行
        lock.release()
        await asyncio.gather(*tasks)

        assert calls == [{"k": 1}]
        assert ext.llm is not None


# =============================================================================
# FlowKnowledgeRetrieval
# =============================================================================


class TestFlowKnowledgeRetrievalInitLock:
    @pytest.mark.asyncio
    async def test_ensure_kb_config_concurrent_first_calls_load_once(
        self, monkeypatch
    ):
        """ensure_kb_config 双检加锁：并发首调只从 provider 加载一次（判别）。

        ``get_kb_config`` 内 sleep 让出事件循环制造真交错：无锁时两个协程都会
        通过 ``if self._kb_config is not None`` 检查，重复加载。
        """
        from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
            FlowKnowledgeRetrieval,
        )

        comp = FlowKnowledgeRetrieval(
            {
                "connectionId": "conn-1",
                "knowledgeBaseIds": ["kb-1"],
                "retrievalConfig": {},
            }
        )
        assert isinstance(comp._init_lock, asyncio.Lock)

        expected = {"connection": {"id": "conn-1"}, "knowledge_bases": [{"id": "kb-1"}]}
        loads = []

        async def _slow_get_kb_config(ir_node):
            loads.append(ir_node)
            await asyncio.sleep(0.02)
            return expected

        provider = MagicMock()
        provider.get_kb_config = _slow_get_kb_config
        monkeypatch.setattr(FlowKnowledgeRetrieval, "_kb_provider", provider)

        results = await asyncio.gather(
            comp.ensure_kb_config(), comp.ensure_kb_config()
        )

        assert len(loads) == 1
        assert loads[0] == {
            "configs": {
                "connectionId": "conn-1",
                "knowledgeBaseIds": ["kb-1"],
                "retrievalConfig": {},
            }
        }
        assert results == [expected, expected]
        assert comp._kb_config == expected

        # 已加载后再次调用不再触发 provider（命中首检）
        assert await comp.ensure_kb_config() == expected
        assert len(loads) == 1
