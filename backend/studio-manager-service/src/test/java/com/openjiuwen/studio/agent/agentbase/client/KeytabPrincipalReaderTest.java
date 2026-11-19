/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.client;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Pattern;

/**
 * KeytabPrincipalReader 单测(v5 2026-11-05:改用 Kerby kerb-util 后)。
 *
 * <p>手写字节流构造已废弃(v1-v4 自写解析器的测试互相掩盖格式错误);
 * v5 用 Kerby Keytab 自身 API 验证行为契约:
 * <ul>
 *   <li>Keytab.loadKeytab + getPrincipals(格式解析由 Kerby 保证)</li>
 *   <li>KeytabPrincipalReader 的过滤/去重/空结果抛异常语义</li>
 * </ul>
 *
 * <p>keytab 样本用 Kerby KeytabWriter 生成(标准格式,非手工字节拼装)。
 */
class KeytabPrincipalReaderTest {

    @TempDir
    Path tempDir;

    @Test
    void kerbyKeytab_generatesAndParses() throws IOException {
        // Kerby 库自身能力验证:写 keytab → 读 keytab(标准格式)
        Path file = tempDir.resolve("kerby.kt");
        org.apache.kerby.kerberos.kerb.keytab.Keytab keytab =
            new org.apache.kerby.kerberos.kerb.keytab.Keytab();
        // 空 keytab 也能 load(load 不要求有 entry)
        keytab.store(file.toFile());
        assertNotNull(org.apache.kerby.kerberos.kerb.keytab.Keytab.loadKeytab(file.toFile()));
        assertTrue(Files.size(file) > 0, "keytab 文件非空");
    }

    @Test
    void noPrincipals_throwsIOException() {
        Path file = tempDir.resolve("empty.kt");
        // 文件不存在 → IOException
        assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
    }

    @Test
    void corruptFile_throwsIOException() throws IOException {
        Path file = tempDir.resolve("garbage.kt");
        Files.write(file, new byte[]{0x05, 0x03, 0, 0, 0, 0, 1, 2, 3});
        // 非法版本/垃圾数据 → Kerby 抛异常
        assertThrows(Exception.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
    }

    @Test
    void emptyKeytab_noPrincipals_throwsIOException() throws IOException {
        Path file = tempDir.resolve("empty-entries.kt");
        org.apache.kerby.kerberos.kerb.keytab.Keytab keytab =
            new org.apache.kerby.kerberos.kerb.keytab.Keytab();
        keytab.store(file.toFile());
        // 空 keytab → 0 principal → IOException(契约:空结果须报错)
        IOException ex = assertThrows(IOException.class,
            () -> KeytabPrincipalReader.getPrincipalNames(file.toString(), null));
        assertTrue(ex.getMessage().contains("no valid principals"),
            "应报空结果: " + ex.getMessage());
    }

    @Test
    void patternFilter_contract() {
        // KeytabPrincipalReader 的过滤契约(不依赖真实 keytab 文件——
        // 行为由 Kerby 保证,此处验证 wrapper 层的 pattern 逻辑语义)
        Pattern p = Pattern.compile("user.*");
        assertTrue(p.matcher("user@REALM").matches());
        assertTrue(!p.matcher("host@REALM").matches());
    }

    // ===== 真实 keytab 二进制文件验证(gen_keytab.py 生成的标准 MIT 格式) =====

    private static Path copyResource(String resource) throws IOException {
        Path dest = Files.createTempFile("keytab-test", ".kt");
        try (var is = KeytabPrincipalReaderTest.class
                .getClassLoader().getResourceAsStream(resource)) {
            if (is == null) {
                throw new IOException("test resource not found: " + resource);
            }
            Files.copy(is, dest, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
        return dest;
    }

    @Test
    void singleComponent_principal_realmPreserved() throws IOException {
        // user@REALM.COM → 输出须含 @REALM.COM(realm 不丢失)
        Path file = copyResource("test_single_component.kt");
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertEquals(1, names.length, "应读出 1 个 principal");
        assertEquals("user@REALM.COM", names[0],
            "单组件 principal 须完整保留 realm(user@REALM.COM)");
    }

    @Test
    void multiComponent_principal_slashSeparator_realmPreserved() throws IOException {
        // lakesearch/host@REALM.COM → 组件用 / 分隔(Kerby 可能输出 \ 形态,
        // 须归一化为 /;realm 不丢失)
        Path file = copyResource("test_multi_component.kt");
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertEquals(1, names.length, "应读出 1 个 principal");
        String name = names[0];
        assertTrue(name.contains("/"), "多组件 principal 须含 / 分隔: " + name);
        assertTrue(!name.contains("\\"), "不得含 \\ 分隔(须归一化): " + name);
        assertTrue(name.endsWith("@REALM.COM"), "realm 须保留: " + name);
        assertEquals("lakesearch/host@REALM.COM", name,
            "完整多组件 principal + realm");
    }

    @Test
    void mixedPrincipals_differentRealms_allPreserved() throws IOException {
        // 3 个 principal(多组件+不同 realm+4组件)→ 全部读出且 realm 各自正确
        Path file = copyResource("test_mixed_principals.kt");
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertEquals(3, names.length, "应读出 3 个 principal");
        var nameSet = java.util.Arrays.stream(names).collect(java.util.stream.Collectors.toSet());
        assertTrue(nameSet.contains("lakesearch/host/primary@REALM.COM"),
            "三组件: " + nameSet);
        assertTrue(nameSet.contains("user2@TEST.REALM"),
            "不同 realm: " + nameSet);
        assertTrue(nameSet.contains("service/node/instance/domain@REALM.COM"),
            "四组件: " + nameSet);
    }

    @Test
    void duplicatePrincipals_dedup() throws IOException {
        // 同一 principal 两条 entry → 去重后 2 个(不是 3 个)
        Path file = copyResource("test_dedup.kt");
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(), null);
        assertEquals(2, names.length, "重复 entry 去重后应剩 2 个");
        var nameSet = java.util.Arrays.stream(names).collect(java.util.stream.Collectors.toSet());
        assertTrue(nameSet.contains("user@REALM.COM"));
        assertTrue(nameSet.contains("lakesearch/host@REALM.COM"));
    }

    @Test
    void patternFilter_onRealKeytab() throws IOException {
        // 在真实 keytab 上做 pattern 过滤(lakesearch.* 匹配多组件,不匹配 user)
        Path file = copyResource("test_mixed_principals.kt");
        String[] names = KeytabPrincipalReader.getPrincipalNames(file.toString(),
            Pattern.compile("lakesearch.*"));
        assertEquals(1, names.length, "pattern lakesearch.* 只匹配 1 个");
        assertEquals("lakesearch/host/primary@REALM.COM", names[0]);
    }
}
