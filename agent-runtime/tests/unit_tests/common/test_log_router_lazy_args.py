#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""UT for LogRouter.route_log lazy-formatting arg handling (G.LOG.01).

Pins the contract that lets call sites use stdlib %-style lazy formatting
together with ``simple_log``:

- explicit ``simple_log`` in non-verbose mode: the simple message is logged
  WITHOUT the msg's format args (simple_log never carries placeholders), so
  ``logger.debug("x %s", v, simple_log="x")`` must not format-error.
- no ``simple_log``: msg + args are forwarded for lazy %-formatting.
- verbose mode: msg + args are forwarded unchanged.
"""
import jiuwen.common.log.base as log_base


class _StubLogger:
    def __init__(self):
        self.calls = []

    def debug(self, msg, *args, **kwargs):
        self.calls.append((msg, args, kwargs))


def _wrapped(monkeypatch, verbose):
    monkeypatch.setenv("LOG_VERBOSE", "true" if verbose else "false")
    monkeypatch.setattr(log_base, "LOG_VERBOSE_MODE", verbose)
    stub = _StubLogger()
    router = log_base.LogRouter()
    return router.route_log(stub.debug), stub


def test_non_verbose_explicit_simple_log_drops_args(monkeypatch):
    wrapped, stub = _wrapped(monkeypatch, verbose=False)
    wrapped("loading ir data of %s", "child-1", simple_log="loading ir data of child")
    assert stub.calls == [("loading ir data of child", (), {"stacklevel": 1})]


def test_non_verbose_without_simple_log_keeps_lazy_args(monkeypatch):
    wrapped, stub = _wrapped(monkeypatch, verbose=False)
    wrapped("param extra: %s", "value")
    assert stub.calls == [("param extra: %s", ("value",), {"stacklevel": 1})]


def test_verbose_forwards_msg_with_args(monkeypatch):
    wrapped, stub = _wrapped(monkeypatch, verbose=True)
    wrapped("loading ir data of %s", "child-1", simple_log="loading ir data of child")
    assert stub.calls == [("loading ir data of %s", ("child-1",), {"stacklevel": 2})]


def test_non_verbose_drops_exc_info(monkeypatch):
    wrapped, stub = _wrapped(monkeypatch, verbose=False)
    wrapped("boom", exc_info=RuntimeError("x"))
    msg, _args, kwargs = stub.calls[0]
    assert msg == "boom"
    assert "exc_info" not in kwargs
