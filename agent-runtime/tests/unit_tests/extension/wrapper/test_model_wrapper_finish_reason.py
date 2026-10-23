# -*- coding: UTF-8 -*-
"""ModelWrapper._post_stream_message 的 finish_reason 复制契约测试（#1583）。

core 侧 finish_reason 在消息顶层，OTel 载荷约定放 usage_metadata 内；但复制
只允许发生在非流式（ainvoke）路径——流式路径的中途内容块一旦带上 finish_reason，
会被 _format_yield_result 当作 finish 块提前截断增量输出（原业务回归）。
"""

import os
import sys
import types
from typing import Optional

# packages/（位于 agent-studio 仓库根，agent-runtime 上一级）下的 editable 包
# （common_utils 等）在 pytest 的断言改写下 import 不到，手动加回 sys.path
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.insert(0, _pkg_path)


def _install_psycopg2_stub() -> None:
    """model_wrapper 导入链经 store 层依赖 psycopg2（单测环境未装的原生库）。

    内联在测试文件里（不放 conftest）以避免影响同目录其他用例的收集行为。
    """
    if "psycopg2" in sys.modules:
        return

    psycopg2 = types.ModuleType("psycopg2")
    _error = type("Error", (Exception,), {})
    psycopg2.Error = _error
    psycopg2.OperationalError = type("OperationalError", (_error,), {})

    extras = types.ModuleType("psycopg2.extras")
    extras.execute_values = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("unit tests must not touch the database")
    )
    psycopg2.extras = extras

    sql_mod = types.ModuleType("psycopg2.sql")

    class _SqlObj:
        def __init__(self, *args, **kwargs):
            pass

        def format(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def as_string(self, *args, **kwargs):
            return ""

    for name in ("Identifier", "SQL", "Literal", "Placeholder", "Composed"):
        setattr(sql_mod, name, type(name, (_SqlObj,), {}))
    psycopg2.sql = sql_mod

    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["psycopg2.sql"] = sql_mod


_install_psycopg2_stub()

from openjiuwen.core.foundation.llm.schema.message import (  # noqa: E402
    AssistantMessage,
    UsageMetadata as CoreUsageMetadata,
)

# 绕过 jiuwen.extension.wrapper.__init__（会拉起 mcp / customer_header 等
# 与被测逻辑无关且单测环境缺依赖的模块），按文件直接加载被测模块
import importlib.util  # noqa: E402


def _seed_trace_compat_stub() -> Optional[dict]:
    """为 model_wrapper 顶层 `from agent_runtime.common.trace_compat import ...`
    提供最小替身，避免拉起 agent_runtime.common.__init__ → common_utils →
    redis（单测环境缺失）整条链。

    真实模块可导入时（CI 装有 redis）返回 None、不装任何替身；替身仅在
    加载被测模块期间存在，加载完由 _drop_trace_compat_stub 还原，不向同
    会话其他用例泄漏（被测逻辑只用 _post_stream_message，不触会话创建）。
    """
    try:
        from agent_runtime.common import trace_compat  # noqa: F401

        return None
    except ModuleNotFoundError:
        pass

    import agent_runtime

    fake_common = types.ModuleType("agent_runtime.common")
    fake_common.__path__ = []
    fake_trace = types.ModuleType("agent_runtime.common.trace_compat")

    async def _fake_session_with_trace(session_id=None, **kwargs):
        return None

    fake_trace.create_agent_session_with_trace = _fake_session_with_trace
    fake_common.trace_compat = fake_trace

    sys.modules["agent_runtime.common"] = fake_common
    sys.modules["agent_runtime.common.trace_compat"] = fake_trace
    agent_runtime.common = fake_common
    return {"had_common": True}


def _drop_trace_compat_stub(seeded: Optional[dict]) -> None:
    if not seeded:
        return
    sys.modules.pop("agent_runtime.common", None)
    sys.modules.pop("agent_runtime.common.trace_compat", None)
    import agent_runtime

    if getattr(agent_runtime, "common", None) is not None:
        del agent_runtime.common


_RUNTIME_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_spec = importlib.util.spec_from_file_location(
    "_model_wrapper_under_test",
    os.path.join(_RUNTIME_ROOT, "jiuwen", "extension", "wrapper", "model_wrapper.py"),
)
_model_wrapper = importlib.util.module_from_spec(_spec)
_seeded = _seed_trace_compat_stub()
try:
    _spec.loader.exec_module(_model_wrapper)
finally:
    _drop_trace_compat_stub(_seeded)
ModelWrapper = _model_wrapper.ModelWrapper


def _core_response(finish_reason: str) -> AssistantMessage:
    return AssistantMessage(
        content="done",
        finish_reason=finish_reason,
        usage_metadata=CoreUsageMetadata(model_name="test-model", input_tokens=1),
    )


class TestPostStreamMessageFinishReason:
    @staticmethod
    def test_default_keeps_finish_reason_empty():
        """默认（流式路径调用形态）：顶层 finish_reason 不进 usage_metadata。"""
        ai_message, _ = ModelWrapper._post_stream_message(_core_response("stop"))
        assert ai_message.usage_metadata.finish_reason == ""

    @staticmethod
    def test_copy_finish_reason_true_copies_real_value():
        """显式开启（非流式路径）：真实值复制，供 OTel 载荷读取。"""
        ai_message, _ = ModelWrapper._post_stream_message(
            _core_response("stop"), copy_finish_reason=True
        )
        assert ai_message.usage_metadata.finish_reason == "stop"

    @staticmethod
    def test_copy_finish_reason_skips_placeholder():
        """占位值 null 与空值不复制（保持默认空串）。"""
        for placeholder in ("null", ""):
            ai_message, _ = ModelWrapper._post_stream_message(
                _core_response(placeholder), copy_finish_reason=True
            )
            assert ai_message.usage_metadata.finish_reason == ""
