/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.util;

import static com.openjiuwen.studio.agent.space.app.constant.Constant.SPACE_OBS_DOMAIN_ID_PREFIX;
import static com.openjiuwen.studio.agent.space.app.constant.Constant.SPACE_OBS_TASK_ID_PREFIX;
import static com.openjiuwen.studio.agent.space.app.constant.Constant.SPACE_OBS_TEMP_DIRECTORY_PREFIX;

import com.openjiuwen.studio.agent.common.storage.FileMeta;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.agent.space.api.vo.AgentBuilderFileVo;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderMediaType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderStorageType;
import com.openjiuwen.studio.agent.space.app.enums.AgentBuilderUploadScene;
import com.openjiuwen.studio.agent.space.app.util.md.MdConvertUtil;
import com.openjiuwen.studio.agent.space.common.context.AuthorizationContextHolder;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderFileEntity;

import jakarta.annotation.Resource;
import lombok.Data;
import lombok.experimental.Accessors;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Objects;
import java.util.UUID;

/**
 * 文件传输工具
 * 总管文件传输，收束环境差异
 */
@Slf4j
@Service
public class FileTransferUtils {
    @Value("${storage.type:OBS}")
    private String storageType;

    @Resource
    private ObsApiClient obsApiClient;

    @Resource
    private FileStore fileStore;

    @Value("${agent.builder.task.obs.bucket.name:agentBuilder}")
    private String SPACE_OBS_BUCKET_NAME;

    @Value("${agent.builder.task.obs.directory.temp:space/task/tmp/{domain_id}/{UUID}/}")
    private String SPACE_OBS_DIRECTORY_TMP;

    @Value("${agent.builder.task.obs.directory.runtime:space/task/runtime/{domain_id}/{task_id}/}")
    private String SPACE_OBS_DIRECTORY_RUNTIME;

    private FileTransferResult uploadTaskFile2Obs(AgentBuilderFile file, @Nullable String taskId,
        AgentBuilderUploadScene scene) {
        // 获取桶
        String uploadDirectory = "";
        if (AgentBuilderUploadScene.USER_UPLOAD.equals(scene)) {
            String uploadDirectoryBase = SPACE_OBS_DIRECTORY_TMP;
            uploadDirectoryBase = StringUtils.replace(uploadDirectoryBase, "{domain_id}",
                AuthorizationContextHolder.domainId());
            uploadDirectory = StringUtils.replace(uploadDirectoryBase, "{UUID}",
                SPACE_OBS_TEMP_DIRECTORY_PREFIX + UUID.randomUUID().toString().replaceAll("-", ""));
            log.info("[uploadTaskFile2Obs] User upload directory set to: {}", uploadDirectory);
        } else if (AgentBuilderUploadScene.RUNTIME_UPLOAD.equals(scene)) {
            String uploadDirectoryBase = SPACE_OBS_DIRECTORY_RUNTIME;
            uploadDirectoryBase = StringUtils.replace(uploadDirectoryBase, "{domain_id}",
                SPACE_OBS_DOMAIN_ID_PREFIX + AuthorizationContextHolder.domainId());
            uploadDirectory = StringUtils.replace(uploadDirectoryBase, "{task_id}", SPACE_OBS_TASK_ID_PREFIX + taskId);
            log.info("[uploadTaskFile2Obs] Runtime upload directory set to: {}", uploadDirectory);
        }

        String uploadKey = obsApiClient.uploadFile(SPACE_OBS_BUCKET_NAME, uploadDirectory, file);
        log.info("[uploadTaskFile2Obs] File uploaded successfully with key: {}", uploadKey);

        // 创建并返回文件传输结果
        return new FileTransferResult().setStorageType(AgentBuilderStorageType.OBS)
            .setFileKey(uploadKey)
            .setSuccess(true);
    }

    /**
     * 上传任务文件
     *
     * @param file   文件
     * @param taskId 任务id，场景为运行时时才需要传
     * @param scene  场景
     * @return 文件上传结果
     */
    public FileTransferResult uploadTaskFile(AgentBuilderFile file, @Nullable String taskId,
        AgentBuilderUploadScene scene) {
        boolean storageEnabled = "OBS".equalsIgnoreCase(storageType);
        log.info("[uploadTaskFile] storageEnabled : {}", storageEnabled);
        if (storageEnabled) {
            try {
                return uploadTaskFile2Obs(file, taskId, scene);
            } catch (AgentSpaceException e) {
                log.error("[uploadTaskFile] upload file to obs fail, occur AgentSpaceException, ex is {}", e);
                throw new AgentSpaceException("failed to upload file to obs!");
            }
        } else {
            log.error("storage is disabled, failed to upload file!");
            throw new AgentSpaceException("storage is disabled, failed to upload file!");
        }
    }

    /**
     * 上传任务文件
     *
     * @param file  文件
     * @param scene 场景
     * @return 文件上传结果
     */
    public FileTransferResult uploadTaskFile(AgentBuilderFile file, AgentBuilderUploadScene scene) {
        return uploadTaskFile(file, null, scene);
    }

    /**
     * 用户上传文件复制到任务路径下
     *
     * @param obsKey 文件路径
     * @param taskId 任务id
     * @return 是否复制成功
     */
    private FileTransferResult taskUserTempFileCopyToTaskDir(String obsKey, String taskId) {
        String bucketName = SPACE_OBS_BUCKET_NAME;
        String fileName = obsKey.substring(obsKey.lastIndexOf('/') + 1);
        String destDirBase = SPACE_OBS_DIRECTORY_RUNTIME;
        destDirBase = StringUtils.replace(destDirBase, "{domain_id}", AuthorizationContextHolder.domainId());
        String destDir = StringUtils.replace(destDirBase, "{task_id}", taskId);
        destDir += fileName;

        // 如果obsKey已经是正式目录，说明已经执行过次操作，直接返回
        if (StringUtils.equals(obsKey, destDir)) {
            return new FileTransferResult().setStorageType(AgentBuilderStorageType.OBS)
                .setFileKey(obsKey)
                .setSuccess(true);
        }

        // 复制临时目录文件到正式目录
        boolean copied = obsApiClient.safeCopyObsObject(bucketName, obsKey, bucketName, destDir);
        if (copied) {
            return new FileTransferResult().setStorageType(AgentBuilderStorageType.OBS)
                .setFileKey(destDir)
                .setSuccess(true);
        } else {
            return new FileTransferResult().setStorageType(AgentBuilderStorageType.OBS)
                .setFileKey(destDir)
                .setSuccess(false);
        }
    }

    /**
     * 删除用户上传文件
     *
     * @param obsKey 文件路径
     */
    private void taskUserTempFileDelete(String obsKey) {
        obsApiClient.safeDeleteObsObject(SPACE_OBS_BUCKET_NAME, obsKey);
    }

    /**
     * 文件绑定任务
     */
    public FileTransferResult userFileBinding2Task(String obsKey, String taskId) {
        FileTransferResult copied = taskUserTempFileCopyToTaskDir(obsKey, taskId);
        taskUserTempFileDelete(obsKey);
        return copied;
    }

    /**
     * 删除obs文件
     *
     * @param obsKey 文件路径
     */
    public void safeDeleteObsObject(String obsKey) {
        obsApiClient.safeDeleteObsObject(SPACE_OBS_BUCKET_NAME, obsKey);
    }

    @NotNull
    private InputStream getObsInputStream(AgentBuilderFileEntity file) {
        InputStream inputStream = null;
        int count = 0;
        while (count < 3) {
            try {
                inputStream = obsApiClient.downloadFile(SPACE_OBS_BUCKET_NAME, file.getUri());
                break;
            } catch (Exception ex) {
                log.error("download file {} from OBS failed, ex is {}", file.getId() + ":" + file.getName(),
                    ex.getMessage() + " " + ex.getCause());
                count++;
            }
        }
        if (count >= 3) {
            log.error("download file {} from OBS failed, exceed max retry times", file.getId() + ":" + file.getName());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_DOWNLOAD_FAIL_ERROR);
        }
        return inputStream;
    }

    public String getDownloadUrlFromObs(String bucketName, String obsKey, long expires) {
        return obsApiClient.getTemporaryGetRsp(bucketName, obsKey, expires * 86400);
    }

    private ResponseEntity<InputStreamResource> buildDownloadFileRsp(String fileName, long fileLength,
        InputStream inputStream) {
        // 设置响应头
        HttpHeaders headers = new HttpHeaders();

        // 编码文件名，兼容不同浏览器
        String encodedFileName = URLEncoder.encode(fileName, StandardCharsets.UTF_8);
        headers.add(HttpHeaders.CONTENT_DISPOSITION,
            "attachment; filename=\"" + encodedFileName + "\"; " + "filename*=utf-8''" + encodedFileName);
        headers.add(HttpHeaders.CACHE_CONTROL, "no-cache, no-store, must-revalidate");
        headers.add(HttpHeaders.PRAGMA, "no-cache");
        headers.add(HttpHeaders.EXPIRES, "0");

        // 确定文件类型
        MediaType mediaType = AgentBuilderMediaType.matchFileType(fileName);
        return ResponseEntity.ok()
            .headers(headers)
            .contentType(mediaType)
            .contentLength(fileLength)
            .body(new InputStreamResource(inputStream));
    }

    /**
     * 下载任务文件，并支持将 .md 文件转换为 pdf/docx 格式的文件
     *
     * @param file 库中存储的文件信息
     * @return 文件流
     */
    public ResponseEntity<InputStreamResource> downloadTaskFileAndTransfer(AgentBuilderFileEntity file,
        String targetFormat) {
        // 只支持转换 .md 文件
        if (!targetFormat.isEmpty()
            && AgentBuilderMediaType.matchFileType(file.getName()) != AgentBuilderMediaType.MARKDOWN.getMediaType()) {
            log.error("[downloadFileAndTransfer] validate file fail, file type error, fileId:{}, type: {}, {}",
                file.getId(), AgentBuilderMediaType.matchFileType(file.getName()),
                AgentBuilderMediaType.MARKDOWN.getMediaType());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_NOT_SUPPORT_ERROR);
        }
        FileInfo fileInfo = getFileInfo(file);
        if (targetFormat.isEmpty()) {
            return buildDownloadFileRsp(file.getName(), fileInfo.fileLength(), fileInfo.contentStream());
        } else {
            return transferAndBuildDownloadFileRsp(file, targetFormat, fileInfo.contentStream());
        }
    }

    private ResponseEntity<InputStreamResource> transferAndBuildDownloadFileRsp(AgentBuilderFileEntity file,
        String targetFormat, InputStream contentStream) {
        String fileName = file.getName();
        int lastDotIndex = StringUtils.lastIndexOf(fileName, '.');
        if (lastDotIndex == -1) {
            fileName = fileName + "." + targetFormat;
        } else {
            fileName = StringUtils.substring(fileName, 0, lastDotIndex) + '.' + targetFormat;
        }
        FileInfo fileInfo = transferFileType(file, targetFormat, contentStream);
        return buildDownloadFileRsp(fileName, fileInfo.fileLength(), fileInfo.contentStream);
    }

    private record FileInfo(InputStream contentStream, long fileLength) {}

    private FileInfo getFileInfo(AgentBuilderFileEntity file) {
        if (AgentBuilderStorageType.OBS.getType() == file.getStorageType()) {
            return getObsFileInfo(file);
        } else if (AgentBuilderStorageType.DB.getType() == file.getStorageType()) {
            return getDbFileInfo(file);
        } else {
            log.error("[getFileInfo] validate file fail, file storage type error, fileId:{}, storage: {}", file.getId(),
                file.getStorageType());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_NOT_SUPPORT_ERROR);
        }
    }

    private FileInfo getObsFileInfo(AgentBuilderFileEntity file) {
        InputStream contentStream = getObsInputStream(file);
        FileMeta meta = fileStore.getMeta(SPACE_OBS_BUCKET_NAME + "/" + file.getUri());
        long fileLength = meta != null ? meta.getSize() : 0L;
        return new FileInfo(contentStream, fileLength);
    }

    private FileInfo getDbFileInfo(AgentBuilderFileEntity file) {
        byte[] fileBytes = Base64.getDecoder().decode(file.getContent());
        long fileLength = fileBytes.length;
        InputStream contentStream = new ByteArrayInputStream(fileBytes);
        return new FileInfo(contentStream, fileLength);
    }

    private static FileInfo transferFileType(AgentBuilderFileEntity file, String targetFormat, InputStream contentStream) {
        byte[] fileBytes;
        try {
            if (Objects.equals(targetFormat, "pdf")) {
                fileBytes = MdConvertUtil.getInstance().markdownToPdf(contentStream, targetFormat);
            } else if (Objects.equals(targetFormat, "docx")) {
                fileBytes = MdConvertUtil.getInstance().markdownToWord(contentStream, targetFormat);
            } else {
                throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_NOT_SUPPORT_ERROR);
            }
        } catch (IOException e) {
            log.error("[transferFileType] transfer file fail, fileId:{}, targetFormat: {}", file.getId(), targetFormat);
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_FILE_NOT_SUPPORT_ERROR);
        }
        return new FileInfo(new ByteArrayInputStream(fileBytes), fileBytes.length);
    }

    public AgentBuilderFile multipartFile2AgentBuilderFile(MultipartFile multipartFile) {
        try {
            AgentBuilderFile file = new AgentBuilderFile();
            file.setOriginalFilename(multipartFile.getOriginalFilename()).setBytes(multipartFile.getBytes());
            return file;
        } catch (IOException e) {
            log.error(
                "[multipartFile2AgentBuilderFile] convert multipartFile to AgentBuilderFile fail, occur IOException, ex is {}",
                e.getMessage() + " " + e.getCause());
            throw new AgentSpaceException(AgentSpaceErrorCodes.AGENT_BUILDER_SERVICE_INTERNAL_ERROR,
                "multipartFile2AgentBuilderFile occur IOException.");
        }
    }

    @Data
    @Accessors(chain = true)
    public static class AgentBuilderFile {
        private String originalFilename;

        private byte[] bytes;

        public InputStream getInputStream() {
            return new ByteArrayInputStream(this.bytes);
        }
    }

    @Data
    @Accessors(chain = true)
    public static class FileTransferResult {
        private AgentBuilderStorageType storageType;

        /**
         * 文件key，obs为路径，数据库为id
         */
        private String fileKey;

        /**
         * 记录结果
         */
        private boolean success;

        public <T> void fillAgentBuilderFileEntityContent(T fileEntity) {
            if (!(fileEntity instanceof AgentBuilderFileEntity || fileEntity instanceof AgentBuilderFileVo)) {
                log.warn("[fillAgentBuilderFileEntityContent] Unsupported file entity type, type is: {}",
                    fileEntity.getClass().getName());
                return;
            }
            if (!this.success) {
                log.error("[fillAgentBuilderFileEntityContent] file upload fail, fileId:{}, storage: {}",
                    getId(fileEntity), this.getStorageType());
            } else {
                if (AgentBuilderStorageType.OBS.equals(this.getStorageType())) {
                    setUri(fileEntity, this.getFileKey());
                    setContent(fileEntity, null); // 清空content字段
                    setStorageType(fileEntity, this.getStorageType().getType());
                } else if (AgentBuilderStorageType.DB.equals(this.getStorageType())) {
                    setContent(fileEntity, this.getFileKey());
                    setStorageType(fileEntity, this.getStorageType().getType());
                } else {
                    log.warn(
                        "[fillAgentBuilderFileEntityContent] file StorageType unknown, FileName: {}, FileId: {}, StorageType: {}",
                        getName(fileEntity), getId(fileEntity), this.getStorageType());
                }
            }
        }

        private <T> String getId(T fileEntity) {
            if (fileEntity instanceof AgentBuilderFileEntity) {
                return ((AgentBuilderFileEntity) fileEntity).getId();
            } else {
                return ((AgentBuilderFileVo) fileEntity).getId();
            }
        }

        private <T> String getName(T fileEntity) {
            if (fileEntity instanceof AgentBuilderFileEntity) {
                return ((AgentBuilderFileEntity) fileEntity).getName();
            } else {
                return ((AgentBuilderFileVo) fileEntity).getName();
            }
        }

        private <T> T setUri(T fileEntity, String uri) {
            if (fileEntity instanceof AgentBuilderFileEntity) {
                ((AgentBuilderFileEntity) fileEntity).setUri(uri);
            } else {
                ((AgentBuilderFileVo) fileEntity).setUri(uri);
            }
            return fileEntity;
        }

        private <T> T setContent(T fileEntity, String content) {
            if (fileEntity instanceof AgentBuilderFileEntity) {
                ((AgentBuilderFileEntity) fileEntity).setContent(content);
            } else {
                ((AgentBuilderFileVo) fileEntity).setContent(content);
            }
            return fileEntity;
        }

        private <T> T setStorageType(T fileEntity, int type) {
            if (fileEntity instanceof AgentBuilderFileEntity) {
                ((AgentBuilderFileEntity) fileEntity).setStorageType(type);
            } else {
                ((AgentBuilderFileVo) fileEntity).setStorageType(type);
            }
            return fileEntity;
        }
    }
}
