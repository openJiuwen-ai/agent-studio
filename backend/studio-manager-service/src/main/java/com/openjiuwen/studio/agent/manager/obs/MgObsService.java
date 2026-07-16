/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.obs;

import com.obs.services.ObsClient;
import com.obs.services.ObsConfiguration;
import com.obs.services.exception.ObsException;
import com.obs.services.model.AccessControlList;
import com.obs.services.model.BucketVersioningConfiguration;
import com.obs.services.model.CreateBucketRequest;
import com.obs.services.model.DeleteObjectsRequest;
import com.obs.services.model.DeleteObjectsResult;
import com.obs.services.model.HttpMethodEnum;
import com.obs.services.model.ListObjectsRequest;
import com.obs.services.model.ObjectListing;
import com.obs.services.model.ObjectMetadata;
import com.obs.services.model.ObsObject;
import com.obs.services.model.PutObjectRequest;
import com.obs.services.model.TemporarySignatureRequest;
import com.obs.services.model.TemporarySignatureResponse;
import com.obs.services.model.VersioningStatusEnum;
import com.obs.services.model.fs.NewFolderRequest;
import com.obs.services.model.fs.ObsFSFolder;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.service.CommonObsService;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;

import com.openjiuwen.studio.agent.manager.utils.OkHttpUtils;
import lombok.extern.slf4j.Slf4j;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import org.apache.commons.io.IOUtils;
import org.apache.commons.io.output.ByteArrayOutputStream;
import org.apache.commons.lang3.ObjectUtils;
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

import javax.annotation.PostConstruct;

/**
 * obs服务管理，用于上传或下载ir文件
 *
 * @since 2024.9.23
 */
@Slf4j
@Service
public class MgObsService implements CommonObsService {
    @Autowired
    private OkHttpUtils okHttpUtils;

    @Value("${obs.opensource:false}")
    private boolean opensource;

    @Value("${obs.ak}")
    private String accessKey;

    @Value("${obs.sk}")
    private String secretKey;

    @Value("${obs.url}")
    private String url;

    @Value("${obs.bucket}")
    private String bucket;

    @Value("${obs.stagingBucket}")
    private String stagingBucket;

    @Value("${obs.path.style}")
    private String pathStyle;

    private volatile ObsClient obsClient;

    @PostConstruct
    public void init() throws IOException {
        secretKey = CryptoUtils.decrypt(secretKey);
        try {
            ObsConfiguration config = new ObsConfiguration();
            config.setEndPoint(url);
            // 静态代码检查G.EXP.04：equals常量前置，避免pathStyle为null时抛出NullPointerException
            config.setPathStyle("path".equals(pathStyle));
            obsClient = new ObsClient(accessKey, secretKey, config);
        } catch (ObsException e) {
            log.error("init obs client failed!", e);
            obsClient.close();
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
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

    /**
     * 定时清理超过七天未更新的开源obs中的文件，未加锁可能执行多次
     */
    @Scheduled(fixedDelay = 24 * 60 * 60 * 1000)
    public void cleanObsObjects() {
        final long millis = TimeUnit.DAYS.toMillis(7);
        if (opensource) {
            try {
                // 获取文件列表
                List<ObsObject> objects = listObsObjects(CommonConstant.FILE);
                if (ObjectUtils.isEmpty(objects)) {
                    return;
                }

                // 删除超过七天未更新的文件
                for (ObsObject object : objects) {
                    Instant lastModified = object.getMetadata().getLastModified().toInstant();
                    Instant now = Instant.now();
                    if (Duration.between(lastModified, now).toMillis() > millis) {
                        deleteObsFile(object.getObjectKey());
                    }
                }
                log.info("delete obs files succeed!");
            } catch (ObsException e) {
                log.error("delete obs files failed!", e);
                throw new AgentStudioException(StudioError.OBS_FAILED);
            }
        }
    }

    public String uploadObsFile(String pathKey, String objectKey, String type, String fileInfo, String prefix) {
        return uploadObsFile(String.format("%s/%s/%s/%s.json", type, prefix, pathKey, objectKey), fileInfo, -1);
    }

    /**
     * 上传OBS文件
     *
     * @param objectKey 文件路径
     * @param content 文件内容
     * @param expires 过期时间（单位：天）
     * @return 文件路径
     */
    public String uploadObsFile(String objectKey, String content, int expires) {
        try (ByteArrayInputStream inputStream = new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))) {
            return uploadObsFile(objectKey, inputStream, expires);
        } catch (ObsException | IOException e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 上传OBS文件到用户桶
     *
     * @param objectKey 文件路径
     * @param content 文件内容
     * @param expires 过期时间（单位：天）
     * @return 文件路径
     */
    public String uploadStagingBucket(String objectKey, String content, int expires) {
        try (ByteArrayInputStream inputStream = new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))) {
            return uploadStreamStagingBucket(objectKey, inputStream, expires);
        } catch (ObsException | IOException e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 上传OBS文件
     *
     * @param objectKey 文件路径
     * @param inputStream 文件输入流
     * @param expires 过期时间（单位：天）
     * @return 文件路径
     */
    public String uploadStreamStagingBucket(String objectKey, InputStream inputStream, int expires) {
        // 如不存在则新建桶
        creatBucketIfAbsent();

        try {
            ObjectMetadata metadata = new ObjectMetadata();
            metadata.setContentLength((long) inputStream.available());
            PutObjectRequest request = new PutObjectRequest();
            request.setBucketName(stagingBucket);
            request.setInput(inputStream);
            request.setMetadata(opensource ? metadata : null);
            request.setObjectKey(objectKey);
            if (expires > 0) {
                request.setExpires(expires);
            }
            obsClient.putObject(request);
            log.info("upload obs file success, file path:{}", objectKey);
            return objectKey;
        } catch (ObsException | IOException e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }
    /**
     * 上传OBS文件
     *
     * @param objectKey 文件路径
     * @param inputStream 文件输入流
     * @param expires 过期时间（单位：天）
     * @return 文件路径
     */
    public String uploadObsFile(String objectKey, InputStream inputStream, int expires) {
        // 如不存在则新建桶
        creatBucketIfAbsent();

        try {
            ObjectMetadata metadata = new ObjectMetadata();
            metadata.setContentLength((long) inputStream.available());
            PutObjectRequest request = new PutObjectRequest();
            request.setBucketName(bucket);
            request.setInput(inputStream);
            request.setMetadata(opensource ? metadata : null);
            request.setObjectKey(objectKey);
            if (expires > 0) {
                request.setExpires(expires);
            }

            obsClient.putObject(request);
            log.info("upload obs file success, file path:{}", objectKey);
            return objectKey;
        } catch (ObsException | IOException e) {
            log.error("upload obs file failed!", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    public String downloadObsFile(String relativePath) {
        String obsFile = null;
        InputStream inputStream = null;
        try {
            ObsObject obsObject = obsClient.getObject(bucket, relativePath);
            inputStream = obsObject.getObjectContent();
            if (inputStream != null) {
                obsFile = IOUtils.toString(inputStream, StandardCharsets.UTF_8);
            }
        } catch (Exception e) {
            log.error("download file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        } finally {
            IOUtils.closeQuietly(inputStream);
        }
        return obsFile;
    }

    /**
     * 下载OBS图片文件
     *
     * @param relativePath 文件路径
     * @return 字节流
     */
    public String downloadObsImageFile(String relativePath) {
        InputStream content = null;
        String iconPath = "icon/" + relativePath;
        try {
            ObsObject obsObject = obsClient.getObject(bucket, iconPath);
            content = obsObject.getObjectContent();
            if (content != null) {
                // 将InputStream转为字节数组
                ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
                byte[] buffer = new byte[1024];
                int bytesRead;
                while ((bytesRead = content.read(buffer)) != -1) {
                    outputStream.write(buffer, 0, bytesRead);
                }
                byte[] bytes = outputStream.toByteArray();
                return Base64.getEncoder().encodeToString(bytes);
            } else {
                throw new AgentStudioException(StudioError.OBS_FAILED);
            }
        } catch (Exception e) {
            log.error("download image file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        } finally {
            IOUtils.closeQuietly(content);
        }
    }

    /**
     * 上传文件，预设过期时间
     *
     * @param inputStream 待文件的输入流
     * @param fileName 文件名
     * @param expires 过期时间（天）
     * @return 对象名
     */
    public String uploadObsFileWithExpires(InputStream inputStream, String fileName, int expires) {
        String objectKey = String.format("%s/%s", CommonConstant.FILE, fileName);
        return uploadObsFile(objectKey, inputStream, expires);
    }

    public ObsFSFolder newFolder(NewFolderRequest request) throws ObsException {
        try {
            return obsClient.newFolder(request);
        } catch (ObsException e) {
            log.error("newFolder failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public void deleteObsFile(String relativePath) {
        try {
            if (obsClient.doesObjectExist(bucket, relativePath)) {
                obsClient.deleteObject(bucket, relativePath);
            }
        } catch (ObsException e) {
            log.error("delete file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    public void softDeleteObsFile(String relativePath) {
        try {
            if (obsClient.doesObjectExist(bucket, relativePath)) {
                copyObsObject(relativePath, relativePath + CommonConstant.DELETED_SUFFIX);
                obsClient.deleteObject(bucket, relativePath);
            }
        } catch (ObsException e) {
            log.error("soft delete file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 根据目录路径批量删除OBS文件
     *
     * @param dirPath dirPath
     */
    public void deleteObsObjects(String dirPath) {
        try {
            ListObjectsRequest request = new ListObjectsRequest(bucket);
            request.setDelimiter(CommonConstant.FOLDER_SEPARATOR);
            /* 如果path不以/结尾会出现如查询data返回data2/之类的错误文件夹信息 */
            String path = dirPath;
            if (StringUtils.isNotEmpty(dirPath) && !dirPath.endsWith(CommonConstant.FOLDER_SEPARATOR)) {
                path = dirPath + CommonConstant.FOLDER_SEPARATOR;
            }
            request.setPrefix(path);
            ObjectListing objects = obsClient.listObjects(request);
            objects.getObjects().forEach(obsObject -> obsClient.deleteObject(bucket, obsObject.getObjectKey()));
        } catch (ObsException e) {
            log.error("delete file from obs failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 获取指定路径下的obs对象列表
     *
     * @param path 不含桶名的路径
     * @return obs对象列表
     */
    public List<ObsObject> listObsObjects(String path) {
        ListObjectsRequest listObjectsRequest = buildObjectsRequest(path);
        ObjectListing objectListing = obsClient.listObjects(listObjectsRequest);
        if (ObjectUtils.isEmpty(objectListing)) {
            return new ArrayList<>();
        }
        return objectListing.getObjects();
    }

    /**
     * 分页获取指定路径下的obs对象列表
     *
     * @param path 不含桶名的路径
     * @return obs对象列表
     */
    public List<ObsObject> listPageObsObjects(String path, int index, int pageSize) {
        ListObjectsRequest listObjectsRequest = buildObjectsRequest(path);
        listObjectsRequest.setMaxKeys(pageSize);
        ObjectListing objectListing = null;
        try {
            do {
                objectListing = obsClient.listObjects(listObjectsRequest);
                listObjectsRequest.setMarker(objectListing.getNextMarker());
            } while (objectListing.isTruncated() && --index > 0);

        } catch (ObsException e) {
            log.error("list obs file failed!");
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
        return objectListing.getObjects();
    }

    private ListObjectsRequest buildObjectsRequest(String path) {
        ListObjectsRequest listObjectsRequest = new ListObjectsRequest();
        listObjectsRequest.setBucketName(bucket);
        listObjectsRequest.setDelimiter(CommonConstant.FOLDER_SEPARATOR);
        // 如果path不以/结尾会出现如查询data返回data2/之类的错误文件夹信息
        if (StringUtils.isNotEmpty(path) && !path.endsWith(CommonConstant.FOLDER_SEPARATOR)) {
            path = path + CommonConstant.FOLDER_SEPARATOR;
        }
        listObjectsRequest.setPrefix(path);
        return listObjectsRequest;
    }

    private void creatBucketIfAbsent() {
        if (!obsClient.headBucket(bucket)) {
            try {
                CreateBucketRequest request = new CreateBucketRequest();
                request.setBucketName(bucket);

                // 设置桶访问权限为私有读写
                request.setAcl(AccessControlList.REST_CANNED_PRIVATE);
                obsClient.createBucket(request);
                // 开启多版本控制
                obsClient.setBucketVersioning(bucket, new BucketVersioningConfiguration(VersioningStatusEnum.ENABLED));
            } catch (ObsException e) {
                log.error("create obs bucket failed!");
                throw new AgentStudioException(StudioError.OBS_FAILED);
            }
        }
    }

    /**
     * 获取下载指定对象的临时URL
     *
     * @param objectName 对象名，不包含桶名
     * @param expires 临时URL的过期时间（秒）
     * @return TemporarySignatureResponse
     */
    public TemporarySignatureResponse getTemporaryGetRsp(boolean stagingFlag, String objectName, long expires) {
        try {
            TemporarySignatureRequest request = new TemporarySignatureRequest(HttpMethodEnum.GET, expires);
            request.setBucketName(stagingFlag? stagingBucket: bucket);
            request.setObjectKey(objectName);
            return obsClient.createTemporarySignature(request);
        } catch (ObsException e) {
            log.error("Failed to obtain the temporary OBS URL.");
            throw new AgentStudioException(StudioError.GET_OBS_TEMPORARY_URL_FAILED);
        }
    }

    /**
     * 拷贝obs对象
     *
     * @param sourceIrName 源对象名
     * @param targetIrName 目标对象名
     */
    public void copyObsObject(String sourceIrName, String targetIrName) {
        try {
            obsClient.copyObject(bucket, sourceIrName, bucket, targetIrName);
        } catch (ObsException e) {
            log.error("OBS object copy failed.", e);
            throw new AgentStudioException(StudioError.COPY_FROM_OBS_FAIL);
        }
    }

    public ObjectMetadata getObjectMetadata(String objectKey) {
        try {
            if (obsClient.doesObjectExist(bucket, objectKey)) {
                ObsObject obsObject = obsClient.getObject(bucket, objectKey);
                if (obsObject == null) {
                    return new ObjectMetadata();
                }
                return obsObject.getMetadata();
            }
        } catch (ObsException e) {
            log.error("get object metadata from obs failed, check obs configration", e);
        }
        return new ObjectMetadata();
    }

    /**
     * 是否存在对应的key
     */
    public boolean isExistedKey(String sourceKey) {
        return obsClient.doesObjectExist(bucket, sourceKey);
    }

    public String getAbsolutePath(String relativePath) {
        return String.format("obs://%s/%s", bucket, relativePath);
    }

    /**
     * 根据前缀删除obs对象
     *
     * @param prefix obs前缀
     * @return 删除结果
     */
    public DeleteObjectsResult deleteByPrefix(String prefix) {
        ListObjectsRequest request = new ListObjectsRequest(bucket);
        request.setPrefix(prefix);
        request.setMaxKeys(100);
        ObjectListing objectListing;
        DeleteObjectsResult sumDelResult = new DeleteObjectsResult();
        do {
            objectListing = obsClient.listObjects(request);
            DeleteObjectsRequest deleteRequest = new DeleteObjectsRequest(bucket);
            if (objectListing.getObjects().size() > 0) {
                for (ObsObject obj : objectListing.getObjects()) {
                    deleteRequest.addKeyAndVersion(obj.getObjectKey(), null);
                }
                DeleteObjectsResult delResult = obsClient.deleteObjects(deleteRequest);
                // 打印删除结果
                log.info("Batch delete OBS prefix:{}, success:{}. failed:{}.", prefix,
                    delResult.getDeletedObjectResults().size(), delResult.getErrorResults().size());
                sumDelResult.getDeletedObjectResults().addAll(delResult.getDeletedObjectResults());
                sumDelResult.getErrorResults().addAll(delResult.getErrorResults());
            }
        } while (objectListing != null && objectListing.isTruncated());
        log.info("Batch delete OBS summary prefix:{}, success:{}. failed:{}.", prefix,
            sumDelResult.getDeletedObjectResults().size(), sumDelResult.getErrorResults().size());
        return sumDelResult;
    }

    /**
     * 根据前缀给对象加后缀
     *
     * @param prefix obs前缀
     * @return 删除结果
     */
    public void appendSuffixByPrefix(String prefix, String suffix) {
        ListObjectsRequest request = new ListObjectsRequest(bucket);
        request.setPrefix(prefix);
        request.setMaxKeys(100);
        ObjectListing objectListing;
        DeleteObjectsResult sumDelResult = new DeleteObjectsResult();
        do {
            objectListing = obsClient.listObjects(request);
            DeleteObjectsRequest deleteRequest = new DeleteObjectsRequest(bucket);
            if (objectListing.getObjects().size() > 0) {
                for (ObsObject obj : objectListing.getObjects()) {
                    String objectKey = obj.getObjectKey();
                    if (!objectKey.contains(suffix)) {
                        String targetKey = objectKey + suffix;
                        copyObsObject(objectKey, targetKey);
                    }
                    deleteRequest.addKeyAndVersion(objectKey, null);
                }
                DeleteObjectsResult delResult = obsClient.deleteObjects(deleteRequest);
                sumDelResult.getDeletedObjectResults().addAll(delResult.getDeletedObjectResults());
                sumDelResult.getErrorResults().addAll(delResult.getErrorResults());
            }
        } while (objectListing != null && objectListing.isTruncated());
        log.info("Batch delete OBS summary prefix:{}, success:{}. failed:{}.", prefix,
                sumDelResult.getDeletedObjectResults().size(), sumDelResult.getErrorResults().size());
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
