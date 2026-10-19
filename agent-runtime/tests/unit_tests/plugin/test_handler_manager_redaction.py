#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2026

"""文件下载错误报文脱敏回归测试。

背景: OBS 预签名 URL 查询串携带 AccessKeyId/Signature 等凭据，
requests 异常报文可能以下列形态携带 URL，未脱敏会随报文回显前端并写日志:
1. 完整 URL —— HTTPError: "... for url: https://host/path?query"
2. 裸路径形态（无 scheme）—— SSLError/ConnectionError:
   "... Max retries exceeded with url: /bucket/key?query"
"""

from jiuwen.plugin.handlers.handler_manager import _redact_urls

# 与真实 OBS 预签名同构的凭据样例（非真实凭据）
AK = "HPUAYQY82RWM7EYBN8SD"
SIGNATURE = "gm306gQ8u2j4zuz9CXIQzfiGaVQ%3D"

SSL_ERROR_MSG = (
    "SSLError: HTTPSConnectionPool(host='obs.example.com', port=443): "
    "Max retries exceeded with url: /bucket/key.png"
    f"?AccessKeyId={AK}&Expires=1792637913&Signature={SIGNATURE} "
    "(Caused by SSLError(CertificateError(\"hostname doesn't match\")))"
)

CONNECTION_ERROR_MSG = (
    "ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=8800): "
    "Max retries exceeded with url: /img1.png?token=secret-token-123 "
    "(Caused by NewConnectionError('<socket... failed>'))"
)

HTTP_ERROR_MSG = (
    "404 Client Error: File not found for url: "
    f"https://obs.example.com/file/x.png?AccessKeyId={AK}&Signature={SIGNATURE}"
)


class TestRedactUrlsFullUrlForm:
    """完整 URL（带 scheme）形态脱敏。"""

    @staticmethod
    def test_http_error_query_redacted():
        out = _redact_urls(HTTP_ERROR_MSG)
        assert AK not in out and SIGNATURE not in out
        assert "https://obs.example.com/file/x.png?***" in out

    @staticmethod
    def test_url_without_query_unchanged():
        msg = "for url: https://example.com/plain.png"
        assert _redact_urls(msg) == msg


class TestRedactUrlsBarePathForm:
    """裸路径形态（requests SSLError/ConnectionError 实测报文，无 scheme）。"""

    @staticmethod
    def test_ssl_error_presigned_query_redacted():
        out = _redact_urls(SSL_ERROR_MSG)
        assert AK not in out and SIGNATURE not in out
        assert "url: /bucket/key.png?***" in out

    @staticmethod
    def test_connection_error_query_redacted():
        out = _redact_urls(CONNECTION_ERROR_MSG)
        assert "secret-token-123" not in out
        assert "url: /img1.png?***" in out

    @staticmethod
    def test_mixed_forms_both_redacted():
        out = _redact_urls(SSL_ERROR_MSG + " | " + HTTP_ERROR_MSG)
        assert AK not in out and SIGNATURE not in out


class TestRedactUrlsNonUrlText:
    """非 URL 文本不受影响。"""

    @staticmethod
    def test_timeout_message_unchanged():
        msg = "Read timed out. (read timeout=60)"
        assert _redact_urls(msg) == msg

    @staticmethod
    def test_plain_text_unchanged():
        msg = "url is invalid: illegal ip address"
        assert _redact_urls(msg) == msg
