/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@RestController
@RequestMapping("/api/storage")
@ConditionalOnProperty(name = "storage.type", havingValue = "LOCAL")
@Slf4j
public class StorageDownloadController {

    private final LocalFileStoreImpl localFileStore;

    public StorageDownloadController(FileStore fileStore) {
        this.localFileStore = (LocalFileStoreImpl) fileStore;
    }

    @GetMapping("/download")
    public ResponseEntity<Resource> download(@RequestParam("path") String path) {
        try {
            String decodedPath = java.net.URLDecoder.decode(path, StandardCharsets.UTF_8);
            if (decodedPath.startsWith("/")) {
                return ResponseEntity.badRequest().build();
            }
            Path basePath = Paths.get(localFileStore.getBasePath()).toAbsolutePath().normalize();
            Path filePath = basePath.resolve(decodedPath).normalize();

            if (!filePath.startsWith(basePath)) {
                return ResponseEntity.badRequest().build();
            }
            if (!Files.exists(filePath) || !Files.isRegularFile(filePath)) {
                return ResponseEntity.notFound().build();
            }

            FileSystemResource resource = new FileSystemResource(filePath);
            String contentType = Files.probeContentType(filePath);
            if (contentType == null) {
                contentType = MediaType.APPLICATION_OCTET_STREAM_VALUE;
            }

            return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(contentType))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                    "attachment; filename=\"" + filePath.getFileName() + "\"")
                .body(resource);
        } catch (Exception e) {
            log.error("download file failed: {}", path, e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
