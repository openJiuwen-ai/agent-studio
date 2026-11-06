# -*- coding: UTF-8 -*-
"""ModelWrapper identity 通道契约（身份 + 会话事实 + 调用事实 → 真 llm span）。

控制器层经 AgentCoreModelLayer 调用模型时，ModelWrapper 收到的会话是裸会话
（无 agent card），core rail 的 common-info 路径取不到 agent_id/会话事实/
请求参数——壳下 llm span 因此缺 gen_ai.agent.* / gen_ai.conversation_id /
gen_ai.request.*。修复：调用方 kwargs 里的归因信息 + 会话 id + 消息数 +
请求参数经 get_model(identity=) 一次带给 core（handler 平铺消费，
write-if-absent 盖属性）。2026-11-06 决策：本线要求配套新版 core
（identity 参数贯通 get_model 链路），旧 core 探测降级已撤除——identity
有事实即透传，不再探测签名。
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
    还原。
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


class TestIdentityFacts:
    """身份 + 会话事实 + 请求参数 + 消息数 → get_model(identity=) 一次带齐。"""

    @staticmethod
    def _patch(monkeypatch, captured):
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(_model_wrapper, "create_agent_session_with_trace", fake_session)
        return ModelWrapper()

    @staticmethod
    def test_ainvoke_carries_agent_and_conversation_facts(monkeypatch):
        """agent_id + 会话事实：conversation_id=会话 id（rail 同口径）、
        message_count=消息条数，与身份一并带给 core。"""
        captured: dict = {}
        wrapper = TestIdentityFacts._patch(monkeypatch, captured)
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}, {"role": "user", "content": "再问"}],
                "m1",
                "s1",
                agent_id="agent-7",
            )
        )
        assert captured["calls"], "get_model must be called"
        assert _identity_kwargs(captured) == [
            {"agent_id": "agent-7", "conversation_id": "s1", "message_count": 2}
        ]

    @staticmethod
    def test_request_params_rail_key_convention(monkeypatch):
        """请求参数按 core gen_ai.request.* 消费口径：stop→stop_sequences，
        未传的键（top_k/reasoning_level）不写。"""
        captured: dict = {}
        wrapper = TestIdentityFacts._patch(monkeypatch, captured)
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                temperature=0.3,
                top_p=0.9,
                max_tokens=1024,
                stop=["\n"],
            )
        )
        assert _identity_kwargs(captured) == [
            {
                "conversation_id": "s1",
                "message_count": 1,
                "request_params": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 1024,
                    "stop_sequences": ["\n"],
                },
            }
        ]

    @staticmethod
    def test_user_id_passthrough(monkeypatch):
        """user_id（调用方有则带）→ core handler 落 gen_ai.user.id。"""
        captured: dict = {}
        wrapper = TestIdentityFacts._patch(monkeypatch, captured)
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}], "m1", "s1", user_id="u-9"
            )
        )
        assert _identity_kwargs(captured) == [
            {"conversation_id": "s1", "user_id": "u-9", "message_count": 1}
        ]

    @staticmethod
    def test_astream_same_identity_contract(monkeypatch):
        """流式路径同契约：get_model 在进入模型流之前就应带齐事实。"""
        captured: dict = {}
        wrapper = TestIdentityFacts._patch(monkeypatch, captured)

        async def _consume():
            async for _chunk in wrapper.astream(
                [{"role": "user", "content": "hi"}], "m1", "s1", agent_id="agent-9"
            ):
                break

        asyncio.run(_consume())
        assert captured["calls"], "get_model must be called"
        assert _identity_kwargs(captured) == [
            {"agent_id": "agent-9", "conversation_id": "s1", "message_count": 1}
        ]


class TestIdentityFragmentShape:
    """identity 片段形状：无事实不发（不产生空 identity 参数）。"""

    @staticmethod
    def test_no_facts_yields_empty_fragment():
        assert ModelWrapper._trace_identity_kwargs({}) == {}

    @staticmethod
    def test_message_count_none_omitted():
        out = ModelWrapper._trace_identity_kwargs({}, session_id="s1")
        assert out == {"identity": {"conversation_id": "s1"}}


class TestParentRefsPassthrough:
    """kwargs 父级 refs → identity 同通道透传：层级（②）与身份/事实一次带齐。"""

    @staticmethod
    def _patch(monkeypatch, captured):
        runner, fake_session = _make_runner(captured)
        monkeypatch.setattr(_model_wrapper, "Runner", runner)
        monkeypatch.setattr(_model_wrapper, "create_agent_session_with_trace", fake_session)
        return ModelWrapper()

    @staticmethod
    def test_ainvoke_forwards_agent_name_and_refs(monkeypatch):
        """agent_id + agent_name + refs 齐全 → identity 连同会话事实一并带给 core。"""
        captured: dict = {}
        wrapper = TestParentRefsPassthrough._patch(monkeypatch, captured)
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
                "conversation_id": "s1",
                "parent_trace_id": "ab" * 16,
                "parent_span_id": "cd" * 8,
                "parent_trace_flags": "01",
                "message_count": 1,
            }
        ]

    @staticmethod
    def test_ainvoke_forwards_refs_without_agent_id(monkeypatch):
        """只有 refs（无 agent_id，如无身份的工作流 LLM 节点）→ 层级仍要修。"""
        captured: dict = {}
        wrapper = TestParentRefsPassthrough._patch(monkeypatch, captured)
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
            {
                "conversation_id": "s1",
                "parent_trace_id": "ab" * 16,
                "parent_span_id": "cd" * 8,
                "message_count": 1,
            }
        ]

    @staticmethod
    def test_partial_refs_dropped(monkeypatch):
        """span_id 无 trace_id → 层级键成对才有效，半对不进 identity。"""
        captured: dict = {}
        wrapper = TestParentRefsPassthrough._patch(monkeypatch, captured)
        asyncio.run(
            wrapper.ainvoke(
                [{"role": "user", "content": "hi"}],
                "m1",
                "s1",
                agent_id="agent-7",
                parent_span_id="cd" * 8,
            )
        )
        assert _identity_kwargs(captured) == [
            {"agent_id": "agent-7", "conversation_id": "s1", "message_count": 1}
        ]
