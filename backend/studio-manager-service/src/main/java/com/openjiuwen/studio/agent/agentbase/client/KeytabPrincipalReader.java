/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.client;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * MIT keytab 文件 principal 读取器(镜像瘦身第一部分 1A,2026-11-04)。
 *
 * <p>背景:原经 hadoop-common 的
 * {@code org.apache.hadoop.security.authentication.util.KerberosUtil.getPrincipalNames}
 * 读取 keytab principal;去除 hadoop 依赖后改为内置解析(文件整体读入后按格式切片,
 * keytab 为 KB 级小文件)。
 *
 * <p>keytab 二进制格式(MIT krb5 通用格式,JDK ktab / MIT ktutil / Windows ktpass 均兼容):
 * <pre>
 * u16 文件版本(0x0501 或 0x0502)
 * 重复条目:
 *   版本 0x0502 时先有 u32 entryLen(0 或到 EOF 结束)
 *   u32 组件数
 *   域 realm(u16 len + bytes)
 *   组件数 × 组件(u16 len + bytes)
 *   u32 principal 类型
 *   u32 时间戳、u8 kvno、u16 加密类型、u16 密钥长度、密钥(本读取器跳过)
 * </pre>
 * principal 字符串 = {@code 组件1/组件2/...@REALM}(与 KerberosUtil 输出形态一致,
 * 供 Kerberos LoginModule 的 principal 选项使用)。解析失败抛 IOException
 * (调用方沿用原"Fail to get principal"日志与异常路径)。
 */
public final class KeytabPrincipalReader {

    private static final int KEYTAB_VNO_1 = 0x0501;
    private static final int KEYTAB_VNO_2 = 0x0502;
    private static final int MAX_COMPONENTS = 255;
    private static final int MAX_PART_LENGTH = 4096;

    private KeytabPrincipalReader() {
    }

    /**
     * 读取 keytab 全部 principal 并按模式过滤。
     *
     * @param keytabFile keytab 文件路径
     * @param pattern 过滤模式(null 时不过滤)
     * @return 匹配的 principal 数组(可能为空,不为 null)
     * @throws IOException 文件不可读或版本非法
     */
    public static String[] getPrincipalNames(String keytabFile, Pattern pattern) throws IOException {
        byte[] file = Files.readAllBytes(Paths.get(keytabFile));
        if (file.length < 2) {
            throw new IOException("keytab file too short: " + keytabFile);
        }
        int version = ((file[0] & 0xFF) << 8) | (file[1] & 0xFF);
        if (version != KEYTAB_VNO_1 && version != KEYTAB_VNO_2) {
            throw new IOException("unsupported keytab version: 0x" + Integer.toHexString(version));
        }
        List<String> names = new ArrayList<>();
        int pos = 2;
        while (pos < file.length) {
            if (version == KEYTAB_VNO_2) {
                if (pos + 4 > file.length) {
                    break;
                }
                int entryLen = getInt(file, pos);
                pos += 4;
                if (entryLen <= 0 || pos + entryLen > file.length) {
                    break;
                }
                addIfMatches(names, pattern, parsePrincipal(file, pos));
                pos += entryLen;
            } else {
                // 0x0501:无长度前缀,逐条目推进
                int next = addV1Entry(names, pattern, file, pos);
                if (next < 0) {
                    break;
                }
                pos = next;
            }
        }
        return names.toArray(new String[0]);
    }

    private static void addIfMatches(List<String> names, Pattern pattern, String principal) {
        if (principal != null && (pattern == null || pattern.matcher(principal).matches())) {
            names.add(principal);
        }
    }

    /**
     * 从 entry 起始位置解析 principal(组件数+realm+组件)。
     * 返回 null 表示该位置不是合法 principal 条目。
     */
    private static String parsePrincipal(byte[] file, int pos) {
        int count = getInt(file, pos);
        if (count <= 0 || count > MAX_COMPONENTS) {
            return null;
        }
        int p = pos + 4;
        int realmEnd = readString16End(file, p);
        if (realmEnd < 0) {
            return null;
        }
        String realm = new String(file, p + 2, realmEnd - p - 2, StandardCharsets.UTF_8);
        p = realmEnd;
        List<String> components = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            int end = readString16End(file, p);
            if (end < 0) {
                return null;
            }
            components.add(new String(file, p + 2, end - p - 2, StandardCharsets.UTF_8));
            p = end;
        }
        return String.join("/", components) + "@" + realm;
    }

    /**
     * v1(0x0501)条目:解析 principal 并越过其后字段(类型+时间戳+kvno+加密类型+密钥)。
     *
     * @return 下一条目起始位置;-1 表示当前条目非法或缓冲越界
     */
    private static int addV1Entry(List<String> names, Pattern pattern, byte[] file, int pos) {
        String principal = parsePrincipal(file, pos);
        if (principal == null) {
            return -1;
        }
        int count = getInt(file, pos);
        int p = pos + 4;
        p = readString16End(file, p);
        for (int i = 0; i < count; i++) {
            p = readString16End(file, p);
        }
        if (p < 0) {
            return -1;
        }
        // u32 类型 + u32 时间戳 + u8 kvno + u16 加密类型 = 11
        p += 11;
        if (p + 2 > file.length) {
            return -1;
        }
        int keyLen = ((file[p] & 0xFF) << 8) | (file[p + 1] & 0xFF);
        p += 2 + keyLen;
        if (p > file.length) {
            return -1;
        }
        addIfMatches(names, pattern, principal);
        return p;
    }

    private static int getInt(byte[] file, int pos) {
        if (pos + 4 > file.length) {
            return -1;
        }
        return ((file[pos] & 0xFF) << 24) | ((file[pos + 1] & 0xFF) << 16)
                | ((file[pos + 2] & 0xFF) << 8) | (file[pos + 3] & 0xFF);
    }

    /**
     * u16 长度前缀字符串的结束位置;负值表示长度非法或越界。
     */
    private static int readString16End(byte[] file, int pos) {
        if (pos + 2 > file.length) {
            return -1;
        }
        int len = ((file[pos] & 0xFF) << 8) | (file[pos + 1] & 0xFF);
        if (len < 0 || len > MAX_PART_LENGTH || pos + 2 + len > file.length) {
            return -1;
        }
        return pos + 2 + len;
    }
}
