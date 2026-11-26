# -*- coding: UTF-8 -*-
"""issue #1756：网关 200 + 非 SSE 错误体的诊断解析（脱敏/截断）。"""
from model_service.client import _describe_gateway_body


def test_code_and_msg():
    body = b'{"code":401,"msg":"auth failed: invalid api key","data":null}'
    assert _describe_gateway_body(body) == "code=401 auth failed: invalid api key"


def test_nested_error_fields():
    body = b'{"error":{"code":"invalid_api_key","message":"Incorrect API key provided"}}'
    assert _describe_gateway_body(body) == "code=invalid_api_key Incorrect API key provided"


def test_non_json_not_exposed():
    # 检视意见：对外只暴露白名单 code/msg；非 JSON 原文只进内部日志
    assert _describe_gateway_body(b"<html>502 Bad Gateway</html>") == ""


def test_json_without_whitelist_fields_not_exposed():
    assert _describe_gateway_body(b'{"detail":"internal host 10.0.0.1"}') == ""


def test_credential_redacted_and_bounded():
    body = ('{"msg":"bad key sk-abcdef123456 and Bearer abc.def api_key=abcd1234"}').encode()
    out = _describe_gateway_body(body)
    assert "sk-abcdef123456" not in out
    assert "Bearer abc.def" not in out
    assert "abcd1234" not in out
    assert len(out) <= 200


def test_empty_body():
    assert _describe_gateway_body(b"") == ""
