# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""FlowCode CODE_BLACK_LIST 解析回归。

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


def _call_check_blacklist(flow_code, code):
    getattr(flow_code, "_check_blacklist")(code)


class TestLoadCodeBlacklist:
    @staticmethod
    def test_unset_returns_empty():
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CODE_BLACK_LIST", None)
            assert _load_code_blacklist() == []

    @staticmethod
    def test_empty_string_returns_empty():
        """CODE_BLACK_LIST="" 不得再抛 JSONDecodeError"""
        with patch.dict(os.environ, {"CODE_BLACK_LIST": ""}):
            assert _load_code_blacklist() == []

    @staticmethod
    def test_whitespace_returns_empty():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "   "}):
            assert _load_code_blacklist() == []

    @staticmethod
    def test_invalid_json_returns_empty():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "not-json"}):
            assert _load_code_blacklist() == []

    @staticmethod
    def test_non_list_json_returns_empty():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '{"a": 1}'}):
            assert _load_code_blacklist() == []

    @staticmethod
    def test_valid_list_parsed():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess","os.system"]'}):
            assert _load_code_blacklist() == ["subprocess", "os.system"]


class TestCheckBlacklistEmptyEnv:
    @staticmethod
    def test_empty_env_does_not_raise():
        flow_code = FlowCode(
            FlowCodeConfig(code="def main(args): return {}", exec_env="local")
        )
        with patch.dict(os.environ, {"CODE_BLACK_LIST": ""}):
            _call_check_blacklist(flow_code, "def main(args): return {}")

    @staticmethod
    def test_blacklist_still_blocks():
        flow_code = FlowCode(
            FlowCodeConfig(code="def main(args): return {}", exec_env="local")
        )
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess"]'}):
            with pytest.raises(Exception) as exc_info:
                _call_check_blacklist(
                    flow_code, "import subprocess\ndef main(args): return {}"
                )
            assert "subprocess" in str(exc_info.value)
