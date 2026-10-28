/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.util;

import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.StringUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.UUID;

@Slf4j
@Component
public class ObsApiClient {

    private final FileStore fileStore;

    public ObsApiClient(FileStore fileStore) {
        this.fileStore = fileStore;
    }

    public InputStream downloadFile(String bucketName, String obsKey) {
        try {
            return fileStore.readStream(bucketName + "/" + obsKey);
        } catch (Exception ex) {
            log.error("[downloadFile] download file failed, error is {}", ex.getMessage() + ex.getCause());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR,
                "download file failed");
        }
    }

    public String uploadFile(String bucketName, String directory, FileTransferUtils.AgentBuilderFile file) {
        String fileName = safeFileName(file.getOriginalFilename());
        String obsKey = directory + fileName;
        if (!directory.endsWith(StringUtil.SLASHES_STRING)) {
            obsKey = directory + StringUtil.SLASHES_STRING + fileName;
        }
        try {
            fileStore.write(bucketName + "/" + obsKey, file.getInputStream());
        } catch (Exception ex) {
            log.error("file {} upload failed, error detail is: {}", fileName, ex.getMessage() + ex.getCause());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR,
                "file upload failed");
        }
        return obsKey;
    }

    /**
     * 客户端文件名不可直接拼入存储键：剔除路径分隔符等非法字符，避免 {@code ../} 或绝对路径注入。
     */
    private static String safeFileName(String originalFilename) {
        String safeName = AppCommonUtils.sanitizeFilename(originalFilename);
        if (safeName.isBlank() || ".".equals(safeName) || "..".equals(safeName)) {
            return UUID.randomUUID().toString();
        }
        return safeName;
    }

    public String getTemporaryGetRsp(String bucketName, String objectName, long expires) {
        try {
            return fileStore.getUrl(bucketName + "/" + objectName, expires);
        } catch (Exception e) {
            log.error("Get temporary getRsp failed, error is {}", e);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR);
        }
    }

    public boolean safeCopyObsObject(String srcBucketName, String srcObsKey, String destBucketName, String destObsKey) {
        try {
            copyObsObject(srcBucketName, srcObsKey, destBucketName, destObsKey);
            return true;
        } catch (Exception ex) {
            log.warn("copy objects {} from bucket {} to {} failed. ex is {}", srcObsKey, srcBucketName,
                destBucketName, ex.getMessage() + " " + ex.getCause());
            return false;
        }
    }

    public void copyObsObject(String srcBucketName, String srcObsKey, String destBucketName, String destObsKey) {
        try {
            fileStore.copy(srcBucketName + "/" + srcObsKey, destBucketName + "/" + destObsKey);
        } catch (Exception ex) {
            log.error("copy objects {} from bucket {} to {} failed. ex is {}", srcObsKey, srcBucketName,
                destBucketName, ex);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR,
                "copy objects failed");
        }
    }

    public boolean safeDeleteObsObject(String bucketName, String directory) {
        if (StringUtils.isEmpty(bucketName) || StringUtils.isEmpty(directory)) {
            log.warn(
                "delete objects failed, due to lack of bucket name or directory. bucket name is {}, directory is {}",
                bucketName, directory);
            return true;
        }
        try {
            return deleteObsObject(bucketName, directory);
        } catch (Exception ex) {
            log.warn("delete obs object failed, error detail is: {}", ex.getMessage() + " " + ex.getCause());
            return false;
        }
    }

    public boolean deleteObsObject(String bucketName, String objectKey) {
        if (StringUtils.isEmpty(bucketName) || StringUtils.isEmpty(objectKey)) {
            log.error(
                "delete objects failed, due to lack of bucket name or directory. bucket name is {}, directory is {}",
                bucketName, objectKey);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR,
                "invalid bucket name or directory");
        }
        try {
            fileStore.delete(bucketName + "/" + objectKey);
            return true;
        } catch (Exception ex) {
            log.error("delete objects {} from bucket {} failed. ex is {}", objectKey, bucketName,
                ex.getMessage() + " " + ex.getCause());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_OBS_EXECUTE_ERROR,
                "delete object failed");
        }
    }
}
