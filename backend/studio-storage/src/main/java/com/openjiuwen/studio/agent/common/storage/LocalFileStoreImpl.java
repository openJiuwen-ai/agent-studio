/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.stream.Stream;

@Slf4j
public class LocalFileStoreImpl implements FileStore {

    private final String basePath;
    private final String defaultNamespace;
    private final String stagingNamespace;
    private final String serverUrl;

    public LocalFileStoreImpl(StorageProperties.Local localConfig) {
        this.basePath = localConfig.getBasePath();
        this.defaultNamespace = localConfig.getBucket();
        this.stagingNamespace = localConfig.getStagingBucket();
        this.serverUrl = localConfig.getServerUrl() != null ? localConfig.getServerUrl().replaceAll("/+$", "") : "";
    }

    private Path resolve(String path) {
        return Paths.get(basePath, path);
    }

    private String extractKeyPrefix(String prefix) {
        int idx = prefix.indexOf('/');
        String keyPrefix = idx >= 0 ? prefix.substring(idx + 1) : "";
        if (!keyPrefix.endsWith("/")) {
            keyPrefix = keyPrefix + "/";
        }
        return keyPrefix;
    }

    @Override
    public String write(String path, String content) {
        Path file = resolve(path);
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, content, StandardCharsets.UTF_8);
            return path;
        } catch (IOException e) {
            log.error("write file failed: {}", path, e);
            throw new RuntimeException("write file failed: " + path, e);
        }
    }

    @Override
    public String write(String path, InputStream inputStream) {
        return write(path, inputStream, -1);
    }

    @Override
    public String write(String path, InputStream inputStream, int expires) {
        Path file = resolve(path);
        try {
            Files.createDirectories(file.getParent());
            Files.copy(inputStream, file, StandardCopyOption.REPLACE_EXISTING);
            return path;
        } catch (IOException e) {
            log.error("write file failed: {}", path, e);
            throw new RuntimeException("write file failed: " + path, e);
        }
    }

    @Override
    public String read(String path) {
        Path file = resolve(path);
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.error("read file failed: {}", path, e);
            throw new RuntimeException("read file failed: " + path, e);
        }
    }

    @Override
    public InputStream readStream(String path) {
        Path file = resolve(path);
        try {
            return Files.newInputStream(file);
        } catch (IOException e) {
            log.error("read stream failed: {}", path, e);
            throw new RuntimeException("read stream failed: " + path, e);
        }
    }

    @Override
    public boolean delete(String path) {
        Path file = resolve(path);
        try {
            return Files.deleteIfExists(file);
        } catch (IOException e) {
            log.error("delete failed: {}", path, e);
            throw new RuntimeException("delete failed: " + path, e);
        }
    }

    @Override
    public boolean exists(String path) {
        return Files.exists(resolve(path));
    }

    @Override
    public boolean copy(String sourcePath, String targetPath) {
        try {
            Path src = resolve(sourcePath);
            Path dest = resolve(targetPath);
            Files.createDirectories(dest.getParent());
            Files.copy(src, dest, StandardCopyOption.REPLACE_EXISTING);
            return true;
        } catch (IOException e) {
            log.error("copy failed: {} -> {}", sourcePath, targetPath, e);
            throw new RuntimeException("copy failed", e);
        }
    }

    @Override
    public List<String> list(String prefix) {
        Path dir = resolve(prefix);
        if (!Files.exists(dir)) {
            return Collections.emptyList();
        }
        String keyPrefix = extractKeyPrefix(prefix);
        List<String> keys = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(dir)) {
            paths.filter(Files::isRegularFile)
                .forEach(p -> keys.add(keyPrefix + dir.relativize(p).toString().replace('\\', '/')));
        } catch (IOException e) {
            log.error("list failed: {}", prefix, e);
        }
        return keys;
    }

    @Override
    public String getDownloadUrl(String path, long expiresSeconds) {
        String encoded = java.net.URLEncoder.encode(path, java.nio.charset.StandardCharsets.UTF_8);
        return serverUrl + "/api/storage/download?path=" + encoded;
    }

    @Override
    public FileMeta getMeta(String path) {
        Path file = resolve(path);
        if (!Files.exists(file)) {
            return null;
        }
        try {
            FileMeta fm = new FileMeta();
            fm.setName(file.getFileName().toString());
            fm.setSize(Files.size(file));
            fm.setLastModified(Files.getLastModifiedTime(file).toMillis());
            fm.setDirectory(Files.isDirectory(file));
            return fm;
        } catch (IOException e) {
            return null;
        }
    }

    @Override
    public List<FileMeta> listMetas(String prefix) {
        Path dir = resolve(prefix);
        if (!Files.exists(dir)) {
            return Collections.emptyList();
        }
        List<FileMeta> metas = new ArrayList<>();
        try (Stream<Path> paths = Files.walk(dir, 1)) {
            paths.filter(p -> !p.equals(dir))
                .forEach(p -> {
                    try {
                        FileMeta fm = new FileMeta();
                        fm.setName(dir.relativize(p).toString().replace('\\', '/'));
                        fm.setSize(Files.isRegularFile(p) ? Files.size(p) : 0L);
                        fm.setLastModified(Files.getLastModifiedTime(p).toMillis());
                        fm.setDirectory(Files.isDirectory(p));
                        metas.add(fm);
                    } catch (IOException ignored) {
                    }
                });
        } catch (IOException e) {
            log.error("list metas failed: {}", prefix, e);
        }
        return metas;
    }

    @Override
    public String getDefaultNamespace() {
        return defaultNamespace;
    }

    @Override
    public String getStagingNamespace() {
        return stagingNamespace;
    }

    public String getBasePath() {
        return basePath;
    }
}
