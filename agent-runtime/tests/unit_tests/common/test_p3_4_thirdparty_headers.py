# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""SYNC-01 P3.4 第三方关联传播测试（D-02 / B07）。

机制：模型/插件/MCP 出站**不传播**平台关联 Header（X-Request-Id /
X-Execution-Id / traceparent）；业务鉴权 Header（X-Auth-Id / X-Auth-Token /
X-Deployment-Id）与插件/MCP 鉴权钩子保留。内部 Runtime/Builder 目标留 P4 联测。

覆盖：
- 动态：`_extract_auth_headers`（模型出站 custom_headers 构造）只含鉴权、
  不含关联 Header——即使请求上下文带 request_id/trace。
- 静态守卫（P1 模式）：8 个出站文件源码断言无关联 Header 注入调用，
  `inject_traceparent` 函数已从 request_context 移除；防回归。
"""

import unittest
from pathlib import Path

from agent_runtime.common.model_providers import _extract_auth_headers
from agent_runtime.context.request_context import _request_ctx, RequestContext

_AGENT_RUNTIME_DIR = Path(__file__).resolve().parents[3]
_RUNTIME_ROOT = _AGENT_RUNTIME_DIR / "agent_runtime"
_JIUWEN_ROOT = _AGENT_RUNTIME_DIR / "jiuwen"

# 5 个第三方出站文件 / 8 个注入点（模型 model_providers×3 / 插件 HTTP request_params×1 /
# MCP mcpapi×2 / 插件 SSE+streamable wrapper×2——插件/MCP 共用 RequestParamsCreator 构造源）
_OUTBOUND_FILES = [
    _RUNTIME_ROOT / "common" / "model_providers.py",
    _JIUWEN_ROOT / "plugin" / "models" / "request_params.py",
    _JIUWEN_ROOT / "plugin" / "models" / "mcpapi.py",
    _JIUWEN_ROOT / "extension" / "wrapper" / "sse_client_new.py",
    _JIUWEN_ROOT / "extension" / "wrapper" / "streamable_http_client_new.py",
]

# 禁止出现在第三方出站构造的注入模式
_FORBIDDEN_PATTERNS = (
    'headers[X_REQUEST_ID] = get_x_request_id()',
    'headers[X_EXECUTION_ID] = get_x_execution_id()',
    'headers["X-Request-Id"] = ctx.request_id',
    'custom_headers["X-Request-Id"] = ctx.request_id',
    'inject_traceparent(',
)

_CORRELATION_HEADERS = ("X-Request-Id", "X-Execution-Id", "traceparent")

# 每个出站文件必须存在的最终边界过滤调用
_REQUIRED_STRIP_CALL = "strip_correlation_headers("


class TestModelOutboundHeadersNoCorrelation(unittest.TestCase):
    def test_extract_auth_headers_contains_only_auth(self):
        """模型出站 custom_headers 只含鉴权/部署 Header，不含关联 Header。"""
        headers = {
            "auth_id": "aid-1",
            "x_auth_token": "tok-1",
            "deployment_id": "dep-1",
        }
        out = _extract_auth_headers(headers)
        self.assertEqual(
            out,
            {"X-Auth-Id": "aid-1", "X-Auth-Token": "tok-1", "X-Deployment-Id": "dep-1"},
        )
        for h in _CORRELATION_HEADERS:
            self.assertNotIn(h, out)

    def test_extract_auth_headers_no_correlation_even_with_request_context(self):
        """请求上下文带 request_id/trace 时，模型出站仍不带关联 Header。"""
        token = _request_ctx.set(
            RequestContext(request_id="rid-1", trace_id="tid-1", execution_id="eid-1")
        )
        try:
            out = _extract_auth_headers({"auth_id": "aid-1"})
            self.assertEqual(out, {"X-Auth-Id": "aid-1"})
            for h in _CORRELATION_HEADERS:
                self.assertNotIn(h, out)
        finally:
            _request_ctx.reset(token)

    def test_extract_auth_headers_empty_input(self):
        self.assertEqual(_extract_auth_headers(None), {})
        self.assertEqual(_extract_auth_headers({}), {})


class TestNoThirdPartyCorrelationInjection(unittest.TestCase):
    """静态守卫（P1 模式）：出站文件无注入调用 + 最终边界 strip 接线存在。"""

    def test_outbound_files_have_no_correlation_injection(self):
        for f in _OUTBOUND_FILES:
            src = f.read_text(encoding="utf-8")
            for pat in _FORBIDDEN_PATTERNS:
                self.assertNotIn(
                    pat, src, f"{f.name} 含禁止的第三方关联 Header 注入: {pat!r}"
                )

    def test_strip_call_wired_at_final_boundary(self):
        """防删守卫：每个出站文件必须保留最终边界 strip_correlation_headers 调用。"""
        for f in _OUTBOUND_FILES:
            src = f.read_text(encoding="utf-8")
            self.assertIn(
                _REQUIRED_STRIP_CALL, src,
                f"{f.name} 缺最终边界 strip_correlation_headers 调用（B07 伪造剥离）",
            )

    def test_inject_traceparent_removed_from_request_context(self):
        """inject_traceparent 函数已删（老分支无此函数；D-02 第三方 W3C 传播停止）。"""
        import agent_runtime.context.request_context as rc

        self.assertFalse(
            hasattr(rc, "inject_traceparent"),
            "inject_traceparent 应已从 request_context 移除（D-02）",
        )
        src = (_RUNTIME_ROOT / "context" / "request_context.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("def inject_traceparent", src)


if __name__ == "__main__":
    unittest.main()


class TestStripCorrelationHeaders(unittest.TestCase):
    """strip_correlation_headers 单元：大小写不敏感剥离 + 鉴权/客户 Header 保留。"""

    def test_strips_all_cases_and_variants(self):
        from agent_runtime.context.request_context import strip_correlation_headers

        h = {
            "X-Request-Id": "a",
            "x-request-id": "b",
            "X-EXECUTION-ID": "c",
            "TraceParent": "d",
            "traceparent": "e",
            "Authorization": "Bearer ok",
            "X-Auth-Id": "aid",
            "cust-userid": "u1",
            "X-Deployment-Id": "dep",
        }
        strip_correlation_headers(h)
        self.assertEqual(
            h,
            {
                "Authorization": "Bearer ok",
                "X-Auth-Id": "aid",
                "cust-userid": "u1",
                "X-Deployment-Id": "dep",
            },
        )

    def test_empty_and_none_safe(self):
        from agent_runtime.context.request_context import strip_correlation_headers

        h = {}
        strip_correlation_headers(h)
        self.assertEqual(h, {})


class TestRequestParamsCreatorStripsSpoofed(unittest.TestCase):
    """审视 9268880d §2 反例转正：配置/输入预置伪造关联 Header 在最终边界剥离。

    真实 RequestParamsCreator.create 流程（_format_headers 合并 _api_headers +
    inputs headers——插件 HTTP / MCP / SSE / streamable 共用此构造源）。
    """

    def test_create_strips_spoofed_correlation_headers(self):
        from jiuwen.plugin.models.request_params import RequestParamsCreator

        creator = RequestParamsCreator(
            api_name="spoof-api",
            api_headers={
                "x-request-id": "spoof-r", # 配置预置伪造（大小写变体）
                "X-Execution-Id": "spoof-e",
                "traceparent": "00-spoof",
                "Authorization": "Bearer real", # 认证保留
            },
            api_url="http://127.0.0.1:1/x", # 不真实发送，仅构造
        )
        rp = creator.create({})
        for h in ("X-Request-Id", "X-Execution-Id", "traceparent"):
            self.assertNotIn(h, rp.headers, f"伪造关联 Header 未剥离: {h}")
        self.assertEqual(rp.headers.get("Authorization"), "Bearer real")


class TestWireLocalReceiver(unittest.TestCase):
    """B07 实际出站抓包：本地接收端抓真实 HTTP wire 上的 Header。

    构造产物（真实 RequestParamsCreator.create，含预置伪造）经真实 HTTP 发送
    到本地接收端——断言 wire 上零关联 Header + 认证保留。
    """

    def test_wire_no_correlation_headers_on_local_receiver(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        import requests as req_lib
        from jiuwen.plugin.models.request_params import RequestParamsCreator

        captured = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # pylint: disable=huawei-invalid-name
                captured["headers"] = dict(self.headers)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):  # 静音
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            creator = RequestParamsCreator(
                api_name="wire-api",
                api_headers={
                    "x-request-id": "spoof-r",
                    "X-Execution-Id": "spoof-e",
                    "traceparent": "00-spoof",
                    "Authorization": "Bearer wire-real",
                },
                api_url=f"http://127.0.0.1:{port}/x",
            )
            rp = creator.create({})
            # 真实 HTTP 发送构造产物（模拟 wrapper 把 request_params.headers 发给第三方）
            resp = req_lib.post(
                f"http://127.0.0.1:{port}/x", headers=rp.headers, timeout=5
            )
            self.assertEqual(resp.status_code, 200)
            wire = {k.lower(): v for k, v in captured["headers"].items()}
            for h in ("x-request-id", "x-execution-id", "traceparent"):
                self.assertNotIn(h, wire, f"wire 上出现关联 Header: {h}")
            self.assertTrue(wire.get("authorization", "").startswith("Bearer wire-real"))
        finally:
            server.shutdown()
            server.server_close()

    def test_wire_model_outbound_headers(self):
        """模型出站 wire：_extract_auth_headers 产物（含预置伪造）真实发送到本地接收端。"""
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        import requests as req_lib

        captured = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # pylint: disable=huawei-invalid-name
                captured["headers"] = dict(self.headers)
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            headers = _extract_auth_headers(
                {
                    "auth_id": "aid-wire",
                    "x_auth_token": "tok-wire",
                    "X-Request-Id": "spoof-model-r", # 预置伪造
                    "traceparent": "00-spoof-model",
                }
            )
            resp = req_lib.post(
                f"http://127.0.0.1:{port}/v1/chat", headers=headers, timeout=5
            )
            self.assertEqual(resp.status_code, 200)
            wire = {k.lower(): v for k, v in captured["headers"].items()}
            for h in ("x-request-id", "x-execution-id", "traceparent"):
                self.assertNotIn(h, wire)
            self.assertEqual(wire.get("x-auth-id"), "aid-wire")
            self.assertEqual(wire.get("x-auth-token"), "tok-wire")
        finally:
            server.shutdown()
            server.server_close()


class _FakeTracerManager:
    """异步 tracer 替身——生产 ainvoke/astream 会 await on_plugin_start/end。"""
    async def on_plugin_start(self, inputs): pass  # pylint: disable=multiple-statements  # noqa
    async def on_plugin_end(self, *a, **kw): pass  # pylint: disable=multiple-statements  # noqa
    async def on_plugin_error(self, error): pass  # pylint: disable=multiple-statements  # noqa


class TestRestfulApiAinvokeFinalBoundary(unittest.IsolatedAsyncioTestCase):
    """审视 b2eea910 §2 防回归（修正异步基类+async mock）：经生产
    RestFulAPI.ainvoke 方法体验证 plugin_auth 钩子重引入→最终 strip 剥离。
    删 ainvoke 中 strip → fake_send 捕到三名称 → 断言失败。
    """

    @staticmethod
    def _make_api():
        from jiuwen.plugin.models.restfulapi import RestFulAPI

        api = RestFulAPI.__new__(RestFulAPI)
        api.method = "POST"
        api.headers = {}
        api.async_switch = None  # 走 _async_send_request 分支
        api.request_params_creator = type("C", (), {})()
        api.request_params_creator.create = lambda inputs, **kw: type("RP", (), {  # pylint: disable=lambda-assign
            "headers": {"Authorization": "Bearer safe"},
            "ip_address_url": "http://127.0.0.1:1/x",
            "query_params_in_inputs": {},
            "request_arg": {},
            "file_params": [],
            "param_wrapper": {},
            "api_cert": False,
        })()
        api.plugin_dependency = {"hook_function": {"plugin_auth": "evil"}}
        api.plugin_reade_buffer_size = 1024
        return api

    async def test_ainvoke_strips_hook_reintroduced_headers(self):
        from unittest import mock

        api = self._make_api()
        captured = {}

        def evil_auth(rp):
            rp.headers["x-request-id"] = "forged"
            rp.headers["X-Execution-Id"] = "forged"
            rp.headers["traceparent"] = "00-forged"

        async def fake_send(rp, tm):
            captured["headers"] = dict(rp.headers)
            return {"status": "ok"}

        def fake_validate(rp, **kw):
            evil_auth(rp)

        with mock.patch.object(api, "_create_tracer_manager", return_value=_FakeTracerManager()), \
             mock.patch.object(api, "_validate_request_params", fake_validate), \
             mock.patch.object(api, "_async_send_request", fake_send), \
             mock.patch.object(api, "_load_cert", lambda rp: None):
            await api.ainvoke({})

        wire = {k.lower(): v for k, v in captured["headers"].items()}
        for h in ("x-request-id", "x-execution-id", "traceparent"):
            self.assertNotIn(h, wire, f"ainvoke 最终发送仍含 {h}")
        self.assertTrue(wire.get("authorization", "").startswith("Bearer safe"))

    async def test_astream_strips_hook_reintroduced_headers(self):
        """astream 同构防回归（删 strip → 捕获到三名称 → 失败）。"""
        from unittest import mock

        api = self._make_api()
        captured = {}

        def evil_auth(rp):
            rp.headers["x-request-id"] = "forged"
            rp.headers["X-Execution-Id"] = "forged"
            rp.headers["traceparent"] = "00-forged"

        class FakeResp:
            async def __aenter__(self): return self  # pylint: disable=multiple-statements  # noqa
            async def __aexit__(self, *a): pass  # pylint: disable=multiple-statements  # noqa
            async def read(self): return b"{}"  # pylint: disable=multiple-statements  # noqa
            status = 200
            headers = {}
            @property  # pylint: disable=blank-line  # noqa
            def content(self):
                # async iterable: yield nothing, return immediately
                class _EmptyContent:
                    def __aiter__(self_inner):  # pylint: disable=no-self-argument
                        return self_inner
                    async def __anext__(self_inner):  # pylint: disable=blank-line  # noqa
                        raise StopAsyncIteration
                return _EmptyContent()

        class FakeSession:
            def __init__(self, **kw): pass  # pylint: disable=multiple-statements  # noqa
            async def __aenter__(self): return self  # pylint: disable=multiple-statements  # noqa
            async def __aexit__(self, *a): pass  # pylint: disable=multiple-statements  # noqa
            @staticmethod  # pylint: disable=blank-line  # noqa
            def request(**kw):  # pylint: disable=blank-line  # noqa
                captured["headers"] = dict(kw.get("headers", {}))
                return FakeResp()

        def fake_validate(rp, **kw):
            evil_auth(rp)

        with mock.patch.object(api, "_create_tracer_manager", return_value=_FakeTracerManager()), \
             mock.patch.object(api, "_validate_request_params", fake_validate), \
             mock.patch("aiohttp.ClientSession", FakeSession), \
             mock.patch("aiohttp.TCPConnector", return_value=None):
            async for _ in api.astream({}):
                pass

        wire = {k.lower(): v for k, v in captured["headers"].items()}
        for h in ("x-request-id", "x-execution-id", "traceparent"):
            self.assertNotIn(h, wire, f"astream 最终发送仍含 {h}")


class _FakeTracerManager:
    async def on_plugin_start(self, inputs): pass  # pylint: disable=multiple-statements  # noqa
    async def on_plugin_end(self, content): pass  # pylint: disable=multiple-statements  # noqa
    async def on_plugin_error(self, error): pass  # pylint: disable=multiple-statements  # noqa


class _FakeMcpCtx:
    """async context manager for streamablehttp_client / sse_client."""
    def __init__(self, captured, kw):
        captured.update(kw)
    async def __aenter__(self):  # pylint: disable=blank-line  # noqa
        return (None, None, None)  # streamable_http: (read, write, _)
    async def __aexit__(self, *a): pass  # pylint: disable=blank-line  # noqa


class _FakeMcpSseCtx:
    """SSE returns 2-tuple."""
    def __init__(self, captured, kw):
        captured.update(kw)
    async def __aenter__(self):  # pylint: disable=blank-line  # noqa
        return (None, None)  # sse: (read, write)
    async def __aexit__(self, *a): pass  # pylint: disable=blank-line  # noqa


class _FakeClientSession:
    async def __aenter__(self): return self  # pylint: disable=multiple-statements  # noqa
    async def __aexit__(self, *a): pass  # pylint: disable=multiple-statements  # noqa
    async def initialize(self): pass  # pylint: disable=multiple-statements  # noqa
    async def call_tool(self, name, args):  # pylint: disable=blank-line  # noqa
        return type("R", (), {"content": []})()


class TestMcpStreamableHttpSendBoundary(unittest.IsolatedAsyncioTestCase):
    """审视 b4f6129c §2.3: MCP streamable_http 生产客户端发送边界捕获。"""

    async def test_streamable_http_no_correlation_at_send(self):
        from unittest import mock
        from jiuwen.plugin.models.mcpapi import McpAPI

        api = McpAPI.__new__(McpAPI)
        api.transport_type = "streamable_http"
        api.name = "test-tool"
        api.plugin_dependency = {}

        captured = {}

        async def fake_create(self, inputs, **kw):
            return type("RP", (), {
                "headers": {"Authorization": "Bearer safe"},
                "ip_address_url": "http://127.0.0.1:1/mcp",
                "query_params_in_inputs": {},
            })()

        def evil_hook(rp, **kw):
            rp.headers["x-request-id"] = "forged"
            rp.headers["X-Execution-Id"] = "forged"
            rp.headers["traceparent"] = "00-forged"

        api.request_params_creator = type("C", (), {"create": fake_create})()

        with mock.patch("jiuwen.plugin.models.mcpapi.TraceManager") as tm, mock.patch.object(api, "replace_mcp_headers_extra", evil_hook), mock.patch.object(api, "_validate_auth_hook_function", lambda rp: None), mock.patch("jiuwen.extension.wrapper.customer_header_inject.inject_customer_headers_to_mcp", lambda rp: None), mock.patch("jiuwen.plugin.models.mcpapi.streamablehttp_client", # pylint: disable=line-too-long  # noqa
                        lambda *a, **kw: _FakeMcpCtx(captured, kw)), mock.patch("jiuwen.plugin.models.mcpapi.ClientSession", # pylint: disable=line-too-long
                        lambda *a: _FakeClientSession()), \
             mock.patch.object(api, "_transform_result", lambda r: []):
            tm.generate_manager.return_value = _FakeTracerManager()
            await api.ainvoke({})

        wire = {k.lower(): v for k, v in captured["headers"].items()}
        for h in ("x-request-id", "x-execution-id", "traceparent"):
            self.assertNotIn(h, wire, f"MCP streamable_http 发送仍含 {h}")
        self.assertTrue(wire.get("authorization", "").startswith("Bearer safe"))


class TestMcpSseSendBoundary(unittest.IsolatedAsyncioTestCase):
    """审视 b4f6129c §2.3: MCP SSE 生产客户端发送边界捕获。"""

    async def test_sse_no_correlation_at_send(self):
        from unittest import mock
        from jiuwen.plugin.models.mcpapi import McpAPI

        api = McpAPI.__new__(McpAPI)
        api.transport_type = "sse"
        api.name = "test-tool"
        api.plugin_dependency = {}

        captured = {}

        async def fake_create(self, inputs, **kw):
            return type("RP", (), {
                "headers": {"Authorization": "Bearer safe"},
                "ip_address_url": "http://127.0.0.1:1/mcp",
                "query_params_in_inputs": {},
            })()

        def evil_hook(rp, **kw):
            rp.headers["x-request-id"] = "forged"
            rp.headers["X-Execution-Id"] = "forged"
            rp.headers["traceparent"] = "00-forged"

        api.request_params_creator = type("C", (), {"create": fake_create})()

        with mock.patch("jiuwen.plugin.models.mcpapi.TraceManager") as tm, mock.patch.object(api, "replace_mcp_headers_extra", evil_hook), mock.patch.object(api, "_validate_auth_hook_function", lambda rp: None), mock.patch("jiuwen.extension.wrapper.customer_header_inject.inject_customer_headers_to_mcp", lambda rp: None), mock.patch("jiuwen.plugin.models.mcpapi.sse_client", # pylint: disable=line-too-long  # noqa
                        lambda *a, **kw: _FakeMcpSseCtx(captured, kw)), mock.patch("jiuwen.plugin.models.mcpapi.ClientSession", # pylint: disable=line-too-long
                        lambda *a: _FakeClientSession()), \
             mock.patch.object(api, "_transform_result", lambda r: []):
            tm.generate_manager.return_value = _FakeTracerManager()
            await api.ainvoke({})

        wire = {k.lower(): v for k, v in captured["headers"].items()}
        for h in ("x-request-id", "x-execution-id", "traceparent"):
            self.assertNotIn(h, wire, f"MCP SSE 发送仍含 {h}")
        self.assertTrue(wire.get("authorization", "").startswith("Bearer safe"))


class TestModelSendBoundaryNote(unittest.TestCase):
    """模型出站发送边界=_extract_auth_headers（strip 在此函数内，模型客户端直接用其输出）。

    _extract_auth_headers 动态测试（TestModelOutboundHeadersNoCorrelation ×3）
    即此边界证据——strip 在客户端发送前的最后构造点，客户端直接使用返回的 dict。
    """
    pass
