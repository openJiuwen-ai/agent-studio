#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""get_list_from_env 空值兜底 — GitHub #1643 / GitCode #1712。

LOG_MASKED_ENABLED=true 且 LOG_MASKED_PATTERNS=（.env 模板默认空）时，
修复前 json.loads("") 抛 ValueError 导致 runtime 启动崩溃。
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest


def _resolve_base_py() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "jiuwen" / "common" / "log" / "base.py"
        if candidate.is_file():
            return candidate
    container = Path("/opt/cloud/agent-runtime/app/jiuwen/common/log/base.py")
    if container.is_file():
        return container
    raise FileNotFoundError("jiuwen/common/log/base.py not found for unit test")


def _load_get_list_from_env():
    """只抽取 get_list_from_env，避免 import base.py 触发 SingletonLogger 初始化。"""
    base_path = _resolve_base_py()
    tree = ast.parse(base_path.read_text(encoding="utf-8"), filename=str(base_path))
    func_node = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "get_list_from_env"
    )
    module = ast.Module(body=[func_node], type_ignores=[])
    if hasattr(ast, "fix_missing_locations"):
        module = ast.fix_missing_locations(module)
    ns: dict = {"os": os, "json": json}
    exec(compile(module, str(base_path), "exec"), ns)  # noqa: S102 — 测源码函数本身
    return ns["get_list_from_env"]


@pytest.fixture(scope="module")
def get_list_from_env():
    return _load_get_list_from_env()


class TestGetListFromEnvEmptyFallback:
    def test_unset_uses_default_empty_list(self, get_list_from_env):
        os.environ.pop("LOG_MASKED_PATTERNS", None)
        assert get_list_from_env("LOG_MASKED_PATTERNS") == []

    def test_empty_string_equals_default(self, get_list_from_env):
        """看守用例：已设置空串不得崩溃，等价 []。"""
        os.environ["LOG_MASKED_PATTERNS"] = ""
        assert get_list_from_env("LOG_MASKED_PATTERNS") == []

    def test_whitespace_string_equals_default(self, get_list_from_env):
        os.environ["LOG_MASKED_PATTERNS"] = "   "
        assert get_list_from_env("LOG_MASKED_PATTERNS") == []

    def test_valid_json_array_parsed(self, get_list_from_env):
        os.environ["LOG_MASKED_PATTERNS"] = json.dumps([r"\d+", "secret"])
        assert get_list_from_env("LOG_MASKED_PATTERNS") == [r"\d+", "secret"]

    def test_invalid_json_still_raises(self, get_list_from_env):
        os.environ["LOG_MASKED_PATTERNS"] = "not-json"
        with pytest.raises(ValueError, match="Invalid JSON format"):
            get_list_from_env("LOG_MASKED_PATTERNS")

    def test_custom_default_when_empty(self, get_list_from_env):
        os.environ["LOG_MASKED_SENS_WORDS"] = ""
        assert get_list_from_env("LOG_MASKED_SENS_WORDS", default='["a"]') == ["a"]
