/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.client;

import org.apache.kerby.kerberos.kerb.keytab.Keytab;

import java.io.File;
import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * MIT keytab principal 读取器(镜像瘦身 1A,评审 v5 2026-11-05:
 * 手写二进制解析器废弃,改用 Apache Kerby kerb-util 库)。
 *
 * <p>背景:原经 hadoop-common 的 KerberosUtil 读取 keytab principal;
 * 去 hadoop 后 v1-v4 自写解析器连续暴露 u32/u16 组件数错读、截断
 * 静默返回、跨版本语义偏差等 bug——手写二进制格式解析不可靠。
 *
 * <p>v5 方案:Apache Kerby {@code kerb-util}(36KB)的 {@code Keytab.loadKeytab()}
 * 是 Hadoop 内部同款实现(战测成熟),一次性消除全部格式解析风险。
 *
 * <p>principal 字符串 = {@code 组件/...@REALM}(与原 KerberosUtil 输出一致)。
 * 空结果/解析失败抛 IOException(调用方沿用原异常路径)。
 */
public final class KeytabPrincipalReader {

    private KeytabPrincipalReader() {
    }

    /**
     * 读取 keytab 全部 principal 并按模式过滤(Kerby 解析+去重)。
     *
     * @param keytabFile keytab 文件路径
     * @param pattern 过滤模式(null 时不过滤)
     * @return 匹配且去重后的 principal 数组(可能为空,不为 null)
     * @throws IOException 文件不可读或无匹配 principal
     */
    public static String[] getPrincipalNames(String keytabFile, Pattern pattern) throws IOException {
        Keytab keytab;
        try {
            keytab = Keytab.loadKeytab(new File(keytabFile));
        } catch (IOException | RuntimeException e) {
            // Kerby 文件不存在抛 IllegalArgumentException,格式非法抛 IOException——
            // 统一包装为 IOException(契约:所有失败都走 IOException)
            throw new IOException("fail to load keytab: " + keytabFile + ", cause: " + e.getMessage(), e);
        }
        Set<String> names = new LinkedHashSet<>();
        keytab.getPrincipals().forEach(principal -> {
            String name = principal.getName();
            if (pattern == null || pattern.matcher(name).matches()) {
                names.add(name);
            }
        });
        if (names.isEmpty()) {
            throw new IOException("no valid principals found in keytab: " + keytabFile);
        }
        return names.toArray(new String[0]);
    }
}
