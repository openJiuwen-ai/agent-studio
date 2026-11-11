# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""Code runner 加固 json.loads：空串/自然语言不得再抛含糊的 Expecting value。"""

from __future__ import annotations

import json

import pytest

from agent_runtime.extension.workflow_node.code_runner.base_code_runner import (
    _SAFE_JSON_LOADS_PROLOGUE,
    build_wrapped_code,
)
from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import (
    _install_guarded_json_loads,
    _restore_json_loads,
)


class TestGuardedJsonLoads:
    def test_empty_string_raises_value_error(self):
        orig = _install_guarded_json_loads()
        try:
            with pytest.raises(ValueError, match="empty input"):
                json.loads("")
            with pytest.raises(ValueError, match="empty input"):
                json.loads(None)
        finally:
            _restore_json_loads(orig)

    def test_natural_language_raises_value_error(self):
        orig = _install_guarded_json_loads()
        try:
            with pytest.raises(ValueError, match="non-JSON"):
                json.loads("零花钱卡")
        finally:
            _restore_json_loads(orig)

    def test_valid_json_still_works(self):
        orig = _install_guarded_json_loads()
        try:
            assert json.loads('{"a":1}') == {"a": 1}
        finally:
            _restore_json_loads(orig)

    def test_wrapped_code_contains_guard(self):
        wrapped = build_wrapped_code("def main(args): return args", {"x": 1})
        assert "_guarded_json_loads" in wrapped
        assert _SAFE_JSON_LOADS_PROLOGUE.strip().splitlines()[0] in wrapped
