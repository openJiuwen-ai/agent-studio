# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""FlowCode CODE_BLACK_LIST 解析回归（BUG2026110905666）。

覆盖：环境变量存在但为空串时，原先 json.loads("") 抛
Expecting value: line 1 column 1 (char 0)，导致对象处理流中的代码节点
invoke 失败。修复后空串/空白/非法 JSON 均视为无黑名单。
"""

import os
from unittest.mock import patch

import pytest
from agent_runtime.extension.workflow_node.flow_code import (
    FlowCode,
    FlowCodeConfig,
    _load_code_blacklist,
)


class TestLoadCodeBlacklist:
    def test_unset_returns_empty(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CODE_BLACK_LIST", None)
            assert _load_code_blacklist() == []

    def test_empty_string_returns_empty(self):
        """BUG2026110905666：CODE_BLACK_LIST="" 不得再抛 JSONDecodeError"""
        with patch.dict(os.environ, {"CODE_BLACK_LIST": ""}):
            assert _load_code_blacklist() == []

    def test_whitespace_returns_empty(self):
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "   "}):
            assert _load_code_blacklist() == []

    def test_invalid_json_returns_empty(self):
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "not-json"}):
            assert _load_code_blacklist() == []

    def test_non_list_json_returns_empty(self):
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '{"a": 1}'}):
            assert _load_code_blacklist() == []

    def test_valid_list_parsed(self):
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess","os.system"]'}):
            assert _load_code_blacklist() == ["subprocess", "os.system"]


class TestCheckBlacklistEmptyEnv:
    def test_empty_env_does_not_raise(self):
        flow_code = FlowCode(
            FlowCodeConfig(code="def main(args): return {}", exec_env="local")
        )
        with patch.dict(os.environ, {"CODE_BLACK_LIST": ""}):
            flow_code._check_blacklist("def main(args): return {}")

    def test_blacklist_still_blocks(self):
        flow_code = FlowCode(
            FlowCodeConfig(code="def main(args): return {}", exec_env="local")
        )
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess"]'}):
            with pytest.raises(Exception) as exc_info:
                flow_code._check_blacklist("import subprocess\ndef main(args): return {}")
            assert "subprocess" in str(exc_info.value)
