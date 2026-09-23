# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SYNC-01 P5-R3a：run_streaming 三分支 105015 包装路径 guard 分支级测试。

审视 §1.2（95aeecd5 实审复核）：openjiuwen 引擎（graph/vertex.py
``except Exception``）会把 vendored JiuWenBaseException(105015)（Exception
子类、非 BaseError 子类）包成 ExecutionError/BaseError(cause=原异常)——
run_streaming 的 ``except ExecutionError``/``except BaseError`` 分支先于
``except Exception`` 匹配，``_resolve_error_code_from_exception`` 遍历
``__cause__`` 取到 105015 后直接 ``yield data.code=105015``（裸码泄漏）。

本文件用真实 ``WorkflowRunner.run_streaming``（monkeypatch 全部模块级
依赖、只在故障注入点 ``workflow.stream`` 注入异常——不 mock 被验证的
guard/判定函数）锁定：

- 包装 105015（ExecutionError/BaseError cause）→ re-raise，不 yield 裸码；
- 直接 JiuWenBaseException(105015)（except Exception 分支）→ re-raise；
- 反证：cause 链为非 105015 业务码 → 不 re-raise，保原 yield 行为
  （error event 携带原码，不被误改）。
"""

# pylint: disable=no-self-use

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.workflow_runner import WorkflowRunner
from jiuwen.common.exception.base import JiuWenBaseException
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError, ExecutionError

_SENTINEL = "SECRET-PLUGIN-RESPONSE-NOT-LIST"


def _runner() -> WorkflowRunner:
    """绕过 __init__（run_streaming 所需实例状态由本文件逐项注入）。"""
    return WorkflowRunner.__new__(WorkflowRunner)


def _make_req():
    """最小 ExecutionRequest 替身（属性 duck-typing）。"""
    params = SimpleNamespace(
        conversation_history=[],
        is_debug=False,
        enable_memory_extract=False,
        model_dump=lambda: {},
    )
    return SimpleNamespace(
        conversation_id="conv-guard",
        ir_path="ir/path.json",
        query="你好",
        user_id="u1",
        resume_input=None,
        params=params,
    )


def _make_stream_exc(exc: BaseException):
    """构造 workflow.stream 异步生成器：直接抛注入异常（故障注入点）。"""

    async def _stream(inputs, session, context=None, stream_modes=None):
        raise exc
        yield  # pragma: no cover — 使本函数成为 async generator  # noqa: G.CTL.02

    return _stream


def _enter_patches(stack: ExitStack, stream_exc: BaseException) -> None:
    """patch run_streaming 从入口到 ``workflow.stream`` 的全部模块级依赖。

    故障注入点仅为 workflow.stream（其余依赖全为成功路径替身）——被验证的
    三分支 guard（is_plugin_response_format_error + re-raise）是真实代码。
    """
    ir_json = {"workflowId": "wf-1", "configs": {}}

    conv_cls = MagicMock()
    conv_cls.extract_node_defs = AsyncMock(return_value={})
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.async_ir_load",
              AsyncMock(return_value=ir_json)))
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.IRConverter", conv_cls))
    # _request_ctx.get() 需返回带 customer_headers/project_id 的对象
    fake_ctx = MagicMock()
    fake_ctx.customer_headers = {}
    fake_ctx.project_id = ""
    fake_cvar = MagicMock()
    fake_cvar.get.return_value = fake_ctx
    stack.enter_context(
        patch("agent_runtime.context.request_context._request_ctx", fake_cvar))
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.create_conversation_context",
              MagicMock(return_value=MagicMock())))
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.CheckpointerFactory",
              MagicMock()))
    # session：无 get_trace_id（hasattr False → 不写 TraceIdStore）
    fake_session = MagicMock(spec=[])
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.create_workflow_session_with_trace",
              MagicMock(return_value=fake_session)))
    exec_store = MagicMock()
    exec_store.save = AsyncMock()
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.ExecutionIdStore", exec_store))
    trace_store = MagicMock()
    trace_store.save = AsyncMock()
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.TraceIdStore", trace_store))
    wrapper_cls = MagicMock()
    wrapper_cls.return_value.wrap_stream_data.return_value = []
    stack.enter_context(
        patch("agent_runtime.runner.workflow_runner.WorkflowStreamDataWrapper",
              wrapper_cls))


async def _drive(stream_exc: BaseException):
    """驱动真实 run_streaming；返回 (raised_exc, yielded_events)。

    re-raise 场景 raised_exc 为传播出的异常；正常 yield 场景为 None。
    """
    runner = _runner()
    runner._is_session_interrupted = AsyncMock(return_value=False)  # noqa: G.CLS.11
    runner._is_session_cancelled = AsyncMock(return_value=False)  # noqa: G.CLS.11
    runner._clear_session_cancelled = AsyncMock()  # noqa: G.CLS.11
    runner._extract_start_user_field_defaults = MagicMock(return_value={})  # noqa: G.CLS.11
    runner._build_global_state_params = MagicMock(return_value={})  # noqa: G.CLS.11
    runner._trigger_memory_extraction = AsyncMock()  # noqa: G.CLS.11
    runner._retrieve_memory = AsyncMock(return_value=None)  # noqa: G.CLS.11
    runner._ir_converter = MagicMock(  # noqa: G.CLS.11
        async_ir_to_workflow=AsyncMock(
            return_value=MagicMock(stream=_make_stream_exc(stream_exc))))

    raised = None
    events = []
    with ExitStack() as stack:
        _enter_patches(stack, stream_exc)
        try:
            async for evt in runner.run_streaming(_make_req()):
                events.append(evt)
        except BaseException as e:  # noqa: BLE001 — 需捕获 re-raise 的传播
            raised = e
    return raised, events


def _assert_no_raw_105015(events):
    """已 yield 事件中不得出现裸 105015（决策 A：不外露）。"""
    for evt in events:
        assert "105015" not in str(evt.get("data", {}).get("code", "")), \
            f"裸 105015 被泄漏: {evt}"
        assert _SENTINEL not in str(evt), f"哨兵正文被泄漏: {evt}"


def _wrapped_105015():
    """ExecutionError(cause=JiuWenBaseException(105015))——vertex 包装形态。"""
    return ExecutionError(
        StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
        cause=JiuWenBaseException(error_code=105015, message=_SENTINEL))


class TestWrapped105015Guard:
    @pytest.mark.asyncio
    async def test_execution_error_wrapped_105015_reraised(self):
        """except ExecutionError 分支：cause 链 105015 → re-raise（不 yield 裸码）。

        修复前：_resolve_error_code_from_exception 遍历 __cause__ 取 105015
        → yield data.code=105015 裸码泄漏（审视 §1.2）。
        """
        wrapped = _wrapped_105015()
        raised, events = await _drive(wrapped)
        assert isinstance(raised, ExecutionError)
        assert raised is wrapped  # re-raise 保留原异常对象
        _assert_no_raw_105015(events)
        # 引擎异常未在 runner 层转成 error 事件（传播交由 catch 端分类）
        assert not [e for e in events if e.get("event") == "error"]

    @pytest.mark.asyncio
    async def test_base_error_wrapped_105015_reraised(self):  # noqa: G.CMT.03
        """except BaseError 分支（非 ExecutionError 的 BaseError 直接实例）：
        cause 链 105015 → 同一 guard re-raise。"""
        wrapped = BaseError(
            StatusCode.ERROR,
            cause=JiuWenBaseException(error_code=105015, message=_SENTINEL))
        raised, events = await _drive(wrapped)
        assert isinstance(raised, BaseError)
        assert raised is wrapped
        _assert_no_raw_105015(events)
        assert not [e for e in events if e.get("event") == "error"]

    @pytest.mark.asyncio
    async def test_direct_jiuwen_105015_reraised(self):  # noqa: G.CMT.03
        """except Exception 分支：直接 JiuWenBaseException(105015)（非
        BaseError）→ guard re-raise（P5-R3a 改用公共判定，行为与
        Phase 5 的 .error_code 判定等价并覆盖 cause 链）。"""
        direct = JiuWenBaseException(error_code=105015, message=_SENTINEL)
        raised, events = await _drive(direct)
        assert isinstance(raised, JiuWenBaseException)
        assert raised is direct
        _assert_no_raw_105015(events)
        assert not [e for e in events if e.get("event") == "error"]


class TestNon105015KeepsBehavior:
    """反证：非 105015 业务码不被 guard 误改（保既有 yield 行为）。"""

    @pytest.mark.asyncio
    async def test_execution_error_wrapped_non_105015_yields_original_code(self):  # noqa: G.CMT.03
        """ExecutionError(cause=105001) → 不 re-raise，error event 携带
        原码 105001（_resolve cause 链提取，保基线行为）+ done 终态。"""
        wrapped = ExecutionError(
            StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
            cause=JiuWenBaseException(error_code=105001, message="biz err"))
        raised, events = await _drive(wrapped)
        assert raised is None, "非 105015 不得 re-raise"
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 1
        assert error_events[0]["data"]["code"] == 105001  # 原码透传，未被误改
        done_events = [e for e in events if e.get("event") == "done"]
        assert len(done_events) == 1  # 基线 error→done 终态保留

    @pytest.mark.asyncio
    async def test_direct_jiuwen_non_105015_yields_original_code(self):  # noqa: G.CMT.03
        """except Exception 分支反证：直接 JiuWenBaseException(105001) →
        不 re-raise，yield error event 原码（str 形态，基线行为）。"""
        direct = JiuWenBaseException(error_code=105001, message="biz err")
        raised, events = await _drive(direct)
        assert raised is None
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 1
        assert str(error_events[0]["data"]["code"]) == "105001"


# ---------------------------------------------------------------------------
# run_debug_streaming（组件调试入口）：:883 except Exception guard
# ---------------------------------------------------------------------------

def _make_debug_req():
    """最小 ComponentDebugRequest 替身。"""
    params = SimpleNamespace()
    return SimpleNamespace(
        conversation_id="conv-debug",
        ir_path="ir/debug.json",
        user_id="u1",
        inputs={"query": "你好"},
    )


async def _drive_debug(stream_exc: BaseException):
    """驱动真实 run_debug_streaming；返回 (raised, events)。

    故障注入点：SingleComponentDebugWrapper.astream 直接抛注入异常
    （组件调试绕过 workflow 引擎，异常形态为直接 JiuWenBaseException）。
    """
    runner = _runner()
    ir_json = {"workflowId": "wf-d", "configs": {}}

    conv_cls = MagicMock()
    conv_cls.extract_node_defs = AsyncMock(return_value={})
    conv_cls.create_single_component = AsyncMock(
        return_value=MagicMock(node_name="n", node_type="t"))
    fake_ctx = MagicMock()
    fake_ctx.customer_headers = {}
    fake_ctx.project_id = ""
    fake_cvar = MagicMock()
    fake_cvar.get.return_value = fake_ctx

    # 故障注入：wrapper.astream 抛注入异常（签名 inputs=/execution_id=）
    async def _astream(*, inputs, execution_id):
        raise stream_exc
        yield  # pragma: no cover — async generator  # noqa: G.CTL.02
    wrapper_instance = MagicMock()
    wrapper_instance.astream = _astream
    wrapper_cls = MagicMock(return_value=wrapper_instance)
    formatter_instance = MagicMock()
    formatter_instance.format.return_value = []
    formatter_instance.finalize.return_value = []
    formatter_cls = MagicMock(return_value=formatter_instance)

    raised = None
    events = []
    with ExitStack() as stack:
        stack.enter_context(
            patch("agent_runtime.runner.workflow_runner.async_ir_load",
                  AsyncMock(return_value=ir_json)))
        stack.enter_context(
            patch("agent_runtime.runner.workflow_runner.IRConverter", conv_cls))
        stack.enter_context(
            patch("agent_runtime.context.request_context._request_ctx", fake_cvar))
        # SingleComponentDebugWrapper / DebugStreamFormatter 在 run_debug_streaming
        # 函数内 import（模块级无此属性）→ patch 源模块，函数内 import 拿到 patched
        stack.enter_context(
            patch("jiuwen.extension.wrapper.single_component_debug_wrapper."
                  "SingleComponentDebugWrapper", wrapper_cls))
        stack.enter_context(
            patch("agent_runtime.runner.debug_formatter.DebugStreamFormatter",
                  formatter_cls))
        try:
            async for evt in runner.run_debug_streaming(
                    _make_debug_req(), "comp-1", "exec-d"):
                events.append(evt)
        except BaseException as e:  # noqa: BLE001
            raised = e
    return raised, events


class TestDebugStream105015Guard:
    @pytest.mark.asyncio
    async def test_debug_direct_105015_reraised(self):
        """run_debug_streaming :883 except Exception：组件调试期直接
        JiuWenBaseException(105015) → guard re-raise（不 yield 裸码）。

        组件调试绕过 workflow 引擎（SingleComponentDebugWrapper 直调
        component.on_invoke），异常不经 vertex 包装，为直接形态——
        :883 原无 guard 会 _resolve→105015→yield 裸码。
        """
        direct = JiuWenBaseException(error_code=105015, message=_SENTINEL)
        raised, events = await _drive_debug(direct)
        assert isinstance(raised, JiuWenBaseException)
        assert raised is direct
        _assert_no_raw_105015(events)
        assert not [e for e in events if e.get("event") == "error"]

    @pytest.mark.asyncio
    async def test_debug_non_105015_keeps_error_event(self):  # noqa: G.CMT.03
        """反证：组件调试期 105001 → 不 re-raise，yield error event 原码
        （保基线调试错误回显行为）。"""
        direct = JiuWenBaseException(error_code=105001, message="biz err")
        raised, events = await _drive_debug(direct)
        assert raised is None
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 1
        assert str(error_events[0]["data"]["code"]) == "105001"
