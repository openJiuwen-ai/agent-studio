/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.common.storage;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.*;

/**
 * LocalFileStoreImpl 本地存储测试
 * 包含：readOrNull 语义测试 + 路径穿越漏洞防护测试
 */
class LocalFileStoreImplTest {

    @TempDir
    Path tempDir;

    private LocalFileStoreImpl fileStore;

    @BeforeEach
    void setUp() {
        // bucket=子目录名；path 格式 namespace/objectKey，splitPath 用 namespace 作子目录。
        StorageProperties.Local localConfig = new StorageProperties.Local();
        localConfig.setBasePath(tempDir.toString());
        localConfig.setBucket("test-bucket");
        localConfig.setStagingBucket("test-staging");
        localConfig.setServerUrl("http://localhost");
        fileStore = new LocalFileStoreImpl(localConfig);
    }

    /** readOrNull: 文件不存在（NoSuchFileException）→ 返回 null（归一"未发布"语义，非抛 500）。 */
    @Test
    void readOrNull_fileNotExists_returnsNull() throws IOException {
        Files.createDirectories(Paths.get(tempDir.toString(), "test-bucket"));
        assertNull(fileStore.readOrNull("test-bucket/missing.json"),
                "文件不存在应返回 null（归一为未发布），不抛 RuntimeException");
    }

    /** readOrNull: 正常读取 → 返回内容。 */
    @Test
    void readOrNull_fileExists_returnsContent() throws IOException {
        Path dir = Paths.get(tempDir.toString(), "test-bucket");
        Files.createDirectories(dir);
        Path file = dir.resolve("exists.json");
        Files.writeString(file, "hello", StandardCharsets.UTF_8);
        assertEquals("hello", fileStore.readOrNull("test-bucket/exists.json"));
    }

    /** read: 文件不存在 → 抛 RuntimeException（read 不归一 null，与 readOrNull 区分；调用方需 null 语义用 readOrNull）。 */
    @Test
    void read_fileNotExists_throws() throws IOException {
        Files.createDirectories(Paths.get(tempDir.toString(), "test-bucket"));
        assertThrows(RuntimeException.class,
                () -> fileStore.read("test-bucket/missing.json"),
                "read 文件不存在应抛 RuntimeException，不归一 null（与 readOrNull 区分）");
    }

    @Test
    void write_within_base_succeeds() {
        fileStore.write("test-bucket/dir/ok.txt", "content");
        assertTrue(Files.exists(tempDir.resolve("test-bucket/dir/ok.txt")));
    }

    @Test
    void leading_slash_key_is_kept_within_base() {
        // 兼容空 bucket 配置：调用方会拼出 "/bucket/..." 形式的键
        fileStore.write("/bucket/ok.txt", "content");

        assertTrue(Files.exists(tempDir.resolve("bucket/ok.txt")));
    }

    @Test
    void leading_slash_key_cannot_escape_base() {
        assertThrows(IllegalArgumentException.class,
            () -> fileStore.write("/bucket/../../../../evil.txt", "pwned"));
    }

    @Test
    void write_rejects_path_traversal() {
        assertThrows(IllegalArgumentException.class,
                () -> fileStore.write("test-bucket/dir/../../../../evil.txt", "pwned"));
    }

    @Test
    void operations_reject_path_traversal() {
        String escaping = "../evil.txt";
        assertThrows(IllegalArgumentException.class, () -> fileStore.read(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.readStream(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.exists(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.delete(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.copy(escaping, "test-bucket/ok.txt"));
    }
}
