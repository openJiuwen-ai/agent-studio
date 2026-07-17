/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.utils;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileStore;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.io.FilenameUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.util.Objects;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Slf4j
@Component
public class ObsUtil {
    private static final long MAX_TOTAL_SIZE = 10L * 1024 * 1024;

    private static final long MAX_ENTRY_SIZE = 5L * 1024 * 1024;

    static final int BUFFER = 512;

    private final FileStore fileStore;

    private final String bucket;

    @Autowired
    public ObsUtil(FileStore fileStore) {
        this.fileStore = fileStore;
        this.bucket = fileStore.getDefaultNamespace();
    }

    public boolean hasBucket(String xAuthToken, String bucketName) {
        return true;
    }

    public boolean hasFile(String xAuthToken, String bucketName, String filePath) {
        try {
            return fileStore.exists(bucketName + "/" + filePath);
        } catch (Exception e) {
            log.error("The obs file is not exist, filePath: {} , error: {}", filePath, e.getMessage());
            throw new AgentStudioException(StudioError.OBS_FILE_NOT_EXIST, filePath);
        }
    }

    public InputStream downloadObsFile(String xAuthToken, String bucketName, String filePath) {
        try {
            InputStream checkContent = fileStore.readStream(bucketName + "/" + filePath);
            checkZipBomb(checkContent);
            return fileStore.readStream(bucketName + "/" + filePath);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("download obs file failed, error: {}", e.getMessage());
            throw new AgentStudioException(StudioError.OBS_DOWNLOAD_FILE_FAILED);
        }
    }

    public void checkZipBomb(InputStream is) {
        ZipInputStream zis = null;
        try {
            zis = new ZipInputStream(is);
            ZipEntry entry;
            int zipSize = 0;
            long totalSize = 0L;
            while ((entry = zis.getNextEntry()) != null) {
                int count;
                byte data[] = new byte[BUFFER];
                zipSize++;
                if (zipSize > 20) {
                    log.error("zip file size is too large");
                    throw new AgentStudioException(StudioError.ZIP_FILE_SIZE_LARGE);
                }

                String safePath = FilenameUtils.normalize(entry.getName());
                if (safePath == null || safePath.startsWith("..")) {
                    log.error("Invalid file path: {}", entry.getName());
                    throw new AgentStudioException(StudioError.INVALID_FILE_PATH, entry.getName());
                }

                if (entry.isDirectory()) {
                    continue;
                }

                long singleRead = 0;
                while ((count = zis.read(data, 0, BUFFER)) != -1) {
                    singleRead += count;
                    if (singleRead > MAX_ENTRY_SIZE) {
                        log.error("file entry size is too large, name: {} ,size:{}", entry.getName(), singleRead);
                        throw new AgentStudioException(StudioError.FILE_ENTRY_SIZE_LARGE, entry.getName(), singleRead);
                    }

                    totalSize += count;
                    if (totalSize > MAX_TOTAL_SIZE) {
                        log.error("file size is too large, size: {}", totalSize);
                        throw new AgentStudioException(StudioError.FILE_SIZE_TOO_LARGE, totalSize);
                    }
                }

                zis.closeEntry();
            }
        } catch (IOException ioException) {
            log.error("obs file check zip bomb failed, {}", ioException.getMessage());
            throw new AgentStudioException(StudioError.OBS_FILE_CHECK_ZIP_BOMB);
        } finally {
            if (Objects.nonNull(is)) {
                try {
                    is.close();
                } catch (IOException e) {
                    log.error("input stream close failed.");
                }
            }
            if (Objects.nonNull(zis)) {
                try {
                    zis.close();
                } catch (IOException e) {
                    log.error("zip input stream close failed.");
                }
            }
        }
    }
}
