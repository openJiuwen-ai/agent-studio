"""COM-08 §4.7/§6: SSE 错误出口与安全文案（敏感哨兵 + 双路径排除证据）。

覆盖：
- §6.3 SSE 矩阵：_handle_error_response (#1) 与 _process_streaming_output (#2)
  wire 不含 "test error message"、不含敏感哨兵，含稳定错误码与安全文案。
- §4.7C async_execution #6/#7：e.message / item.data.message 不进公开文案。
- §4.7C WorkflowAbortException 双路径排除证据（canonical message + data 分离）。
- §6.5 静态治理：生产无 "test error message"。

注：LOG_VERBOSE 已于日志归一化中删除（唯一消费点在新架构下无调用方），
相关“双配置一致”用例随之移除；错误文案与日志行为不再存在开关维度。
"""

from __future__ import annotations

import asyncio
import json
import re
from types import SimpleNamespace
from pathlib import Path


from jiuwen.common.exception.base import JiuWenBaseException, WorkflowAbortException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.flow.workflow import Workflow
from jiuwen.serve.controllers.execution import utils as exec_utils


_RUNTIME_ROOT = Path(__file__).resolve().parents[3]

_BINARY_EXTS = {".pyc", ".so", ".dll", ".png", ".jpg", ".jpeg", ".gif",
                ".pdf", ".zip", ".gz", ".tar", ".class", ".jar", ".lock"}


class _GrepResult:
    """Mimics subprocess.CompletedProcess[str] for grep-like search results."""

    def __init__(self, stdout: str = "", returncode: int = 1, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _run_grep(*args: str) -> _GrepResult:
    """Python-native grep replacement using pathlib + re.

    Supports the argument patterns used by the governance tests:
    -rn <pattern> <path>  (recursive search with line numbers)
    -r <pattern> <path>
    """
    flags: set[str] = set()
    pattern: str | None = None
    path: str | None = None
    for arg in args:
        if arg.startswith("-"):
            flags.update(c for c in arg[1:])
        elif pattern is None:
            pattern = arg
        else:
            path = arg

    if pattern is None:
        return _GrepResult(returncode=1)

    search_path = _RUNTIME_ROOT / (path or ".")
    if not search_path.exists():
        return _GrepResult(returncode=1)

    files: list[Path] = []
    if search_path.is_file():
        files = [search_path]
    else:
        files = sorted(
            f for f in search_path.rglob("*")
            if f.is_file() and f.suffix not in _BINARY_EXTS
        )

    matches: list[str] = []
    for py_file in files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if pattern in line:
                rel = py_file.relative_to(_RUNTIME_ROOT).as_posix()
                matches.append(f"{rel}:{lineno}:{line}")

    if matches:
        return _GrepResult(stdout="\n".join(matches), returncode=0)
    return _GrepResult(returncode=1)


_SENTINEL = "SECRET-TOKEN-abc-123-sensitivedetail"
_CREATEDTIME_RE = re.compile(r'"createdTime":\d+')


# ---------------- §6.3 #1: _handle_error_response ---------------------------


def _make_jiuwen_exc(message: str = "boom", error_code: str = "120001") -> JiuWenBaseException:
    return JiuWenBaseException(error_code=error_code, message=message)


def _handle_error_bytes(item) -> bytes:
    return asyncio.run(exec_utils._handle_error_response(item))  # pylint: disable=protected-access


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
    """从多条 SSE wire 提取 JSON 列表，排除非确定字段（createdTime）。"""
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
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in wire  # pylint: disable=protected-access


def test_handle_error_response_logger_no_raw_message(caplog):
    """§4.7B: logger.error 不以 item.message 作为日志 message；exc_info 保留。

    traceback（exc_info）含 str(exception) 是 Python 本质且 §3.2 允许——
    生产中 §4.5 已保证异常 message 安全（非 str(e)）；本断言只校验日志
    message 本身是固定基础事件，不再无条件写未治理原文。
    """
    import logging

    caplog.set_level(logging.ERROR)
    item = _make_jiuwen_exc(message=_SENTINEL)
    _handle_error_bytes(item)
    rec = caplog.records[-1]
    # 日志 message 是固定基础事件，不含 item.message 哨兵
    assert rec.getMessage() == "workflow execution failed"
    assert _SENTINEL not in rec.getMessage()
    # exc_info 保留（traceback 始终到达底层 logger）
    assert rec.exc_info is not None


# ---------------- §6.3 #2: _process_streaming_output ERROR ------------------


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
        async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # pylint: disable=protected-access
            out.append(chunk)
        return out

    return asyncio.run(collect())


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
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # pylint: disable=protected-access


# ---------------- §4.7C: 其余流式出口哨兵不泄漏 -----------------------------


async def _async_noop(*a, **kw):
    return None


def _noop(*a, **kw):
    return None


def _drive_format_component_output(item, monkeypatch):
    """真实调用 #3 _format_component_output。"""
    monkeypatch.setattr(exec_utils, "async_update_state_of_workflow", _async_noop)

    async def origin():
        yield item

    stub_wf = SimpleNamespace(async_clean_up=_async_noop)
    exec_data = SimpleNamespace(instance=stub_wf)

    async def collect():
        out = []
        async for chunk in exec_utils._format_component_output(  # pylint: disable=protected-access
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


def test_format_component_output_no_sensitive_sentinel(monkeypatch):
    wire = _drive_format_component_output(_make_error_item(), monkeypatch)
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined
    assert b"SECRET-TOKEN" not in joined
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # pylint: disable=protected-access


def test_post_process_workflow_streaming_output_no_sentinel(monkeypatch):
    wire = _drive_post_process_workflow_streaming_output(_make_error_item(), monkeypatch)
    joined = b"".join(wire)
    assert _SENTINEL.encode() not in joined
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # pylint: disable=protected-access


# ---------------- §4.7C: WorkflowAbortException 双路径排除证据 -------------


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
    """§4.7C: 真实经过 Workflow._arun() 的 except 分支。"""
    exc = _abort_exception({"user_field": "user-value"})
    stub = _arun_stub(exc)
    result = asyncio.run(Workflow._arun(stub, "query", False, {}))  # pylint: disable=protected-access
    assert result["code"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code
    assert result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg
    assert result["user_field"] == "user-value"
    assert "user-value" not in result["message"]


def test_get_output_isinstance_workflow_abort_real_path():
    """§4.7C: 真实经过 Workflow._get_output() 的 isinstance 分支。"""
    exc = _abort_exception({"user_field": "user-value"})
    stub = _get_output_stub(exc)
    result = asyncio.run(Workflow._get_output(stub))  # pylint: disable=protected-access
    assert result["code"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.code
    assert result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg
    assert result["user_field"] == "user-value"
    assert "user-value" not in result["message"]


def test_abort_two_real_paths_identical_and_safe():
    exc = _abort_exception({"user_field": "user-value"})
    arun_result = asyncio.run(Workflow._arun(_arun_stub(exc), "q", False, {}))  # pylint: disable=protected-access
    getout_result = asyncio.run(Workflow._get_output(_get_output_stub(exc)))  # pylint: disable=protected-access
    assert arun_result == getout_result
    assert arun_result["message"] == StatusCode.WORKFLOW_EXCEPTION_END_ERROR.errmsg


def test_abort_message_not_user_custom_text():
    """排除项证据：message 是 canonical，不是用户塞入的文案。"""
    exc = _abort_exception({"custom_msg": "attacker-controlled text"})
    assert exc.message != "attacker-controlled text"
    assert "attacker-controlled text" not in exc.message


# ---------------- §4.7C #8/#9: 上游生产点→下游消费者真实链路 -------------


def test_8_task_done_callback_wraps_non_jiuwen_with_canonical(monkeypatch):  # pylint: disable=function-docstring-indents-four
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
        Workflow._task_done_callback(stub, task)  # pylint: disable=protected-access
        await asyncio.gather(*chat_manager.tasks)
        return captured.get("exc")

    wrapped = asyncio.run(_run())
    assert isinstance(wrapped, JiuWenBaseException)
    assert wrapped.error_code == SC.WORKFLOW_EXECUTE_ERROR.code
    # 包装后 message 是 UNSAFE 模板填 canonical errmsg（不含 task 异常 str）
    assert _SENTINEL not in wrapped.message
    assert "task boom" not in wrapped.message
    assert SC.WORKFLOW_EXECUTE_ERROR.errmsg in wrapped.message


def test_9_get_output_jiuwen_branch_chain_to_downstream_no_sentinel(monkeypatch):  # pylint: disable=function-docstring-indents-four
    """#9 _get_output JiuWenBaseException 分支产出（含上游哨兵 message）→ 送入下游 #2
    _process_streaming_output → 最终 wire 不含哨兵、含 _SAFE。"""
    upstream_exc = JiuWenBaseException(error_code="120099", message=_SENTINEL)
    stub = _get_output_stub(upstream_exc)
    # 真实 #9：_get_output 的 JiuWenBaseException 分支
    produced = asyncio.run(Workflow._get_output(stub))  # pylint: disable=protected-access
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
    assert exec_utils._SAFE_PUBLIC_ERROR_MESSAGE.encode() in joined  # pylint: disable=protected-access


# ---------------- §6.5 静态治理 ---------------------------------------------


def test_no_test_error_message_in_production():
    """§6.5: 生产代码不再包含面向响应的 'test error message'。"""
    r = _run_grep("-rn", "test error message", "jiuwen")
    # 仅允许出现在注释中（grep -n 输出格式 file:line:content，取 content 判断）
    for line in r.stdout.splitlines():
        parts = line.split(":", 2)
        content = parts[2] if len(parts) >= 3 else line
        assert content.lstrip().startswith("#"), (
            f"生产代码残留 'test error message': {line}"
        )


# ---------------- §5.3 取消/断连与正常结束 ----------------------------------


def _drive_normal_end_item(item):
    async def origin():
        yield item

    async def collect():
        out = []
        async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # pylint: disable=protected-access
            out.append(chunk)
        return out

    return asyncio.run(collect())


def _events_of(wire):
    return [obj.get("event") for obj in _wire_list_json(wire)]


def test_normal_end_no_error_frame(caplog):  # pylint: disable=function-docstring-indents-four
    """§4.8/§6.3: 正常结束（FINISH）经 #2 精确产生 start+唯一 done 终态，
    无 error/额外 END；无 ERROR 日志。"""
    import logging

    caplog.set_level(logging.ERROR)
    finish_item = SimpleNamespace(
        code=StreamCode.FINISH.value,
        data={"content": "done"},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )
    wire = _drive_normal_end_item(finish_item)
    # 精确终态：start + 唯一 done，无 error
    assert _events_of(wire) == ["start", "done"], _events_of(wire)
    assert b'"event":"error"' not in b"".join(wire)
    # 关联 executionId 保持
    assert b'"executionId":"exec-1"' in b"".join(wire)
    # 正常结束不产生 ERROR 日志
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_message_end_no_error_frame(caplog):  # pylint: disable=function-docstring-indents-four
    """§4.8/§6.3: MESSAGE_END 经 #2 精确产生 start+唯一 message_end 终态，
    无 error；无 ERROR 日志。"""
    import logging

    caplog.set_level(logging.ERROR)
    end_item = SimpleNamespace(
        code=StreamCode.MESSAGE_END.value,
        data={},
        index=0,
        execution_id="exec-1",
        is_struct_message=False,
    )
    wire = _drive_normal_end_item(end_item)
    assert _events_of(wire) == ["start", "message_end"], _events_of(wire)
    assert b'"event":"error"' not in b"".join(wire)
    assert b'"executionId":"exec-1"' in b"".join(wire)
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_cancel_propagates_no_synthetic_error(caplog):  # pylint: disable=function-docstring-indents-four
    """§4.8/§6.3: 取消（CancelledError）经 #2：
    - CancelledError 传播（不被吞成 error 帧）；
    - 已产生的 wire 不含 error、无 done/END（取消后无终态帧）；
    - 无新增 ERROR 日志。
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

    holder = []

    async def collect():
        async for chunk in exec_utils._process_streaming_output(origin(), collector=None):  # pylint: disable=protected-access
            holder.append(chunk)

    try:
        asyncio.run(collect())
        raised = False
    except asyncio.CancelledError:
        raised = True
    assert raised, "CancelledError 应被传播"
    joined = b"".join(holder)
    # 已产生 wire：含 start 与 partial message，无 error、无 done/message_end
    assert b'"event":"error"' not in joined
    assert b'"event":"done"' not in joined
    assert b'"event":"message_end"' not in joined
    assert b'"event":"start"' in joined
    # 无 ERROR 日志
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR], (
        "取消不应产生 ERROR"
    )
