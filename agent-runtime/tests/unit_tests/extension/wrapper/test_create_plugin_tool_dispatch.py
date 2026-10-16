# coding: utf-8
# pylint: disable=protected-access
"""委托/映射/IR分流单元测试。

覆盖修改点 A36-A39：
- A36: load_restful_api_from_ir() 委托 create_plugin_tool()
- A37: _DEBUG_EVENT_RETURN_TO_SERVICE["FlowCustomApi"] == "Api"
- A38: ir_converter callMode=="custom" → FlowCustomApi
- A39: ir_converter callMode 缺省 → FlowApi（向后兼容）
"""

import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest

# model_service 是 monorepo 本地包，在测试环境中可能未安装，预注入 mock 避免导入链断裂
for _mod_name in ("model_service", "model_service.env_resolver"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

from jiuwen.extension.wrapper.restful_api_loader import load_restful_api_from_ir
from jiuwen.extension.wrapper.workflow_wrapper import _DEBUG_EVENT_RETURN_TO_SERVICE
from jiuwen.extension.workflow_node.flow_custom_api import FlowCustomApi
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.serve.controllers.execution.ir_converter import IRConverter


# --------------------------------------------------------------------------- #
# A36: load_restful_api_from_ir() 委托 create_plugin_tool()
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.create_plugin_tool")
def test_load_restful_api_delegates_to_create_plugin_tool(mock_create):
    """A36: load_restful_api_from_ir 委托 create_plugin_tool。"""
    ir_data = {"name": "test", "callMode": "custom"}
    mock_create.return_value = "tool-id-123"

    result = load_restful_api_from_ir(ir_data, tag="agent-1")

    mock_create.assert_called_once_with(ir_data, tag="agent-1")
    assert result == "tool-id-123"


# --------------------------------------------------------------------------- #
# A37: _DEBUG_EVENT_RETURN_TO_SERVICE["FlowCustomApi"] == "Api"
# --------------------------------------------------------------------------- #

def test_workflow_wrapper_flow_custom_api_mapping():
    """A37: _DEBUG_EVENT_RETURN_TO_SERVICE["FlowCustomApi"] == "Api"。"""
    assert "FlowCustomApi" in _DEBUG_EVENT_RETURN_TO_SERVICE
    assert _DEBUG_EVENT_RETURN_TO_SERVICE["FlowCustomApi"] == "Api"
    # 确保和 FlowApi 映射一致
    assert _DEBUG_EVENT_RETURN_TO_SERVICE["FlowApi"] == "Api"


# --------------------------------------------------------------------------- #
# A38: ir_converter callMode=="custom" → FlowCustomApi
# --------------------------------------------------------------------------- #

@patch("jiuwen.serve.controllers.execution.ir_converter.FlowCustomApi")
def test_ir_converter_custom_dispatches_flow_custom_api(mock_flow_custom_api):
    """A38: callMode=="custom" → 返回 FlowCustomApi 实例。"""
    mock_instance = MagicMock()
    mock_flow_custom_api.return_value = mock_instance

    node = {
        "id": "node-1",
        "name": "test_custom",
        "type": "jiuwen.api",
        "configs": {"callMode": "custom", "name": "test_custom"},
    }
    result = asyncio.run(IRConverter._create_component(node, None))

    mock_flow_custom_api.assert_called_once()
    assert result[0] is mock_instance
    assert result[1] == "jiuwen.api"


# --------------------------------------------------------------------------- #
# A39: ir_converter callMode 缺省 → FlowApi（向后兼容）
# --------------------------------------------------------------------------- #

@patch("jiuwen.serve.controllers.execution.ir_converter.FlowApi")
def test_ir_converter_api_dispatches_flow_api(mock_flow_api):
    """A39: callMode 缺省 → 返回 FlowApi 实例。"""
    mock_instance = MagicMock()
    mock_flow_api.return_value = mock_instance

    node = {
        "id": "node-2",
        "name": "test_api",
        "type": "jiuwen.api",
        "configs": {"name": "test_api"},
    }
    result = asyncio.run(IRConverter._create_component(node, None))

    mock_flow_api.assert_called_once()
    assert result[0] is mock_instance
    assert result[1] == "jiuwen.api"
