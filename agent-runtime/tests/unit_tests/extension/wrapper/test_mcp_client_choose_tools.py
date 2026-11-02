# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
BUG2026091603141 回归单测：MCP 客户端 call_tool 按 mcp_choose_tools 过滤。

覆盖两客户端（SSEClientNew / StreamableHttpClientNew）执行层白名单分支：
- 非选中（未勾选）工具拒绝执行（throw PluginParamException，且不下发远端）；
- 选中工具正常执行；
- mcp_choose_tools=None 时放行全部（向后兼容）；
- mcp_choose_tools=[] 时拒绝全部；
- 字符串等非法形态归一化为空集（防子串匹配绕过白名单，P3）。
"""

from unittest.mock import MagicMock, patch

import pytest

from openjiuwen.core.foundation.tool.mcp.base import McpServerConfig

from jiuwen.extension.wrapper.sse_client_new import SSEClientNew
from jiuwen.extension.wrapper.streamable_http_client_new import StreamableHttpClientNew
from jiuwen.plugin.common.exception import PluginParamException


def _make_config(choose_tools, client_type="sse_new"):
    """构造带 mcp_choose_tools（用户勾选的部分方法）的 McpServerConfig。"""
    return McpServerConfig(
        server_id="srv_test",
        server_name="srv_test",
        server_path="http://localhost:9999/mcp",
        client_type=client_type,
        params={
            "mcp_choose_tools": choose_tools,
            "plugin_dependency": {},
            "tool_params": [],
            "auth": {},
            "input_parameters": {},
        },
    )


class FakeSession:
    """同时支持 async with + initialize/call_tool 的伪 MCP session。"""

    def __init__(self):
        self.called_tools = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def initialize(self):
        pass

    async def call_tool(self, tool_name, arguments=None):
        self.called_tools.append(tool_name)
        return MagicMock(
            structuredContent=None,
            content=[MagicMock(text=f"ok:{tool_name}")],
        )


class _FakeSseCtx:
    async def __aenter__(self):
        return (MagicMock(), MagicMock())

    async def __aexit__(self, *exc):
        return False


class _FakeStreamableCtx:
    async def __aenter__(self):
        return (MagicMock(), MagicMock(), MagicMock())

    async def __aexit__(self, *exc):
        return False


def _patch_ctx(module_path, session):
    """按客户端模块路径 patch ClientSession：传实例则包装为工厂，传工厂直接使用。"""
    if callable(session):
        return patch(f"{module_path}.ClientSession", new=session)
    return patch(f"{module_path}.ClientSession", new=lambda *a, **k: session)


CLIENTS = [
    (
        SSEClientNew,
        "sse_new",
        "jiuwen.extension.wrapper.sse_client_new",
        "sse_client",
        _FakeSseCtx,
    ),
    (
        StreamableHttpClientNew,
        "streamable_http_new",
        "jiuwen.extension.wrapper.streamable_http_client_new",
        "streamablehttp_client",
        _FakeStreamableCtx,
    ),
]


@pytest.mark.parametrize(
    "client_cls,ctype,module_path,ctx_fn,ctx_cls",
    CLIENTS,
    ids=["sse", "streamable"],
)
@pytest.mark.asyncio
async def test_unselected_tool_is_rejected(client_cls, ctype, module_path, ctx_fn, ctx_cls):
    """非选中工具拒绝执行且不下发远端。"""
    client = client_cls(_make_config(["tool_selected"], client_type=ctype))
    fake_session = FakeSession()

    with patch(f"{module_path}.{ctx_fn}", new=lambda *a, **k: ctx_cls()), _patch_ctx(
        module_path, fake_session
    ):
        with pytest.raises(PluginParamException) as exc_info:
            await client.call_tool("tool_unselected_a", {"q": "hello"})
        assert "tool_unselected_a" in str(exc_info.value)
        assert fake_session.called_tools == [], (
            f"DEFECT_STILL_PRESENT: 未勾选方法被下发执行: {fake_session.called_tools}"
        )


@pytest.mark.parametrize(
    "client_cls,ctype,module_path,ctx_fn,ctx_cls",
    CLIENTS,
    ids=["sse", "streamable"],
)
@pytest.mark.asyncio
async def test_selected_tool_is_callable(client_cls, ctype, module_path, ctx_fn, ctx_cls):
    """选中工具正常执行。"""
    client = client_cls(_make_config(["tool_selected"], client_type=ctype))
    fake_session = FakeSession()

    with patch(f"{module_path}.{ctx_fn}", new=lambda *a, **k: ctx_cls()), _patch_ctx(
        module_path, fake_session
    ):
        result = await client.call_tool("tool_selected", {"q": "hello"})
        assert fake_session.called_tools == ["tool_selected"]
        assert result is not None


@pytest.mark.parametrize(
    "client_cls,ctype,module_path,ctx_fn,ctx_cls",
    CLIENTS,
    ids=["sse", "streamable"],
)
@pytest.mark.asyncio
async def test_no_choose_tools_all_tools_callable(
    client_cls, ctype, module_path, ctx_fn, ctx_cls
):
    """mcp_choose_tools=None（未配置）时放行全部（向后兼容）。"""
    client = client_cls(_make_config(None, client_type=ctype))
    fake_session = FakeSession()

    with patch(f"{module_path}.{ctx_fn}", new=lambda *a, **k: ctx_cls()), _patch_ctx(
        module_path, fake_session
    ):
        result = await client.call_tool("tool_unselected_a", {"q": "hello"})
        assert fake_session.called_tools == ["tool_unselected_a"]
        assert result is not None


@pytest.mark.parametrize(
    "client_cls,ctype,module_path,ctx_fn,ctx_cls",
    CLIENTS,
    ids=["sse", "streamable"],
)
@pytest.mark.asyncio
async def test_empty_choose_tools_rejects_all(
    client_cls, ctype, module_path, ctx_fn, ctx_cls
):
    """mcp_choose_tools=[]（空列表）时拒绝全部工具。"""
    client = client_cls(_make_config([], client_type=ctype))
    fake_session = FakeSession()

    with patch(f"{module_path}.{ctx_fn}", new=lambda *a, **k: ctx_cls()), _patch_ctx(
        module_path, fake_session
    ):
        with pytest.raises(PluginParamException):
            await client.call_tool("tool_selected", {"q": "hello"})
        assert fake_session.called_tools == []


@pytest.mark.parametrize(
    "client_cls,ctype,module_path,ctx_fn,ctx_cls",
    CLIENTS,
    ids=["sse", "streamable"],
)
@pytest.mark.asyncio
async def test_string_choose_tools_normalized_to_empty(
    client_cls, ctype, module_path, ctx_fn, ctx_cls
):
    """字符串形态归一化为空集：任意工具名均被拒绝，防子串匹配绕过白名单（P3）。"""
    client = client_cls(_make_config("tool_selected", client_type=ctype))
    fake_session = FakeSession()

    with patch(f"{module_path}.{ctx_fn}", new=lambda *a, **k: ctx_cls()), _patch_ctx(
        module_path, fake_session
    ):
        with pytest.raises(PluginParamException):
            await client.call_tool("tool_selected", {"q": "hello"})
        assert fake_session.called_tools == [], (
            f"DEFECT_STILL_PRESENT: 字符串形态绕过白名单: {fake_session.called_tools}"
        )