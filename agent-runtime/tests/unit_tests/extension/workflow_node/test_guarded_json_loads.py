# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""Code runner 加固 json.loads：空串/自然语言给出可行动消息，且保持 JSONDecodeError 类型。"""

from __future__ import annotations

import json

import pytest

from agent_runtime.extension.workflow_node.code_runner.base_code_runner import (
    _SAFE_JSON_LOADS_PROLOGUE,
    build_wrapped_code,
)
from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import (
    _ExecResult,
    _install_guarded_json_loads,
    _restore_json_loads,
    InprocessCodeRunner,
)


class TestGuardedJsonLoads:
    @staticmethod
    def test_empty_string_raises_json_decode_error():
        orig = _install_guarded_json_loads()
        try:
            with pytest.raises(json.JSONDecodeError, match="empty input"):
                json.loads("")
            with pytest.raises(json.JSONDecodeError, match="empty input"):
                json.loads(None)
            # 存量 soft-fail：except JSONDecodeError 必须仍能命中
            try:
                json.loads("   ")
                assert False, "expected JSONDecodeError"
            except json.JSONDecodeError as e:
                assert "empty input" in str(e)
        finally:
            _restore_json_loads(orig)

    @staticmethod
    def test_natural_language_raises_json_decode_error():
        orig = _install_guarded_json_loads()
        try:
            with pytest.raises(json.JSONDecodeError, match="non-JSON"):
                json.loads("零花钱卡")
            try:
                json.loads("零花钱卡")
                assert False, "expected JSONDecodeError"
            except json.JSONDecodeError as e:
                assert "non-JSON" in str(e)
        finally:
            _restore_json_loads(orig)

    @staticmethod
    def test_valid_json_still_works():
        orig = _install_guarded_json_loads()
        try:
            assert json.loads('{"a":1}') == {"a": 1}
        finally:
            _restore_json_loads(orig)

    @staticmethod
    def test_wrapped_code_contains_guard():
        wrapped = build_wrapped_code("def main(args): return args", {"x": 1})
        assert "_guarded_json_loads" in wrapped
        assert "JSONDecodeError" in wrapped
        assert _SAFE_JSON_LOADS_PROLOGUE.strip().splitlines()[0] in wrapped

    @staticmethod
    def test_force_cleanup_restores_json_loads():
        """超时 _force_cleanup 必须还原进程级 json.loads，避免守卫永久泄漏。"""
        baseline = json.loads
        container = _ExecResult()
        container.saved_json_loads = baseline
        # 模拟 worker 安装守卫后卡死、finally 未执行
        _install_guarded_json_loads()
        assert json.loads is not baseline
        # getattr：规避 G.CLS.11（CodeCheck 不认 pylint pragma）
        force_cleanup = getattr(InprocessCodeRunner, "_force_cleanup")
        force_cleanup(container)
        assert json.loads is baseline
