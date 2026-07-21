/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.storage.FileMeta;
import com.openjiuwen.studio.agent.common.storage.FileStore;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.FileInfoVo;
import com.openjiuwen.studio.prompt.engineering.dto.GetObsObjectReq;
import com.openjiuwen.studio.prompt.engineering.dto.ObsObjectResp;
import com.openjiuwen.studio.prompt.engineering.dto.ObsResp;
import com.openjiuwen.studio.prompt.engineering.enums.FileType;
import com.openjiuwen.studio.prompt.engineering.utils.FileUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class PromptObsService {

    private static final String IMAGE_FOLDER = "image";

    private final FileStore fileStore;

    private final String bucket;

    @Autowired
    public PromptObsService(FileStore fileStore) {
        this.fileStore = fileStore;
        this.bucket = fileStore.getDefaultNamespace();
    }

    private String path(String key) {
        return bucket + "/" + key;
    }

    public List<String> listObjectKeys(String rootDir) {
        return fileStore.list(path(rootDir));
    }

    public ObsObjectResp listObsObjects(String projectId, String workspaceId, GetObsObjectReq req)
        throws AgentStudioException {
        Map<String, List<ObsResp>> mapResp = new HashMap<>();
        try {
            String p = req.getPath();
            if (StringUtils.isNotEmpty(p) && !p.endsWith(CommonConstant.FOLDER_SEPARATOR)) {
                p = p + CommonConstant.FOLDER_SEPARATOR;
            }
            String prefix = req.getBucket() + "/" + p;
            List<FileMeta> metas = fileStore.listMetas(prefix);
            List<ObsResp> folder = new ArrayList<>();
            List<ObsResp> files = new ArrayList<>();
            String finalPath = p;
            if (metas != null) {
                for (FileMeta meta : metas) {
                    ObsResp obsResp = new ObsResp();
                    if (meta.isDirectory()) {
                        String dirName = meta.getName();
                        if (dirName.endsWith("/")) {
                            dirName = dirName.substring(0, dirName.length() - 1);
                        }
                        int lastSlash = dirName.lastIndexOf('/');
                        obsResp.setFileName(lastSlash >= 0 ? dirName.substring(lastSlash + 1) : dirName);
                        obsResp.setFileType("folder");
                        folder.add(obsResp);
                    } else {
                        String name = meta.getName();
                        if (name.startsWith(finalPath)) {
                            name = name.substring(finalPath.length());
                        }
                        int lastSlash = name.lastIndexOf('/');
                        if (lastSlash >= 0) {
                            name = name.substring(lastSlash + 1);
                        }
                        obsResp.setFileName(name);
                        obsResp.setLastModified(meta.getLastModified());
                        obsResp.setContentLength(meta.getSize());
                        obsResp.setFileType("file");
                        files.add(obsResp);
                    }
                }
            }
            mapResp.put("folders", folder);
            mapResp.put("files", files);
            ObsObjectResp obsObjectResp = new ObsObjectResp();
            obsObjectResp.setObsObjectMap(mapResp);
            return obsObjectResp;
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("get obs bucket folders error, bucketName: {} {}", req.getBucket().replaceAll("[\r\n]", ""),
                e.getMessage());
            throw new AgentStudioException(StudioError.GET_OBS_BUCKET_ERROR, req.getBucket().replaceAll("[\r\n]", ""));
        }
    }

    public FileInfoVo upLoadImage(String workspaceId, String projectId, MultipartFile file) {
        FileUtil.validateFile(file, FileType.IMAGE);
        String fileId = UUID.randomUUID().toString();
        String objectKey = String.format("%s/%s", IMAGE_FOLDER, fileId);
        try {
            InputStream inputStream = file.getInputStream();
            uploadObsFile(inputStream, objectKey);
            String tempUrl = getObsTempUrl(objectKey, 3600L);
            return new FileInfoVo().setFileId(fileId).setTempUrl(tempUrl);
        } catch (Exception e) {
            log.error("upload image error, {}", e.getMessage());
            throw new AgentStudioException(StudioError.UPLOAD_FILE_ERROR);
        }
    }

    public void uploadObsFile(InputStream inputStream, String objectKey) {
        try {
            fileStore.write(path(objectKey), inputStream);
            log.info("upload obs file success, file path:{}", objectKey);
        } catch (Exception e) {
            log.error("upload obs file failed, {}", e.getMessage());
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    public String getObsTempUrl(String objectKey, long expireSeconds) {
        try {
            return fileStore.getUrl(path(objectKey), expireSeconds);
        } catch (Exception e) {
            log.error("getObsTempUrl: getting temporary signature");
            throw new AgentStudioException(StudioError.DOWNLOAD_FILE_ERROR);
        }
    }

    public String uploadObsFile(String objectKey, String content, int expires) {
        try {
            fileStore.write(path(objectKey), content);
            return objectKey;
        } catch (Exception e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
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

    public void deleteObsFile(String deletePath) {
        fileStore.delete(path(deletePath));
    }

    public Boolean isExistObsFile(String obsPath) {
        return fileStore.exists(path(obsPath));
    }

    public void copyFile(String oldPath, String newPath) {
        if (StringUtils.isBlank(oldPath) || StringUtils.isBlank(newPath)) {
            return;
        }
        try {
            fileStore.copy(path(oldPath), path(newPath));
        } catch (Exception e) {
            log.error("copy file from one to one failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public void deleteByPrefix(String prefix) {
        fileStore.deleteByPrefix(path(prefix));
    }
}
