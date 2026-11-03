/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * LocalFileStoreImpl.readOrNull 测试：文件不存在→null（归一"未发布"语义）、
 * 真实 IO 故障→抛、正常读取→内容。锁住 LOCAL 模式下 readOrNull 的"不存在归一 null"语义，
 * 使 PublishUtils.getPublish 在 storage.type=LOCAL 下能把"未发布"归一为 null → 导出返 400。
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
        fileStore = new LocalFileStoreImpl(localConfig);
    }

    /** readOrNull: 文件不存在（NoSuchFileException）→ 返回 null（归一"未发布"语义，非抛 500）。 */
    @Test
    void readOrNull_fileNotExists_returnsNull() throws IOException {
        // 确保父目录存在但目标文件不存在
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
}
