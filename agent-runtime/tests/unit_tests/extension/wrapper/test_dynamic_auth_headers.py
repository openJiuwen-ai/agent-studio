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
        """双通道下传：session 凭据仅在 runtime_auth，动态凭证值双通道。

        runtime_auth 含 session 凭据+动态凭证值（USER scope 时供
        _add_auth_params 映射消费）；dynamic_auth_headers 仅含动态凭证
        值（DYNAMIC/空 scope 时 wrapper 合并；session 凭据不泄漏）。
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
        assert jiuwen_kwargs["dynamic_auth_headers"] == {"Authorization": "Bearer dyn-tok"}
        # runtime_auth 合并 session 凭据 + 动态凭证值（USER scope 时由
        # _add_auth_params 消费做 source→target 映射；DYNAMIC/空 scope 时
        # _add_auth_params 不读，不影响独立通道行为）
        assert jiuwen_kwargs["runtime_auth"]["headers"] == {
            "X-Session-Token": "Bearer session-tok",
            "Authorization": "Bearer dyn-tok",
        }

    @staticmethod
    def test_invoke_session_auth_dict_not_mutated():
        """session 级字典不被污染：invoke 后原字典内容不变、二次 invoke 不累积。

        _format_runtime_auth 返回的是 session 存储的引用。双通道合并必须
        构造副本（展开语法），绝不能 update 原对象——否则会把本节点
        绑定的动态凭证持久写入 workflow 全局鉴权状态。
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

        session_auth = {"X-Session-Token": "Bearer session-tok"}
        mock_session = MagicMock()
        mock_session._inner.tracer.return_value.agent_handler_valid.return_value = False
        mcp._format_runtime_auth = MagicMock(return_value=session_auth)
        mcp._get_runtime_context_header = MagicMock(return_value=None)

        asyncio.run(mcp.invoke({"userFields": {"Authorization": "Bearer dyn-tok"}}, mock_session, None))

        # 核心断言：session 级字典未被污染
        assert session_auth == {"X-Session-Token": "Bearer session-tok"}, \
            "session auth dict was mutated!"

        # 二次 invoke 不累积
        captured.clear()
        asyncio.run(mcp.invoke({"userFields": {"Authorization": "Bearer dyn-tok"}}, mock_session, None))
        jiuwen_kwargs = captured.get("_jiuwen_runtime_kwargs")
        assert jiuwen_kwargs["runtime_auth"]["headers"] == {
            "X-Session-Token": "Bearer session-tok",
            "Authorization": "Bearer dyn-tok",
        }, "second invoke should not accumulate!"

    @staticmethod
    def test_wrapper_filters_invalid_header_names():
        """wrapper 过滤非法头名：Host/Content-Length/保留头/非法 token 不出站。"""
        from jiuwen.extension.wrapper.outbound_header_guard import is_valid_outbound_header_name

        # 合法名通过
        assert is_valid_outbound_header_name("Authorization") is True
        assert is_valid_outbound_header_name("X-Custom-Header") is True

        # 逐跳敏感头拒绝
        assert is_valid_outbound_header_name("Host") is False
        assert is_valid_outbound_header_name("Content-Length") is False
        assert is_valid_outbound_header_name("Transfer-Encoding") is False

        # 平台保留关联头拒绝
        assert is_valid_outbound_header_name("X-Request-Id") is False
        assert is_valid_outbound_header_name("X-Execution-Id") is False
        assert is_valid_outbound_header_name("traceparent") is False

        # 非法 token 字符拒绝
        assert is_valid_outbound_header_name("Bad Header") is False
        assert is_valid_outbound_header_name("Auth:Inj") is False
        assert is_valid_outbound_header_name("X-头") is False

    @staticmethod
    def test_whitespace_only_header_value_skipped():
        """纯空白值不注入（与 Java StringUtils.isBlank 语义对齐）。"""
        from jiuwen.extension.workflow_node.flow_mcp import FlowMcp

        param = MagicMock()
        param.name = "auth_token"
        param.method = "Headers"
        param.required = False
        param.type = "string"

        mcp = FlowMcp.__new__(FlowMcp)
        mcp._conf = {"type": "sse", "url": "http://test", "tool_name": "t", "name": "s"}
        mcp._is_older_version = False
        mcp._init_lock = None

        mock_client = MagicMock()
        mock_client._tool_params = [param]
        mcp._client = mock_client

        result, _ = mcp._format_api_inputs({"auth_token": "   "})
        assert "auth_token" not in getattr(mcp, "_header_params", {}), \
            "whitespace-only should be skipped"

    @staticmethod
    def test_wrapper_filters_invalid_header_values():
        """wrapper 过滤非法头值：非 Latin-1/含控制字符的值不出站。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={}, name="t",
                dynamic_auth_headers={
                    "Authorization": "Bearer ok",
                    "X-Chinese": "Bearer 中文令牌",
                    "X-Cr": "Bearer tok\r\nen",
                    "X-Null": "bad\x00val",
                    "X-Latin1-Ok": "Bearer café",
                },
            )
            # 合法值保留
            assert request_params.headers.get("Authorization") == "Bearer ok", cls.__name__
            assert request_params.headers.get("X-Latin1-Ok") is not None, cls.__name__
            # 非法值全部过滤
            assert "X-Chinese" not in request_params.headers, cls.__name__
            assert "X-Cr" not in request_params.headers, cls.__name__
            assert "X-Null" not in request_params.headers, cls.__name__

    @staticmethod
    def test_wrapper_filters_invalid_names_from_dynamic_auth():
        """wrapper 的 dynamic_auth_headers 过滤非法头名（存量 IR 绕过防护）。"""
        for cls in (StreamableHttpClientNew, SSEClientNew):
            client = _create_client(cls)
            request_params = client._prepare_request_params(
                inputs={}, name="t",
                dynamic_auth_headers={
                    "Authorization": "Bearer ok",
                    "Host": "evil",
                    "Content-Length": "999",
                    "X-Request-Id": "fake",
                    "Bad Header": "v",
                },
            )
            # 合法名保留
            assert request_params.headers.get("Authorization") == "Bearer ok", cls.__name__
            # 非法名全部过滤
            assert "Host" not in request_params.headers, cls.__name__
            assert "Content-Length" not in request_params.headers, cls.__name__
            assert "X-Request-Id" not in request_params.headers, cls.__name__
            assert "Bad Header" not in request_params.headers, cls.__name__
