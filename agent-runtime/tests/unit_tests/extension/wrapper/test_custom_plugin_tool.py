# coding: utf-8
# pylint: disable=protected-access
"""CustomPluginTool / CustomPluginCard / convert_ir_to_custom_card / create_plugin_tool 单元测试。

覆盖修改点 A5-A18：
- A5:  CustomPluginCard 字段定义
- A6:  CustomPluginTool.__init__ — component_type 空值校验
- A7:  CustomPluginTool.__init__ — 通过 ComponentClassPool 创建插件实例
- A8:  ainvoke() — 成功结果包装 {"data":result,"errCode":0}
- A9:  ainvoke() — 异常捕获包装 errCode=105001
- A10: ainvoke() — result 含 errCode 时原样透传
- A11: astream() — str chunk 直通
- A12: astream() — 非 str chunk json.dumps
- A13: astream() — 异常捕获 yield 错误 JSON
- A14: convert_ir_to_custom_card() — camelCase→snake_case 转换
- A15: convert_ir_to_custom_card() — component_type 从 metadata 回退
- A16: create_plugin_tool() — callMode=="custom" 分流
- A17: create_plugin_tool() — callMode 缺省走 HTTP 逻辑
- A18: create_plugin_tool() — "resource already exist" 幂等返回
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.extension.wrapper.custom_plugin_tool import (
    CustomPluginCard,
    CustomPluginTool,
    convert_ir_to_custom_card,
    create_plugin_tool,
)


# --------------------------------------------------------------------------- #
# A5: CustomPluginCard 字段定义
# --------------------------------------------------------------------------- #

def test_card_fields_default():
    """A5: CustomPluginCard 默认值（params=[], component_type="", 等）。"""
    card = CustomPluginCard(id="test", name="test", description="desc")
    assert card.params == []
    assert card.component_type == ""
    assert card.response == []
    assert card.plugin_name == ""
    assert card.plugin_desc == ""
    assert card.related_info is None
    assert card.input_parameters == {}


# --------------------------------------------------------------------------- #
# A6: CustomPluginTool.__init__ — component_type 空值校验
# --------------------------------------------------------------------------- #

def test_tool_init_empty_component_type_raises():
    """A6: component_type 为空时抛 ValueError。"""
    card = CustomPluginCard(id="t", name="t", description="d", component_type="")
    with pytest.raises(ValueError, match="non-empty component_type"):
        CustomPluginTool(card)


# --------------------------------------------------------------------------- #
# A7: CustomPluginTool.__init__ — 通过 ComponentClassPool 创建插件实例
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_tool_init_creates_plugin_instance(mock_pool):
    """A7: component_class_pool.create_component_instance 被调用，params 正确传入。"""
    mock_plugin = MagicMock()
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(
        id="t", name="t", description="d",
        component_type="custom.draw_box",
    )
    tool = CustomPluginTool(card)

    mock_pool.create_component_instance.assert_called_once_with(
        "custom.draw_box", params=[]
    )
    assert tool._plugin_instance is mock_plugin
    assert tool.component_type == "custom.draw_box"


# --------------------------------------------------------------------------- #
# A8: ainvoke() — 成功结果包装
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_ainvoke_success_wraps_output(mock_pool):
    """A8: 插件返回 {"key":"val"} → 工具返回 {"data":{"key":"val"},"errCode":0,"errMessage":""}。"""
    mock_plugin = AsyncMock()
    mock_plugin.invoke = AsyncMock(return_value={"key": "val"})
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    result = asyncio.run(tool.ainvoke({"input": "v"}))

    assert result == {"data": {"key": "val"}, "errCode": 0, "errMessage": ""}


# --------------------------------------------------------------------------- #
# A9: ainvoke() — 异常捕获包装 errCode=105001
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_ainvoke_plugin_exception_wraps_error(mock_pool):
    """A9: 插件抛异常 → 工具返回 errCode=105001 + errMessage。"""
    mock_plugin = AsyncMock()
    mock_plugin.invoke = AsyncMock(side_effect=RuntimeError("boom"))
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    result = asyncio.run(tool.ainvoke({}))

    assert result["errCode"] == 105001
    assert "RuntimeError" in result["errMessage"]
    assert result["data"] is None


# --------------------------------------------------------------------------- #
# A10: ainvoke() — result 含 errCode 时原样透传
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_ainvoke_result_with_errcode_passthrough(mock_pool):
    """A10: 插件返回 {"errCode":500} → 原样透传。"""
    mock_plugin = AsyncMock()
    mock_plugin.invoke = AsyncMock(return_value={"errCode": 500, "errMessage": "custom"})
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    result = asyncio.run(tool.ainvoke({}))

    assert result == {"errCode": 500, "errMessage": "custom"}


# --------------------------------------------------------------------------- #
# A11: astream() — str chunk 直通
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_astream_str_chunk_passthrough(mock_pool):
    """A11: 插件 yield "chunk" → 直通。"""
    async def _stream(inputs, **kwargs):
        yield "chunk1"
        yield "chunk2"

    mock_plugin = MagicMock()
    mock_plugin.stream = _stream
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    chunks = asyncio.run(_collect_async_iter(tool.astream({})))

    assert chunks == ["chunk1", "chunk2"]


# --------------------------------------------------------------------------- #
# A12: astream() — 非 str chunk json.dumps
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_astream_non_str_chunk_json_dumps(mock_pool):
    """A12: 插件 yield {"k":"v"} → json.dumps。"""
    async def _stream(inputs, **kwargs):
        yield {"k": "v"}

    mock_plugin = MagicMock()
    mock_plugin.stream = _stream
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    chunks = asyncio.run(_collect_async_iter(tool.astream({})))

    assert len(chunks) == 1
    parsed = json.loads(chunks[0])
    assert parsed == {"k": "v"}


# --------------------------------------------------------------------------- #
# A13: astream() — 异常捕获 yield 错误 JSON
# --------------------------------------------------------------------------- #

@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_astream_exception_yields_error_json(mock_pool):
    """A13: 插件 stream 抛异常 → yield 错误 JSON。"""
    async def _stream(inputs, **kwargs):
        yield "ok"
        raise RuntimeError("stream boom")

    mock_plugin = MagicMock()
    mock_plugin.stream = _stream
    mock_pool.create_component_instance.return_value = mock_plugin

    card = CustomPluginCard(id="t", name="t", description="d", component_type="custom.x")
    tool = CustomPluginTool(card)
    import asyncio
    chunks = asyncio.run(_collect_async_iter(tool.astream({})))

    # 第一个 chunk 正常直通
    assert chunks[0] == "ok"
    # 第二个 chunk 是错误 JSON
    err = json.loads(chunks[1])
    assert err["errCode"] == 105001
    assert "RuntimeError" in err["errMessage"]


# --------------------------------------------------------------------------- #
# A14: convert_ir_to_custom_card() — camelCase→snake_case 转换
# --------------------------------------------------------------------------- #

def test_convert_ir_to_custom_card_basic():
    """A14: camelCase IR → snake_case Card，字段正确映射。"""
    ir_data = {
        "name": "test_plugin",
        "description": "test desc",
        "componentType": "custom.draw_box",
        "arguments": [],
        "response": [],
        "logo": "logo.png",
    }
    card = convert_ir_to_custom_card(ir_data)
    assert card.component_type == "custom.draw_box"
    assert card.name == "test_plugin"
    assert card.plugin_name == "test_plugin"
    assert card.plugin_desc == "test desc"
    assert card.related_info == {"logo": "logo.png"}
    assert card.params == []
    assert card.response == []


# --------------------------------------------------------------------------- #
# A15: convert_ir_to_custom_card() — component_type 从 metadata 回退
# --------------------------------------------------------------------------- #

def test_convert_ir_to_custom_card_metadata_fallback():
    """A15: component_type 不在顶层时从 metadata 回退取值。"""
    ir_data = {
        "name": "test_plugin",
        "description": "desc",
        "metadata": {"component_type": "custom.from_metadata"},
        "arguments": [],
        "response": [],
    }
    card = convert_ir_to_custom_card(ir_data)
    assert card.component_type == "custom.from_metadata"


# --------------------------------------------------------------------------- #
# A16: create_plugin_tool() — callMode=="custom" 分流
# --------------------------------------------------------------------------- #

@patch("openjiuwen.core.runner.Runner")
@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_create_plugin_tool_custom_dispatch(mock_pool, mock_runner):
    """A16: callMode=="custom" → 创建 CustomPluginTool。"""
    mock_plugin = MagicMock()
    mock_pool.create_component_instance.return_value = mock_plugin

    mock_result = MagicMock()
    mock_result.is_ok.return_value = True
    mock_runner.resource_mgr.add_tool.return_value = mock_result

    ir_data = {
        "callMode": "custom",
        "name": "test",
        "description": "d",
        "componentType": "custom.test",
        "arguments": [],
        "response": [],
    }
    tool_id = create_plugin_tool(ir_data, tag="agent1")

    mock_pool.create_component_instance.assert_called_once()
    mock_runner.resource_mgr.add_tool.assert_called_once()
    assert tool_id == "test"


# --------------------------------------------------------------------------- #
# A17: create_plugin_tool() — callMode 缺省走 HTTP 逻辑
# --------------------------------------------------------------------------- #

@patch("openjiuwen.core.runner.Runner")
@patch("jiuwen.extension.wrapper.restful_api_new.RestfulApiToolNew")
@patch("jiuwen.extension.wrapper.restful_api_loader.convert_ir_to_card")
def test_create_plugin_tool_api_dispatch(mock_convert_card, mock_tool_cls, mock_runner):
    """A17: callMode 缺省/"api" → 创建 RestfulApiToolNew。"""
    mock_card = MagicMock()
    mock_convert_card.return_value = mock_card
    mock_tool = MagicMock()
    mock_tool.id = "http_tool"
    mock_tool_cls.return_value = mock_tool

    mock_result = MagicMock()
    mock_result.is_ok.return_value = True
    mock_runner.resource_mgr.add_tool.return_value = mock_result

    ir_data = {
        "callMode": "api",
        "name": "http_tool",
        "description": "d",
        "url": "http://x.com",
        "method": "POST",
        "arguments": [],
        "response": [],
    }
    tool_id = create_plugin_tool(ir_data, tag=None)

    mock_convert_card.assert_called_once()
    mock_tool_cls.assert_called_once_with(mock_card)
    assert tool_id == "http_tool"


# --------------------------------------------------------------------------- #
# A18: create_plugin_tool() — "resource already exist" 幂等返回
# --------------------------------------------------------------------------- #

@patch("openjiuwen.core.runner.Runner")
@patch("jiuwen.extension.wrapper.custom_plugin_tool.component_class_pool")
def test_create_plugin_tool_duplicate_idempotent(mock_pool, mock_runner):
    """A18: "resource already exist" → 返回 tool.id 不抛异常。"""
    mock_plugin = MagicMock()
    mock_pool.create_component_instance.return_value = mock_plugin

    mock_result = MagicMock()
    mock_result.is_ok.return_value = False
    mock_err = Exception("resource already exist")
    mock_result.error.return_value = mock_err
    mock_runner.resource_mgr.add_tool.return_value = mock_result

    ir_data = {
        "callMode": "custom",
        "name": "dup_tool",
        "description": "d",
        "componentType": "custom.test",
        "arguments": [],
        "response": [],
    }
    tool_id = create_plugin_tool(ir_data)
    assert tool_id == "dup_tool"


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #

async def _collect_async_iter(agen):
    """收集 async generator 的所有输出到列表。"""
    result = []
    async for item in agen:
        result.append(item)
    return result
