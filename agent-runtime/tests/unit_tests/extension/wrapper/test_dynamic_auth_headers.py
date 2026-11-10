# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""FEAT-093 动态鉴权：wrapper 层 dynamic_auth_headers 合并测试。

机制：FlowMcp 把 method=Headers 参数值经独立通道
jiuwen_kwargs["dynamic_auth_headers"] 下传（与 session 级 runtime_auth
严格分离）；wrapper 仅在 IR auth 无 scope 或 scope=DYNAMIC 时并入出站
headers（sse/streamable 两实现同构）。session 级 runtime_auth 的唯一
消费者是 _add_auth_params 的 USER source→target 映射。
"""
# pylint: disable=protected-access  # 单测需注入/调用内部属性与方法（仓库既有惯例，见同目录 test_single_component_http_debug_inputs.py）

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
    client._raise_error = MagicMock()
    return client


class TestPrepareRequestParamsRuntimeAuthHeaders:
    """dynamic_auth_headers（FlowMcp 独立通道下传的 Headers 参数值）并入出站 headers。"""

    @staticmethod
    def test_dynamic_auth_headers_merged():
        """DYNAMIC（IR auth 为空或 scope=DYNAMIC）时独立通道值并入出站 headers。"""
        for auth_conf in ({}, {"scope": "DYNAMIC"}):
            for cls in (StreamableHttpClientNew, SSEClientNew):
                client = _create_client(cls)
                client._auth = auth_conf
                request_params = client._prepare_request_params(
                    inputs={"query": "hello"},
                    name="echo_user",
                    dynamic_auth_headers={"Authorization": "Bearer tok-1"},
                )
                assert request_params.headers.get("Authorization") == "Bearer tok-1", (auth_conf, cls.__name__)

    @staticmethod
    def test_no_dynamic_auth_headers_unchanged():
        """无 dynamic_auth_headers 时行为不变（不出空注入）。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={"query": "hello"}, name="echo_user"
            )
            assert "Authorization" not in request_params.headers, cls.__name__

    @staticmethod
    def test_non_dict_dynamic_auth_headers_ignored():
        """dynamic_auth_headers 非 dict 时安全跳过；session 级 runtime_auth 不参与本通道。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={}, name="t", dynamic_auth_headers=None,
                runtime_auth={"headers": {"Authorization": "Bearer session-leak"}},
            )
            assert "Authorization" not in request_params.headers, cls.__name__

            client2 = _create_client(cls)
            request_params2 = client2._prepare_request_params(
                inputs={}, name="t", dynamic_auth_headers="not-a-dict"
            )
            assert "Authorization" not in request_params2.headers, cls.__name__

    @staticmethod
    def test_session_runtime_auth_not_merged_for_dynamic_scope():
        """scope=DYNAMIC/空时仅独立通道生效：session 级凭据不经本通道外发。

        （检视修复：防止无鉴权/动态服务整包外发 session 凭据。）
        """
        for auth_conf in ({}, {"scope": "DYNAMIC"}):
            for cls in (StreamableHttpClientNew, SSEClientNew):
                client = _create_client(cls)
                client._auth = auth_conf
                request_params = client._prepare_request_params(
                    inputs={},
                    name="t",
                    runtime_auth={"headers": {"X-Session-Token": "Bearer session-tok"}},
                )
                assert "X-Session-Token" not in request_params.headers, (auth_conf, cls.__name__)

    @staticmethod
    def test_correlation_headers_still_stripped():
        """独立通道携带平台关联头名时仍被最终边界剥离（B07 不回退）。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={},
                name="t",
                dynamic_auth_headers={
                    "Authorization": "Bearer tok-1",
                    "X-Request-Id": "fake-rid",
                },
            )
            assert request_params.headers.get("Authorization") == "Bearer tok-1", cls.__name__
            assert "X-Request-Id" not in request_params.headers, cls.__name__

    @staticmethod
    def test_user_scope_dynamic_auth_headers_not_merged():
        """USER 作用域：session 级 runtime_auth 由映射消费，独立通道亦不并入。

        _add_auth_params 按 auth_keys 的 source→target 映射注入
        （userToken→Authorization）；wrapper 不得再把未映射的 source 键及
        凭据值额外外发、覆盖已正确映射的目标头。
        （SERVICE 作用域的解密失败回退是 _add_auth_params 既有行为，不在本测范围。）
        """
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            client._auth = {
                "scope": "USER",
                "source": {"domain": "headers", "auth_keys": ["userToken"]},
                "target": {"domain": "headers", "auth_keys": ["Authorization"]},
            }
            request_params = client._prepare_request_params(
                inputs={"query": "hello"},
                name="echo_user",
                runtime_auth={"headers": {"userToken": "Bearer tok-9"}},
            )
            assert request_params.headers.get("Authorization") == "Bearer tok-9", cls.__name__
            assert "userToken" not in request_params.headers, cls.__name__

            client2 = _create_client(cls)
            client2._auth = {
                "scope": "USER",
                "source": {"domain": "headers", "auth_keys": ["userToken"]},
                "target": {"domain": "headers", "auth_keys": ["Authorization"]},
            }
            request_params2 = client2._prepare_request_params(
                inputs={"query": "hello"},
                name="echo_user",
                dynamic_auth_headers={"userToken": "Bearer tok-9"},
            )
            assert "userToken" not in request_params2.headers, cls.__name__


class TestFlowMcpHeaderParamsToRuntimeAuth:
    """FlowMcp.invoke 组装 jiuwen_kwargs（独立通道与 session 级分离）。"""

    @staticmethod
    def test_invoke_passes_header_params_via_independent_channel():
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

        # tracer 装饰门禁：decorate_tool_with_trace 以 agent_session._inner 为
        # 真实 session 并按 _inner.tracer().agent_handler_valid() 判定是否装饰；
        # MagicMock 会自动生成 _inner 导致门禁误过、handler await 到未配置的
        # mock。显式置 False 走"未注册 agent handler 原样返回"分支——
        # 本测只验证 jiuwen_kwargs 透传，不测遥测 span
        mock_session = MagicMock()
        mock_session._inner.tracer.return_value.agent_handler_valid.return_value = False
        mcp._format_runtime_auth = MagicMock(return_value={})
        mcp._get_runtime_context_header = MagicMock(return_value=None)

        asyncio.run(mcp.invoke({"userFields": {"Authorization": "Bearer tok-2"}}, mock_session, None))

        jiuwen_kwargs = captured.get("_jiuwen_runtime_kwargs")
        assert jiuwen_kwargs is not None
        assert jiuwen_kwargs["dynamic_auth_headers"]["Authorization"] == "Bearer tok-2"

    @staticmethod
    def test_invoke_separates_session_auth_from_dynamic_headers():
        """通道分离：session 级 runtime_auth 与动态凭证值各走各的键，互不混装。

        （检视修复：混装会使无鉴权/动态服务经 wrapper 门控把 session 级
        凭据整包外发。）
        """
        from jiuwen.extension.workflow_node.flow_mcp import FlowMcp

        mcp = FlowMcp.__new__(FlowMcp)
        mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "t", "name": "s"}
        mcp._is_older_version = False
        mcp._header_params = {"Authorization": "Bearer dyn-tok"}
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
        mock_session._inner.tracer.return_value.agent_handler_valid.return_value = False
        mcp._format_runtime_auth = MagicMock(
            return_value={"X-Session-Token": "Bearer session-tok"})
        mcp._get_runtime_context_header = MagicMock(return_value=None)

        asyncio.run(mcp.invoke({"userFields": {"Authorization": "Bearer dyn-tok"}}, mock_session, None))

        jiuwen_kwargs = captured.get("_jiuwen_runtime_kwargs")
        assert jiuwen_kwargs is not None
        # session 级只含自己的键，未被动态凭证值污染
        assert jiuwen_kwargs["runtime_auth"]["headers"] == {"X-Session-Token": "Bearer session-tok"}
        # 动态凭证值走独立通道，未混入 runtime_auth
        assert jiuwen_kwargs["dynamic_auth_headers"] == {"Authorization": "Bearer dyn-tok"}
