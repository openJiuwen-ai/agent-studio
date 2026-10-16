# coding: utf-8
"""load_components / _load_single_component 单元测试。

覆盖修改点 A30-A35：
- A30: load_components() 路径自动推导（__file__ 三层 dirname）
- A31: load_components() 目录不存在时 log+return
- A32: _load_single_component() 单插件失败不中断
- A33: _load_single_component() .. 路径遍历检查
- A34: _load_single_component() 绝对路径检查
- A35: _load_single_component() 模块名含目录前缀
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# model_service 是 monorepo 本地包，在测试环境中可能未安装，预注入 mock 避免导入链断裂
for _mod_name in ("model_service", "model_service.env_resolver"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

from jiuwen.common.init import load_components, _load_single_component
from jiuwen.common.exception.base import JiuWenBaseException


# --------------------------------------------------------------------------- #
# A30: load_components() 路径自动推导
# --------------------------------------------------------------------------- #

@patch("jiuwen.common.init.os.path.isdir", return_value=False)
def test_load_components_auto_derive_path(mock_isdir):
    """A30: 无 extension_path 参数时从 __file__ 推导。"""
    load_components()  # No extension_path
    called_path = mock_isdir.call_args[0][0]
    assert "extensions" in called_path
    assert "components" in called_path


# --------------------------------------------------------------------------- #
# A31: load_components() 目录不存在时 log+return
# --------------------------------------------------------------------------- #

@patch("jiuwen.common.init.os.path.isdir", return_value=False)
def test_load_components_dir_not_exist(mock_isdir):
    """A31: 目录不存在时 log info + return。"""
    result = load_components(extension_path="/nonexistent/path")
    assert result is None


# --------------------------------------------------------------------------- #
# A32: _load_single_component() 单插件失败不中断
# --------------------------------------------------------------------------- #

@patch("jiuwen.common.init._load_single_component")
@patch("jiuwen.common.init.os.path.isdir", return_value=True)
@patch("jiuwen.common.init.os.listdir", return_value=["good_plugin", "bad_plugin"])
def test_load_single_plugin_failure_skipped(mock_listdir, mock_isdir, mock_load):
    """A32: 一个插件加载失败不影响其他插件。"""
    call_count = {"good": 0, "bad": 0}

    def _side_effect(extension_path, folder_path):
        if "bad_plugin" in folder_path:
            call_count["bad"] += 1
            raise RuntimeError("load error")
        call_count["good"] += 1

    mock_load.side_effect = _side_effect

    # Should not raise even though bad_plugin fails
    load_components(extension_path="/test")

    assert call_count["good"] == 1
    assert call_count["bad"] == 1
    assert mock_load.call_count == 2


# --------------------------------------------------------------------------- #
# A33: _load_single_component() .. 路径遍历检查
# --------------------------------------------------------------------------- #

def test_path_traversal_in_file_path(tmp_path):
    """A33: filePath 含 .. → 抛异常。"""
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()
    json_data = {
        "type": "custom.test",
        "classInfo": {
            "className": "TestClass",
            "filePath": "../escape.py",
        },
    }
    (plugin_dir / "component.json").write_text(json.dumps(json_data))

    with pytest.raises(JiuWenBaseException, match="(?i)path traversal"):
        _load_single_component(str(tmp_path), str(plugin_dir))


# --------------------------------------------------------------------------- #
# A34: _load_single_component() 绝对路径检查
# --------------------------------------------------------------------------- #

def test_absolute_file_path_rejected(tmp_path):
    """A34: filePath 为绝对路径 → 抛异常。"""
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()
    abs_path = os.path.join(os.path.abspath(os.sep), "evil", "plugin.py")
    json_data = {
        "type": "custom.test",
        "classInfo": {
            "className": "TestClass",
            "filePath": abs_path,
        },
    }
    (plugin_dir / "component.json").write_text(json.dumps(json_data))

    with pytest.raises(JiuWenBaseException, match="(?i)absolute"):
        _load_single_component(str(tmp_path), str(plugin_dir))


# --------------------------------------------------------------------------- #
# A35: _load_single_component() 模块名含目录前缀
# --------------------------------------------------------------------------- #

@patch("jiuwen.common.init.component_class_pool")
def test_module_name_includes_folder(mock_pool, tmp_path):
    """A35: module_name 包含目录名前缀。"""
    folder_name = "my_plugin"
    py_filename = "plugin.py"
    file_path_str = f"extensions/components/{folder_name}/{py_filename}"

    plugin_dir = tmp_path / "extensions" / "components" / folder_name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "component.json").write_text(json.dumps({
        "type": "custom.test",
        "classInfo": {"className": "TestClass", "filePath": file_path_str},
    }))
    (plugin_dir / py_filename).write_text(
        "from jiuwen.extension.wrapper.plugin_base import PluginBase\n"
        "class TestClass(PluginBase):\n"
        "    async def invoke(self, inputs, **kwargs):\n"
        "        pass\n"
    )

    _load_single_component(str(tmp_path), str(plugin_dir))

    expected_module = f"custom_plugin_{folder_name}_{os.path.splitext(py_filename)[0]}"
    assert expected_module in sys.modules
    mock_pool.register_component_class.assert_called_once()


# --------------------------------------------------------------------------- #
# S1: _load_single_component() 显式读取 component.json
# --------------------------------------------------------------------------- #

def test_missing_component_json_raises(tmp_path):
    """S1: 目录下有其他 .json 但没有 component.json → 抛异常。"""
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "other.json").write_text(json.dumps({"type": "x"}))

    with pytest.raises(JiuWenBaseException, match="(?i)missing component.json"):
        _load_single_component(str(tmp_path), str(plugin_dir))


# --------------------------------------------------------------------------- #
# S1: _load_single_component() 拒绝未继承 PluginBase 的类
# --------------------------------------------------------------------------- #

@patch("jiuwen.common.init.component_class_pool")
def test_non_pluginbase_class_rejected(mock_pool, tmp_path):
    """S1: 类未继承 PluginBase → 抛异常。"""
    folder_name = "bad_plugin"
    file_path_str = f"extensions/components/{folder_name}/plugin.py"

    plugin_dir = tmp_path / "extensions" / "components" / folder_name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "component.json").write_text(json.dumps({
        "type": "custom.bad",
        "classInfo": {"className": "BadClass", "filePath": file_path_str},
    }))
    (plugin_dir / "plugin.py").write_text("class BadClass:\n    pass\n")

    with pytest.raises(JiuWenBaseException, match="(?i)does not inherit from PluginBase"):
        _load_single_component(str(tmp_path), str(plugin_dir))
    mock_pool.register_component_class.assert_not_called()
