# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FEAT-093 动态鉴权：wrapper 层 runtime_auth.headers 合并测试。

机制：FlowMcp 把 method=Headers 参数值经 jiuwen_kwargs["runtime_auth"]["headers"]
下传（scope 无关通道）；RequestParamsCreator._add_auth_params 仅在 IR auth
scope=USER/SERVICE 时消费 runtime_auth，DYNAMIC（auth 为空）会整段跳过，
故 wrapper 在 create() 之后直接并入出站 headers（sse/streamable 两实现同构）。
"""

from unittest.mock import MagicMock

from jiuwen.extension.wrapper.sse_client_new import SSEClientNew
from jiuwen.extension.wrapper.streamable_http_client_new import StreamableHttpClientNew


def _create_client(cls):
    """构造跳过 __init__ 的 client 实例（只设 _prepare_request_params 依赖的属性）。"""
    client = cls.__new__(cls)
    client._server_path = "http://127.0.0.1:9999/mcp"
    client._name = "test-server"
    client._auth_headers = {}
    client._tool_params = []
    client._auth = {}
    client._plugin_dependency = {}
    client._input_parameters = {}
    client._cert = False
    client._raise_error = lambda msg: None
    return client


class TestPrepareRequestParamsRuntimeAuthHeaders:
    """runtime_auth.headers（FlowMcp 下传的 Headers 参数值）并入出站 headers。"""

    def test_dynamic_auth_headers_merged(self):
        """DYNAMIC（IR auth 为空）时 runtime_auth.headers 仍并入出站 headers。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={"query": "hello"},
                name="echo_user",
                runtime_auth={"headers": {"Authorization": "Bearer tok-1"}},
            )
            assert request_params.headers.get("Authorization") == "Bearer tok-1", cls.__name__

    def test_no_runtime_auth_unchanged(self):
        """无 runtime_auth 时行为不变（不出空注入）。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={"query": "hello"}, name="echo_user"
            )
            assert "Authorization" not in request_params.headers, cls.__name__

    def test_non_dict_runtime_auth_ignored(self):
        """runtime_auth 非 dict / headers 非 dict 时安全跳过。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={}, name="t", runtime_auth=None
            )
            assert "Authorization" not in request_params.headers, cls.__name__

            client2 = _create_client(cls)
            request_params2 = client2._prepare_request_params(
                inputs={}, name="t", runtime_auth={"headers": "not-a-dict"}
            )
            assert "Authorization" not in request_params2.headers, cls.__name__

    def test_correlation_headers_still_stripped(self):
        """runtime_auth.headers 携带平台关联头名时仍被最终边界剥离（B07 不回退）。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={},
                name="t",
                runtime_auth={"headers": {
                    "Authorization": "Bearer tok-1",
                    "X-Request-Id": "fake-rid",
                }},
            )
            assert request_params.headers.get("Authorization") == "Bearer tok-1", cls.__name__
            assert "X-Request-Id" not in request_params.headers, cls.__name__


class TestFlowMcpHeaderParamsToRuntimeAuth:
    """FlowMcp.invoke 组装 jiuwen_kwargs 的 runtime_auth.headers（Mock MCPTool 断言入参）。"""

    def test_invoke_passes_header_params_via_jiuwen_kwargs(self):
        from jiuwen.extension.workflow_node.flow_mcp import FlowMcp

        mcp = FlowMcp.__new__(FlowMcp)
        mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "t", "name": "s"}
        mcp._is_older_version = False
        mcp._header_params = {"Authorization": "Bearer tok-2"}
        mcp._init_lock = None

        param = MagicMock()
        param.name = "Authorization"
        param.method = "Headers"
        param.required = False
        param.type = "string"
        mock_client = MagicMock()
        mock_client._tool_params = [param]
        mcp._client = mock_client

        captured = {}

        async def fake_invoke(inputs):
            captured.update(inputs)
            return {"result": MagicMock(structuredContent={"ok": True}, content=None)}

        mock_tool = MagicMock()
        mock_tool.invoke = fake_invoke
        mcp.api = mock_tool

        import asyncio

        mock_session = MagicMock()
        mcp._format_runtime_auth = lambda session: {}
        mcp._get_runtime_context_header = lambda session: None

        asyncio.run(mcp.invoke({"userFields": {"Authorization": "Bearer tok-2"}}, mock_session, None))

        jiuwen_kwargs = captured.get("_jiuwen_runtime_kwargs")
        assert jiuwen_kwargs is not None
        assert jiuwen_kwargs["runtime_auth"]["headers"]["Authorization"] == "Bearer tok-2"
