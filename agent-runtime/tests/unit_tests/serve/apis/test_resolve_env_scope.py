# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for app_run._resolve_env_scope — 直连 runtime 的 environment_id / workspace_id 兜底.

本机 Python 测试环境缺 SpiffWorkflow（jiuwen.orchestration.flow.state 导入失败），导致
``agent_runtime.serve.apis.app_run`` 整个模块无法 import。为独立测试 ``_resolve_env_scope``，
采用 AST 提取函数源码 + 隔离命名空间 exec（参考 test_web_run.py 的 stub 思路与
experience: ast.get_source_segment + exec），注入其引用的名字：
``load_default_environment_id``、``async_ir_load``、``workflow_logger``、``Optional``。

同时本机未安装 pytest-asyncio，故用例以普通函数 + asyncio.run 运行，不依赖该插件。
"""

import asyncio
import ast
import logging
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, patch

_APP_RUN_PATH = (
    Path(__file__).resolve().parents[4] / "agent_runtime" / "serve" / "apis" / "app_run.py"
)


def _extract_resolve_env_scope():
    """从 app_run.py 提取 _resolve_env_scope 函数源码并在隔离命名空间 exec."""
    source = _APP_RUN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_resolve_env_scope":
            fn = node
            break
    assert fn is not None, "_resolve_env_scope not found in app_run.py"
    code = ast.get_source_segment(source, fn)
    namespace = {
        "Optional": Optional,
        "workflow_logger": logging.getLogger("test_resolve_env_scope"),
    }
    exec(code, namespace)
    fn = namespace.get("_resolve_env_scope")
    assert fn is not None, "_resolve_env_scope was not defined by exec"
    return fn


_resolve_env_scope = _extract_resolve_env_scope()


class TestResolveEnvScope:
    """environment_id / workspace_id 兜底逻辑测试."""

    @staticmethod
    def test_env_id_passed_skips_default_load_and_ws_passed_skips_ir():
        """environment_id 与 workspace_id 均已传 -> 既不读默认环境也不加载 IR."""
        load_default = AsyncMock(return_value="default-env")
        ir_load = AsyncMock(return_value={"metadata": {"workspaceId": "ir-ws"}})
        with (
            patch.dict(_resolve_env_scope.__globals__, {
                "load_default_environment_id": load_default,
                "async_ir_load": ir_load,
            }),
        ):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", "env-given", "ws-given", "ir/path.json")
            )
        assert env_id == "env-given"
        assert ws_id == "ws-given"
        load_default.assert_not_awaited()
        ir_load.assert_not_awaited()

    @staticmethod
    def test_env_id_missing_loads_default_environment_id():
        """environment_id 未传 -> 调 load_default_environment_id 且用其结果."""
        load_default = AsyncMock(return_value="default-env")
        ir_load = AsyncMock(return_value={"metadata": {"workspaceId": "ir-ws"}})
        with (
            patch.dict(_resolve_env_scope.__globals__, {
                "load_default_environment_id": load_default,
                "async_ir_load": ir_load,
            }),
        ):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", None, "ws-given", "ir/path.json")
            )
        assert env_id == "default-env"
        load_default.assert_awaited_once_with("proj-1")
        # workspace 已传，不触发 IR 加载
        ir_load.assert_not_awaited()

    @staticmethod
    def test_ws_id_passed_skips_ir_load():
        """workspace_id 已传 -> 不加载 IR."""
        ir_load = AsyncMock(side_effect=AssertionError("ir should not load"))
        with patch.dict(_resolve_env_scope.__globals__, {"async_ir_load": ir_load}):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", "env-x", "ws-given", "ir/path.json")
            )
        assert ws_id == "ws-given"
        assert env_id == "env-x"

    @staticmethod
    def test_ws_id_missing_reads_from_ir_metadata():
        """workspace_id 未传 -> 从 IR metadata.workspaceId 取值."""
        ir_load = AsyncMock(return_value={"metadata": {"workspaceId": "ir-ws"}})
        with patch.dict(_resolve_env_scope.__globals__, {"async_ir_load": ir_load}):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", "env-x", None, "ir/path.json")
            )
        assert ws_id == "ir-ws"
        ir_load.assert_awaited_once_with("ir/path.json")

    @staticmethod
    def test_ws_id_missing_str_convert_from_ir_metadata():
        """IR metadata.workspaceId 非字符串 -> str() 转换后返回."""
        ir_load = AsyncMock(return_value={"metadata": {"workspaceId": 12345}})
        with patch.dict(_resolve_env_scope.__globals__, {"async_ir_load": ir_load}):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", "env-x", None, "ir/path.json")
            )
        assert ws_id == "12345"

    @staticmethod
    def test_ir_load_failure_keeps_workspace_unchanged():
        """IR 加载失败 -> workspace_id 保持原值（None），异常被捕获记录日志."""
        ir_load = AsyncMock(side_effect=Exception("ir down"))
        with patch.dict(_resolve_env_scope.__globals__, {"async_ir_load": ir_load}):
            env_id, ws_id = asyncio.run(
                _resolve_env_scope("proj-1", "env-x", None, "ir/path.json")
            )
        assert env_id == "env-x"
        assert ws_id is None


class TestWebEntryDoesNotResolveEnv:
    """网页入口不回填环境作用域（安全边界回归保护）.

    网页入口无鉴权、workspace_id 来自请求参数不可信。environment_id 是否注入必须由
    manager 决定（controller/多智能体等 manager 故意不注入的场景，runtime 不得按请求
    workspace 拼接默认环境回填），否则会用攻击者指定的 workspace 加载其它空间变量。
    因此 run_web_workflow / run_web_agent 调用共享执行函数时必须显式传 resolve_env=False。
    """

    _WEB_RUN_PATH = (
        Path(__file__).resolve().parents[4] / "agent_runtime" / "serve" / "apis" / "web_run.py"
    )

    @staticmethod
    def _calls_to_execute_functions():
        """从 web_run.py 提取对 _execute_workflow_run / _execute_agent_run 的调用."""
        source = TestWebEntryDoesNotResolveEnv._WEB_RUN_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in ("_execute_workflow_run", "_execute_agent_run"):
                    calls.append((fn.id, node.keywords))
        return calls

    @staticmethod
    def test_web_entry_passes_resolve_env_false():
        """网页入口调用 _execute_*_run 时必须带 resolve_env=False."""
        calls = TestWebEntryDoesNotResolveEnv._calls_to_execute_functions()
        assert calls, "no _execute_*_run calls found in web_run.py"
        for fn_name, keywords in calls:
            resolve_env_kw = [k for k in keywords if k.arg == "resolve_env"]
            assert resolve_env_kw, (
                f"{fn_name} called without resolve_env keyword in web_run.py; "
                "web entry must not resolve default env with untrusted request workspace"
            )
            assert resolve_env_kw[0].value.value is False, (
                f"{fn_name} called with resolve_env=True in web_run.py; "
                "web entry must not resolve default env with untrusted request workspace"
            )

