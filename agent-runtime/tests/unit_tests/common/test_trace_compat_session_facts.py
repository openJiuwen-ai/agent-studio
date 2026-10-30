# -*- coding: UTF-8 -*-
"""trace_compat 会话事实兼容层单测（issue #1583）。

create_agent_session_with_trace 对 source_metadata 的探测透传：旧版
openjiuwen create_agent_session 无该参数且无 **kwargs 兜底时摘出不传
（遥测事实优雅降级，不得 TypeError 破坏会话创建，检视意见）；底层
支持时原样透传，供 core OtelRail / 双写桥取 openjiuwen.gen_ai.user.id。
"""

import os
import sys

# packages/（agent-studio 仓库根，agent-runtime 上一级）下的 editable 包
# （common_utils 等）在 pytest 的断言改写下 import 不到，手动补进 sys.path
# （append 到末尾：仅补齐缺失路径，不抢占既有解析顺序）
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
for _pkg in ("common_utils", "storage", "model_service"):
    _pkg_path = os.path.join(_REPO_ROOT, "packages", _pkg)
    if os.path.isdir(_pkg_path) and _pkg_path not in sys.path:
        sys.path.append(_pkg_path)

from agent_runtime.common import trace_compat as tc


class TestSourceMetadataCompat:
    @staticmethod
    def test_dropped_when_unsupported(monkeypatch):
        """旧版底层无 source_metadata 参数 → 摘出不传，会话创建不受影响。"""
        seen = {}

        def _fake_create(session_id=None, **kwargs):
            seen.update(kwargs)
            return "SESSION"

        monkeypatch.setattr(tc, "_create_agent_session", _fake_create)
        monkeypatch.setattr(tc, "_agent_accepts_source_metadata", False)
        result = tc.create_agent_session_with_trace(
            session_id="s1", card=object(), source_metadata={"user_id": "u1"}
        )
        assert result == "SESSION"
        assert "source_metadata" not in seen

    @staticmethod
    def test_passthrough_when_supported(monkeypatch):
        """底层支持 → 会话事实原样随 session 携带。"""
        seen = {}

        def _fake_create(session_id=None, **kwargs):
            seen.update(kwargs)
            return "SESSION"

        monkeypatch.setattr(tc, "_create_agent_session", _fake_create)
        monkeypatch.setattr(tc, "_agent_accepts_source_metadata", True)
        tc.create_agent_session_with_trace(
            session_id="s1", card=object(), source_metadata={"user_id": "u1"}
        )
        assert seen["source_metadata"] == {"user_id": "u1"}

    @staticmethod
    def test_absent_source_metadata_noop(monkeypatch):
        """调用方未携带 → 不注入空键。"""
        seen = {}

        def _fake_create(session_id=None, **kwargs):
            seen.update(kwargs)
            return "SESSION"

        monkeypatch.setattr(tc, "_create_agent_session", _fake_create)
        monkeypatch.setattr(tc, "_agent_accepts_source_metadata", True)
        tc.create_agent_session_with_trace(session_id="s1", card=object())
        assert "source_metadata" not in seen
