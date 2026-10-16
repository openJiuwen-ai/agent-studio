# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""COM-07A §4.2: SseTerminalGuard 成功终态 try_end() 与互斥测试。"""

import threading

from agent_builder.common.error_contract.stream_state import (
    SseTerminalGuard,
    StreamState,
)


def test_try_end_from_streaming_succeeds():
    g = SseTerminalGuard()
    assert g.begin_streaming() is True
    assert g.try_end() is True
    assert g.state == StreamState.ENDED


def test_try_end_second_call_returns_false():
    g = SseTerminalGuard()
    g.begin_streaming()
    assert g.try_end() is True
    assert g.try_end() is False  # 已 ENDED


def test_try_end_from_not_started_returns_false():
    g = SseTerminalGuard()
    assert g.try_end() is False
    assert g.state == StreamState.NOT_STARTED


def test_try_end_after_try_send_error_returns_false():
    """error 终态后 END 不得再获权(error/END 互斥)。"""
    g = SseTerminalGuard()
    g.begin_streaming()
    assert g.try_send_error() is True  # → TERMINATED
    assert g.try_end() is False
    assert g.state == StreamState.TERMINATED


def test_try_send_error_after_try_end_returns_false():
    """END 终态后 error 不得再获权。"""
    g = SseTerminalGuard()
    g.begin_streaming()
    assert g.try_end() is True  # → ENDED
    assert g.try_send_error() is False
    assert g.state == StreamState.ENDED


def test_cancel_after_try_end_does_not_overwrite():
    """ENDED 终态不被 cancel 覆盖。"""
    g = SseTerminalGuard()
    g.begin_streaming()
    g.try_end()
    g.cancel()
    assert g.state == StreamState.ENDED


def test_try_end_after_cancel_returns_false():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.cancel()
    assert g.try_end() is False
    assert g.state == StreamState.CANCELLED


def test_allow_message_false_after_end():
    g = SseTerminalGuard()
    g.begin_streaming()
    g.try_end()
    assert g.allow_message() is False


def test_concurrent_try_end_exactly_one_winner():
    """并发 try_end:恰好一个赢家。"""
    g = SseTerminalGuard()
    g.begin_streaming()
    results = []
    barrier = threading.Barrier(8)

    def race():
        barrier.wait()
        results.append(g.try_end())

    threads = [threading.Thread(target=race) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(results) == 1
    assert g.state == StreamState.ENDED


def test_concurrent_try_end_vs_try_send_error_one_terminal():
    """END 与 error 并发:恰好一个终态。"""
    g = SseTerminalGuard()
    g.begin_streaming()
    ends = []
    errors = []
    barrier = threading.Barrier(2)

    def race_end():
        barrier.wait()
        ends.append(g.try_end())

    def race_error():
        barrier.wait()
        errors.append(g.try_send_error())

    t1 = threading.Thread(target=race_end)
    t2 = threading.Thread(target=race_error)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert sum(ends) + sum(errors) == 1
    assert g.state in (StreamState.ENDED, StreamState.TERMINATED)
