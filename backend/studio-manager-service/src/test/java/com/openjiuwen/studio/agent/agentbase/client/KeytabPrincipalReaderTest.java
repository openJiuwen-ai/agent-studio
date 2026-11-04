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
 * KeytabPrincipalReader 单测(评审 v4 2026-11-05:组件数 u16 修正后同步重写)。
 *
 * <p>构造符合 MIT keytab 标准字节流的黄金样本:
 * <ul>
 *   <li>组件数:u16(2字节,评审 v3 误用 u32/v4 修正)</li>
 *   <li>v1(0x0501):组件数含 realm(须+1)</li>
 *   <li>v2(0x0502):组件数不含 realm</li>
 *   <li>principal 去重:同一 principal 多 enctype 不重复</li>
 *   <li>截断/损坏:立即抛 IOException</li>
 * </ul>
 */
class KeytabPrincipalReaderTest {

    @TempDir
    Path tempDir;

    @Test
    void v2_singleEntry_parsesPrincipal() throws IOException {
        byte[] keytab = buildV2Keytab(buildV2Entry("user", 1, "REALM", 1, 1));
        Path file = tempDir.resolve("test.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"user@REALM"}, names);
    }

    @Test
    void v2_multiComponent_parsesJoinedPrincipal() throws IOException {
        byte[] keytab = buildV2Keytab(buildV2Entry("host", 2, "REALM", 2, 1));
        Path file = tempDir.resolve("multi.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"host/server.example.com@REALM"}, names);
    }

    @Test
    void v2_multipleEntries_deduplicatesSamePrincipal() throws IOException {
        // 同一 principal 两个 enctype(评审建议:去重,对齐 Kerby Set 语义)
        byte[] keytab = concat(
            v2Header(),
            v2LengthPrefix(buildV2Entry("user1", 1, "REALM", 1, 18)),  // enctype 18
            v2LengthPrefix(buildV2Entry("user1", 1, "REALM", 2, 17)),  // enctype 17
            v2LengthPrefix(buildV2Entry("user2", 1, "REALM", 1, 18)));
        Path file = tempDir.resolve("dedup.kt");
        Files.write(file, keytab);
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertArrayEquals(new String[]{"user1@REALM", "user2@REALM"}, names,
            "同一 principal 不同 enctype 须去重");
    }

    @Test
    void v2_patternFilter_returnsMatchingOnly() throws IOException {
        byte[] keytab = concat(
            v2Header(),
            v2LengthPrefix(buildV2Entry("host1", 1, "REALM", 1, 1)),
            v2LengthPrefix(buildV2Entry("user1", 1, "REALM", 2, 1)));
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
    void v2_noMatchingPrincipals_throwsIOException() throws IOException {
        byte[] keytab = buildV2Keytab(buildV2Entry("host1", 1, "REALM", 1, 1));
        Path file = tempDir.resolve("no-match.kt");
        Files.write(file, keytab);
        IOException ex = assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(),
                Pattern.compile("nomatch.*")));
        assertTrue(ex.getMessage().contains("no valid principals"),
            "应报空结果: " + ex.getMessage());
    }

    @Test
    void v2_truncatedEntry_throwsIOException() throws IOException {
        // 评审 v4:截断条目立即抛,不再静默返回部分结果
        byte[] keytab = concat(v2Header(), new byte[]{0, 0, 0, 50, 1, 2});
        Path file = tempDir.resolve("truncated.kt");
        Files.write(file, keytab);
        IOException ex = assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
        assertTrue(ex.getMessage().contains("exceeds file boundary"),
            "应报截断: " + ex.getMessage());
    }

    @Test
    void v2_partialThenTruncated_throwsIOException() throws IOException {
        // 评审 v4:前若干条目完整+末尾截断 → 抛 IOException(非静默返回部分结果)
        byte[] keytab = concat(
            v2Header(),
            v2LengthPrefix(buildV2Entry("user1", 1, "REALM", 1, 1)),
            new byte[]{0, 0, 0, 99, 5});  // entryLen=99 但只有1字节
        Path file = tempDir.resolve("partial-truncated.kt");
        Files.write(file, keytab);
        assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
    }

    // ==== keytab 字节构造(评审 v4:组件数用 u16=shortToBytes,非 u32)====

    private static byte[] buildV2Keytab(byte[] entry) {
        return concat(v2Header(), v2LengthPrefix(entry));
    }

    private static byte[] v2Header() {
        return new byte[]{0x05, 0x02};
    }

    private static byte[] v2LengthPrefix(byte[] entry) {
        return concat(intToBytes(entry.length), entry);
    }

    /**
     * 构造 v2 条目(不含长度前缀)。
     * 评审 v4:组件数用 u16(2字节),对齐 MIT keytab 标准格式。
     */
    private static byte[] buildV2Entry(String firstComponent, int componentCount, String realm,
            int nameType, int enctype) {
        byte[] countBytes = shortToBytes(componentCount);
        byte[] realmBytes = string16(realm);
        byte[] component1 = string16(firstComponent);
        byte[] component2 = componentCount > 1 ? string16("server.example.com") : new byte[0];
        byte[] typeBytes = intToBytes(nameType);
        byte[] timestamp = intToBytes(0);
        byte[] kvnoByte = new byte[]{0x01};
        byte[] enctypeBytes = shortToBytes(enctype);
        byte[] keylen = shortToBytes(1);
        byte[] key = new byte[]{0x01};
        return concat(countBytes, realmBytes, component1, component2, typeBytes,
            timestamp, kvnoByte, enctypeBytes, keylen, key);
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
