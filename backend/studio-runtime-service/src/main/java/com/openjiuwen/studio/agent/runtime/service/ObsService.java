/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.CommonObsService;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.utils.AlarmLogUtil;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;

import io.micrometer.common.util.StringUtils;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class ObsService implements CommonObsService {

    private final FileStore fileStore;

    @Getter
    private final String bucket;

    @Getter
    private final String stagingBucket;

    @Autowired
    private OkHttpUtils okHttpUtils;

    @Autowired
    private AlarmLogUtil alarmLogUtil;

    @Autowired
    public ObsService(FileStore fileStore) {
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

    private String fullPath(String basePath, String key) {
        return path(StringUtils.isEmpty(basePath) ? key : basePath + "/" + key);
    }

    @Override
    public void putObject(String objectKey, String content) {
        putObject(null, objectKey, content);
    }

    @Override
    public void deleteObject(String objectKey) {
        fileStore.delete(path(objectKey));
    }

    @Override
    public String getObject(String objectKey) {
        return getObject(null, objectKey).get(Constant.Obs.CONTENT);
    }

    public String downloadObsFile(String objectKey) {
        long startTime = System.currentTimeMillis();
        try {
            return fileStore.read(path(objectKey));
        } catch (Exception e) {
            log.error("download file from obs failed!");
            alarmLogUtil.logAlarm("OBS", "download file from obs failed!", e.getMessage());
            throw new AgentStudioException(StudioError.OBS_FAILED);
        } finally {
            log.info("downloadObsFile:{}, cost: {} ms", objectKey, System.currentTimeMillis() - startTime);
        }
    }

    public void putObject(String basePath, String objectKey, String content) {
        long startTime = System.currentTimeMillis();
        String p = fullPath(basePath, objectKey);
        fileStore.write(p, content);
        log.info("putObject:{}, cost: {} ms", p, System.currentTimeMillis() - startTime);
    }

    public String putObject(String objectPath, InputStream inputStream, int expires) {
        fileStore.write(path(objectPath), inputStream, expires);
        return objectPath;
    }

    public String putObjectToBucket(String bucketName, String objectPath, InputStream inputStream, int expires) {
        fileStore.write(bucketName + "/" + objectPath, inputStream, expires);
        return objectPath;
    }

    public Map<String, String> getObject(String basePath, String objectKey) {
        long startTime = System.currentTimeMillis();
        String p = fullPath(basePath, objectKey);
        try {
            String content = fileStore.read(p);
            String md5 = content != null ? md5Hex(content) : "";
            log.info("getObject:{}, cost: {} ms", p, System.currentTimeMillis() - startTime);
            return Map.of(Constant.Obs.CONTENT, content != null ? content : "", Constant.Obs.MD5, md5);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("download file from obs failed!");
            alarmLogUtil.logAlarm("OBS", "download file from obs failed!", e.getMessage());
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public InputStream getByUrl(String url) {
        long startTime = System.currentTimeMillis();
        try {
            Request httpRequest = new Request.Builder().url(url).get().build();
            OkHttpClient httpClient = okHttpUtils.getHttpClient();
            Response rsp = httpClient.newCall(httpRequest).execute();
            if (rsp.body() == null) {
                log.error("File is empty.");
                alarmLogUtil.logAlarm("OBS", "File is empty.", "File is empty.");
                throw new AgentStudioException(StudioError.FILE_NOT_EXIST);
            }
            return rsp.body().byteStream();
        } catch (IOException e) {
            log.error("Get inputStream from obs by url failed.", e);
            alarmLogUtil.logAlarm("OBS", "Get inputStream from obs by url failed. url: " + url, e.getMessage());
            throw new AgentStudioException(StudioError.GET_BY_URL_FAILED);
        } finally {
            log.info("getByUrl cost: {} ms", System.currentTimeMillis() - startTime);
        }
    }

    public String getMd5(String basePath, String objectKey) {
        return getObject(basePath, objectKey).getOrDefault(Constant.Obs.MD5, "");
    }

    public List<String> listObjectKeys(String rootDir) {
        return fileStore.list(path(rootDir));
    }

    public String uploadObsFileWithExpires(InputStream inputStream, String fileName, int expires) {
        String objectKey = String.format("%s/%s", Constant.FILE, fileName);
        return putObject(objectKey, inputStream, expires);
    }

    public String uploadToStagingWithPublicRead(InputStream inputStream, String fileName, int expires) {
        String objectKey = String.format("%s/%s", Constant.FILE, fileName);
        fileStore.write(stagingPath(objectKey), inputStream, expires);
        return fileStore.getUrl(stagingPath(objectKey), expires > 0 ? (long) expires * 86400 : 3600L);
    }

    public String uploadToStagingWithExpires(InputStream inputStream, String fileName, int expires) {
        String objectKey = String.format("%s/%s", Constant.FILE, fileName);
        return putObjectToBucket(stagingBucket, objectKey, inputStream, expires);
    }

    public String getStagingDownloadUrl(String objectName, long expiresSeconds) {
        return fileStore.getUrl(stagingBucket + "/" + objectName, expiresSeconds);
    }

    private String md5Hex(String content) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(content.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }
}
