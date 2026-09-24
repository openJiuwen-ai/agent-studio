/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service;

import static java.util.Comparator.comparing;
import static java.util.stream.Collectors.collectingAndThen;
import static java.util.stream.Collectors.toCollection;

import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.agentbase.common.constant.Constants;
import com.openjiuwen.studio.agent.agentbase.common.enums.KnowledgeBaseType;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeRepoMapper;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeRepo;
import com.openjiuwen.studio.agent.agentbase.model.UploadFilesResp;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeRepoContext;
import com.openjiuwen.studio.agent.agentbase.service.validate.KnowledgeDatasetValidateService;
import com.openjiuwen.studio.agent.agentbase.service.validate.ResourceValidateService;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.knowledge.ChunkUtils;
import com.openjiuwen.studio.agent.agentbase.utils.ShareScopeValidUtil;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesRequestBody;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.DownloadFileByAccessKeyQo;
import com.openjiuwen.studio.agent.manager.dto.FileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FileInfo;
import com.openjiuwen.studio.agent.manager.dto.ListFileChunksQo;
import com.openjiuwen.studio.agent.manager.dto.ListFileChunksReq;
import com.openjiuwen.studio.agent.manager.dto.ListFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.RetrieveFileContentQo;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeFileQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoReq;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoRsp;
import com.openjiuwen.studio.agent.manager.dto.UploadKnowledgeFileResponseBody;
import com.openjiuwen.studio.agent.manager.service.IKnowledgeFileManagementService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.util.Strings;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicReference;

@Slf4j
@Service
public class KnowledgeBaseDatasetServiceImpl implements IKnowledgeFileManagementService {

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    private final RedisClient redisClient;

    @Value("${knowledge.file-type}")
    private String knowledgeFileType;

    @Value("${knowledge.image-file-type}")
    private String imageTypes;

    @Value("${knowledge.ocr-enable}")
    private boolean ocrEnabled;

    private final KnowledgeRepoMapper knowledgeRepoMapper;

    private final KnowledgeRepoContext knowledgeRepoContext;

    private final KnowledgeDatasetValidateService knowledgeDatasetValidateService;

    private final ResourceValidateService resourceValidateService;

    public KnowledgeBaseDatasetServiceImpl(KnowledgeRepoMapper knowledgeRepoMapper,
        KnowledgeRepoContext knowledgeRepoContext, KnowledgeBaseMapper knowledgeBaseMapper,
        KnowledgeDatasetValidateService knowledgeDatasetValidateService,
        ResourceValidateService resourceValidateService, RedisClient redisClient) {
        this.knowledgeRepoMapper = knowledgeRepoMapper;
        this.knowledgeRepoContext = knowledgeRepoContext;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
        this.knowledgeDatasetValidateService = knowledgeDatasetValidateService;
        this.resourceValidateService = resourceValidateService;
        this.redisClient = redisClient;
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "KnowledgeBaseFile",
        description = "批量删除知识库文件",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public BatchDeleteKnowledgeFilesResponseBody batchDeleteKnowledgeFiles(String projectId, String knowledgeBaseId,
        String workspaceId, BatchDeleteKnowledgeFilesRequestBody body) {
        log.info("operation log projectId: {}, userId:{}, batchDeleteFile", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        // 删除需校验知识文件权限
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("Can not delete file {} from external knowledge repo: {}", body.getFileIds(), knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_TO_DELETE_FILE, body.getFileIds(), knowledgeBaseId);
        }
        // 查询知识库文件
        List<FileInfo> fileInfo = retrieveDeletedFile(body, knowledgeBaseEntity);
        String domainId = RequestContextUtils.getRequestUserDomainId();
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
            projectId);
        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(body.getFileIds(), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The files [{}] are not belong current knowledge base [{}]", body.getFileIds(), knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        // 删除知识库文件
        BatchDeleteKnowledgeFilesResponseBody batchDeleteFileResp = knowledgeRepoContext.getService(
                knowledgeRepoEntity.getSource())
            .batchDeleteFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), body);
        AtomicReference<Long> deleteFileSize = new AtomicReference<>(0L);
        fileInfo.forEach(file -> {
            deleteFileSize.updateAndGet(v -> v + file.getFileSize());
        });
        // 更新数据库中知识库大小
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, -deleteFileSize.get(),
            -batchDeleteFileResp.getDeletedCount());
        return batchDeleteFileResp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "KnowledgeBaseFile",
        description = "创建知识库文件切片",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public CreateFileChunkRsp createFileChunk(String projectId, String knowledgeBaseId, String fileId,
        String workspaceId, FileChunkReq body) {
        log.info("operation log projectId: {}, userId:{}, createFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 新增切片需校验知识文件权限
        checkFileChunkPrivilege(knowledgeBaseEntity, "create file chunk");

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeBaseEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());

        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] is not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }

        // 调用kooSearch接口新增切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource()).createFileChunk(knowledgeRepo, fileId, body);
        return new CreateFileChunkRsp().setTitle(body.getTitle());
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "KnowledgeBaseFile",
        description = "删除知识库文件",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteFile(String projectId, String fileId, String knowledgeBaseId, String workspaceId) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        log.info("operation log projectId: {}, userId:{}, deleteFile", projectId,
            RequestContextUtils.getRequestUserId());
        // 删除需校验知识文件权限
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("Can not delete file {} from external knowledge repo: {}", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_TO_DELETE_FILE, fileId, knowledgeBaseId);
        }
        // 查询知识库文件
        FileInfo fileInfo = retrieveFile(fileId, knowledgeBaseEntity);
        String domainId = RequestContextUtils.getRequestUserDomainId();
        // 删除知识库文件
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
            projectId);
        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file {} is not belong current knowledge base {}", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .deleteFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), fileId);
        // 更新数据库中知识库大小
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, -fileInfo.getFileSize(), -1);
        return new CommonDeleteRsp().setId(fileId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "KnowledgeBaseFile",
        description = "删除知识库文件切片",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteFileChunk(String projectId, String knowledgeBaseId, String fileId, String chunkId,
        String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 删除切片需校验知识文件权限
        checkFileChunkPrivilege(knowledgeBaseEntity, "delete file chunk");

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] is not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        // 调用kooSearch接口删除切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .deleteFileChunk(knowledgeRepo, fileId, chunkId);
        return new CommonDeleteRsp().setId(chunkId);
    }

    @Override
    public FileChunkListRsp listFileChunks(String projectId, String knowledgeBaseId, String fileId,
        ListFileChunksQo listFileChunksQo) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        int pageNum = listFileChunksQo.getOffset() / listFileChunksQo.getLimit() + 1;

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setWorkspaceId(listFileChunksQo.getWorkspaceId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        ListFileChunksReq listFileChunksReq = new ListFileChunksReq().setFileId(fileId)
            .setPageNum(pageNum)
            .setPageSize(listFileChunksQo.getLimit());
        FileChunkListRsp response = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .listFileChunks(knowledgeRepo, listFileChunksReq);
        response.getFileChunkList().forEach(item -> {
            // 针对content内容为空进行处理
            if (StringUtils.isEmpty(item.getContent())) {
                item.setContent(Strings.EMPTY);
            }

            // 针对切片中的图片进行处理
            List<String> imageIds = ChunkUtils.extractImageId(item.getContent());
            if (CollectionUtils.isNotEmpty(imageIds)) {
                item.setContent(ChunkUtils.removeImageId(item.getContent()));
                item.setImageIds(imageIds);
                List<String> imagePaths = new ArrayList<>();
                imageIds.forEach(imageId -> {
                    imagePaths.add(ChunkUtils.generateChunkImageUriPath(projectId, knowledgeBaseId, imageId));
                });
                item.setImagePaths(imagePaths);
            }
        });
        return response;
    }

    @Override
    public ListKnowledgeFilesResponseBody listKnowledgeFiles(String projectId, String knowledgeBaseId,
        ListKnowledgeFilesQo listFilesQo) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, listFilesQo.getWorkspaceId(), knowledgeBaseEntity);
        int pageNum = listFilesQo.getOffset() / listFilesQo.getLimit() + 1;
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        ListFileReq listFileReq = new ListFileReq().setFileName(
                Optional.of(listFilesQo).map(ListKnowledgeFilesQo::getName).orElse(null))
            .setFileStatus(Optional.of(listFilesQo).map(ListKnowledgeFilesQo::getStatus).orElse(null))
            .setFileType(Optional.of(listFilesQo).map(ListKnowledgeFilesQo::getType).orElse(null))
            .setPageNum(pageNum)
            .setPageSize(listFilesQo.getLimit());
        return knowledgeRepoContext.getService(knowledgeRepoEntity.getSource()).listFiles(knowledgeRepo, listFileReq);
    }


    @Override
    public Resource downloadKnowledgeImageByAccessKey(String projectId, String imageId, String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, queryImageByAccessKey", projectId,
            RequestContextUtils.getRequestUserId());
        String imageStr = redisClient.get(Constants.KNOWLEDGE_IMAGE_CACHE_PREFIX + imageId);
        if (StringUtils.isBlank(imageStr)) {
            throw new AgentBaseException(ErrorCode.IMAGE_NOT_EXIST_OR_EXPIRED);
        }
        String[] imageDetail = imageStr.split(",");
        return downloadKnowledgeImage(projectId, imageDetail[0], imageDetail[1]);
    }

    @Override
    public FileInfo showKnowledgeFile(String projectId, String fileId, String knowledgeBaseId,
        ShowKnowledgeFileQo retrieveFileQo) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        return retrieveFile(fileId, knowledgeBaseEntity);
    }

    @Override
    public Resource retrieveFileContent(String projectId, String fileId, String knowledgeBaseId,
        RetrieveFileContentQo retrieveFileContentQo) {
        log.info("operation log projectId: {}, userId:{}, retrieveFileContent", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, retrieveFileContentQo.getWorkspaceId(),
            knowledgeBaseEntity);
        return downloadFile(projectId, fileId, knowledgeBaseEntity);
    }

    @Override
    public Resource downloadFileByAccessKey(String projectId, String fileAccessKey, String knowledgeBaseId,
        DownloadFileByAccessKeyQo downloadFileByAccessKeyQo) {
        String fileStr = redisClient.get(Constants.KNOWLEDGE_FILE_CACHE_PREFIX + fileAccessKey);
        if (StringUtils.isBlank(fileStr)) {
            log.error("file access key is invalid or expired, knowledgeBaseId: {}", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }
        String[] fileDetail = fileStr.split(",");
        String realKnowledgeBaseId = fileDetail[0];
        String fileId = fileDetail[2];
        if (!knowledgeBaseId.equals(realKnowledgeBaseId)) {
            log.error("file {} not exist in knowledgeBase {} ", fileAccessKey, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST);
        }
        return retrieveFileContent(projectId, fileId, knowledgeBaseId,
            new RetrieveFileContentQo().setWorkspaceId(downloadFileByAccessKeyQo.getWorkspaceId()));
    }

    @Override
    public Resource downloadKnowledgeImage(String projectId, String knowledgeBaseId, String imageId) {
        log.info("operation log projectId: {}, userId:{}, queryImage", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, knowledgeBaseEntity.getWorkspaceId(),
            knowledgeBaseEntity);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        return knowledgeRepoContext.getService(knowledgeRepoEntity.getSource()).queryImage(knowledgeRepo, imageId);
    }
    
    public Resource downloadFile(String projectId, String fileId, KnowledgeBaseEntity knowledgeBaseEntity) {
        // 校验文件是否在知识库下
        FileInfo fileInfo = retrieveFile(fileId, knowledgeBaseEntity);
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseEntity.getId());
        // 下载文件
        byte[] fileBytes = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .downloadFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), fileId)
            .getBody();
        if (fileBytes == null) {
            log.error("The file content is empty,file id = {},can not download", fileId);
            throw new AgentBaseException(ErrorCode.EMPTY_FILE_CONTENT, fileId);
        }

        // 处理响应
        ResponseModel.TransferResource resource = new ResponseModel.TransferResource(
            new ByteArrayInputStream(fileBytes));
        resource.setFilename(URLEncoder.encode(fileInfo.getFileName(), StandardCharsets.UTF_8));
        resource.setLength(fileInfo.getFileSize());
        return resource;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBaseFile",
        description = "修改知识库文件切片",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public UpdateFileChunkRsp updateFileChunk(String projectId, String knowledgeBaseId, String fileId, String chunkId,
        String workspaceId, FileChunkReq body) {
        log.info("operation log projectId: {}, userId:{}, updateFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 修改切片需校验知识文件权限
        checkFileChunkPrivilege(knowledgeBaseEntity, "update file chunk");

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] is not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        // 调用kooSearch接口新增切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .updateFileChunk(knowledgeRepo, fileId, chunkId, body);
        return new UpdateFileChunkRsp().setId(chunkId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "KnowledgeBaseFile",
        description = "修改知识库文件元信息",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public UpdateFileMetaInfoRsp updateFileMetaInfo(String projectId, String knowledgeBaseId, String fileId,
        String workspaceId, UpdateFileMetaInfoReq body) {
        log.info("operation log projectId: {}, userId:{}, updateFileMetaInfo", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.fileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] is not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.INVALID_PARAMETER);
        }
        // 调用接口修改元信息（标签）
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .updateFileMetaInfo(knowledgeRepo, fileId, body);
        return new UpdateFileMetaInfoRsp().setFileId(fileId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "KnowledgeBaseFile",
        description = "上传知识库文件",
        resourceId = "knowledgeBaseId",
        resourceName = ""
    )
    public UploadKnowledgeFileResponseBody uploadKnowledgeFile(String workspaceId, String projectId,
        String knowledgeBaseId, MultipartFile file, List<String> tags) {
        log.info("operation log projectId: {}, userId:{}, uploadFile", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        // 外部知识库不支持上传
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("Can not upload file to external knowledge repo: {}", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_TO_UPLOAD_FILE, knowledgeBaseId);
        }
        String domainId = RequestContextUtils.getRequestUserDomainId();
        // 文件校验
        validateImageFile(Objects.requireNonNull(file.getOriginalFilename()));
        resourceValidateService.validateUploadFile(knowledgeBaseId, knowledgeBaseEntity, file,
            knowledgeFileType.split(","));
        // 上传文件
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        String fileId = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .uploadFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), file, tags);
        log.info("Success to upload file: {} to knowledge repo: {} by user: {}", fileId, knowledgeBaseId, projectId);
        // 查询上传的文件信息
        final FileInfo fileInfo = retrieveFile(fileId, knowledgeBaseEntity);
        // 更新知识库size
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, fileInfo.getFileSize(), 1);
        return new UploadKnowledgeFileResponseBody().setFileId(fileId);
    }

    /**
     * 使用resource方式上传
     * 与 MultipartFile 的区别在于：未先校验文件真实大小（使用 UsFileUtil 检查流时，会直接消耗掉 Resource 中的流），导致后续无法再次读取文件内容。
     * 当前应用场景：从obs下载并上传到知识库，默认文件大小安全
     *
     * @param projectId
     * @param knowledgeBaseId
     * @param resource
     * @return
     */
    public UploadFilesResp uploadFileUsingResource(String projectId, String knowledgeBaseId, MultipartFile resource) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        // 外部知识库不支持上传
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("Can not upload file to external knowledge repo: {}", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_TO_UPLOAD_FILE, knowledgeBaseId);
        }
        String domainId = RequestContextUtils.getRequestUserDomainId();
        // 文件校验
        String fileName = resource.getOriginalFilename();
        validateImageFile(Objects.requireNonNull(fileName));
        // 文件校验
        // 上传文件
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(projectId, knowledgeBaseId);
        String fileId = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .uploadFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), resource, null);
        log.info("Success to upload file: {} to knowledge repo: {} by user: {}", fileId, knowledgeBaseId, projectId);
        // 查询上传的文件信息
        final FileInfo fileInfo = retrieveFile(fileId, knowledgeBaseEntity);
        // 更新知识库size
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, fileInfo.getFileSize(), 1);
        return UploadFilesResp.builder().fileId(fileId).build();
    }

    public KnowledgeRepoEntity getKnowledgeRepo(String projectId, String knowledgeRepoId) {
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeRepoId,
            projectId);
        if (Objects.isNull(knowledgeRepoEntity)) {
            log.error("The knowledgeRepo {} not exist.", knowledgeRepoId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, knowledgeRepoId);
        }
        return knowledgeRepoEntity;
    }

    private KnowledgeBaseEntity getKnowledgeBase(String projectId, String knowledgeBaseId) {
        final KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (Objects.isNull(knowledgeBaseEntity)) {
            log.error("The knowledgeBase {} not exist.", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST, knowledgeBaseId);
        }
        return knowledgeBaseEntity;
    }

    public FileInfo retrieveFile(String fileId, KnowledgeBaseEntity knowledgeRepoEntity) {
        // 调用KooSearch接口查询全量文件，再根据fileId过滤（KooSearch没有查询指定文件的接口）
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeRepoEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()));
        List<FileInfo> fileInfos = getAllFiles(knowledgeRepo);
        final List<FileInfo> fileInfoList = fileInfos.stream().filter(file -> fileId.equals(file.getFileId())).toList();
        if (CollectionUtils.isEmpty(fileInfoList)) {
            log.error("The file {} not exist in knowledgeBase {}.", fileId, knowledgeRepo.getKnowledgeRepoId());
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        return fileInfoList.get(0);
    }

    private void validateImageFile(String fileName) {
        String fileType = fileName.substring(fileName.lastIndexOf('.') + 1);
        List<String> imageTypeList = Arrays.asList(imageTypes.split(","));
        // 校验OCR是否开启，未开启则禁止上传图片类型
        if (!ocrEnabled && imageTypeList.contains(fileType)) {
            log.error("The file type {} is not supported, OCR is not enabled.", fileType);
            throw new AgentBaseException(ErrorCode.ILLEGAL_FILE_TYPE, imageTypes);
        }
    }

    private List<FileInfo> getAllFiles(KnowledgeRepo knowledgeRepo) {
        int pageNum = 1;
        ListKnowledgeFilesResponseBody fileInfoListRsp = knowledgeRepoContext.getService(knowledgeRepo.getSource())
            .listFiles(knowledgeRepo,
                new ListFileReq().setFileName(null).setPageNum(pageNum).setPageSize(CommonConstant.MAX_PAGE_SIZE));
        int total = fileInfoListRsp.getCount();
        if (total == 0) {
            return new ArrayList<>();
        }
        List<FileInfo> allFiles = new ArrayList<>(fileInfoListRsp.getFileInfoList());

        // 知识库文件总数量大于单次查询的上限，分多次循环查询
        if (total > CommonConstant.MAX_PAGE_SIZE) {
            for (int i = 0; i < total / CommonConstant.MAX_PAGE_SIZE; i++) {
                pageNum++;
                List<FileInfo> tempFileInfos = knowledgeRepoContext.getService(knowledgeRepo.getSource())
                    .listFiles(knowledgeRepo, new ListFileReq().setFileName(null)
                        .setPageNum(pageNum)
                        .setPageSize(CommonConstant.MAX_PAGE_SIZE))
                    .getFileInfoList();
                if (CollectionUtils.isEmpty(tempFileInfos)) {
                    break;
                }
                allFiles.addAll(tempFileInfos);
            }
        }
        // 根据文件id进行去重
        return allFiles.stream()
            .collect(
                collectingAndThen(toCollection(() -> new TreeSet<>(comparing(FileInfo::getFileId))), ArrayList::new));
    }

    private void checkFileChunkPrivilege(KnowledgeBaseEntity knowledgeRepoEntity, String operation) {
        // 不支持删除引用知识库的文件
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeRepoEntity.getType())) {
            log.error("The external knowledgeBase {} not support this {}.", knowledgeRepoEntity.getId(), operation);
            throw new AgentBaseException(ErrorCode.UNSUPPORTED_OPERATION, knowledgeRepoEntity.getId(), operation);
        }
    }

    private List<FileInfo> retrieveDeletedFile(BatchDeleteKnowledgeFilesRequestBody deleteFileReq,
        KnowledgeBaseEntity knowledgeBaseEntity) {
        // 调用KooSearch接口查询全量文件，再根据fileId过滤（KooSearch没有查询指定文件的接口）
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeBaseEntity.getType()));
        List<FileInfo> fileInfos = getAllFiles(knowledgeRepo);
        final List<FileInfo> fileInfoList = fileInfos.stream()
            .filter(file -> deleteFileReq.getFileIds().contains(file.getFileId()))
            .toList();

        // 批量删除查到的文件数需与数据库中搜到的相等
        if (CollectionUtils.isEmpty(fileInfoList) || deleteFileReq.getFileIds().size() != fileInfoList.size()) {
            log.error("The file {} not exist in knowledgeBase {}.", deleteFileReq.getFileIds().toString(),
                knowledgeRepo.getKnowledgeRepoId());
            throw new AgentBaseException(ErrorCode.THE_FILE_NOT_BELONG_KNOWLEDGE_BASE);
        }
        return fileInfoList;
    }
}
