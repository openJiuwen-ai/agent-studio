# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Start 用户字段默认值注入/提取的类型归一测试(runner + handler)。

背景(2026-09-14 bug 修复):328d4923(fix:end节点未输出空字符串)把 Start
userFields.inputs 的 default_value 原样注入 _request/global_variables,
object/array 等非 string 字段的空默认 '' 让 Start 输出过不了 openjiuwen
IR 输出校验(json.loads('')/int('') 失败,报 Incorrect type for key)。

修复(需求确认):所有类型字段都注入默认值,注入前按声明类型归一——空默认
转合法类型值(object -> {},array -> [],integer -> 0 等),避免 '' 触发
Start 输出 IR 校验失败。

runner/handler 模块的 import 链依赖 SpiffWorkflow(bpmn_process_spec 大小写
与安装版本不一致),故沿用 test_workflow_handler_interrupt_resume.py 的
AST 提取源码模式:从源文件提取方法本体,在注入 convert_user_field_default
的命名空间执行,锁定"全部类型注入 + 空默认类型归一"的注入行为。
"""
# pylint: disable=protected-access

import ast
import os
import textwrap

import pytest

from jiuwen.extension.workflow_node.start import Start

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_RUNNER_PATH = os.path.join(
    _REPO_ROOT,
    "agent-runtime",
    "agent_runtime",
    "runner",
    "workflow_runner.py",
)
_HANDLER_PATH = os.path.join(
    _REPO_ROOT,
    "agent-runtime",
    "jiuwen",
    "controller",
    "task_executor",
    "handler",
    "workflow_handler.py",
)


def _extract_method_source(filepath, method_name):
    """从 Python 源文件提取指定方法的源码文本(与既有测试同款)。"""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return ast.get_source_segment(source, node)
    return None


def _bind_method(filepath, method_name, globals_):
    """提取方法源码并在给定命名空间执行,返回可调用函数。"""
    source = _extract_method_source(filepath, method_name)
    if source is None:
        raise RuntimeError(f"无法从源文件提取 {method_name}")
    ns = dict(globals_)
    exec(compile(textwrap.dedent(source), filepath, "exec"), ns)  # noqa: S102
    return ns[method_name]


# 提取真实方法并绑定依赖(提取的源码以 Start.convert_user_field_default
# 引用转换逻辑,命名空间需注入 Start 类)
_extract_defaults = _bind_method(
    _RUNNER_PATH,
    "_extract_start_user_field_defaults",
    {"Start": Start},
)
_inject_defaults = _bind_method(
    _HANDLER_PATH,
    "_inject_start_field_defaults",
    {"Start": Start},
)


def _ir_with_start_fields(fields, comp_type="jiuwen.start"):
    """构造最小 IR:一个 Start 组件,userFields.inputs 为给定字段列表。"""
    return {
        "components": [
            {
                "type": comp_type,
                "configs": {"userFields": {"inputs": fields, "outputs": []}},
            }
        ]
    }


def _field(field_id, field_type, default_value="", schema=None):
    field = {"id": field_id, "type": field_type, "default_value": default_value}
    if schema is not None:
        field["schema"] = schema
    return field


_OBJ_SCHEMA = [{"id": "id", "type": "string"}, {"id": "ot", "type": "string"}]


class TestExtractStartUserFieldDefaults:
    """_extract_start_user_field_defaults — 全部类型字段进入 defaults。"""

    @staticmethod
    def test_all_types_extracted_with_normalized_defaults():
        """string/object/array/integer/boolean 字段都提取,空默认归一为类型值。"""
        ir = _ir_with_start_fields(
            [
                _field("name", "string", ""),
                _field("age", "string", "张三"),
                _field("obj", "object", "", _OBJ_SCHEMA),
                _field("obj_filled", "object", '{"a": 1}'),
                _field("arr", "array", ""),
                _field("count", "integer", "30"),
                _field("flag", "boolean", "false"),
            ]
        )
        assert _extract_defaults(ir) == {
            "name": "",
            "age": "张三",
            "obj": {"id": "", "ot": ""},
            "obj_filled": {"a": 1},
            "arr": [],
            "count": 30,
            "flag": False,
        }

    @staticmethod
    def test_no_start_component_returns_empty():
        assert _extract_defaults({"components": [{"type": "jiuwen.llm"}]}) == {}

    @staticmethod
    def test_no_components_returns_empty():
        assert _extract_defaults({}) == {}

    @staticmethod
    def test_null_default_normalized():
        """string 字段 default_value 为 null → 注入空串;object 为 null → 按 schema 填充。"""
        ir = _ir_with_start_fields(
            [
                {"id": "name", "type": "string", "default_value": None},
                {
                    "id": "obj",
                    "type": "object",
                    "default_value": None,
                    "schema": _OBJ_SCHEMA,
                },
            ]
        )
        assert _extract_defaults(ir) == {"name": "", "obj": {"id": "", "ot": ""}}

    @staticmethod
    def test_duplicate_ids_deduplicated():
        ir = _ir_with_start_fields(
            [
                _field("name", "string", "first"),
                _field("name", "string", "second"),
            ]
        )
        assert _extract_defaults(ir) == {"name": "first"}


class TestInjectStartFieldDefaults:
    """_inject_start_field_defaults — 全部类型默认注入 global_variables。"""

    @staticmethod
    def _make_context(ir):
        class _Ctx:
            def __init__(self, ir_json):
                self.workflow_ir = ir_json

        return _Ctx(ir)

    @staticmethod
    def test_injects_all_types_defaults():
        ir = _ir_with_start_fields(
            [
                _field("name", "string", ""),
                _field("obj", "object", "", _OBJ_SCHEMA),
                _field("obj_filled", "object", '{"a": 1}'),
                _field("count", "integer", "30"),
            ]
        )
        params = {"global_variables": {"query": "hi"}}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(ir))
        assert params["global_variables"] == {
            "query": "hi",
            "name": "",
            "obj": {"id": "", "ot": ""},
            "obj_filled": {"a": 1},
            "count": 30,
        }

    @staticmethod
    def test_does_not_override_existing_value():
        ir = _ir_with_start_fields([_field("name", "string", "default")])
        params = {"global_variables": {"name": "real"}}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(ir))
        assert params["global_variables"] == {"name": "real"}

    @staticmethod
    def test_null_existing_value_gets_default():
        ir = _ir_with_start_fields([_field("name", "string", "default")])
        params = {"global_variables": {"name": None}}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(ir))
        assert params["global_variables"] == {"name": "default"}

    @staticmethod
    def test_no_ir_returns_without_changes():
        params = {"global_variables": {"query": "hi"}}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(None))
        assert params == {"global_variables": {"query": "hi"}}

    @staticmethod
    def test_no_start_component_no_change():
        ir = _ir_with_start_fields([], comp_type="jiuwen.llm")
        params = {}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(ir))
        assert params == {}

    @staticmethod
    def test_empty_string_default_still_injected():
        """object 空默认注入填充后的子字段值(而非跳过),保证 End 仍能输出字段。"""
        ir = _ir_with_start_fields([_field("obj", "object", "", _OBJ_SCHEMA)])
        params = {"global_variables": {"query": "hi"}}
        _inject_defaults(params, TestInjectStartFieldDefaults._make_context(ir))
        assert params["global_variables"] == {"query": "hi", "obj": {"id": "", "ot": ""}}
