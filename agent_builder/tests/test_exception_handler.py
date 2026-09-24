# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""DEF-06 §7.3/§7.4: Builder Flask 异常 Handler 专项测试。

覆盖 @catch_exception 装饰器与 server.py 全局 errorhandler 的真实 Flask
client 调用链：legacy 码映射到 canonical 输出、未登记/``-1``/未知异常安全兜底、
未知异常 ERROR 级（非 DEBUG）、响应不含异常原文、i18n、request_id
body/Header 同值、装饰器不双响、全局父类 Handler 覆盖未装饰路由、
404/405 命中 Werkzeug Handler。
"""

import json
import logging

import pytest

from agent_builder.adapter.exception_bridge import JiuWenBaseException, JiuWenException
from agent_builder.serve.common.exception.exception_handler import ExceptionHandler
from agent_builder.serve.server import instance_app


def _build_app():
    """构建带真实 server.py errorhandler 的 Flask app（无 blueprint 依赖）。"""
    app = instance_app({"apps": {}})

    # --- 装饰器路由（@catch_exception）---
    @app.route("/dec/reg", methods=["GET"])
    @ExceptionHandler.catch_exception
    def _dec_reg():
        raise JiuWenBaseException(error_code=102155, message="job not found secret")

    @app.route("/dec/unreg", methods=["GET"])
    @ExceptionHandler.catch_exception
    def _dec_unreg():
        raise JiuWenBaseException(error_code=99999, message="unknown code")

    @app.route("/dec/minus1", methods=["GET"])
    @ExceptionHandler.catch_exception
    def _dec_minus1():
        raise JiuWenException("minus one boom")

    @app.route("/dec/unknown", methods=["GET"])
    @ExceptionHandler.catch_exception
    def _dec_unknown():
        raise RuntimeError("secret-token-xyz")

    # --- 装饰器路由：全部获准 legacy 码参数化 ---
    @app.route("/dec/legacy/<int:code>", methods=["GET"])
    @ExceptionHandler.catch_exception
    def _dec_legacy(code):
        raise JiuWenBaseException(error_code=code, message=f"legacy {code} detail")

    # --- 未装饰路由（走全局 errorhandler）---
    @app.route("/glob/biz", methods=["GET"])
    def _glob_biz():
        raise JiuWenBaseException(error_code=102156, message="status conflict")

    @app.route("/glob/unknown", methods=["GET"])
    def _glob_unknown():
        raise RuntimeError("global secret")

    return app


@pytest.fixture()
def client():
    return _build_app().test_client()


def _body(resp):
    return json.loads(resp.data)


# ------------------- §7.3 装饰器测试 -------------------


def test_decorator_registered_code_mapped_to_canonical(client):
    resp = client.get("/dec/reg", headers={"X-Request-Id": "rid-dec-reg"})
    assert resp.status_code == 404
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100007"
    assert body["request_id"] == "rid-dec-reg"
    for f in ("error_msg", "error_reason", "error_suggestion"):
        assert body[f], f"{f} non-empty"
    assert resp.headers.get("X-Request-Id") == "rid-dec-reg"
    # 异常原文不进响应
    assert "job not found secret" not in resp.data.decode()


def test_decorator_unregistered_code_fallback(client):
    resp = client.get("/dec/unreg", headers={"X-Request-Id": "rid-unreg"})
    assert resp.status_code == 500
    assert _body(resp)["error_code"] == "openjiuwen.13100004"


def test_decorator_minus_one_fallback(client):
    resp = client.get("/dec/minus1", headers={"X-Request-Id": "rid-m1"})
    assert resp.status_code == 500
    assert _body(resp)["error_code"] == "openjiuwen.13100004"


def test_decorator_unknown_exception_no_leak(client):
    resp = client.get("/dec/unknown", headers={"X-Request-Id": "rid-unk"})
    assert resp.status_code == 500
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100004"
    assert "secret-token-xyz" not in resp.data.decode()


def test_decorator_i18n_zh_and_en(client):
    zh = client.get("/dec/reg", headers={"X-Request-Id": "rid-zh", "x-language": "zh-cn"})
    en = client.get("/dec/reg", headers={"X-Request-Id": "rid-en", "x-language": "en-us"})
    zh_body = _body(zh)
    en_body = _body(en)
    assert zh_body["error_code"] == en_body["error_code"] == "openjiuwen.13100007"
    assert zh_body["error_msg"] != en_body["error_msg"]


@pytest.mark.parametrize("code,str_code,http_status", [
    (102154, "openjiuwen.13100006", 400), (102155, "openjiuwen.13100007", 404), (102156, "openjiuwen.13100008", 409),
    (102158, "openjiuwen.13100009", 500), (102159, "openjiuwen.13100010", 500), (102170, "openjiuwen.13100011", 500),
    (102213, "openjiuwen.13100012", 500), (102214, "openjiuwen.13100013", 500),
])
def test_decorator_all_legacy_codes_mapped_to_canonical(client, code, str_code, http_status):
    """§7.3: 全部 legacy 码经 Flask 装饰器请求链映射到 canonical 输出 + 目录 HTTP。"""
    resp = client.get(f"/dec/legacy/{code}", headers={"X-Request-Id": f"rid-{code}"})
    assert resp.status_code == http_status
    body = _body(resp)
    assert body["error_code"] == str_code
    assert body["request_id"] == f"rid-{code}"
    for f in ("error_msg", "error_reason", "error_suggestion"):
        assert body[f], f"{f} non-empty"
    assert f"legacy {code} detail" not in resp.data.decode()


def test_decorator_request_id_body_header_same(client):
    resp = client.get("/dec/reg", headers={"X-Request-Id": "rid-sync"})
    body = _body(resp)
    assert body["request_id"] == "rid-sync"
    assert resp.headers.get("X-Request-Id") == "rid-sync"


def test_decorator_unknown_logs_exactly_one_error_stack(client, caplog):
    """§6.4: 未知异常恰好一条 ERROR + exc_info（不再 DEBUG）。"""
    caplog.set_level(logging.DEBUG)
    client.get("/dec/unknown", headers={"X-Request-Id": "rid-unk"})
    error_stacks = [r for r in caplog.records
                    if r.levelno >= logging.ERROR and r.exc_info is not None]
    assert len(error_stacks) == 1, (
        f"unknown exception should log exactly one ERROR stack, got {len(error_stacks)}"
    )


def test_decorator_registered_logs_exactly_one_error_stack(client, caplog):
    """§6.4: 已登记业务异常恰好一条 ERROR + exc_info。"""
    caplog.set_level(logging.DEBUG)
    client.get("/dec/legacy/102155", headers={"X-Request-Id": "rid-biz-stack"})
    biz_error_stacks = [r for r in caplog.records if r.levelno >= logging.ERROR and r.exc_info is not None]
    biz_stacks = [r for r in biz_error_stacks if "JiuWenBaseException" in r.getMessage()]
    assert len(biz_stacks) == 1, (
        f"registered business exception should log exactly one ERROR stack, "
        f"got {len(biz_stacks)} (global handler double-fire?)"
    )


def test_decorator_consumes_exception_global_not_reached(client, caplog):
    """§6.3.3: 装饰器已消费的异常不再到达全局 Handler（不双响/不双日志）。"""
    caplog.set_level(logging.DEBUG)
    client.get("/dec/legacy/102155", headers={"X-Request-Id": "rid-once"})
    # 装饰器分支恰好一条 JiuWenBaseException ERROR（全局 Handler 不再记第二条）
    biz_errors = [r for r in caplog.records
                  if r.levelno >= logging.ERROR and "JiuWenBaseException" in r.getMessage()]
    assert len(biz_errors) == 1


# ------------------- §7.4 全局 Handler 测试 -------------------


def test_global_business_handler_hit(client):
    """未装饰路由抛 JiuWenBaseException → 命中全局父类 Handler。"""
    resp = client.get("/glob/biz", headers={"X-Request-Id": "rid-glob-biz"})
    assert resp.status_code == 409
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100008"
    assert body["request_id"] == "rid-glob-biz"
    assert resp.headers.get("X-Request-Id") == "rid-glob-biz"
    assert "status conflict" not in resp.data.decode()


def test_global_unknown_handler_hit(client):
    """未装饰路由抛未知异常 → 命中通用 Handler。"""
    resp = client.get("/glob/unknown", headers={"X-Request-Id": "rid-glob-unk"})
    assert resp.status_code == 500
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100004"
    assert "global secret" not in resp.data.decode()


def test_global_404_hits_werkzeug_handler(client):
    """404 命中 Werkzeug Handler，返回标准五字段（非 HTML）。"""
    resp = client.get("/nonexistent-route", headers={"X-Request-Id": "rid-404"})
    assert resp.status_code == 404
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100002"
    assert body["request_id"] == "rid-404"
    assert resp.headers.get("X-Request-Id") == "rid-404"
    # 不退回 HTML
    assert resp.is_json


def test_global_405_hits_werkzeug_handler(client):
    """405 命中 Werkzeug Handler。"""
    resp = client.post("/dec/reg", headers={"X-Request-Id": "rid-405"})
    assert resp.status_code == 405
    body = _body(resp)
    assert body["error_code"] == "openjiuwen.13100003"


def test_global_404_logs_warn_no_stack(client, caplog):
    """§6.4: 404 为 WARN 且不伪造 traceback。"""
    caplog.set_level(logging.DEBUG)
    client.get("/nonexistent-route", headers={"X-Request-Id": "rid-404-warn"})
    stacks = [r for r in caplog.records if r.exc_info is not None]
    assert not stacks, "404 must not carry a fabricated traceback"
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warns, "404 should log at WARN level"


def test_global_business_logs_exactly_one_stack(client, caplog):
    """§6.4: 全局业务异常恰好一条 ERROR + exc_info。"""
    caplog.set_level(logging.DEBUG)
    client.get("/glob/biz", headers={"X-Request-Id": "rid-glob-biz-stack"})
    stacks = [r for r in caplog.records
              if r.levelno >= logging.ERROR and r.exc_info is not None]
    assert len(stacks) == 1, (
        f"global business exception should log exactly one ERROR stack, "
        f"got {len(stacks)}"
    )


def test_p5_log01_no_secret_in_log_messages(client, caplog):
    """P5-LOG-01 COM-08: 异常正文不得进入日志基础消息（防 token/路径/下游正文泄漏）。

    /glob/unknown 抛 RuntimeError("global secret") → 全局 Exception handler
    （server.py _com03_flask_unknown_handler）记日志。断言基础 message 不含
    原始异常正文（exc_info=True 保留 traceback 供诊断,基础 message 只记 allowlist）。
    同样覆盖 /dec/legacy（@catch_exception JiuWenBaseException 正文）。
    """
    caplog.set_level(logging.DEBUG)
    client.get("/glob/unknown", headers={"X-Request-Id": "rid-log01-unknown"})
    client.get("/dec/legacy/102156", headers={"X-Request-Id": "rid-log01-legacy"})
    for rec in caplog.records:
        if rec.levelno >= logging.WARNING:
            assert "global secret" not in rec.getMessage(), (
                f"RuntimeError 原始正文泄漏进日志: {rec.getMessage()!r}")
            assert "status conflict" not in rec.getMessage(), (
                f"JiuWenBaseException 原始正文泄漏进日志: {rec.getMessage()!r}")


def test_global_unknown_logs_exactly_one_stack(client, caplog):
    """§6.4: 全局未知异常恰好一条 ERROR + exc_info。"""
    caplog.set_level(logging.DEBUG)
    client.get("/glob/unknown", headers={"X-Request-Id": "rid-glob-unk-stack"})
    stacks = [r for r in caplog.records
              if r.levelno >= logging.ERROR and r.exc_info is not None]
    assert len(stacks) == 1, (
        f"global unknown exception should log exactly one ERROR stack, "
        f"got {len(stacks)}"
    )
