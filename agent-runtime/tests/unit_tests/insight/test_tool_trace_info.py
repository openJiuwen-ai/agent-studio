# -*- coding: UTF-8 -*-
"""工具标识 OTel 扁平键单测（issue #1583 第 6 节）。

extract_tool_trace_info 为纯函数，直接行为测试；handlers 与五处插件
tracer 构造点的接线（module import 链穿透 psycopg2 / SpiffWorkflow 等
单测环境缺失依赖）以 AST 契约锁定：透传或合并调用被删时此处失败，
防止行为用例全绿但接线静默丢失。
"""

import ast
import os

from jiuwen.insight.utils import extract_tool_trace_info

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _load_tree(rel_path):
    with open(os.path.join(_REPO_ROOT, rel_path), encoding="utf-8") as f:
        return ast.parse(f.read())


def _method_of(tree, class_name, method_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        return item
    return None


def _call_names(method, attr):
    """collect every ast.Call whose func attribute name matches."""
    return [
        call
        for call in ast.walk(method)
        if isinstance(call, ast.Call) and getattr(call.func, "attr", None) == attr
    ]


class TestExtractToolTraceInfo:
    @staticmethod
    def test_pops_and_str_coerces():
        kwargs = {"tool_call_id": "call_9", "tool_type": "mcp", "trace_handlers": []}
        info = extract_tool_trace_info(kwargs)

        assert info == {"tool_call_id": "call_9", "tool_type": "mcp"}
        assert "tool_call_id" not in kwargs
        assert "tool_type" not in kwargs
        assert "trace_handlers" in kwargs  # 非遥测键不受影响

    @staticmethod
    def test_empty_values_popped_but_not_produced():
        kwargs = {"tool_call_id": "", "tool_type": None}
        assert extract_tool_trace_info(kwargs) == {}
        assert kwargs == {}  # 空值也摘出，不残留进工具运行时入参

    @staticmethod
    def test_absent_keys_noop():
        assert extract_tool_trace_info({"other": 1}) == {}


class TestHandlerToolFactsWiring:
    """task_executor handlers 把 planner tool_call 标识透传进 ainvoke kwargs。"""

    @staticmethod
    def _ainvoke_call(rel_path, class_name, method_name, callee_attr):
        tree = _load_tree(rel_path)
        method = _method_of(tree, class_name, method_name)
        assert method is not None, f"{class_name}.{method_name} 缺失"
        calls = _call_names(method, callee_attr)
        assert calls, f"{class_name}.{method_name} 不再调用 {callee_attr}"
        return calls[0]

    def test_plugin_handler_passes_tool_facts(self):
        call = self._ainvoke_call(
            "jiuwen/controller/task_executor/handler/plugin_handler.py",
            "PluginHandler",
            "execute_plugin_from_function_call",
            "ainvoke",
        )
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert "tool_call_id" in keywords, "plugin.ainvoke 未透传 tool_call_id"
        assert "tool_type" in keywords, "plugin.ainvoke 未透传 tool_type"

    def test_mcp_handler_passes_tool_facts(self):
        call = self._ainvoke_call(
            "jiuwen/controller/task_executor/handler/mcp_handler.py",
            "McpHandler",
            "execute_mcp_from_function_call",
            "ainvoke",
        )
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert "tool_call_id" in keywords, "mcp.ainvoke 未透传 tool_call_id"
        assert "tool_type" in keywords, "mcp.ainvoke 未透传 tool_type"


class TestPluginTracerWiring:
    """五处插件 tracer 构造点把工具标识并入 instance_info 扁平键。"""

    @staticmethod
    def _assert_extract_call(method, where):
        for node in ast.walk(method):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "extract_tool_trace_info"
            ):
                return
        raise AssertionError(f"{where} 不再合并 extract_tool_trace_info")

    def test_tracer_manager_merges_tool_facts(self):
        cases = [
            ("jiuwen/extension/wrapper/mcp_tool_wrapper.py", "McpToolWrapper",
             "_create_tracer_manager"),
            ("jiuwen/extension/wrapper/restful_api_new.py", "RestfulApiToolNew",
             "_create_tracer_manager"),
            ("jiuwen/plugin/models/restfulapi.py", "RestFulAPI",
             "_create_tracer_manager"),
        ]
        for rel_path, cls, method_name in cases:
            method = _method_of(_load_tree(rel_path), cls, method_name)
            assert method is not None, f"{cls}.{method_name} 缺失"
            self._assert_extract_call(method, f"{rel_path}::{cls}.{method_name}")

    def test_direct_generate_manager_sites_merge_tool_facts(self):
        tree = _load_tree("jiuwen/plugin/models/function.py")
        ainvoke = _method_of(tree, "Function", "ainvoke")
        assert ainvoke is not None, "Function.ainvoke 缺失"
        self._assert_extract_call(ainvoke, "function.py::Function.ainvoke")

        tree = _load_tree("jiuwen/plugin/models/mcpapi.py")
        merges = 0
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "extract_tool_trace_info"
            ):
                merges += 1
        assert merges == 2, f"mcpapi.py 应有 2 处合并点，实际 {merges}"

    def test_mcp_runtime_kwargs_excludes_tool_facts(self):
        """遥测键不得泄入 MCP 工具运行时入参（JIUWEN_RUNTIME_KWARGS）。"""
        tree = _load_tree("jiuwen/extension/wrapper/mcp_tool_wrapper.py")
        excluded = set()
        for node in ast.walk(tree):
            # 找 `k not in (...)` 形态的排除元组，收集其字符串常量
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.ops[0], ast.NotIn)
                and isinstance(node.comparators[0], ast.Tuple)
            ):
                excluded.update(
                    elt.value
                    for elt in node.comparators[0].elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                )
        assert "tool_call_id" in excluded, "JIUWEN_RUNTIME_KWARGS 未排除 tool_call_id"
        assert "tool_type" in excluded, "JIUWEN_RUNTIME_KWARGS 未排除 tool_type"
