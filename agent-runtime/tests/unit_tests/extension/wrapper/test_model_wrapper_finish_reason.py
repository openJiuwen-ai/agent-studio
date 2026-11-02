# -*- coding: UTF-8 -*-
"""ModelWrapper._post_stream_message 的 finish_reason 复制契约测试（#1583）。

core 侧 finish_reason 在消息顶层，OTel 载荷约定放 usage_metadata 内；但复制
只允许发生在非流式（ainvoke）路径——流式路径的中途内容块一旦带上 finish_reason，
会被 _format_yield_result 当作 finish 块提前截断增量输出（原业务回归）。

另覆盖 ainvoke 批式兜底打戳：core 模型不上报 TTFT 双时间戳（恒空串），批式
链路（AgentCoreModelLayer.ainvoke → ModelWrapper.ainvoke → core model.invoke）
无人打戳，控制器批式 span 会恒缺 TTFT——由 wrapper 在请求前/响应到达代打，
与 astream 的自打戳、qwen._chat 的批式打戳语义对齐。
"""

import asyncio
import importlib.util
import os
import sys
import types
from datetime import datetime
from typing import Optional

# packages/（位于 agent-studio 仓库根，agent-runtime 上一级）下的 editable 包
# （common_utils 等）在 pytest 的断言改写下 import 不到，手动补进 sys.path
# （append 到末尾：仅补齐缺失路径，不抢占既有解析顺序，避免模块重名遮蔽）
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.append(_pkg_path)


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

    def _execute_values(*args, **kwargs):
        raise AssertionError("unit tests must not touch the database")

    extras.execute_values = _execute_values
    psycopg2.extras = extras

    sql_mod = types.ModuleType("psycopg2.sql")

    class _SqlObj:
        def __init__(self, *args, **kwargs):
            pass

        def format(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        @staticmethod
        def as_string(*args, **kwargs):
            return ""

    for name in ("Identifier", "SQL", "Literal", "Placeholder", "Composed"):
        setattr(sql_mod, name, type(name, (_SqlObj,), {}))
    psycopg2.sql = sql_mod

    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = extras
    sys.modules["psycopg2.sql"] = sql_mod


def _seed_psycopg2_stub() -> bool:
    """真实 psycopg2 可导入时返回 False、不装替身（CI 装有原生库）。

    替身仅在加载被测模块期间存在，加载完立即卸载，不向同会话其他用例
    泄漏（与 _seed_trace_compat_stub 同一 try/finally 语义）。
    """
    try:
        import psycopg2  # noqa: F401

        return False
    except ModuleNotFoundError:
        _install_psycopg2_stub()
        return True


def _uninstall_psycopg2_stub() -> None:
    for _key in ("psycopg2", "psycopg2.extras", "psycopg2.sql"):
        sys.modules.pop(_key, None)

from openjiuwen.core.foundation.llm.schema.message import (  # noqa: E402
    AssistantMessage,
    UsageMetadata as CoreUsageMetadata,
)

# 绕过 jiuwen.extension.wrapper.__init__（会拉起 mcp / customer_header 等
# 与被测逻辑无关且单测环境缺依赖的模块），按文件直接加载被测模块


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
_stubbed = _seed_psycopg2_stub()
try:
    _spec.loader.exec_module(_model_wrapper)
finally:
    if _stubbed:
        _uninstall_psycopg2_stub()
    _drop_trace_compat_stub(_seeded)
ModelWrapper = _model_wrapper.ModelWrapper


class _ModelWrapperHarness(ModelWrapper):
    """被测方法的测试入口：单例静态方法无需（也不应）构造实例。

    子类内经 cls 访问受保护静态方法，为类外直接触碰保护成员的合规替代。
    """

    @classmethod
    def call_post_stream_message(cls, *args, **kwargs):
        return cls._post_stream_message(*args, **kwargs)


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
        ai_message, _ = _ModelWrapperHarness.call_post_stream_message(
            _core_response("stop")
        )
        assert ai_message.usage_metadata.finish_reason == ""

    @staticmethod
    def test_copy_finish_reason_true_copies_real_value():
        """显式开启（非流式路径）：真实值复制，供 OTel 载荷读取。"""
        ai_message, _ = _ModelWrapperHarness.call_post_stream_message(
            _core_response("stop"), copy_finish_reason=True
        )
        assert ai_message.usage_metadata.finish_reason == "stop"

    @staticmethod
    def test_copy_finish_reason_skips_placeholder():
        """占位值 null 与空值不复制（保持默认空串）。"""
        for placeholder in ("null", ""):
            ai_message, _ = _ModelWrapperHarness.call_post_stream_message(
                _core_response(placeholder), copy_finish_reason=True
            )
            assert ai_message.usage_metadata.finish_reason == ""

    @staticmethod
    def test_copy_finish_reason_normalizes_tool_calls():
        """OpenAI 风格工具调用终态归一化为 function_call（与 astream 一致）。

        core 若用 "tool_calls" 表达工具调用终态，原样复制会让非流式工具
        调用响应的 finish_reason 脱离 jiuwen 约定（stop/function_call）；
        其它值（如 "length"）保持原样透传。
        """
        for variant in ("tool_calls", "tool_call"):
            ai_message, _ = _ModelWrapperHarness.call_post_stream_message(
                _core_response(variant), copy_finish_reason=True
            )
            assert ai_message.usage_metadata.finish_reason == "function_call"
        ai_message, _ = _ModelWrapperHarness.call_post_stream_message(
            _core_response("length"), copy_finish_reason=True
        )
        assert ai_message.usage_metadata.finish_reason == "length"


class TestAInvokeTimestampFallback:
    """ainvoke 批式兜底打戳（#1583）：core 未自报时间戳时代打、自报时不覆盖。"""

    @staticmethod
    def _run_ainvoke(core_usage, monkeypatch):
        """桩掉会话/资源管理后驱动 ainvoke，返回转换后的 AIMessage。"""

        class _FakeModel:
            @staticmethod
            async def invoke(messages, **kwargs):
                return AssistantMessage(
                    content="done",
                    finish_reason="stop",
                    usage_metadata=core_usage,
                )

        async def _get_model(model_id, session):
            return _FakeModel()

        class _FakeRunner:
            # SimpleNamespace 充当 resource_mgr 替身：属性即函数、无绑定语义，
            # 也避免为桩再引入一个不符合 PascalCase 的嵌套类名（G.NAM.01）
            resource_mgr = types.SimpleNamespace(get_model=_get_model)

        def _fake_session(session_id=None, **kwargs):
            # 真实 trace_compat 为同步返回（wrapper 不 await 直接使用）
            return None

        monkeypatch.setattr(_model_wrapper, "Runner", _FakeRunner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", _fake_session
        )
        wrapper = ModelWrapper()
        return asyncio.run(
            wrapper.ainvoke([{"role": "user", "content": "hi"}], "m1", "s1")
        )

    @staticmethod
    def test_core_empty_timestamps_get_stamped(monkeypatch):
        """core 未填时间戳（默认空串）→ wrapper 代打双时间戳，TTFT 可算。"""
        ai_message = TestAInvokeTimestampFallback._run_ainvoke(
            CoreUsageMetadata(model_name="test-model", input_tokens=1), monkeypatch
        )
        usage = ai_message.usage_metadata
        assert usage.requests_start_time and usage.first_token_time
        start = datetime.fromisoformat(usage.requests_start_time)
        first = datetime.fromisoformat(usage.first_token_time)
        assert first >= start  # 响应到达不早于请求发出

    @staticmethod
    def test_core_stamped_timestamps_not_overwritten(monkeypatch):
        """core 已自报时间戳 → 保留原值，兜底不覆盖。"""
        core_usage = CoreUsageMetadata(
            model_name="test-model",
            input_tokens=1,
            request_start_time="2026-10-23T10:00:00+08:00",
            first_token_time="2026-10-23T10:00:00.500+08:00",
        )
        ai_message = TestAInvokeTimestampFallback._run_ainvoke(
            core_usage, monkeypatch
        )
        usage = ai_message.usage_metadata
        assert usage.requests_start_time == "2026-10-23T10:00:00+08:00"
        assert usage.first_token_time == "2026-10-23T10:00:00.500+08:00"

    @staticmethod
    def test_no_usage_metadata_no_crash(monkeypatch):
        """core 无 usage_metadata → 无处打戳，不得崩溃。"""
        ai_message = TestAInvokeTimestampFallback._run_ainvoke(None, monkeypatch)
        assert ai_message.usage_metadata is None
        assert ai_message.content == "done"
