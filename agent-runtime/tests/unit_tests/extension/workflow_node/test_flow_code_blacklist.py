# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""FlowCode CODE_BLACK_LIST 解析回归。

空串/空白容错为无黑名单；非法 JSON/非 list fail-closed，避免配置写错时
静默关闭安全控制。
"""

import os
from unittest.mock import patch

import pytest
from agent_runtime.extension.workflow_node.code_blacklist import load_code_blacklist
from agent_runtime.extension.workflow_node.flow_code import (
    FlowCode,
    FlowCodeConfig,
)

# 兼容别名：flow_code 再导出供既有调用
_load_code_blacklist = load_code_blacklist


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
    def test_invalid_json_fail_closed():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "not-json"}):
            with pytest.raises(Exception) as exc_info:
                _load_code_blacklist()
            assert "CODE_BLACK_LIST" in str(exc_info.value)

    @staticmethod
    def test_non_list_json_fail_closed():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '{"a": 1}'}):
            with pytest.raises(Exception) as exc_info:
                _load_code_blacklist()
            assert "list" in str(exc_info.value).lower()

    @staticmethod
    def test_valid_list_parsed():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess","os.system"]'}):
            assert _load_code_blacklist() == ["subprocess", "os.system"]

    @staticmethod
    def test_non_string_items_filtered():
        with patch.dict(os.environ, {"CODE_BLACK_LIST": '["subprocess", 123]'}):
            assert _load_code_blacklist() == ["subprocess"]


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

    @staticmethod
    def test_invalid_json_blocks_invoke():
        flow_code = FlowCode(
            FlowCodeConfig(code="def main(args): return {}", exec_env="local")
        )
        with patch.dict(os.environ, {"CODE_BLACK_LIST": "not-json"}):
            with pytest.raises(Exception) as exc_info:
                _call_check_blacklist(flow_code, "def main(args): return {}")
            assert "CODE_BLACK_LIST" in str(exc_info.value)
