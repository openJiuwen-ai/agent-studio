/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import java.io.InputStream;
import java.util.List;


public interface FileStore {

    String write(String path, String content);

    String write(String path, InputStream inputStream);

    String write(String path, InputStream inputStream, int expires);

    String read(String path);

    InputStream readStream(String path);

    boolean delete(String path);

    boolean exists(String path);

    boolean copy(String sourcePath, String targetPath);

    List<String> list(String prefix);

    default boolean deleteByPrefix(String prefix) {
        List<String> keys = list(prefix);
        if (keys == null || keys.isEmpty()) {
            return true;
        }
        boolean allDeleted = true;
        for (String key : keys) {
            String fullPath = prefix;
            if (!prefix.endsWith("/")) {
                fullPath = prefix + "/";
            }
            if (!delete(fullPath + key)) {
                allDeleted = false;
            }
        }
        return allDeleted;
    }

    String getDownloadUrl(String path, long expiresSeconds);

    FileMeta getMeta(String path);

    List<FileMeta> listMetas(String prefix);

    String getDefaultNamespace();

    String getStagingNamespace();
}
