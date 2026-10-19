#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2026

"""pinned_https_resolution 回归测试。

覆盖三处 code review 修复：
1. 同 hostname 并发/嵌套使用时先退出者不得移除后退出者的钉死记录
2. IPv6 地址不因 inet_aton（仅 IPv4）抛 OSError 导致合法下载失败
3. AF_INET6 钉死解析返回四元组 sockaddr（协议约定）
"""

import socket
import threading

import pytest

from jiuwen.common.utils.utils import (
    _is_inner_ipaddr_v6,
    _orig_getaddrinfo,
    pinned_https_resolution,
    validate_and_keep_https_url,
)

# 确定性公网 IP 字面量——不用 example.com：它有多条 A 记录且 DNS 轮询返回顺序不定，
# 不同 getaddrinfo 调用会拿到不同 IP，比较绝对 IP 必然 flaky
PUBLIC_HOST = "8.8.8.8"
PUBLIC_V6 = "2001:4860:4860::8888"  # 公网 IPv6（Google DNS）


class TestPinnedResolutionBasic:
    """基本钉死与还原。"""

    @staticmethod
    def test_pin_and_restore():
        orig = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
        with pinned_https_resolution(PUBLIC_HOST):
            pinned = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
            assert pinned == orig
        # 退出后还原为原始解析
        assert socket.getaddrinfo is _orig_getaddrinfo
        after = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
        assert after == orig

    @staticmethod
    def test_other_host_unaffected():
        with pinned_https_resolution(PUBLIC_HOST):
            # 其它主机名走原解析（回环地址可解析）
            infos = socket.getaddrinfo("localhost", None)
            assert infos[0][4][0] in ("127.0.0.1", "::1")

    @staticmethod
    def test_inner_ipv4_blocked():
        with pytest.raises(ValueError):
            with pinned_https_resolution("127.0.0.1"):
                pass


class TestPinnedResolutionSameHostRefCount:
    """同 hostname 引用计数（H 项回归）。"""

    @staticmethod
    def test_nested_same_host_inner_exit_keeps_pin():
        with pinned_https_resolution(PUBLIC_HOST):
            outer_ip = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
            with pinned_https_resolution(PUBLIC_HOST):
                pass  # 内层退出
            # 内层退出后外层钉死仍在（修复前会被 pop 掉）
            still = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
            assert still == outer_ip
        assert socket.getaddrinfo is _orig_getaddrinfo

    @staticmethod
    def test_concurrent_threads_same_host():
        """两线程并发钉同一主机名，先退出者不影响后退出者。"""
        import time

        from jiuwen.common.utils.utils import _pinned_refcounts, _pinned_resolution_lock

        errors = []
        exit1_ok = threading.Event()  # 主线程通知线程1退出
        exited_done = threading.Event()  # 线程1已完整退出
        pinned = {}

        def thread1():
            try:
                with pinned_https_resolution(PUBLIC_HOST):
                    pinned.setdefault("ip", socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0])
                    exit1_ok.wait(timeout=15)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
            finally:
                exited_done.set()

        def thread2():
            try:
                with pinned_https_resolution(PUBLIC_HOST):
                    pinned.setdefault("ip", socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0])
                    exited_done.wait(timeout=15)  # 等线程1完整退出后验证
                    still = socket.getaddrinfo(PUBLIC_HOST, 443)[0][4][0]
                    assert still == pinned["ip"], "先退出线程移除了后退出者的钉死记录!"
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        t1 = threading.Thread(target=thread1)
        t2 = threading.Thread(target=thread2)
        t1.start()
        t2.start()
        # 等两个线程都进入钉死区（refcount >= 2）
        deadline = time.time() + 15
        while time.time() < deadline:
            with _pinned_resolution_lock:
                if _pinned_refcounts.get(PUBLIC_HOST, 0) >= 2:
                    break
            time.sleep(0.05)
        else:
            errors.append(AssertionError("两线程未同时进入钉死区（refcount 未到 2）"))

        exit1_ok.set()  # 通知线程1退出
        t1.join(timeout=15)
        t2.join(timeout=15)
        assert not errors, errors
        assert socket.getaddrinfo is _orig_getaddrinfo


class TestPinnedResolutionIpv6:
    """IPv6 双栈安全（M 项回归）。"""

    @staticmethod
    def test_inner_v6_classifier():
        assert _is_inner_ipaddr_v6("::1") is True  # 回环
        assert _is_inner_ipaddr_v6("fe80::1") is True  # 链路本地
        assert _is_inner_ipaddr_v6("fc00::1") is True  # 私有
        assert _is_inner_v6_public()
        assert _is_inner_ipaddr_v6("not-an-ip") is True  # fail-safe

    @staticmethod
    def test_ipv6_public_not_oserror():
        """公网 IPv6 不因 inet_aton 抛 OSError（合法下载不误杀）。"""
        with pinned_https_resolution(PUBLIC_V6):
            infos = socket.getaddrinfo(PUBLIC_V6, 443)
            sockaddr = infos[0][4]
            # AF_INET6 四元组 sockaddr
            assert len(sockaddr) == 4, f"IPv6 sockaddr 须四元组: {sockaddr}"
            assert sockaddr[0] == PUBLIC_V6
        assert socket.getaddrinfo is _orig_getaddrinfo

    @staticmethod
    def test_ipv6_loopback_blocked():
        with pytest.raises(ValueError):
            with pinned_https_resolution("::1"):
                pass


def _is_inner_v6_public():
    return _is_inner_ipaddr_v6("2001:4860:4860::8888") is False


class TestValidateHttpsUrlIpv6:
    """validate_and_keep_https_url 的 https 分支双栈可达性（M 项回归）。

    修复前：https 分支经 url_to_ip_protocol_and_port 的 gethostbyname
    （仅 A 记录）——纯 IPv6 字面量在进入钉死解析前就抛
    resolving IP address failed，IPv6 文件 URL 无法下载。
    """

    @staticmethod
    def test_https_ipv6_literal_passes_gate():
        url = f"https://[{PUBLIC_V6}]/file/x.png?sig=abc"
        valid, hostname = validate_and_keep_https_url(url)
        assert valid == url
        assert hostname == PUBLIC_V6

    @staticmethod
    def test_https_ipv6_inner_blocked():
        with pytest.raises(ValueError):
            validate_and_keep_https_url("https://[::1]/file/x.png")

    @staticmethod
    def test_https_ipv4_still_works():
        url = f"https://{PUBLIC_HOST}/file/x.png?sig=abc"
        valid, hostname = validate_and_keep_https_url(url)
        assert valid == url
        assert hostname == PUBLIC_HOST

    @staticmethod
    def test_https_ipv6_full_chain_validate_then_pin():
        """全链：validate（前置闸）→ pinned（钉死）均可达 IPv6。"""
        url = f"https://[{PUBLIC_V6}]/file/x.png"
        valid, hostname = validate_and_keep_https_url(url)
        assert hostname == PUBLIC_V6
        with pinned_https_resolution(hostname):
            infos = socket.getaddrinfo(PUBLIC_V6, 443)
            assert infos[0][4][0] == PUBLIC_V6
        assert socket.getaddrinfo is _orig_getaddrinfo


class TestPinnedGetaddrinfoParamCompat:
    """_pinned_getaddrinfo 对调用方参数的兼容（L 项回归）。"""

    @staticmethod
    def test_udp_query_delegates_to_original():
        with pinned_https_resolution(PUBLIC_HOST):
            # UDP 查询（type=SOCK_DGRAM）不是受保护的 TCP 连接，回退原解析
            udp_infos = socket.getaddrinfo(
                PUBLIC_HOST, 53, socket.AF_INET, socket.SOCK_DGRAM
            )
            assert all(i[1] == socket.SOCK_DGRAM for i in udp_infos)

    @staticmethod
    def test_matching_tcp_query_uses_pin():
        with pinned_https_resolution(PUBLIC_HOST):
            # 默认（AF_UNSPEC/SOCK_STREAM）解析返回钉死地址
            infos = socket.getaddrinfo(PUBLIC_HOST, 443)
            assert len(infos) == 1
            assert infos[0][0] == socket.AF_INET
            assert infos[0][1] == socket.SOCK_STREAM
            assert infos[0][4][0] == PUBLIC_HOST
