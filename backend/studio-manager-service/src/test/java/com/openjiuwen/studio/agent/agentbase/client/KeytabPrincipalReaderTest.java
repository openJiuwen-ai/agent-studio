/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.client;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Pattern;

/**
 * KeytabPrincipalReader 单测(评审修订 2026-11-04):构造 0x0501/0x0502
 * keytab 字节流验证解析——principal 字符串、多条目、模式过滤、
 * 非法输入 fail-fast。
 */
class KeytabPrincipalReaderTest {

    @TempDir
    Path tempDir;

    @Test
    void v2_singleEntry_parsesPrincipal() throws IOException {
        // keytab 0x0502:1 条目,principal = "user@REALM"
        byte[] keytab = buildV2Keytab(buildEntry("user", 1, "REALM", 1, 1));
        Path file = tempDir.resolve("test.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"user@REALM"}, names);
    }

    @Test
    void v2_multiComponent_parsesJoinedPrincipal() throws IOException {
        // principal = "host/server.example.com@REALM"(2 组件)
        byte[] keytab = buildV2Keytab(buildEntry("host", 2, "REALM", 2, 1));
        Path file = tempDir.resolve("multi.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"host/server.example.com@REALM"}, names);
    }

    @Test
    void v2_multipleEntries_returnsAll() throws IOException {
        byte[] keytab = concat(buildV2KeytabHeader(),
            lengthPrefix(buildEntry("user1", 1, "REALM", 1, 1)),
            lengthPrefix(buildEntry("user2", 1, "REALM", 2, 1)));
        Path file = tempDir.resolve("multi-entry.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"user1@REALM", "user2@REALM"}, names);
    }

    @Test
    void v2_patternFilter_returnsMatchingOnly() throws IOException {
        byte[] keytab = concat(buildV2KeytabHeader(),
            lengthPrefix(buildEntry("host1", 1, "REALM", 1, 1)),
            lengthPrefix(buildEntry("user1", 1, "REALM", 2, 1)));
        Path file = tempDir.resolve("filter.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(),
            Pattern.compile("user.*"));
        assertArrayEquals(new String[]{"user1@REALM"}, names);
    }

    @Test
    void v2_emptyFile_throwsIOException() {
        Path file = tempDir.resolve("empty.kt");
        assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
    }

    @Test
    void v2_invalidVersion_throwsIOException() throws IOException {
        Path file = tempDir.resolve("bad-version.kt");
        Files.write(file, new byte[]{0x05, 0x03, 0, 0, 0, 0});
        IOException ex = assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
        assertTrue(ex.getMessage().contains("unsupported keytab version"),
            "应报版本非法: " + ex.getMessage());
    }

    @Test
    void v2_noMatchingPrincipals_throwsIOExceptionNotEmptyArray() throws IOException {
        // 评审修订:空结果(无匹配 principal)须抛 IOException 而非返回空数组——
        // 调用方 [0] 取首元素,空数组会 AIOOBE 绕过外层 catch
        byte[] keytab = concat(buildV2KeytabHeader(),
            lengthPrefix(buildEntry("host1", 1, "REALM", 1, 1)));
        Path file = tempDir.resolve("no-match.kt");
        Files.write(file, keytab);
        IOException ex = assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(),
                Pattern.compile("nomatch.*")));
        assertTrue(ex.getMessage().contains("no valid principals"),
            "应报空结果: " + ex.getMessage());
    }

    @Test
    void v2_truncatedFile_throwsIOExceptionNotEmptyArray() throws IOException {
        // 评审修订:截断文件(条目不完整)也须抛 IOException
        byte[] keytab = concat(buildV2KeytabHeader(), new byte[]{0, 0, 0, 50, 1, 2}); // entryLen=50 但只有2字节
        Path file = tempDir.resolve("truncated.kt");
        Files.write(file, keytab);
        assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
    }

    // ==== keytab 字节构造 ====

    private static byte[] buildV2Keytab(byte[] entry) {
        return concat(buildV2KeytabHeader(), lengthPrefix(entry));
    }

    private static byte[] buildV2KeytabHeader() {
        return new byte[]{0x05, 0x02};
    }

    private static byte[] lengthPrefix(byte[] entry) {
        return concat(intToBytes(entry.length), entry);
    }

    /**
     * 构造 v2 条目(不含长度前缀):组件数 + realm + 组件 + 类型 + 时间戳 + kvno + 加密类型 + 密钥。
     */
    private static byte[] buildEntry(String firstComponent, int componentCount, String realm,
            int nameType, int kvno) {
        byte[] countBytes = intToBytes(componentCount);
        byte[] realmBytes = string16(realm);
        byte[] component1 = string16(firstComponent);
        byte[] component2 = componentCount > 1 ? string16("server.example.com") : new byte[0];
        byte[] typeBytes = intToBytes(nameType);
        byte[] timestamp = intToBytes(0);
        byte[] kvnoByte = new byte[]{(byte) kvno};
        byte[] enctype = shortToBytes(18);
        byte[] keylen = shortToBytes(1);
        byte[] key = new byte[]{0x01};
        return concat(countBytes, realmBytes, component1, component2, typeBytes,
            timestamp, kvnoByte, enctype, keylen, key);
    }

    private static byte[] intToBytes(int value) {
        return new byte[]{
            (byte) (value >> 24), (byte) (value >> 16), (byte) (value >> 8), (byte) value};
    }

    private static byte[] shortToBytes(int value) {
        return new byte[]{(byte) (value >> 8), (byte) value};
    }

    private static byte[] string16(String s) {
        byte[] strBytes = s.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        return concat(shortToBytes(strBytes.length), strBytes);
    }

    private static byte[] concat(byte[]... arrays) {
        int total = 0;
        for (byte[] a : arrays) {
            total += a.length;
        }
        byte[] result = new byte[total];
        int pos = 0;
        for (byte[] a : arrays) {
            System.arraycopy(a, 0, result, pos, a.length);
            pos += a.length;
        }
        return result;
    }
}
