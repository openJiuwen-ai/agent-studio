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
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.KnowledgeRepoContext;
import com.openjiuwen.studio.agent.agentbase.service.validate.KnowledgeDatasetValidateService;
import com.openjiuwen.studio.agent.agentbase.service.validate.ResourceValidateService;
import com.openjiuwen.studio.agent.common.dto.knowledge.ChunkUtils;
import com.openjiuwen.studio.agent.agentbase.utils.ShareScopeValidUtil;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.DownloadFaqFileByAccessKeyQo;
import com.openjiuwen.studio.agent.manager.dto.DownloadFaqFileQo;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FaqFileInfoListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileInfo;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileChunksQo;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileChunksReq;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFilesQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.UploadFaqFileRsp;
import com.openjiuwen.studio.agent.manager.service.IKnowledgeFaqFileManagementService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeSet;

@Slf4j
@Service
public class KnowledgeBaseFaqFileServiceImpl implements IKnowledgeFaqFileManagementService {

    private final KnowledgeBaseMapper knowledgeBaseMapper;

    @Value("${knowledge.faq-file-type}")
    private String knowledgeFaqFileType;

    public static final long MB = 1024 * 1024L;

    private final KnowledgeRepoMapper knowledgeRepoMapper;

    private final KnowledgeRepoContext knowledgeRepoContext;

    private final ResourceValidateService resourceValidateService;

    private final KnowledgeDatasetValidateService knowledgeDatasetValidateService;

    private final RedisClient redisClient;

    public KnowledgeBaseFaqFileServiceImpl(KnowledgeRepoMapper knowledgeRepoMapper,
        KnowledgeRepoContext knowledgeRepoContext, KnowledgeBaseMapper knowledgeBaseMapper,
        ResourceValidateService resourceValidateService,
        KnowledgeDatasetValidateService knowledgeDatasetValidateService, RedisClient redisClient) {
        this.knowledgeRepoMapper = knowledgeRepoMapper;
        this.knowledgeRepoContext = knowledgeRepoContext;
        this.resourceValidateService = resourceValidateService;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
        this.knowledgeDatasetValidateService = knowledgeDatasetValidateService;
        this.redisClient = redisClient;
    }

    @Override
    public CreateFileChunkRsp createFaqFileChunk(String projectId, String knowledgeBaseId, String fileId,
        String workspaceId, FaqFileChunkReq body) {
        log.info("operation log projectId: {}, userId:{}, createFaqFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 新增FAQ切片需校验知识文件权限
        checkFaqFileChunkPrivilege(knowledgeBaseEntity);

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.faqFileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] are not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.CREATE_FAQ_FILE_CHUNK_ERROR);
        }
        // 调用kooSearch接口新增FAQ切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .createFaqFileChunk(knowledgeRepo, fileId, body);
        return new CreateFileChunkRsp().setTitle(body.getTitle());
    }

    @Override
    public CommonDeleteRsp deleteFaqFile(String projectId, String knowledgeBaseId, String fileId, String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteFaqFile", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 输出需校验知识FAQ文件权限
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("External knowledge base can not delete faq file", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_DELETE_KNOWLEDGE_REPO_FILE);
        }

        // 查询知识库FAQ文件
        FileInfo fileInfo = retrieveFaqFile(fileId, knowledgeBaseEntity);

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        // 删除知识库FAQ文件
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .deleteFaqFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), fileId);
        String domainId = RequestContextUtils.getRequestUserDomainId();
        // 更新数据库中知识库大小
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, -fileInfo.getFileSize(), -1);
        return new CommonDeleteRsp().setId(fileId);
    }

    @Override
    public CommonDeleteRsp deleteFaqFileChunk(String projectId, String knowledgeBaseId, String fileId, String chunkId,
        String workspaceId) {
        log.info("operation log projectId: {}, userId:{}, deleteFaqFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 删除FAQ切片需校验知识文件权限
        checkFaqFileChunkPrivilege(knowledgeBaseEntity);

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.faqFileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] are not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.DELETE_FAQ_FILE_CHUNK_ERROR);
        }
        // 调用kooSearch接口新增FAQ切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .deleteFaqFileChunk(knowledgeRepo, fileId, chunkId);
        return new CommonDeleteRsp().setId(chunkId);
    }

    @Override
    public Resource downloadFaqFile(String projectId, String knowledgeBaseId, String fileId,
        DownloadFaqFileQo downloadFaqFileQo) {
        log.info("operation log projectId: {}, userId:{}, downloadFaqFile", projectId,
            RequestContextUtils.getRequestUserId());
        // 校验知识库是否属于用户
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, knowledgeBaseEntity.getWorkspaceId(),
            knowledgeBaseEntity);
        return download(projectId, fileId, knowledgeBaseEntity);
    }

    @Override
    public Resource downloadFaqFileByAccessKey(String projectId, String fileAccessKey, String knowledgeBaseId,
        DownloadFaqFileByAccessKeyQo downloadFaqFileByAccessKeyQo) {
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
        return downloadFaqFile(projectId, knowledgeBaseId, fileId,
            new DownloadFaqFileQo().setWorkspaceId(downloadFaqFileByAccessKeyQo.getWorkspaceId()));
    }

    public Resource download(String projectId, String fileId, KnowledgeBaseEntity knowledgeBaseEntity) {
        // 校验文件是否在知识库下
        FileInfo fileInfo = retrieveFaqFile(fileId, knowledgeBaseEntity);
        // 下载文件
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseEntity.getId(), projectId);
        byte[] fileBytes = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .downloadFaqFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), fileId)
            .getBody();
        if (fileBytes == null) {
            log.error("File [{}] content is empty,can not download", fileId);
            throw new AgentBaseException(ErrorCode.FAQ_FILE_IS_EMPTY);
        }
        // 处理响应
        ResponseModel.TransferResource resource = new ResponseModel.TransferResource(
            new ByteArrayInputStream(fileBytes));
        resource.setFilename(URLEncoder.encode(fileInfo.getFileName(), StandardCharsets.UTF_8));
        resource.setLength(fileInfo.getFileSize());
        return resource;
    }

    @Override
    public FaqFileChunkListRsp listFaqFileChunks(String projectId, String knowledgeBaseId, String fileId,
        ListFaqFileChunksQo listFaqFileChunksQo) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        int pageNum = listFaqFileChunksQo.getOffset() / listFaqFileChunksQo.getLimit() + 1;

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        ListFaqFileChunksReq listFaqFileChunksReq = new ListFaqFileChunksReq().setFileId(fileId)
            .setPageNum(pageNum)
            .setPageSize(listFaqFileChunksQo.getLimit());
        FaqFileChunkListRsp faqFileChunkListRsp = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .listFaqFileChunks(knowledgeRepo, listFaqFileChunksReq);
        // 处理切片中的图片信息
        faqFileChunkListRsp.getFileChunkList().forEach(item -> {
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
        return faqFileChunkListRsp;
    }

    @Override
    public FaqFileInfoListRsp listFaqFiles(String projectId, String knowledgeBaseId, ListFaqFilesQo body) {
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);
        ShareScopeValidUtil.checkKnowledgeScope(knowledgeBaseId, knowledgeBaseEntity.getWorkspaceId(),
            knowledgeBaseEntity);
        // 转换搜索数目
        int pageNum = body.getOffset() / body.getLimit() + 1;
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());

        // 构造搜索请求
        ListFaqFileReq listFaqFileReq = new ListFaqFileReq().setFileName(
                Optional.of(body).map(ListFaqFilesQo::getName).orElse(null))
            .setFileStatus(Optional.of(body).map(ListFaqFilesQo::getStatus).orElse(null))
            .setIds(Optional.of(body).map(ListFaqFilesQo::getIds).orElse(null))
            .setPageNum(pageNum)
            .setPageSize(body.getLimit());
        return knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .listFaqFiles(knowledgeRepo, listFaqFileReq);
    }

    @Override
    public UpdateFileChunkRsp updateFaqFileChunk(String projectId, String knowledgeBaseId, String fileId,
        String chunkId, String workspaceId, FaqFileChunkReq body) {
        log.info("operation log projectId: {}, userId:{}, updateFaqFileChunk", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 修改FAQ切片需校验知识文件权限
        checkFaqFileChunkPrivilege(knowledgeBaseEntity);

        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
            .setMetadata(knowledgeRepoEntity.getMetadata());
        if (!knowledgeDatasetValidateService.faqFileBelongToKnowledgeRepo(List.of(fileId), knowledgeBaseEntity,
            knowledgeRepoEntity, knowledgeRepoContext)) {
            log.error("The file [{}] are not belong current knowledge base [{}]", fileId, knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.UPDATE_FAQ_FILE_CHUNK_ERROR);
        }
        // 调用kooSearch接口新增FAQ切片
        knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .updateFaqFileChunk(knowledgeRepo, fileId, chunkId, body);
        return new UpdateFileChunkRsp().setId(chunkId);
    }

    @Override
    public UploadFaqFileRsp uploadFaqFile(String workspaceId, String projectId, String knowledgeBaseId,
        MultipartFile file) {
        log.info("operation log projectId: {}, userId:{}, uploadFaqFile", projectId,
            RequestContextUtils.getRequestUserId());
        final KnowledgeBaseEntity knowledgeBaseEntity = getKnowledgeBase(projectId, knowledgeBaseId);

        // 不支持上传FAQ文件到用户账号下的知识库
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeBaseEntity.getType())) {
            log.error("External knowledge base can not upload faq file", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_UPLOAD_KNOWLEDGE_REPO_FILE);
        }
        String domainId = RequestContextUtils.getRequestUserDomainId();
        // 文件校验
        resourceValidateService.validateUploadFile(knowledgeBaseId, knowledgeBaseEntity, file,
            knowledgeFaqFileType.split(","));
        // 上传文件
        final KnowledgeRepoEntity knowledgeRepoEntity = getKnowledgeRepo(knowledgeBaseId,
            RequestContextUtils.getRequestProjectId());
        String fileId = knowledgeRepoContext.getService(knowledgeRepoEntity.getSource())
            .uploadFaqFile(new KnowledgeRepo().setKnowledgeRepoId(knowledgeBaseEntity.getExternalId())
                .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()))
                .setMetadata(knowledgeRepoEntity.getMetadata()), file);
        log.info("Success to upload FAQ file: {} to knowledge repo: {} by user: {}", fileId, knowledgeBaseId,
            projectId);
        // 查询上传的文件信息
        final FileInfo fileInfo = retrieveFaqFile(fileId, knowledgeBaseEntity);
        // 更新知识库size
        knowledgeRepoMapper.atomicUpdateRepoSize(knowledgeBaseId, projectId, fileInfo.getFileSize(), 1);
        return new UploadFaqFileRsp().setFileId(fileId);
    }

    private FileInfo retrieveFaqFile(String fileId, KnowledgeBaseEntity knowledgeRepoEntity) {
        // 调用KooSearch接口查询全量文件，再根据fileId过滤（KooSearch没有查询指定文件的接口）
        KnowledgeRepo knowledgeRepo = new KnowledgeRepo().setKnowledgeRepoId(knowledgeRepoEntity.getExternalId())
            .setType(KnowledgeBaseType.fromValue(knowledgeRepoEntity.getType()));
        List<FileInfo> allFileInfos = getAllFaqFiles(knowledgeRepo);
        final List<FileInfo> fileInfos = allFileInfos.stream().filter(file -> fileId.equals(file.getFileId())).toList();
        if (CollectionUtils.isEmpty(fileInfos)) {
            log.error("File [{}] is not exist", fileId);
            throw new AgentBaseException(ErrorCode.FILE_NOT_FOUND, fileId);
        }
        return fileInfos.get(0);
    }

    private List<FileInfo> getAllFaqFiles(KnowledgeRepo knowledgeRepo) {
        int pageNum = 1;
        FaqFileInfoListRsp fileInfoListRsp = knowledgeRepoContext.getService(knowledgeRepo.getSource())
            .listFaqFiles(knowledgeRepo,
                new ListFaqFileReq().setFileName(null).setPageNum(pageNum).setPageSize(CommonConstant.MAX_PAGE_SIZE));
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
                    .listFaqFiles(knowledgeRepo, new ListFaqFileReq().setFileName(null)
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

    private KnowledgeRepoEntity getKnowledgeRepo(String knowledgeBaseId, String projectId) {
        final KnowledgeRepoEntity knowledgeRepoEntity = knowledgeRepoMapper.selectByPrimaryKey(knowledgeBaseId,
            projectId);
        if (Objects.isNull(knowledgeRepoEntity)) {
            log.error("knowledge base [{}] is not exist", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST);
        }
        return knowledgeRepoEntity;
    }

    private KnowledgeBaseEntity getKnowledgeBase(String projectId, String knowledgeBaseId) {
        final KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseMapper.selectById(projectId, knowledgeBaseId);
        if (Objects.isNull(knowledgeBaseEntity)) {
            log.error("knowledge base [{}] is not exist", knowledgeBaseId);
            throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_EXIST);
        }
        return knowledgeBaseEntity;
    }

    private void checkFaqFileChunkPrivilege(KnowledgeBaseEntity knowledgeRepoEntity) {
        // 不支持删除引用知识库的文件
        if (KnowledgeBaseType.EXTERNAL.toString().equals(knowledgeRepoEntity.getType())) {
            log.error("Can not operate external knowledge base [{}]", knowledgeRepoEntity.getExternalId());
            throw new AgentBaseException(ErrorCode.NO_PERMISSION_DELETE_KNOWLEDGE_REPO_FILE);
        }
    }
}

