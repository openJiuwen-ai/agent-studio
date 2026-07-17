/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.obs;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.CommonObsService;
import com.openjiuwen.studio.agent.common.storage.FileMeta;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;

import com.openjiuwen.studio.agent.manager.utils.OkHttpUtils;
import lombok.extern.slf4j.Slf4j;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import org.apache.commons.io.IOUtils;
import org.apache.commons.io.output.ByteArrayOutputStream;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.DependsOn;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class MgObsService implements CommonObsService {
    @Autowired
    private OkHttpUtils okHttpUtils;

    private final FileStore fileStore;

    private final String bucket;

    private final String stagingBucket;

    @Autowired
    public MgObsService(FileStore fileStore) {
        this.fileStore = fileStore;
        this.bucket = fileStore.getDefaultNamespace();
        this.stagingBucket = fileStore.getStagingNamespace();
    }

    private String path(String key) {
        return bucket + "/" + key;
    }

    private String stagingPath(String key) {
        return stagingBucket + "/" + key;
    }

    @Override
    public void putObject(String objectKey, String content) {
        uploadObsFile(objectKey, content, -1);
    }

    @Override
    public void deleteObject(String objectKey) {
        deleteObsFile(objectKey);
    }

    @Override
    public String getObject(String objectKey) {
        return downloadObsFile(objectKey);
    }

    @Scheduled(fixedDelay = 24 * 60 * 60 * 1000)
    public void cleanObsObjects() {
        final long millis = TimeUnit.DAYS.toMillis(7);
        try {
            List<FileMeta> metas = fileStore.listMetas(path(CommonConstant.FILE));
            if (metas == null || metas.isEmpty()) {
                return;
            }
            for (FileMeta meta : metas) {
                if (System.currentTimeMillis() - meta.getLastModified() > millis) {
                    deleteObsFile(meta.getName());
                }
            }
            log.info("delete expired files succeed!");
        } catch (Exception e) {
            log.error("delete expired files failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public String uploadObsFile(String pathKey, String objectKey, String type, String fileInfo, String prefix) {
        return uploadObsFile(String.format("%s/%s/%s/%s.json", type, prefix, pathKey, objectKey), fileInfo, -1);
    }

    public String uploadObsFile(String objectKey, String content, int expires) {
        try (ByteArrayInputStream inputStream = new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))) {
            return uploadObsFile(objectKey, inputStream, expires);
        } catch (Exception e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public String uploadStagingBucket(String objectKey, String content, int expires) {
        try (ByteArrayInputStream inputStream = new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))) {
            return uploadStreamStagingBucket(objectKey, inputStream, expires);
        } catch (Exception e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public String uploadStreamStagingBucket(String objectKey, InputStream inputStream, int expires) {
        try {
            fileStore.write(stagingPath(objectKey), inputStream, expires);
            log.info("upload obs file success, file path:{}", objectKey);
            return objectKey;
        } catch (Exception e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    public String uploadObsFile(String objectKey, InputStream inputStream, int expires) {
        try {
            fileStore.write(path(objectKey), inputStream, expires);
            log.info("upload obs file success, file path:{}", objectKey);
            return objectKey;
        } catch (Exception e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    public String downloadObsFile(String relativePath) {
        try {
            return fileStore.read(path(relativePath));
        } catch (Exception e) {
            log.error("download file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public String downloadObsImageFile(String relativePath) {
        String iconPath = "icon/" + relativePath;
        try {
            InputStream content = fileStore.readStream(path(iconPath));
            if (content != null) {
                ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
                byte[] buffer = new byte[1024];
                int bytesRead;
                while ((bytesRead = content.read(buffer)) != -1) {
                    outputStream.write(buffer, 0, bytesRead);
                }
                IOUtils.closeQuietly(content);
                byte[] bytes = outputStream.toByteArray();
                return Base64.getEncoder().encodeToString(bytes);
            } else {
                throw new AgentStudioException(StudioError.OBS_FAILED);
            }
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("download image file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public String uploadObsFileWithExpires(InputStream inputStream, String fileName, int expires) {
        String objectKey = String.format("%s/%s", CommonConstant.FILE, fileName);
        return uploadObsFile(objectKey, inputStream, expires);
    }

    public boolean deleteByPrefix(String prefix) {
        return fileStore.deleteByPrefix(path(prefix));
    }

    public void deleteObsFile(String relativePath) {
        fileStore.delete(path(relativePath));
    }

    public void softDeleteObsFile(String relativePath) {
        try {
            if (fileStore.exists(path(relativePath))) {
                fileStore.copy(path(relativePath), path(relativePath + CommonConstant.DELETED_SUFFIX));
                fileStore.delete(path(relativePath));
            }
        } catch (Exception e) {
            log.error("soft delete file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public void deleteObsObjects(String dirPath) {
        try {
            fileStore.deleteByPrefix(path(dirPath));
        } catch (Exception e) {
            log.error("delete file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public List<String> listObsObjectKeys(String path) {
        return fileStore.list(this.path(path));
    }

    public String getTemporaryGetRsp(boolean stagingFlag, String objectName, long expires) {
        String ns = stagingFlag ? stagingBucket : bucket;
        return fileStore.getUrl(ns + "/" + objectName, expires);
    }

    public void copyObsObject(String sourceIrName, String targetIrName) {
        try {
            fileStore.copy(path(sourceIrName), path(targetIrName));
        } catch (Exception e) {
            log.error("OBS object copy failed.", e);
            throw new AgentStudioException(StudioError.COPY_FROM_OBS_FAIL);
        }
    }

    public FileMeta getObjectMetadata(String objectKey) {
        try {
            FileMeta meta = fileStore.getMeta(path(objectKey));
            return meta != null ? meta : new FileMeta();
        } catch (Exception e) {
            log.error("get object metadata failed, check storage configration", e);
            return new FileMeta();
        }
    }

    public boolean isExistedKey(String sourceKey) {
        return fileStore.exists(path(sourceKey));
    }

    public String getAbsolutePath(String relativePath) {
        return String.format("obs://%s/%s", bucket, relativePath);
    }

    public void appendSuffixByPrefix(String prefix, String suffix) {
        List<String> keys = fileStore.list(path(prefix));
        for (String objectKey : keys) {
            if (!objectKey.contains(suffix)) {
                String targetKey = objectKey + suffix;
                copyObsObject(objectKey, targetKey);
            }
            fileStore.delete(path(objectKey));
        }
    }

    /**
     * 根据临时url从obs获取文件流
     *
     * @param url 临时url
     * @return InputStream
     */
    public InputStream getByUrl(String url) {
        long startTime = System.currentTimeMillis();
        InputStream inputStream;
        try {
            Request.Builder builder = new Request.Builder();
            Request httpRequest = builder.url(url).get().build();
            OkHttpClient httpClient = okHttpUtils.getHttpClient();
            Response rsp = httpClient.newCall(httpRequest).execute();
            if (rsp.body() == null) {
                log.error("File is empty.");
                throw new AgentStudioException(StudioError.FILE_NOT_EXIST);
            }
            inputStream = rsp.body().byteStream();
        } catch (IOException e) {
            log.error("Get inputStream from obs by url failed.", e);
            throw new AgentStudioException(StudioError.GET_BY_URL_FAILED);
        } finally {
            log.info("getByUrl cost: {} ms", System.currentTimeMillis() - startTime);
        }
        return inputStream;
    }
}
