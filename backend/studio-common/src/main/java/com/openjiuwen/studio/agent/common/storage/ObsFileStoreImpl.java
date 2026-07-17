/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import com.obs.services.ObsClient;
import com.obs.services.ObsConfiguration;
import com.obs.services.exception.ObsException;
import com.obs.services.model.AccessControlList;
import com.obs.services.model.BucketVersioningConfiguration;
import com.obs.services.model.CreateBucketRequest;
import com.obs.services.model.HttpMethodEnum;
import com.obs.services.model.ListObjectsRequest;
import com.obs.services.model.ObjectListing;
import com.obs.services.model.ObjectMetadata;
import com.obs.services.model.ObsObject;
import com.obs.services.model.PutObjectRequest;
import com.obs.services.model.TemporarySignatureRequest;
import com.obs.services.model.TemporarySignatureResponse;
import com.obs.services.model.VersioningStatusEnum;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.io.IOUtils;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Slf4j
public class ObsFileStoreImpl implements FileStore {

    private final StorageProperties.Obs obsConfig;
    private volatile ObsClient obsClient;

    public ObsFileStoreImpl(StorageProperties.Obs obsConfig) {
        this.obsConfig = obsConfig;
    }

    public void init() {
        String sk = CryptoUtils.decrypt(obsConfig.getSk());
        try {
            ObsConfiguration config = new ObsConfiguration();
            config.setEndPoint(obsConfig.getUrl());
            config.setPathStyle("path".equals(obsConfig.getPathStyle()));
            obsClient = new ObsClient(obsConfig.getAk(), sk, config);
        } catch (ObsException e) {
            log.error("init obs client failed!", e);
            if (obsClient != null) {
                try {
                    obsClient.close();
                } catch (IOException ex) {
                    log.error("close obs client failed!", ex);
                }
            }
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }

        if (obsConfig.isAutoCreateBucket()) {
            ensureBucket(obsConfig.getBucket());
            if (obsConfig.getStagingBucket() != null && !obsConfig.getStagingBucket().isEmpty()) {
                ensureBucket(obsConfig.getStagingBucket());
            }
        }
    }

    public void destroy() {
        if (obsClient != null) {
            try {
                obsClient.close();
            } catch (IOException e) {
                log.error("close obs client failed!", e);
            }
        }
    }

    private String[] splitPath(String path) {
        int slash = path.indexOf('/');
        if (slash <= 0) {
            return new String[]{obsConfig.getBucket(), path};
        }
        return new String[]{path.substring(0, slash), path.substring(slash + 1)};
    }

    @Override
    public String write(String path, String content) {
        String[] parts = splitPath(path);
        try (ByteArrayInputStream is = new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))) {
            doPut(parts[0], parts[1], is, -1);
        } catch (IOException e) {
            log.error("write failed: {}", path, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
        return path;
    }

    @Override
    public String write(String path, InputStream inputStream) {
        return write(path, inputStream, -1);
    }

    @Override
    public String write(String path, InputStream inputStream, int expires) {
        String[] parts = splitPath(path);
        doPut(parts[0], parts[1], inputStream, expires);
        return path;
    }

    private void doPut(String bucket, String key, InputStream inputStream, int expires) {
        ensureBucket(bucket);
        try {
            ObjectMetadata metadata = new ObjectMetadata();
            metadata.setContentLength((long) inputStream.available());
            PutObjectRequest request = new PutObjectRequest();
            request.setBucketName(bucket);
            request.setInput(inputStream);
            request.setMetadata(obsConfig.isOpensource() ? metadata : null);
            request.setObjectKey(key);
            if (expires > 0) {
                request.setExpires(expires);
            }
            obsClient.putObject(request);
            log.info("write success: {}/{}", bucket, key);
        } catch (ObsException | IOException e) {
            log.error("write failed: {}/{}", bucket, key, e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    @Override
    public String read(String path) {
        String[] parts = splitPath(path);
        InputStream is = null;
        try {
            ObsObject obj = obsClient.getObject(parts[0], parts[1]);
            is = obj.getObjectContent();
            if (is != null) {
                return IOUtils.toString(is, StandardCharsets.UTF_8);
            }
            return null;
        } catch (Exception e) {
            log.error("read failed: {}", path, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        } finally {
            IOUtils.closeQuietly(is);
        }
    }

    @Override
    public InputStream readStream(String path) {
        String[] parts = splitPath(path);
        try {
            ObsObject obj = obsClient.getObject(parts[0], parts[1]);
            return obj.getObjectContent();
        } catch (ObsException e) {
            log.error("read stream failed: {}", path, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    @Override
    public boolean delete(String path) {
        String[] parts = splitPath(path);
        try {
            if (obsClient.doesObjectExist(parts[0], parts[1])) {
                obsClient.deleteObject(parts[0], parts[1]);
                return true;
            }
            return false;
        } catch (ObsException e) {
            log.error("delete failed: {}", path, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    @Override
    public boolean exists(String path) {
        String[] parts = splitPath(path);
        try {
            return obsClient.doesObjectExist(parts[0], parts[1]);
        } catch (ObsException e) {
            log.error("check exists failed: {}", path, e);
            return false;
        }
    }

    @Override
    public boolean copy(String sourcePath, String targetPath) {
        String[] src = splitPath(sourcePath);
        String[] tgt = splitPath(targetPath);
        try {
            obsClient.copyObject(src[0], src[1], tgt[0], tgt[1]);
            return true;
        } catch (ObsException e) {
            log.error("copy failed: {} -> {}", sourcePath, targetPath, e);
            throw new AgentStudioException(StudioError.COPY_FROM_OBS_FAIL);
        }
    }

    @Override
    public List<String> list(String prefix) {
        String[] parts = splitPath(prefix);
        String bucket = parts[0];
        String keyPrefix = parts.length > 1 ? parts[1] : "";
        if (keyPrefix.isEmpty() || !keyPrefix.endsWith("/")) {
            keyPrefix = keyPrefix + "/";
        }
        ListObjectsRequest request = new ListObjectsRequest(bucket);
        request.setPrefix(keyPrefix);
        request.setMaxKeys(1000);
        List<String> keys = new ArrayList<>();
        ObjectListing result;
        do {
            result = obsClient.listObjects(request);
            if (result.getObjects() != null) {
                for (ObsObject obj : result.getObjects()) {
                    keys.add(obj.getObjectKey());
                }
            }
            request.setMarker(result.getNextMarker());
        } while (result.isTruncated());
        return keys;
    }

    @Override
    public boolean deleteByPrefix(String prefix) {
        String[] parts = splitPath(prefix);
        String bucket = parts[0];
        String keyPrefix = parts.length > 1 ? parts[1] : "";
        ListObjectsRequest request = new ListObjectsRequest(bucket);
        request.setPrefix(keyPrefix);
        request.setMaxKeys(100);
        ObjectListing objectListing;
        boolean allDeleted = true;
        do {
            objectListing = obsClient.listObjects(request);
            for (ObsObject obj : objectListing.getObjects()) {
                try {
                    obsClient.deleteObject(bucket, obj.getObjectKey());
                } catch (ObsException e) {
                    log.warn("delete object failed: {}", obj.getObjectKey());
                    allDeleted = false;
                }
            }
        } while (objectListing != null && objectListing.isTruncated());
        return allDeleted;
    }

    @Override
    public String getDownloadUrl(String path, long expiresSeconds) {
        String[] parts = splitPath(path);
        try {
            TemporarySignatureRequest request = new TemporarySignatureRequest(HttpMethodEnum.GET, expiresSeconds);
            request.setBucketName(parts[0]);
            request.setObjectKey(parts[1]);
            TemporarySignatureResponse response = obsClient.createTemporarySignature(request);
            return response.getSignedUrl();
        } catch (ObsException e) {
            log.error("get download url failed: {}", path, e);
            throw new AgentStudioException(StudioError.GET_OBS_TEMPORARY_URL_FAILED);
        }
    }

    @Override
    public FileMeta getMeta(String path) {
        String[] parts = splitPath(path);
        try {
            ObjectMetadata meta = obsClient.getObjectMetadata(parts[0], parts[1]);
            if (meta == null) {
                return null;
            }
            FileMeta fm = new FileMeta();
            fm.setName(parts[1]);
            fm.setSize(meta.getContentLength());
            fm.setLastModified(meta.getLastModified().getTime());
            fm.setDirectory(false);
            return fm;
        } catch (ObsException e) {
            log.error("get meta failed: {}", path, e);
            return null;
        }
    }

    @Override
    public List<FileMeta> listMetas(String prefix) {
        String[] parts = splitPath(prefix);
        String bucket = parts[0];
        String keyPrefix = parts.length > 1 ? parts[1] : "";
        if (!keyPrefix.endsWith("/")) {
            keyPrefix = keyPrefix + "/";
        }
        ListObjectsRequest request = new ListObjectsRequest(bucket);
        request.setPrefix(keyPrefix);
        request.setDelimiter("/");
        request.setMaxKeys(1000);
        List<FileMeta> metas = new ArrayList<>();
        ObjectListing result;
        do {
            result = obsClient.listObjects(request);
            if (result.getCommonPrefixes() != null) {
                for (String commonPrefix : result.getCommonPrefixes()) {
                    FileMeta fm = new FileMeta();
                    fm.setName(commonPrefix);
                    fm.setSize(0L);
                    fm.setLastModified(-1L);
                    fm.setDirectory(true);
                    metas.add(fm);
                }
            }
            if (result.getObjects() != null) {
                for (ObsObject obj : result.getObjects()) {
                    if (obj.getObjectKey().equals(keyPrefix)) {
                        continue;
                    }
                    FileMeta fm = new FileMeta();
                    fm.setName(obj.getObjectKey());
                    ObjectMetadata meta = obj.getMetadata();
                    fm.setSize(meta != null ? meta.getContentLength() : -1L);
                    fm.setLastModified(meta != null && meta.getLastModified() != null
                        ? meta.getLastModified().getTime() : -1L);
                    fm.setDirectory(false);
                    metas.add(fm);
                }
            }
            request.setMarker(result.getNextMarker());
        } while (result.isTruncated());
        return metas;
    }

    private void ensureBucket(String bucketName) {
        if (!obsClient.headBucket(bucketName)) {
            try {
                CreateBucketRequest request = new CreateBucketRequest();
                request.setBucketName(bucketName);
                request.setAcl(AccessControlList.REST_CANNED_PRIVATE);
                obsClient.createBucket(request);
                obsClient.setBucketVersioning(bucketName,
                    new BucketVersioningConfiguration(VersioningStatusEnum.ENABLED));
            } catch (ObsException e) {
                log.error("create bucket {} failed!", bucketName, e);
                throw new AgentStudioException(StudioError.OBS_FAILED);
            }
        }
    }

    public String getUrl() {
        return obsConfig.getUrl();
    }

    @Override
    public String getDefaultNamespace() {
        return obsConfig.getBucket();
    }

    @Override
    public String getStagingNamespace() {
        return obsConfig.getStagingBucket();
    }
}
