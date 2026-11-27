#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""workflow_constant 配置加载逻辑单元测试。

覆盖：默认配置加载、自定义文件名、非法路径回落、非 mapping 顶层回落、
非法正整数回落、type_default_value_dict 值类型校验与部分覆盖。
"""

import importlib
import os
from pathlib import Path

import pytest

import jiuwen.orchestration.flow.constant as _constant

# resource 目录与 constant.py 的相对解析保持一致（jiuwen/resource）
_RESOURCE_DIR = Path(_constant.__file__).resolve().parents[2] / "resource"


def _reload_constant(monkeypatch, env=None):
    """以给定环境变量重载 constant 模块，返回重载后的模块对象。"""
    monkeypatch.delenv("WORKFLOW_CONSTANT_YAML", raising=False)
    if env:
        monkeypatch.setenv("WORKFLOW_CONSTANT_YAML", env)
    import jiuwen.orchestration.flow.constant as constant_module
    return importlib.reload(constant_module)


@pytest.fixture(autouse=True)
def _restore_constant():
    """每个用例结束后重载一次模块，恢复默认环境，避免污染后续测试。"""
    yield
    os.environ.pop("WORKFLOW_CONSTANT_YAML", None)
    import jiuwen.orchestration.flow.constant as constant_module
    importlib.reload(constant_module)


class TestResolveConfigFilename:
    @staticmethod
    def test_default_loads_packaged_yaml(monkeypatch):
        module = _reload_constant(monkeypatch)
        assert (_RESOURCE_DIR / "workflow_constant.yaml").exists()
        # 默认 yaml 已打包且可加载：至少能读到四个超时键
        assert module.TASK_EXECUTE_TIMEOUT > 0

    @staticmethod
    def test_custom_filename_used(monkeypatch):
        # 自定义文件名：写入 resource 目录后通过环境变量切换加载
        target = _RESOURCE_DIR / "workflow_constant_custom.yaml"
        target.write_text("task_execute_timeout: 1234\n", encoding="utf-8")
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_custom.yaml")
            assert module.TASK_EXECUTE_TIMEOUT == 1234
        finally:
            target.unlink(missing_ok=True)

    @pytest.mark.parametrize(
        "bad_value",
        ["../secret.yaml", "/etc/passwd", "C:\\win.ini", "", "..", "."],
    )
    @staticmethod
    def test_unsafe_filename_falls_back(monkeypatch, bad_value):
        # 非法值回落默认文件：加载结果与不设环境变量一致
        module = _reload_constant(monkeypatch, env=bad_value)
        default_module = _reload_constant(monkeypatch)
        assert module.CONFIG_PATH == default_module.CONFIG_PATH


class TestLoadWorkflowConstant:
    @staticmethod
    def test_non_mapping_toplevel_falls_back(monkeypatch):
        # 顶层为 list 的非法 yaml：回落空配置（所有键走内置默认），不崩溃
        target = _RESOURCE_DIR / "workflow_constant_bad_list.yaml"
        target.write_text("- a\n- b\n", encoding="utf-8")
        try:
            module = _reload_constant(
                monkeypatch, env="workflow_constant_bad_list.yaml"
            )
            assert module.workflow_constant == {}
            assert module.TASK_EXECUTE_TIMEOUT == 300
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def test_scalar_toplevel_falls_back(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_bad_scalar.yaml"
        target.write_text("just_a_string\n", encoding="utf-8")
        try:
            module = _reload_constant(
                monkeypatch, env="workflow_constant_bad_scalar.yaml"
            )
            assert module.workflow_constant == {}
        finally:
            target.unlink(missing_ok=True)


class TestLoadPositiveInt:
    @staticmethod
    def test_string_numeric_tolerated(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_str_num.yaml"
        target.write_text('task_execute_timeout: "900"\n', encoding="utf-8")
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_str_num.yaml")
            assert module.TASK_EXECUTE_TIMEOUT == 900
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def test_invalid_falls_back_to_builtin(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_bad_int.yaml"
        target.write_text("task_execute_timeout: abc\n", encoding="utf-8")
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_bad_int.yaml")
            # 非法值回落内置默认
            assert module.TASK_EXECUTE_TIMEOUT == 300
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def test_non_positive_falls_back(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_zero.yaml"
        target.write_text("task_execute_timeout: 0\n", encoding="utf-8")
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_zero.yaml")
            assert module.TASK_EXECUTE_TIMEOUT == 300
        finally:
            target.unlink(missing_ok=True)


class TestTypeDefaultValueOverrides:
    @staticmethod
    def test_partial_override_keeps_other_defaults(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_partial.yaml"
        target.write_text(
            "type_default_value_dict:\n  integer: 7\n", encoding="utf-8"
        )
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_partial.yaml")
            assert module.TYPE_DEFAULT_VALUE_DICT["integer"] == 7
            # 未覆盖的键保留内置默认
            assert module.TYPE_DEFAULT_VALUE_DICT["string"] == ""
            assert module.TYPE_DEFAULT_VALUE_DICT["boolean"] is None
            assert module.TYPE_DEFAULT_VALUE_DICT["array"] is None
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def test_invalid_value_type_keeps_builtin(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_bad_type.yaml"
        target.write_text(
            "type_default_value_dict:\n"
            "  string: 123\n"
            "  integer: abc\n"
            "  boolean: 1\n"
            "  array: []\n",
            encoding="utf-8",
        )
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_bad_type.yaml")
            # 全部非法类型：保留内置默认
            assert module.TYPE_DEFAULT_VALUE_DICT["string"] == ""
            assert module.TYPE_DEFAULT_VALUE_DICT["integer"] is None
            assert module.TYPE_DEFAULT_VALUE_DICT["boolean"] is None
            assert module.TYPE_DEFAULT_VALUE_DICT["array"] is None
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def test_unknown_key_ignored(monkeypatch):
        target = _RESOURCE_DIR / "workflow_constant_unknown_key.yaml"
        target.write_text(
            "type_default_value_dict:\n  unknown_key: 1\n", encoding="utf-8"
        )
        try:
            module = _reload_constant(monkeypatch, env="workflow_constant_unknown_key.yaml")
            assert "unknown_key" not in module.TYPE_DEFAULT_VALUE_DICT
            assert module.TYPE_DEFAULT_VALUE_DICT["integer"] is None
        finally:
            target.unlink(missing_ok=True)


class TestExtensionFlowInputDefaults:
    @staticmethod
    def test_extension_uses_same_defaults(monkeypatch):
        # extension 侧 TYPE_DEFAULT_VALUE_DICT 与 orchestration 侧共享配置
        module = _reload_constant(monkeypatch)
        import jiuwen.extension.workflow_node.flow_input as flow_input_module
        importlib.reload(flow_input_module)
        assert (
            flow_input_module.TYPE_DEFAULT_VALUE_DICT["integer"]
            == module.TYPE_DEFAULT_VALUE_DICT["integer"]
        )
        assert (
            flow_input_module.TYPE_DEFAULT_VALUE_DICT["number"]
            == module.TYPE_DEFAULT_VALUE_DICT["number"]
        )
        # 容器语义保留 extension 侧既有行为
        assert flow_input_module.TYPE_DEFAULT_VALUE_DICT["array"] == []
        assert flow_input_module.TYPE_DEFAULT_VALUE_DICT["object"] == {}
        importlib.reload(flow_input_module)
