#  !/usr/bin/env python
#  -*- coding: UTF-8 -*-
#  Copyright c) Huawei Technologies Co., Ltd. 2025-2026

"""pinned_https_resolution 回归测试。

覆盖多处 code review 修复：
1. 同 hostname 并发/嵌套使用时先退出者不得移除后退出者的钉死记录
2. IPv6 地址不因 inet_aton（仅 IPv4）抛 OSError 导致合法下载失败
3. AF_INET6 钉死解析返回四元组 sockaddr（协议约定）
4. 169.254.0.0/16（链路本地/云元数据 169.254.169.254）拦截——与
   Java 侧 urlCheckUtils.isInternalIp（isLinkLocalAddress）口径对齐
5. 多地址钉死：连接期保留全部校验地址（双栈主机多地址回退），
   显式异族 TCP 查询 fail-closed
6. 新校验路径 IPv4/IPv6 统一走 _is_inner_ipaddr_strict（ipaddress
   全家桶：组播/保留/0.0.0.0/8/文档段；CGNAT 100.64/10 两侧一致放行）
"""

import socket
import threading

import pytest

from jiuwen.common.utils.utils import (
    _is_inner_ipaddr_strict,
    _orig_getaddrinfo,
    _pinned_entries,
    _pinned_resolution_lock,
    is_inner_ipaddress,
    pinned_https_resolution,
    url_to_ip_with_protocol_and_port,
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
        assert _is_inner_ipaddr_strict("::1") is True  # 回环
        assert _is_inner_ipaddr_strict("fe80::1") is True  # 链路本地
        assert _is_inner_ipaddr_strict("fc00::1") is True  # 私有
        assert _is_inner_v6_public()
        assert _is_inner_ipaddr_strict("not-an-ip") is True  # fail-safe

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
    return _is_inner_ipaddr_strict("2001:4860:4860::8888") is False


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


class TestInnerIp169LinkLocal:
    """169.254.0.0/16（链路本地/云元数据）拦截（H 项回归）。

    修复前 Python 侧只拦 10/8、172.16/12、192.168/16、127/8、0.0.0.0，
    云元数据 169.254.169.254 可穿透气体检——Java 侧 isInternalIp 经
    isLinkLocalAddress 早已拦截，两侧口径不一致。
    """

    @staticmethod
    def test_is_inner_ipaddress_link_local():
        assert is_inner_ipaddress("169.254.169.254") is True
        assert is_inner_ipaddress("169.254.0.1") is True
        assert is_inner_ipaddress("169.254.255.255") is True
        # 段外不误伤
        assert is_inner_ipaddress("169.255.0.1") is False
        assert is_inner_ipaddress("8.8.8.8") is False

    @staticmethod
    def test_https_metadata_url_blocked():
        with pytest.raises(ValueError):
            validate_and_keep_https_url(
                "https://169.254.169.254/latest/meta-data/"
            )

    @staticmethod
    def test_http_metadata_url_blocked():
        with pytest.raises(ValueError):
            url_to_ip_with_protocol_and_port(
                "http://169.254.169.254/latest/meta-data/"
            )

    @staticmethod
    def test_pinned_metadata_blocked():
        with pytest.raises(ValueError):
            with pinned_https_resolution("169.254.169.254"):
                pass

    @staticmethod
    def test_v4_mapped_link_local_blocked():
        # IPv4 映射 IPv6（::ffff:a.b.c.d）按映射的 IPv4 判定
        assert _is_inner_ipaddr_strict("::ffff:169.254.169.254") is True
        assert _is_inner_ipaddr_strict("::ffff:8.8.8.8") is False

    @staticmethod
    def test_strict_ipv4_full_family():
        """新校验路径 IPv4 统一走 ipaddress 全家桶（严于 Java 对齐口径）。"""
        # 旧口径（is_inner_ipaddress，Java isInternalIp 对齐）不拦的段
        assert _is_inner_ipaddr_strict("224.0.0.1") is True  # 组播 224/4
        assert _is_inner_ipaddr_strict("239.255.255.255") is True
        assert _is_inner_ipaddr_strict("240.0.0.1") is True  # 保留 240/4
        assert _is_inner_ipaddr_strict("0.1.2.3") is True  # 0.0.0.0/8 全段
        assert _is_inner_ipaddr_strict("192.0.2.1") is True  # 文档段 TEST-NET-1
        # 公网与 CGNAT 放行（100.64/10 与 Java/旧口径一致不拦）
        assert _is_inner_ipaddr_strict("8.8.8.8") is False
        assert _is_inner_ipaddr_strict("100.64.1.1") is False
        # 旧口径的既有拦截在新口径同样成立
        assert _is_inner_ipaddr_strict("10.1.1.1") is True
        assert _is_inner_ipaddr_strict("169.254.169.254") is True


class TestPinnedMultiAddress:
    """多地址钉死（L 项回归）：连接期保留多地址回退。

    修复前只钉死 getaddrinfo 返回的 infos[0]——双栈主机首个 AAAA/A
    不可达时 https 下载失败，而校验阶段本能看到全部地址。
    """

    HOST = "multi.pinned.test"

    @staticmethod
    def _inject(host, entries):
        with _pinned_resolution_lock:
            _pinned_entries[host] = entries

    @staticmethod
    def _remove(host):
        with _pinned_resolution_lock:
            _pinned_entries.pop(host, None)

    def test_all_addresses_pinned_and_returned(self):
        v6 = "2001:4860:4860::8888"
        with pinned_https_resolution(PUBLIC_HOST):
            self._inject(
                self.HOST,
                [
                    (socket.AF_INET, ("93.184.216.34", 0)),
                    (socket.AF_INET6, (v6, 0, 0, 0)),
                ],
            )
            try:
                # AF_UNSPEC（默认）返回全部钉死地址，保序——连接层可逐个尝试
                infos = socket.getaddrinfo(self.HOST, 443)
                assert [i[4][0] for i in infos] == ["93.184.216.34", v6]
                assert infos[0][0] == socket.AF_INET
                assert infos[1][0] == socket.AF_INET6
                # AF_INET6 sockaddr 四元组
                assert len(infos[1][4]) == 4
                assert infos[1][4][1] == 443
            finally:
                self._remove(self.HOST)

    def test_family_filter_returns_only_matching(self):
        v6 = "2001:4860:4860::8888"
        with pinned_https_resolution(PUBLIC_HOST):
            self._inject(
                self.HOST,
                [
                    (socket.AF_INET, ("93.184.216.34", 0)),
                    (socket.AF_INET6, (v6, 0, 0, 0)),
                ],
            )
            try:
                v4_only = socket.getaddrinfo(
                    self.HOST, 443, socket.AF_INET, socket.SOCK_STREAM
                )
                assert len(v4_only) == 1
                assert v4_only[0][0] == socket.AF_INET
                assert v4_only[0][4][0] == "93.184.216.34"
                v6_only = socket.getaddrinfo(self.HOST, 443, socket.AF_INET6)
                assert len(v6_only) == 1
                assert v6_only[0][4][0] == v6
            finally:
                self._remove(self.HOST)

    def test_family_mismatch_fails_closed(self):
        # 钉死记录只有 AF_INET6，显式 AF_INET 的 TCP 查询 fail-closed
        # （gaierror）——回退原解析会在钉死窗口内重新引入未校验地址，
        # DNS rebinding 可经家族切换绕过校验
        with pinned_https_resolution(PUBLIC_HOST):
            self._inject(
                self.HOST, [(socket.AF_INET6, ("2001:4860:4860::8888", 0, 0, 0))]
            )
            try:
                with pytest.raises(socket.gaierror):
                    socket.getaddrinfo(self.HOST, 443, socket.AF_INET)
            finally:
                self._remove(self.HOST)

    def test_udp_query_still_delegates(self):
        # 多地址形态下 UDP 查询仍回退原解析（非受保护连接）。注入的
        # 假主机名真实解析必然 gaierror——这正是"已回退原解析"的证明：
        # 若被钉死逻辑接管，会返回注入的 sockaddr 而不抛错
        with pinned_https_resolution(PUBLIC_HOST):
            self._inject(
                self.HOST, [(socket.AF_INET, ("93.184.216.34", 0))]
            )
            try:
                with pytest.raises(socket.gaierror):
                    socket.getaddrinfo(
                        self.HOST, 53, socket.AF_INET, socket.SOCK_DGRAM
                    )
            finally:
                self._remove(self.HOST)

    @staticmethod
    def test_multi_socktype_resolution_deduped():
        """同 IP 多 socktype 形态（glibc 字面量返回 STREAM/DGRAM/RAW 三条，
        Windows 仅 1 条）按 (family, ip) 去重——不去重则连接期解析返回
        重复条目（Linux CI 上 len==1 断言炸）。
        """
        real_getaddrinfo = socket.getaddrinfo

        def fake_getaddrinfo(host, port, *args, **kwargs):
            # 模拟 glibc 对 IPv4 字面量的 port=None 解析
            return [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "",
                 ("93.184.216.34", 0)),
                (socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, "",
                 ("93.184.216.34", 0)),
                (socket.AF_INET, socket.SOCK_RAW, 0, "",
                 ("93.184.216.34", 0)),
            ]

        socket.getaddrinfo = fake_getaddrinfo
        try:
            with pinned_https_resolution("multi-socktype.test"):
                infos = socket.getaddrinfo("multi-socktype.test", 443)
                assert len(infos) == 1, infos
                assert infos[0][0] == socket.AF_INET
                assert infos[0][1] == socket.SOCK_STREAM
                assert infos[0][4][0] == "93.184.216.34"
        finally:
            socket.getaddrinfo = real_getaddrinfo


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
