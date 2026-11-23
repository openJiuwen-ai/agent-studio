#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""UT for LogRouter.route_log lazy-formatting + COM-08 always-safe contract.

COM-08：route_log 不按级别/开关分支 msg/exc_info——always-safe：
simple_log 作基础消息、exc_info 始终到达底层 logger。
本测试 pin 该契约：

- simple_log 在场 → 用 simple_log，丢弃 msg 的惰性格式化参数（避免占位符错配）。
- 无 simple_log → 转发 msg + args（惰性 %-format）。
- exc_info 始终保留。
"""
import jiuwen.common.log.base as log_base


class _StubLogger:
    def __init__(self):
        self.calls = []

    def debug(self, msg, *args, **kwargs):
        self.calls.append((msg, args, kwargs))


def _wrapped():
    stub = _StubLogger()
    router = log_base.LogRouter()
    return router.route_log(stub.debug), stub


def test_simple_log_present_drops_msg_args():
    """simple_log 在场 → 用 simple_log，丢弃 msg 格式参数（占位符错配防护）。"""
    wrapped, stub = _wrapped()
    wrapped("loading ir data of %s", "child-1", simple_log="loading ir data of child")
    assert stub.calls == [("loading ir data of child", (), {"stacklevel": 2})]


def test_no_simple_log_keeps_lazy_args():
    """无 simple_log → 转发 msg + args（惰性 %-format）。"""
    wrapped, stub = _wrapped()
    wrapped("param extra: %s", "value")
    assert stub.calls == [("param extra: %s", ("value",), {"stacklevel": 2})]


def test_exc_info_always_kept():
    """COM-08: exc_info 始终到达底层 logger。"""
    wrapped, stub = _wrapped()
    err = RuntimeError("x")
    wrapped("boom", exc_info=err)
    msg, _args, kwargs = stub.calls[0]
    assert msg == "boom"
    assert kwargs.get("exc_info") is err
