/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.stream.Stream;

class LocalFileStoreImplTest {

    private Path baseDir;

    private LocalFileStoreImpl fileStore;

    @BeforeEach
    void setUp() throws IOException {
        baseDir = Files.createTempDirectory("local-store");
        StorageProperties.Local local = new StorageProperties.Local();
        local.setBasePath(baseDir.toString());
        local.setBucket("bucket");
        local.setStagingBucket("staging");
        local.setServerUrl("http://localhost");
        fileStore = new LocalFileStoreImpl(local);
    }

    @AfterEach
    void tearDown() throws IOException {
        try (Stream<Path> paths = Files.walk(baseDir)) {
            paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                try {
                    Files.deleteIfExists(path);
                } catch (IOException ignored) {
                    // 清理失败不影响用例结果
                }
            });
        }
    }

    @Test
    void write_within_base_succeeds() {
        fileStore.write("bucket/dir/ok.txt", "content");

        assertTrue(Files.exists(baseDir.resolve("bucket/dir/ok.txt")));
    }

    @Test
    void write_rejects_path_traversal() {
        assertThrows(IllegalArgumentException.class,
            () -> fileStore.write("bucket/dir/../../../../evil.txt", "pwned"));
    }

    @Test
    void operations_reject_path_traversal() {
        String escaping = "../evil.txt";

        assertThrows(IllegalArgumentException.class, () -> fileStore.read(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.readStream(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.exists(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.delete(escaping));
        assertThrows(IllegalArgumentException.class, () -> fileStore.copy(escaping, "bucket/ok.txt"));
    }
}
