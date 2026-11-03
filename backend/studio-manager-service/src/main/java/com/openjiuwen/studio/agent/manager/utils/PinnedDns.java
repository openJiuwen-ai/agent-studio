/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import okhttp3.Dns;

/**
 * 校验通过的 DNS 钉死（消除校验/连接 TOCTOU，与 Python 侧
 * {@code pinned_https_resolution} 对齐）。
 *
 * <p>SSRF 校验（{@code UrlCheckUtils.checkUrlAndResolve}）与 OkHttp 实际连接
 * 各解析一次 DNS，两次之间攻击者可控的 DNS 可换址（rebinding：校验时解析
 * 公网、连接时解析内网）。调用方在校验通过后以 {@link #pin} 把
 * <strong>校验阶段</strong>解析到的地址按主机名钉入 {@link ThreadLocal}，
 * 本次连接期内 OkHttp 的 DNS 解析固定返回这些地址（多地址全量返回，
 * 保留连接层逐地址回退）；{@link #unpin} 在 finally 中清理。
 *
 * <p>未钉死的主机名/线程一律透传 {@link Dns#SYSTEM}——对不经过 pin 的
 * 既有流量零影响。仅对同步调用生效（{@code execute()} 在调用线程上做
 * DNS 解析）；异步调用的解析在 OkHttp 调度线程上，天然读不到本线程钉死。
 */
public final class PinnedDns implements Dns {
    private static final ThreadLocal<Map<String, List<InetAddress>>> PINS = new ThreadLocal<>();

    /**
     * 钉死 hostname 的解析结果（覆盖同主机名的既有钉死记录）。
     */
    public static void pin(String hostname, List<InetAddress> addresses) {
        Map<String, List<InetAddress>> pins = PINS.get();
        if (pins == null) {
            pins = new HashMap<>();
            PINS.set(pins);
        }
        pins.put(hostname, addresses);
    }

    /**
     * 清理本线程的全部钉死记录（下载结束的 finally 中调用）。
     */
    public static void unpin() {
        PINS.remove();
    }

    @Override
    public List<InetAddress> lookup(String hostname) throws UnknownHostException {
        Map<String, List<InetAddress>> pins = PINS.get();
        if (pins != null) {
            List<InetAddress> pinned = pins.get(hostname);
            if (pinned != null && !pinned.isEmpty()) {
                return pinned;
            }
        }
        return Dns.SYSTEM.lookup(hostname);
    }
}
