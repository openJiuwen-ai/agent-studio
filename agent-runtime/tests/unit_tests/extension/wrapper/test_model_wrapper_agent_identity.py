# -*- coding: UTF-8 -*-
"""ModelWrapper agent 身份归因透传契约（双写桥 llm span 缺身份修复）。

控制器层经 AgentCoreModelLayer 调用模型时，ModelWrapper 收到的会话是裸会话
（无 agent card），core rail 的 common-info 路径取不到 agent_id——控制器壳下
的 llm span 因此缺 gen_ai.agent.* 身份（部署实证缺陷 ①）。修复：调用方
kwargs 里的 agent_id 经 get_model(identity=) 显式带入；能力探测
（_decorator_accepts_identity，与 get_model 的 identity 参数由同一对 core
双子引入）不过则不传——旧 core 的 get_model 无该参数，盲传 TypeError 会打断
模型调用。无 agent_id 也不传，调用形态与既有完全一致。
"""

import asyncio
import importlib.util
import os
import sys
import types
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
    """真实 psycopg2 可导入时返回 False、不装替身（CI 装有原生库）。"""
    try:
        import psycopg2  # noqa: F401

        return False
    except ModuleNotFoundError:
        _install_psycopg2_stub()
        return True


def _uninstall_psycopg2_stub() -> None:
    for _key in ("psycopg2", "psycopg2.extras", "psycopg2.sql"):
        sys.modules.pop(_key, None)


def _seed_trace_compat_stub() -> Optional[dict]:
    """为 model_wrapper 顶层 `from agent_runtime.common.trace_compat import ...`
    提供最小替身（含本用例导入的身份能力探测函数），避免拉起
    agent_runtime.common.__init__ → common_utils → redis 整条链。

    真实模块可导入时返回 None、不装替身；加载完由 _drop_trace_compat_stub
    还原。探测函数的具体返回值不在此定——用例经 monkeypatch 覆盖
    model_wrapper 模块内绑定的名字来控制能力开关。
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

    def _fake_accepts_identity():
        return False

    fake_trace.create_agent_session_with_trace = _fake_session_with_trace
    # 受保护成员经 setattr 写入，规避 G.CLS.11（pylint pragma 不生效）
    setattr(fake_trace, "_decorator_accepts_identity", _fake_accepts_identity)
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
    "_model_wrapper_identity_under_test",
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

from openjiuwen.core.foundation.llm.schema.message import (  # noqa: E402
    AssistantMessage,
    UsageMetadata as CoreUsageMetadata,
)


def _core_final_message() -> AssistantMessage:
    return AssistantMessage(
        content="done",
        finish_reason="stop",
        usage_metadata=CoreUsageMetadata(model_name="test-model", input_tokens=1),
    )


def _make_runner(captured: dict):
    """resource_mgr 替身：记录 get_model 收到的全部 kwargs、回放假模型。"""

    class _FakeModel:
        @staticmethod
        async def invoke(messages, **kwargs):
            return _core_final_message()

        @staticmethod
        async def stream(messages, **kwargs):
            yield _core_final_message()

    async def _get_model(model_id, session=None, **kwargs):
        captured["model_id"] = model_id
        captured.setdefault("calls", []).append(dict(kwargs))
        return _FakeModel()

    class _FakeRunner:
        # SimpleNamespace 充当 resource_mgr 替身：属性即函数、无绑定语义，
        # 也避免为桩再引入一个不符合 PascalCase 的嵌套类名（G.NAM.01）
        resource_mgr = types.SimpleNamespace(get_model=_get_model)

    def _fake_session(session_id=None, **kwargs):
        return None

    return _FakeRunner, _fake_session


def _identity_kwargs(captured: dict):
    """全部 get_model 调用里出现过的 identity 取值（None 表示从未传）。"""
    seen = [call.get("identity") for call in captured.get("calls", [])]
    return seen


class TestAgentIdentityPassthrough:
    """kwargs.agent_id → get_model(identity=)，能力门禁与缺省形态逐条钉死。"""

    @staticmethod
    def test_ainvoke_passes_agent_identity_when_capable(monkeypatch):
        """探测通过 + agent_id 在 → get_model 收到 identity={"agent_id": ...}。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}], "m1", "s1", agent_id="agent-7"
            )
        )
        assert captured["calls"], "get_model must be called"
        assert _identity_kwargs(captured) == [{"agent_id": "agent-7"}]

    @staticmethod
    def test_ainvoke_omits_identity_without_agent_id(monkeypatch):
        """能力通过但无 agent_id（存量调用方）→ 不带 identity，wire 不变。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(wrapper.ainvoke([{"role": "user", "content": "hi"}], "m1", "s1"))
        assert _identity_kwargs(captured) == [None]

    @staticmethod
    def test_ainvoke_omits_identity_when_probe_closed(monkeypatch):
        """探测不过（旧 core 无 identity 参数）→ 即便 agent_id 在也不传：
        盲传会让旧 get_model 抛 TypeError 打断模型调用，门禁是保护不是装饰。
        """
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: False)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}], "m1", "s1", agent_id="agent-7"
            )
        )
        assert _identity_kwargs(captured) == [None]

    @staticmethod
    def test_astream_passes_agent_identity_when_capable(monkeypatch):
        """流式路径同样透传：get_model 在进入模型流之前就应带上身份。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()

        async def _consume():
            async for _chunk in wrapper.astream(
                [{"role": "user", "content": "hi"}], "m1", "s1", agent_id="agent-9"
            ):
                break

        asyncio.run(_consume())
        assert captured["calls"], "get_model must be called"
        assert _identity_kwargs(captured) == [{"agent_id": "agent-9"}]


class TestParentRefsPassthrough:
    """kwargs 父级 refs → identity 同通道透传：层级（②）与身份（①）一次带齐。"""

    @staticmethod
    def test_ainvoke_forwards_agent_name_and_refs(monkeypatch):
        """agent_id + agent_name + refs 齐全 → identity 一并带给 core。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                agent_id="agent-7",
                agent_name="问答智能体",
                parent_trace_id="ab" * 16,
                parent_span_id="cd" * 8,
                parent_trace_flags="01",
            )
        )
        assert _identity_kwargs(captured) == [
            {
                "agent_id": "agent-7",
                "agent_name": "问答智能体",
                "parent_trace_id": "ab" * 16,
                "parent_span_id": "cd" * 8,
                "parent_trace_flags": "01",
            }
        ]

    @staticmethod
    def test_ainvoke_forwards_refs_without_agent_id(monkeypatch):
        """只有 refs（无 agent_id，如无身份的工作流 LLM 节点）→ 层级仍要修。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                parent_trace_id="ab" * 16,
                parent_span_id="cd" * 8,
            )
        )
        assert _identity_kwargs(captured) == [
            {"parent_trace_id": "ab" * 16, "parent_span_id": "cd" * 8}
        ]

    @staticmethod
    def test_agent_name_alone_not_forwarded(monkeypatch):
        """门禁：无 agent_id 且无 refs → 即便有 agent_name 也不传（wire 不变）。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}], "m1", "s1", agent_name="仅名字"
            )
        )
        assert _identity_kwargs(captured) == [None]

    @staticmethod
    def test_refs_ignored_when_probe_closed(monkeypatch):
        """探测不过（旧 core）→ refs 也不传：旧 handler 不认识，盲传无收益。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: False)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                agent_id="agent-7",
                parent_trace_id="ab" * 16,
                parent_span_id="cd" * 8,
            )
        )
        assert _identity_kwargs(captured) == [None]

    @staticmethod
    def test_partial_refs_dropped(monkeypatch):
        """span_id 无 trace_id → 层级键成对才有效，半对不进 identity。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                agent_id="agent-7",
                parent_span_id="cd" * 8,
            )
        )
        assert _identity_kwargs(captured) == [{"agent_id": "agent-7"}]

    @staticmethod
    def test_span_id_alone_without_trace_id_yields_no_identity(monkeypatch):
        """无 agent_id 且只有半对 refs → 整个 identity 片段不发（jdfff 11-05）。

        改前门禁只查 parent_span_id：半对也放行，落到
        {"identity": {}} 空参数——与既有调用形态不一致。"""
        monkeypatch.setattr(_model_wrapper, "_decorator_accepts_identity", lambda: True)
        captured: dict = {}
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(
            _model_wrapper, "create_agent_session_with_trace", fake_session
        )
        wrapper = ModelWrapper()
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                parent_span_id="cd" * 8,
            )
        )
        assert _identity_kwargs(captured) == [None]
