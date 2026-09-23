"""COM-08 §6/§8: LOG_VERBOSE 双配置不变性 + 敏感哨兵 + 双路径排除证据。

覆盖：
- §6.3 SSE 矩阵：_handle_error_response (#1) 与 _process_streaming_output (#2)
  两种 LOG_VERBOSE 配置 wire 精确一致；不含 "test error message"；不含敏感哨兵。
- §4.7C async_execution #6/#7：e.message / item.data.message 不进公开文案。
- §4.7C WorkflowAbortException :729+:843 双路径排除证据（canonical message + data 分离）。
- §6.5 静态治理：error_contract 零开关读取；生产无 "test error message"；无 LOG_VERBOSE 用法。
"""

from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace


from jiuwen.common.exception.base import JiuWenBaseException, WorkflowAbortException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.diagnostics import DiagnosticPolicy, set_default_policy
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.flow.workflow import Workflow
from jiuwen.serve.controllers.async_execution import utils as async_exec_utils
from jiuwen.serve.controllers.execution import utils as exec_utils


_SENTINEL = "SECRET-TOKEN-abc-123-sensitivedetail"
_CREATEDTIME_RE = re.compile(r'"createdTime":\d+')


# ---------------- §6.3 #1: _handle_error_response 双配置不变 ----------------


def _make_jiuwen_exc(message: str = "boom", error_code: str = "120001") -> JiuWenBaseException:
    return JiuWenBaseException(error_code=error_code, message=message)


def _handle_error_bytes(item) -> bytes:
    return asyncio.run(exec_utils._handle_error_response(item))  # noqa: G.CLS.11


def _wire_json(wire: bytes) -> dict:
    """从 SSE wire 提取 JSON 并排除非确定字段（createdTime）。"""
    text = wire.decode("utf-8")
    payload = text.strip().removeprefix("data:").strip()
    obj = json.loads(payload)
    obj.pop("createdTime", None)
    if isinstance(obj.get("data"), dict):
        obj["data"].pop("createdTime", None)
    return obj


def _wire_list_json(wires: list[bytes]) -> list[dict]:
    """从多条 SSE wire 提取 JSON 列表，排除非确定字段。"""
    out = []
    for w in wires:
        text = w.decode("utf-8")
        for chunk in text.split("\n\n"):
            chunk = chunk.strip()
            if not chunk.startswith("data:"):
                continue
            obj = json.loads(chunk.removeprefix("data:").strip())
            obj.pop("createdTime", None)
            if isinstance(obj.get("data"), dict):
                obj["data"].pop("createdTime", None)
            out.append(obj)
    return out


def test_handle_error_response_two_configs_identical(monkeypatch):
    item = _make_jiuwen_exc(message=_SENTINEL)
    monkeypatch.setenv("LOG_VERBOSE", "false")
    wire_false = _handle_error_bytes(item)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    wire_true = _handle_error_bytes(item)
    assert _wire_json(wire_false) == _wire_json(wire_true)


def test_handle_error_response_no_test_error_message():
    wire = _handle_error_bytes(_make_jiuwen_exc())
    assert b"test error message" not in wire


def test_handle_error_response_no_sensitive_sentinel():
    """item.message 含敏感哨兵，wire 不得包含。"""
    wire = _handle_error_bytes(_make_jiuwen_exc(message=_SENTINEL))
    assert _SENTINEL.encode() not in wire
    assert b"SECRET-TOKEN" not in wire


def test_handle_error_response_contains_code_and_safe_message():
    wire = _handle_error_bytes(_make_jiuwen_exc(error_code="120001"))
    assert b"120001" in wire
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in wire  # noqa: G.CLS.11


def test_handle_error_response_logger_no_raw_message(caplog):
    """§4.7B: logger.error 不再以 item.message 作为日志 message；exc_info 保留。

    traceback（exc_info）含 str(exception) 是 Python 本质且 §3.2 允许——
    生产中 §4.5 已保证异常 message 安全（非 str(e)）；本断言只校验日志
    message 本身是固定基础事件，不再无条件写未治理原文。
    """
    import logging

    caplog.set_level(logging.ERROR)
    set_default_policy(DiagnosticPolicy(verbose=False))
    try:
        item = _make_jiuwen_exc(message=_SENTINEL)
        _handle_error_bytes(item)
    finally:
        set_default_policy(None)
    rec = caplog.records[-1]
    # 日志 message 是固定基础事件，不含 item.message 哨兵
    assert rec.getMessage() == "workflow execution failed"
    assert _SENTINEL not in rec.getMessage()
    # exc_info 保留（traceback 两种配置都到达底层 logger）
    assert rec.exc_info is not None


def test_handle_error_response_logger_verbose_adds_allowlist_field(caplog):
    import logging

    caplog.set_level(logging.ERROR)
    set_default_policy(DiagnosticPolicy(verbose=True))
    try:
        _handle_error_bytes(_make_jiuwen_exc(error_code="120007"))
    finally:
        set_default_policy(None)
    rec = caplog.records[-1]
    assert "120007" in rec.getMessage()  # error_code 进 allowlist 字段
    assert _SENTINEL not in rec.getMessage()


# ---------------- §6.3 #2: _process_streaming_output ERROR 双配置不变 -------


def _make_error_item(message: str = _SENTINEL, code: str = "120002") -> SimpleNamespace:
    return SimpleNamespace(
        code=StreamCode.ERROR.value,
        data={"code": code, "message": message},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )


def _drive_process_streaming_output(item) -> list[bytes]:
    async def origin():
        yield item

    async def collect():
        out = []
        async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # noqa: G.CLS.11
            out.append(chunk)
        return out

    return asyncio.run(collect())


def test_process_streaming_output_two_configs_identical(monkeypatch):
    monkeypatch.setenv("LOG_VERBOSE", "false")
    wire_false = _drive_process_streaming_output(_make_error_item())
    monkeypatch.setenv("LOG_VERBOSE", "true")
    wire_true = _drive_process_streaming_output(_make_error_item())
    assert _wire_list_json(wire_false) == _wire_list_json(wire_true)


def test_process_streaming_output_no_test_error_message():
    wire = _drive_process_streaming_output(_make_error_item())
    joined = b"".join(wire)
    assert b"test error message" not in joined


def test_process_streaming_output_no_sensitive_sentinel():
    wire = _drive_process_streaming_output(_make_error_item(message=_SENTINEL))
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined
    assert b"SECRET-TOKEN" not in joined


def test_process_streaming_output_contains_code_and_safe_message():
    wire = _drive_process_streaming_output(_make_error_item(code="120002"))
    joined = b"".join(wire)
    assert b"120002" in joined
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # noqa: G.CLS.11


# ---------------- §4.7C #6/#7: async_execution 不透传 e.message ------------


# ---------------- §4.7C #3/#4/#5/#6: 真实生产函数驱动 + 哨兵反例 --------


async def _async_noop(*a, **kw):
    return None


def _noop(*a, **kw):
    return None


class _CaptureERM:
    """替身 ExecutionResultManager：捕获 append_message 的 StreamingChatResponse。"""

    def __init__(self):
        self.captured = []

    def append_message(self, key, value):
        self.captured.append((key, value))

    def get_messages(self, key):
        return [v for k, v in self.captured if k == key]


class _FakeAESM:
    def set_state_status(self, conv, status):
        pass

    def get_state_parsed(self, conv):  # noqa: G.CLS.07
        return SimpleNamespace(status=None)


class _FakeAEASM:
    async def set_state_structure(self, conv, state):
        pass


def _drive_format_component_output(item, monkeypatch):
    """真实调用 #3 _format_component_output。"""
    monkeypatch.setattr(exec_utils, "async_update_state_of_workflow", _async_noop)

    async def origin():
        yield item

    stub_wf = SimpleNamespace(async_clean_up=_async_noop)
    exec_data = SimpleNamespace(instance=stub_wf)

    async def collect():
        out = []
        async for chunk in exec_utils._format_component_output(  # noqa: G.CLS.11
            "conv-1", origin(), exec_data, stub_wf
        ):
            out.append(chunk)
        return out

    return asyncio.run(collect())


def _drive_post_process_workflow_streaming_output(item, monkeypatch):
    """真实调用 #4 post_process_workflow_streaming_output。"""
    monkeypatch.setattr(exec_utils, "async_update_state_of_workflow", _async_noop)
    monkeypatch.setattr(
        exec_utils, "wf_performance_buffer",
        SimpleNamespace(info=_noop, record=_noop),
    )

    async def origin():
        yield item

    stub_wf = SimpleNamespace(
        workflow_id="wf-1",
        graph_engine=SimpleNamespace(
            graph_instance=SimpleNamespace(async_clean_up=_async_noop)
        ),
    )

    async def collect():
        out = []
        async for chunk in exec_utils.post_process_workflow_streaming_output(
            "conv-1", origin(), stub_wf
        ):
            out.append(chunk)
        return out

    return asyncio.run(collect())


def _drive_post_process_async(item, monkeypatch):
    """真实调用 #5 post_process_workflow_streaming_output_async，捕获持久化结果。"""
    from jiuwen.orchestration.flow.enum import ExecutionStatus

    fake_erm = _CaptureERM()
    monkeypatch.setattr(exec_utils, "ExecutionResultManager", lambda: fake_erm)
    monkeypatch.setattr(exec_utils, "AsyncExecAsyncStateManager", _FakeAEASM)
    monkeypatch.setattr(exec_utils, "async_update_state_of_workflow", _async_noop)
    monkeypatch.setattr(
        exec_utils, "_get_conv_status_by_exec_status",
        lambda status: async_exec_utils.AsyncExecutionStatus.FAILED,
    )
    stub_wf = SimpleNamespace(
        get_workflow_execute_status=lambda: ExecutionStatus.END,
        clean_up=_async_noop,
    )
    asyncio.run(
        exec_utils.post_process_workflow_streaming_output_async(
            "conv-1", [item], stub_wf
        )
    )
    return fake_erm.captured


def _drive_async_exec_post_process_7(item, monkeypatch):
    """真实调用 #7 async_execution/utils.py::post_process_workflow_streaming_output_async。"""
    from jiuwen.orchestration.flow.enum import ExecutionStatus

    fake_erm = _CaptureERM()
    monkeypatch.setattr(async_exec_utils, "ExecutionResultManager", lambda: fake_erm)
    monkeypatch.setattr(async_exec_utils, "AsyncExecStateManager", _FakeAESM)
    monkeypatch.setattr(async_exec_utils, "update_state_of_workflow", _noop)
    monkeypatch.setattr(
        async_exec_utils, "_get_conv_status_by_exec_status",
        lambda *a, **kw: async_exec_utils.AsyncExecutionStatus.FAILED,
    )
    stub_wf = SimpleNamespace(
        get_workflow_execute_status=lambda: ExecutionStatus.END,
        clean_up=_noop,
    )
    async_exec_utils.post_process_workflow_streaming_output_async(
        "conv-1", [item], stub_wf
    )
    return fake_erm.captured


def _drive_handle_init_exceptions(monkeypatch):
    """真实调用 #6 handle_init_exceptions，捕获 append_message。"""
    fake_erm = _CaptureERM()
    monkeypatch.setattr(async_exec_utils, "ExecutionResultManager", lambda: fake_erm)
    monkeypatch.setattr(async_exec_utils, "AsyncExecStateManager", _FakeAESM)
    exc = _make_jiuwen_exc(message=_SENTINEL)
    async_exec_utils.handle_init_exceptions(exc, "exec-1", "conv-1")
    return fake_erm.captured


# #3 _format_component_output
def test_format_component_output_no_sensitive_sentinel(monkeypatch):
    wire = _drive_format_component_output(_make_error_item(), monkeypatch)
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined
    assert b"SECRET-TOKEN" not in joined
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # noqa: G.CLS.11


def test_format_component_output_two_configs_identical(monkeypatch):
    monkeypatch.setenv("LOG_VERBOSE", "false")
    w_false = _drive_format_component_output(_make_error_item(), monkeypatch)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    w_true = _drive_format_component_output(_make_error_item(), monkeypatch)
    assert _wire_list_json(w_false) == _wire_list_json(w_true)


# #4 post_process_workflow_streaming_output
def test_post_process_workflow_streaming_output_no_sentinel(monkeypatch):
    wire = _drive_post_process_workflow_streaming_output(_make_error_item(), monkeypatch)
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # noqa: G.CLS.11


def test_post_process_workflow_streaming_output_two_configs_identical(monkeypatch):
    monkeypatch.setenv("LOG_VERBOSE", "false")
    w_false = _drive_post_process_workflow_streaming_output(_make_error_item(), monkeypatch)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    w_true = _drive_post_process_workflow_streaming_output(_make_error_item(), monkeypatch)
    assert _wire_list_json(w_false) == _wire_list_json(w_true)


# #5 post_process_workflow_streaming_output_async（持久化结果）
def test_post_process_async_persisted_message_no_sentinel(monkeypatch):
    captured = _drive_post_process_async(_make_error_item(), monkeypatch)
    blob = "\n".join(v.model_dump_json(by_alias=True, exclude_none=True)
                     for _, v in captured if hasattr(v, "model_dump_json"))
    assert _SENTINEL not in blob
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE in blob  # noqa: G.CLS.11


def test_post_process_async_two_configs_identical(monkeypatch):
    """§4.7C/§6.3/§8: #5 持久化结果 false/true 精确一致（排除 createdTime）。"""
    monkeypatch.setenv("LOG_VERBOSE", "false")
    c_false = _drive_post_process_async(_make_error_item(), monkeypatch)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    c_true = _drive_post_process_async(_make_error_item(), monkeypatch)

    def _blob(captured):
        return "\n".join(
            v.model_dump_json(by_alias=True, exclude_none=True)
            for _, v in captured if hasattr(v, "model_dump_json")
        )

    assert _CREATEDTIME_RE.sub("x", _blob(c_false)) == _CREATEDTIME_RE.sub("x", _blob(c_true))


# #6 handle_init_exceptions（真实调用，非手工构造）
def test_handle_init_exceptions_no_sensitive_in_persisted(monkeypatch):
    captured = _drive_handle_init_exceptions(monkeypatch)
    blob = "\n".join(
        v.model_dump_json(by_alias=True, exclude_none=True)
        for _, v in captured if hasattr(v, "model_dump_json")
    )
    assert _SENTINEL not in blob
    assert async_exec_utils._SAFE_PUBLIC_ERROR_MESSAGE in blob  # noqa: G.CLS.11


def test_handle_init_exceptions_two_configs_identical(monkeypatch):
    """§4.7C/§6.3/§8: #6 持久化结果 false/true 精确一致（排除 createdTime）。"""
    monkeypatch.setenv("LOG_VERBOSE", "false")
    c_false = _drive_handle_init_exceptions(monkeypatch)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    c_true = _drive_handle_init_exceptions(monkeypatch)

    def _blob(captured):
        return "\n".join(
            v.model_dump_json(by_alias=True, exclude_none=True)
            for _, v in captured if hasattr(v, "model_dump_json")
        )

    assert _CREATEDTIME_RE.sub("x", _blob(c_false)) == _CREATEDTIME_RE.sub("x", _blob(c_true))


# #7 async_execution/utils.py::post_process_workflow_streaming_output_async
def test_async_exec_post_process_7_no_sentinel(monkeypatch):
    captured = _drive_async_exec_post_process_7(_make_error_item(), monkeypatch)
    blob = "\n".join(
        v.model_dump_json(by_alias=True, exclude_none=True)
        for _, v in captured if hasattr(v, "model_dump_json")
    )
    assert _SENTINEL not in blob
    assert async_exec_utils._SAFE_PUBLIC_ERROR_MESSAGE in blob  # noqa: G.CLS.11


def test_async_exec_post_process_7_two_configs_identical(monkeypatch):
    monkeypatch.setenv("LOG_VERBOSE", "false")
    c_false = _drive_async_exec_post_process_7(_make_error_item(), monkeypatch)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    c_true = _drive_async_exec_post_process_7(_make_error_item(), monkeypatch)

    def _blob(captured):
        return "\n".join(
            v.model_dump_json(by_alias=True, exclude_none=True)
            for _, v in captured if hasattr(v, "model_dump_json")
        )

    def _norm(s):
        return _CREATEDTIME_RE.sub('"createdTime":0', s)

    assert _norm(_blob(c_false)) == _norm(_blob(c_true))


def test_async_execution_safe_message_constant_no_sentinel():
    assert _SENTINEL not in async_exec_utils._SAFE_PUBLIC_ERROR_MESSAGE  # noqa: G.CLS.11


# ---------------- §4.7C: WorkflowAbortException :729+:843 双路径排除证据 ---


def _abort_exception(user_data: dict | None = None) -> WorkflowAbortException:
    return WorkflowAbortException(data=user_data or {"user_field": "user-value"})


def test_workflow_abort_message_is_canonical_not_user_defined():
    """§4.7C: WorkflowAbortException.message 固定 canonical，非用户自定义。"""
    exc = _abort_exception()
    assert exc.message == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg
    assert exc.error_code == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code
    assert "user-value" not in exc.message  # 用户数据不在 message


def test_workflow_abort_data_separated_from_message():
    exc = _abort_exception({"user_field": "user-value"})
    assert exc.data == {"user_field": "user-value"}
    assert exc.message == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg


def _arun_stub(abort_exc):
    """构造 stub self 用于真实 Workflow._arun——_achat 抛 WorkflowAbortException。"""
    async def _update_runtime_context(params, query):
        return None

    async def _achat(**kwargs):
        raise abort_exc

    return SimpleNamespace(
        _update_runtime_context=_update_runtime_context,
        _achat=_achat,
        parent_workflow_id=None,
    )


def _get_output_stub(abort_exc):
    """构造 stub self 用于真实 Workflow._get_output——chat_manager.get_out 返回 WorkflowAbortException。"""
    async def get_out():
        return abort_exc

    chat_manager = SimpleNamespace(get_out=get_out)

    def extend_error_template(tmpl):
        return tmpl

    return SimpleNamespace(chat_manager=chat_manager, extend_error_template=extend_error_template)


def test_arun_except_workflow_abort_real_path():
    """§4.7C: 真实经过 Workflow._arun() 的 :729 except 分支。"""
    exc = _abort_exception({"user_field": "user-value"})
    stub = _arun_stub(exc)
    result = asyncio.run(Workflow._arun(stub, "query", False, {}))  # noqa: G.CLS.11
    assert result["code"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code
    assert result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg
    assert result["user_field"] == "user-value"
    assert "user-value" not in result["message"]


def test_get_output_isinstance_workflow_abort_real_path():
    """§4.7C: 真实经过 Workflow._get_output() 的 :843 isinstance 分支。"""
    exc = _abort_exception({"user_field": "user-value"})
    stub = _get_output_stub(exc)
    result = asyncio.run(Workflow._get_output(stub))  # noqa: G.CLS.11
    assert result["code"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code
    assert result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg
    assert result["user_field"] == "user-value"
    assert "user-value" not in result["message"]


def test_abort_two_real_paths_identical_and_safe():
    exc = _abort_exception({"user_field": "user-value"})
    arun_result = asyncio.run(Workflow._arun(_arun_stub(exc), "q", False, {}))  # noqa: G.CLS.11
    getout_result = asyncio.run(Workflow._get_output(_get_output_stub(exc)))  # noqa: G.CLS.11
    assert arun_result == getout_result
    assert arun_result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg


def test_abort_two_real_paths_no_log_verbose_dependency(monkeypatch):
    """§4.7C §6.3 §8: 四格双配置矩阵——_arun 与 _get_output 分别在 false/true 下精确一致。"""
    monkeypatch.setenv("LOG_VERBOSE", "false")
    exc_f = _abort_exception({"user_field": "v"})
    arun_false = asyncio.run(Workflow._arun(_arun_stub(exc_f), "q", False, {}))  # noqa: G.CLS.11
    getout_false = asyncio.run(Workflow._get_output(_get_output_stub(exc_f)))  # noqa: G.CLS.11
    monkeypatch.setenv("LOG_VERBOSE", "true")
    exc_t = _abort_exception({"user_field": "v"})
    arun_true = asyncio.run(Workflow._arun(_arun_stub(exc_t), "q", False, {}))  # noqa: G.CLS.11
    getout_true = asyncio.run(Workflow._get_output(_get_output_stub(exc_t)))  # noqa: G.CLS.11
    # 四格矩阵
    assert arun_false == arun_true          # _arun(false) == _arun(true)
    assert getout_false == getout_true      # _get_output(false) == _get_output(true)
    assert arun_false == getout_false       # _arun(false) == _get_output(false)
    assert arun_true == getout_true         # _arun(true) == _get_output(true)
    assert arun_false["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg


def test_abort_message_not_user_custom_text():
    """排除项证据：message 是 canonical，不是用户塞入的文案。"""
    exc = _abort_exception({"custom_msg": "attacker-controlled text"})
    assert exc.message != "attacker-controlled text"
    assert "attacker-controlled text" not in exc.message


# ---------------- §4.7C #8/#9: 上游生产点→下游消费者真实链路 ------------


def test_8_task_done_callback_wraps_non_jiuwen_with_canonical(monkeypatch):  # noqa: G.CMT.03
    """#8 _task_done_callback：非 JiuWenBaseException task 异常（含哨兵 str）被包装为
    固定 canonical WORKFLOW_EXECUTE_ERROR，哨兵不进包装后的 message。"""
    from jiuwen.common.exception.status_code import StatusCode as SC

    sentinel_exc = RuntimeError(f"task boom {_SENTINEL}")

    class _TaskStub:
        def __init__(self, exc):
            self._exc = exc

        def exception(self):
            return self._exc

    task = _TaskStub(sentinel_exc)
    captured: dict = {}

    async def put_out(exc):
        captured["exc"] = exc

    chat_manager = SimpleNamespace(
        get_loop=lambda: asyncio.get_running_loop(),
        tasks=set(),
        put_out=put_out,
        set_finish=lambda v: None,
    )
    stub = SimpleNamespace(
        _cur_tasks={task},
        chat_manager=chat_manager,
        extend_error_template=lambda tmpl: tmpl,
    )

    async def _run():
        Workflow._task_done_callback(stub, task)  # noqa: G.CLS.11
        await asyncio.gather(*chat_manager.tasks)
        return captured.get("exc")

    wrapped = asyncio.run(_run())
    assert isinstance(wrapped, JiuWenBaseException)
    assert wrapped.error_code == SC.WORKFLOW_EXECUTE_ERROR.code
    # 包装后 message 是 UNSAFE 模板填 canonical errmsg（不含 task 异常 str）
    assert _SENTINEL not in wrapped.message
    assert "task boom" not in wrapped.message
    assert SC.WORKFLOW_EXECUTE_ERROR.errmsg in wrapped.message


def test_9_get_output_jiuwen_branch_chain_to_downstream_no_sentinel(monkeypatch):  # noqa: G.CMT.03
    """#9 _get_output JiuWenBaseException 分支产出（含上游哨兵 message）→ 送入下游 #2
    _process_streaming_output → 最终 wire 不含哨兵、含 _SAFE。"""
    upstream_exc = JiuWenBaseException(error_code="120099", message=_SENTINEL)
    stub = _get_output_stub(upstream_exc)
    # 真实 #9：_get_output 的 JiuWenBaseException 分支（:855）
    produced = asyncio.run(Workflow._get_output(stub))  # noqa: G.CLS.11
    assert produced["code"] == "120099"
    # #9 的 message 含上游哨兵（#9 本身透传 output.message）——证明需要下游兜底
    assert _SENTINEL in produced["message"]
    # 送入下游 #2 _process_streaming_output
    downstream_item = SimpleNamespace(
        code=StreamCode.ERROR.value,
        data={"code": produced["code"], "message": produced["message"]},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )
    wire = _drive_process_streaming_output(downstream_item)
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined  # 下游 #2 用 _SAFE 兜底
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # noqa: G.CLS.11


def test_8_9_chain_two_configs_identical(monkeypatch):
    """#8/#9 上游生产 false/true 下产出一致（不读 LOG_VERBOSE）。"""
    monkeypatch.setenv("LOG_VERBOSE", "false")
    exc = JiuWenBaseException(error_code="120099", message="stable upstream")
    produced_false = asyncio.run(Workflow._get_output(_get_output_stub(exc)))  # noqa: G.CLS.11
    monkeypatch.setenv("LOG_VERBOSE", "true")
    produced_true = asyncio.run(Workflow._get_output(_get_output_stub(exc)))  # noqa: G.CLS.11
    assert produced_false == produced_true


# ---------------- §6.5 静态治理 ----------------


def test_error_contract_zero_log_verbose_read():
    """§6.5: error_contract 模块不读取 LOG_VERBOSE。"""
    import subprocess

    root = "agent_runtime/error_contract"
    r = subprocess.run(  # noqa: G.EDV.05
        ["grep", "-rn", "LOG_VERBOSE", root],
        capture_output=True, text=True,
    )
    assert r.stdout == "", f"error_contract 读取了 LOG_VERBOSE:\n{r.stdout}"


def test_no_test_error_message_in_production():
    """§6.5: 生产代码不再包含面向响应的 'test error message'。"""
    import subprocess

    r = subprocess.run(  # noqa: G.EDV.05
        ["grep", "-rn", "test error message", "jiuwen"],
        capture_output=True, text=True,
    )
    # 仅允许出现在注释中（grep -n 输出格式 file:line:content，取 content 判断）
    for line in r.stdout.splitlines():
        parts = line.split(":", 2)
        content = parts[2] if len(parts) >= 3 else line
        assert content.lstrip().startswith("#"), (
            f"生产代码残留 'test error message': {line}"
        )


def test_no_log_verbose_mode_usage_in_production():
    """§6.5: 生产代码不再有 LOG_VERBOSE_MODE 用法（仅 diagnostics 读 env）。"""
    import subprocess

    r = subprocess.run(  # noqa: G.EDV.05
        ["grep", "-rn", "LOG_VERBOSE_MODE", "jiuwen"],
        capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        parts = line.split(":", 2)
        content = parts[2] if len(parts) >= 3 else line
        assert content.lstrip().startswith("#"), (
            f"生产代码残留 LOG_VERBOSE_MODE: {line}"
        )


def test_only_diagnostics_reads_log_verbose_env():
    """§6.5: 生产代码仅 diagnostics.py 调用 os.getenv('LOG_VERBOSE')。"""
    import subprocess

    r = subprocess.run(  # noqa: G.EDV.05
        ["grep", "-rn", 'getenv("LOG_VERBOSE"', "jiuwen"],
        capture_output=True, text=True,
    )
    hits = [line for line in r.stdout.splitlines() if line]
    # 仅 diagnostics.py 应出现
    for line in hits:
        assert "common/log/diagnostics.py" in line, f"非法 LOG_VERBOSE 读取点: {line}"


# ---------------- §5.3 取消/断连与正常结束 ----------------


def _drive_normal_end_item(item):
    async def origin():
        yield item

    async def collect():
        out = []
        async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # noqa: G.CLS.11
            out.append(chunk)
        return out

    return asyncio.run(collect())


def _events_of(wire):
    return [obj.get("event") for obj in _wire_list_json(wire)]


def test_normal_end_no_error_frame_two_configs(monkeypatch, caplog):  # noqa: G.CMT.03
    """§4.8/§6.3: 正常结束（FINISH）经 #2 精确产生 start+唯一 done 终态，
    无 error/额外 END；两配置 wire 一致；无 ERROR 日志。"""
    import logging

    caplog.set_level(logging.ERROR)
    finish_item = SimpleNamespace(
        code=StreamCode.FINISH.value,
        data={"content": "done"},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )
    monkeypatch.setenv("LOG_VERBOSE", "false")
    w_false = _drive_normal_end_item(finish_item)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    w_true = _drive_normal_end_item(finish_item)
    for wire in (w_false, w_true):
        # 精确终态：start + 唯一 done，无 error
        assert _events_of(wire) == ["start", "done"], _events_of(wire)
        assert b'"event":"error"' not in b"".join(wire)
        # 关联 executionId 保持
        assert b'"executionId":"exec-1"' in b"".join(wire)
    assert _wire_list_json(w_false) == _wire_list_json(w_true)
    # 正常结束不产生 ERROR 日志
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_message_end_no_error_frame_two_configs(monkeypatch, caplog):  # noqa: G.CMT.03
    """§4.8/§6.3: MESSAGE_END 经 #2 精确产生 start+唯一 message_end 终态，
    无 error；两配置一致；无 ERROR 日志。"""
    import logging

    caplog.set_level(logging.ERROR)
    end_item = SimpleNamespace(
        code=StreamCode.MESSAGE_END.value,
        data={},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )
    monkeypatch.setenv("LOG_VERBOSE", "false")
    w_false = _drive_normal_end_item(end_item)
    monkeypatch.setenv("LOG_VERBOSE", "true")
    w_true = _drive_normal_end_item(end_item)
    for wire in (w_false, w_true):
        assert _events_of(wire) == ["start", "message_end"], _events_of(wire)
        assert b'"event":"error"' not in b"".join(wire)
        assert b'"executionId":"exec-1"' in b"".join(wire)
    assert _wire_list_json(w_false) == _wire_list_json(w_true)
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_cancel_propagates_no_synthetic_error_two_configs(monkeypatch, caplog):  # noqa: G.CMT.03
    """§4.8/§6.3: 取消（CancelledError）经 #2：
    - CancelledError 传播（不被吞成 error 帧）；
    - 已产生的 wire 不含 error、无 done/END（取消后无终态帧）；
    - 两配置已产生的 wire 精确一致；
    - 两配置均无新增 ERROR 日志。
    取消资源清理属 ASGI 层 COM-07A；本测试证 COM-08 不在取消路径发伪 error。"""
    import logging

    caplog.set_level(logging.ERROR)

    async def origin():
        yield SimpleNamespace(
            code=StreamCode.PARTIAL_CONTENT.value,
            data={"content": "partial"},
            index=0,
            execution_id="exec-1",
            is_struct_message=False,
        )
        raise asyncio.CancelledError()

    def _run():
        holder = []

        async def collect():
            async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # noqa: G.CLS.11
                holder.append(chunk)

        try:
            asyncio.run(collect())
            return holder, False
        except asyncio.CancelledError:
            return holder, True

    for verbose in (False, True):
        set_default_policy(DiagnosticPolicy(verbose=verbose))
        try:
            caplog.clear()
            wire, raised = _run()
            assert raised, f"verbose={verbose}: CancelledError 应被传播"
            joined = b"".join(wire)
            # 已产生 wire：含 start 与 partial message，无 error、无 done/message_end
            assert b'"event":"error"' not in joined
            assert b'"event":"done"' not in joined
            assert b'"event":"message_end"' not in joined
            assert b'"event":"start"' in joined
            # 无 ERROR 日志
            assert not [r for r in caplog.records if r.levelno >= logging.ERROR], (
                f"verbose={verbose}: 取消不应产生 ERROR"
            )
            if verbose is False:
                wire_false = wire
            else:
                assert _wire_list_json(wire_false) == _wire_list_json(wire)
        finally:
            set_default_policy(None)
