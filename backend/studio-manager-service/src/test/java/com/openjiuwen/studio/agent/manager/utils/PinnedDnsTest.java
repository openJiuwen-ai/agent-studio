/* Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

/**
 * PinnedDns 回归测试：校验/连接 DNS TOCTOU 钉死（FEAT-073，与 Python 侧
 * pinned_https_resolution 对齐的 Java 侧实现）。
 */
class PinnedDnsTest {
    /** RFC 6761 保留 TLD，真实解析必然失败——用于区分"钉死"与"系统解析" */
    private static final String FAKE_HOST = "pinned-dns-unit-test.invalid";

    private final PinnedDns pinnedDns = new PinnedDns();

    @AfterEach
    void cleanup() {
        PinnedDns.unpin();
    }

    @Test
    void testLookupReturnsPinnedAddresses() throws UnknownHostException {
        // 多地址全量钉死（保留连接层逐地址回退），顺序保持
        List<InetAddress> pinned = List.of(
            InetAddress.getByName("8.8.8.8"),
            InetAddress.getByName("2001:4860:4860::8888"));
        PinnedDns.pin(FAKE_HOST, pinned);
        assertEquals(pinned, pinnedDns.lookup(FAKE_HOST));
    }

    @Test
    void testUnpinFallsBackToSystem() throws UnknownHostException {
        List<InetAddress> pinned = List.of(InetAddress.getByName("8.8.8.8"));
        PinnedDns.pin(FAKE_HOST, pinned);
        assertEquals(pinned, pinnedDns.lookup(FAKE_HOST));
        PinnedDns.unpin();
        // .invalid 保留域真实解析必然失败——证明已回退系统解析（钉死已清理）
        assertThrows(UnknownHostException.class, () -> pinnedDns.lookup(FAKE_HOST));
    }

    @Test
    void testUnpinnedHostDelegatesToSystem() throws UnknownHostException {
        PinnedDns.pin(FAKE_HOST, List.of(InetAddress.getByName("8.8.8.8")));
        // 未钉死的主机名透传系统解析（localhost 本地可解析不抛错）
        pinnedDns.lookup("localhost");
    }

    @Test
    void testThreadIsolation() throws Exception {
        // ThreadLocal 语义：其它线程读不到本线程的钉死记录，
        // 走系统解析（.invalid 必然 UnknownHostException）
        PinnedDns.pin(FAKE_HOST, List.of(InetAddress.getByName("8.8.8.8")));
        AtomicReference<Exception> otherThreadFailure = new AtomicReference<>();
        Thread thread = new Thread(() -> {
            try {
                pinnedDns.lookup(FAKE_HOST);
            } catch (UnknownHostException e) {
                otherThreadFailure.set(e);
            }
        });
        thread.start();
        thread.join(5000);
        assertTrue(otherThreadFailure.get() instanceof UnknownHostException,
            "其它线程不应看到本线程的钉死记录");
    }
}
