/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service.knowledgerepo;

import com.openjiuwen.studio.agent.agentbase.client.CssUniSearchClient;
import com.openjiuwen.studio.agent.agentbase.common.constant.CommonConstant;
import com.openjiuwen.studio.agent.agentbase.model.BatchCreateResponse;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeLabelsRsp;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeRepoInfo;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeRepoResp;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeTaskRequestBody;
import com.openjiuwen.studio.agent.agentbase.model.CssFileInfo;
import com.openjiuwen.studio.agent.agentbase.model.DeleteKnowledgeLabelsReq;
import com.openjiuwen.studio.agent.agentbase.model.DeleteKnowledgeLabelsRsp;
import com.openjiuwen.studio.agent.agentbase.model.DeleteKnowledgeRepoReq;
import com.openjiuwen.studio.agent.agentbase.model.DeleteKnowledgeResp;
import com.openjiuwen.studio.agent.agentbase.model.FaqListReq;
import com.openjiuwen.studio.agent.agentbase.model.FaqResp;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeRepo;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeSegRuleInfo;
import com.openjiuwen.studio.agent.agentbase.model.ListFaqResponse;
import com.openjiuwen.studio.agent.agentbase.model.ListFileDocsRsp;
import com.openjiuwen.studio.agent.agentbase.model.ListFilesRsp;
import com.openjiuwen.studio.agent.agentbase.model.ListKnowledgeLabelsResp;
import com.openjiuwen.studio.agent.agentbase.model.ListKnowledgeRepoResp;
import com.openjiuwen.studio.agent.agentbase.model.ListTaskCriteria;
import com.openjiuwen.studio.agent.agentbase.model.ModelSearchCriteria;
import com.openjiuwen.studio.agent.agentbase.model.ModifyKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.agentbase.model.SearchTextResp;
import com.openjiuwen.studio.agent.agentbase.model.SegmentRule;
import com.openjiuwen.studio.agent.agentbase.model.UploadFilesResp;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.connection.LakeSearchConnection;
import com.openjiuwen.studio.agent.agentbase.service.knowledgerepo.knowledgesourceprovider.LakeSearchConnectionProvider;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.HeaderRename;
import com.openjiuwen.studio.agent.common.dto.knowledge.CreateKnowledgeRepoReq;
import com.openjiuwen.studio.agent.common.dto.knowledge.FaqDeleteBatchResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FaqInfo;
import com.openjiuwen.studio.agent.common.dto.knowledge.FaqReq;
import com.openjiuwen.studio.agent.common.dto.knowledge.FaqSearchCriteria;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileDocInfo;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileExtract;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeFaq;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeRepoInfo;
import com.openjiuwen.studio.agent.common.dto.knowledge.ListModelResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.ParseConf;
import com.openjiuwen.studio.agent.common.dto.knowledge.SearchTextReq;
import com.openjiuwen.studio.agent.common.dto.knowledge.SplitConf;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.RagAuthMode;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.foundation.base.utils.JacksonUtils;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteFaqResp;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesRequestBody;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CommonBatchDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeTaskResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeTaskReq;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FaqFileInfoListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkInfo;
import com.openjiuwen.studio.agent.manager.dto.FileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FileInfo;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRepoMetadata;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSegmentRule;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeTagInfo;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileChunksReq;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListFaqResp;
import com.openjiuwen.studio.agent.manager.dto.ListFileChunksReq;
import com.openjiuwen.studio.agent.manager.dto.ListFileReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeRepoReq;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTagsResp;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTasksResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModelInfo;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoReq;
import com.openjiuwen.studio.agent.manager.dto.UploadFaqFileRsp;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;

import java.net.URI;
import java.util.*;
import java.util.stream.Collectors;

/**
 * LakeSearch知识库Service
 *
 * @since 2025-01-02
 */
@Slf4j
@Service("MgLakeSearch")
public class LakeSearchService implements KnowledgeRepoService {

    private final CssUniSearchClient cssUniSearchClient;

    private final LakeSearchConnectionProvider lakeSearchConnectionProvider;

    private final KnowledgeConnectionRouterService knowledgeConnectionRouterService;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${knowledge.lakeSearch.auth-mode}")
    private String authMode;

    @Value("${knowledge.lakeSearch.endpoint}")
    private String lakeSearchEndpoint;

    @Value("${knowledge.lakeSearch.project-id}")
    private String lakeSearchProjectId;

    @Value("${knowledge.lakeSearch.application-id}")
    private String lakeSearchApplicationId;

    public LakeSearchService(CssUniSearchClient cssUniSearchClient,
        LakeSearchConnectionProvider lakeSearchConnectionProvider,
        KnowledgeConnectionRouterService knowledgeConnectionRouterService) {
        this.cssUniSearchClient = cssUniSearchClient;
        this.lakeSearchConnectionProvider = lakeSearchConnectionProvider;
        this.knowledgeConnectionRouterService = knowledgeConnectionRouterService;
    }

    @Override
    public CreateKnowledgeRepoInfo createKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        CreateKnowledgeRepoReq createKnowledgeRepoReq = CreateKnowledgeRepoReq.builder()
            .name(knowledgeRepo.getDisplayName())
            .detail(knowledgeRepo.getDescription())
            .embeddingModel(knowledgeRepo.getEmbeddingModel())
            .reRankModel(knowledgeRepo.getRerankModel())
            .repoType(knowledgeRepo.getRepoType().getValue())
            .fileExtract(FileExtract.builder()
                .parseConf(knowledgeRepo.getParseConf())
                .splitConf(knowledgeRepo.getSplitConf())
                .build())
            .languageId("zh")
            .build();
        CreateKnowledgeRepoResp createKnowledgeRepoResp;
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
        try {
            // 调用LakeSearch接口创建知识库
            createKnowledgeRepoResp = cssUniSearchClient.createKnowledgeRepo(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                createKnowledgeRepoReq);
            log.info("Success to create KnowledgeRepo: {}", createKnowledgeRepoResp);
        } catch (Exception exception) {
            log.error("Fail to create LakeSearch knowledge repo, projectId: {}, repoName: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getDisplayName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        CreateKnowledgeRepoInfo createKnowledgeRepoInfo = new CreateKnowledgeRepoInfo();
        createKnowledgeRepoInfo.setKnowledgeBaseId(createKnowledgeRepoResp.getRepoId());
        createKnowledgeRepoInfo.setKnowledgeBaseConnectionId(connectionId);
        return createKnowledgeRepoInfo;
    }

    @Override
    public String modifyKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        ModifyKnowledgeRepoRequestBody modifyKnowledgeRepoRequestBody = ModifyKnowledgeRepoRequestBody.builder()
            .name(knowledgeRepo.getDisplayName())
            .build();
        Optional.ofNullable(knowledgeRepo.getRerankModel()).ifPresent(modifyKnowledgeRepoRequestBody::setRerankModel);
        if (!Objects.isNull(knowledgeRepo.getSplitConf()) || !Objects.isNull(knowledgeRepo.getParseConf())) {
            FileExtract fileExtract = new FileExtract();
            Optional.ofNullable(knowledgeRepo.getSplitConf()).ifPresent(fileExtract::setSplitConf);
            Optional.ofNullable(knowledgeRepo.getParseConf()).ifPresent(fileExtract::setParseConf);
            modifyKnowledgeRepoRequestBody.setFileExtract(fileExtract);
        }
        try {
            // 调用LakeSearch接口修改知识库配置
            ModifyKnowledgeRepoResponseBody modifyKnowledgeRepoRsp = cssUniSearchClient.modifyKnowledgeRepo(
                getUri(knowledgeRepo.getMetadata()), getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId,
                lakeSearchApplicationId, knowledgeRepo.getKnowledgeRepoId(), modifyKnowledgeRepoRequestBody);
            return modifyKnowledgeRepoRsp.getKnowledgeRepoId();
        } catch (Exception exception) {
            log.error("Fail to modify knowledge repo, projectId: {}, repoName: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getDisplayName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void deleteKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        DeleteKnowledgeRepoReq deleteKnowledgeRepoReq = DeleteKnowledgeRepoReq.builder()
            .repoIds(Collections.singletonList(knowledgeRepo.getKnowledgeRepoId()))
            .build();
        try {
            // 调用LakeSearch接口，删除知识库
            DeleteKnowledgeResp deleteKnowledgeResp = cssUniSearchClient.deleteKnowledgeRepo(
                getUri(knowledgeRepo.getMetadata()), getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId,
                lakeSearchApplicationId, deleteKnowledgeRepoReq);
            log.info("Success to delete KnowledgeRepo: {}", deleteKnowledgeResp);
        } catch (Exception exception) {
            log.error("Fail to delete knowledge repo, projectId: {}, knowledgeRepoId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getKnowledgeRepoId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public KnowledgeRepo retrieveKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        KnowledgeRepoInfo knowledgeRepoInfo;
        try {
            knowledgeRepoInfo = cssUniSearchClient.showKnowledgeRepo(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId);
            log.info("Success to retrieve KnowledgeRepo: {}",
                Optional.ofNullable(knowledgeRepoInfo).map(KnowledgeRepoInfo::getName).orElse(knowledgeRepoId));
        } catch (Exception exception) {
            log.error("Fail to retrieve knowledge repo, projectId: {}, knowledgeRepoId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        if (Objects.isNull(knowledgeRepoInfo)) {
            log.error("Knowledge repo is not exist in LakeSearch: {}", knowledgeRepoId);
            throw new AgentBaseException(ErrorCode.RESOURCE_NOT_EXIST, knowledgeRepoId);

        }
        KnowledgeRepo realKnowledgeRepo = new KnowledgeRepo();
        realKnowledgeRepo.setDisplayName(knowledgeRepoInfo.getName());
        realKnowledgeRepo.setKnowledgeRepoId(knowledgeRepoInfo.getId());
        realKnowledgeRepo.setStatus(knowledgeRepoInfo.getStatus());
        realKnowledgeRepo.setEmbeddingModel(knowledgeRepoInfo.getEmbeddingModel());
        realKnowledgeRepo.setRerankModel(knowledgeRepoInfo.getRerankModel());
        realKnowledgeRepo.setParseConf(Optional.ofNullable(knowledgeRepoInfo.getFileExtract())
            .map(FileExtract::getParseConf)
            .orElse(new ParseConf()));
        realKnowledgeRepo.setSplitConf(Optional.ofNullable(knowledgeRepoInfo.getFileExtract())
            .map(FileExtract::getSplitConf)
            .orElse(new SplitConf()));
        return realKnowledgeRepo;
    }

    @Override
    public ListKnowledgeRepoResp listKnowledgeRepos(ListKnowledgeRepoReq req) {
        return listKnowledgeRepos(req, null);
    }

    /**
     * 查询知识库列表
     *
     * @param req ListKnowledgeRepoReq
     * @param metadata 知识库调用信息
     * @return ListKnowledgeRepoResp
     */
    public ListKnowledgeRepoResp listKnowledgeRepos(ListKnowledgeRepoReq req, String metadata) {
        ListKnowledgeRepoResp knowledgeRepoInfos;
        try {
            knowledgeRepoInfos = cssUniSearchClient.listKnowledgeRepos(getUri(metadata), getHeaders(metadata),
                lakeSearchProjectId, lakeSearchApplicationId, req.getPageNum(), req.getPageSize(), req.getName(),
                req.getKnowledgeBaseType(), null, null, null, null);
            log.info("Success to list KnowledgeRepos: {}", knowledgeRepoInfos.getTotal());
            return knowledgeRepoInfos;
        } catch (Exception exception) {
            log.error("Fail to list knowledge repos, projectId: {}, knowledgeRepoName: {}.",
                RequestContextUtils.getRequestProjectId(), req.getName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public String uploadFile(KnowledgeRepo knowledgeRepo, MultipartFile file, List<String> tags) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        UploadFilesResp uploadFilesResp;
        try {
            // 调用LakeSearch接口上传文档
            uploadFilesResp = cssUniSearchClient.uploadFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId,
                file, tags);
            log.info("Success to uploadFile: {}", uploadFilesResp);
        } catch (Exception exception) {
            log.error("Fail to upload file to knowledge repo, projectId: {}, knowledgeRepoId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, exception);

            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        return uploadFilesResp.getFileId();
    }

    @Override
    public void deleteFile(KnowledgeRepo knowledgeRepo, String fileId) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口删除文档，只支持删除自建知识库下的文档
            cssUniSearchClient.deleteFiles(getUri(knowledgeRepo.getMetadata()), getHeaders(knowledgeRepo.getMetadata()),
                lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId, fileId);
        } catch (Exception exception) {
            log.error("Fail to delete file from knowledge repo, projectId: {}, knowledgeRepoId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public ListKnowledgeFilesResponseBody listFiles(KnowledgeRepo knowledgeRepo, ListFileReq listFileReq) {
        ListFilesRsp listFilesRsp;
        try {
            // 调用LakeSearch接口查询知识库文档列表
            listFilesRsp = cssUniSearchClient.searchFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), listFileReq.getPageNum(), listFileReq.getPageSize(),
                listFileReq.getFileName(), listFileReq.getFileType(), listFileReq.getFileStatus());
            log.info("Success to list Files: {}", listFilesRsp.getTotal());
        } catch (Exception exception) {
            log.error("Fail to list file from knowledge repo, projectId: {}, knowledgeRepoId: {}, fileName: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getKnowledgeRepoId(),
                listFileReq.getFileName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        List<FileInfo> fileInfos = new ArrayList<>();
        for (CssFileInfo cssFileInfo : listFilesRsp.getFiles()) {
            fileInfos.add(getFileInfoFromCssFileInfo(cssFileInfo));
        }
        return new ListKnowledgeFilesResponseBody().setFileInfoList(fileInfos).setCount(listFilesRsp.getTotal());
    }

    @Override
    public ResponseEntity<byte[]> downloadFile(KnowledgeRepo knowledgeRepo, String fileId) {
        ResponseEntity<byte[]> responseEntity;
        try {
            // 调用LakeSearch接口下载知识库文档
            responseEntity = cssUniSearchClient.downloadFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId);
            log.info("Success to download file: {}", fileId);
        } catch (Exception exception) {
            log.error("Fail to download file from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        return responseEntity;
    }

    @Override
    public void createFileChunk(KnowledgeRepo knowledgeRepo, String fileId, FileChunkReq fileChunkReq) {
        try {
            cssUniSearchClient.createFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, fileChunkReq);
        } catch (Exception exception) {
            log.error("Fail to create file chunk from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void updateFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId, FileChunkReq fileChunkReq) {
        try {
            cssUniSearchClient.updateFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, chunkId, fileChunkReq);
        } catch (Exception exception) {
            log.error("Fail to update file chunk from knowledge repo, projectId: {}, fileId: {}, chunkId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, chunkId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void updateFileMetaInfo(KnowledgeRepo knowledgeRepo, String fileId,
        UpdateFileMetaInfoReq updateFileMetaInfoReq) {
        try {
            cssUniSearchClient.updateFileInfo(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, updateFileMetaInfoReq.getTags());
        } catch (Exception exception) {
            log.error("Fail to update file info from knowledge repo, projectId: {}, fileId: {}, error: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, exception.getMessage(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void deleteFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId) {
        try {
            cssUniSearchClient.batchDeleteFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, Collections.singletonList(chunkId));
        } catch (Exception exception) {
            log.error("Fail to delete file chunk from knowledge repo, projectId: {}, fileId: {}, chunkId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, chunkId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public FileChunkListRsp listFileChunks(KnowledgeRepo knowledgeRepo, ListFileChunksReq listFileChunksReq) {
        ListFileDocsRsp listFileDocsRsp;
        try {
            listFileDocsRsp = cssUniSearchClient.listFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), listFileChunksReq.getFileId(), listFileChunksReq.getPageNum(),
                listFileChunksReq.getPageSize());
        } catch (Exception exception) {
            log.error("Fail to list file chunks from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), listFileChunksReq.getFileId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        FileChunkListRsp fileChunkListRsp = new FileChunkListRsp();
        fileChunkListRsp.setCount(listFileDocsRsp.getTotal());
        fileChunkListRsp.setFileChunkList(getFileChunkInfoFromFileDocInfo(listFileDocsRsp.getDocs()));
        return fileChunkListRsp;
    }

    @Override
    public SearchTextResp searchText(List<KnowledgeRepo> knowledgeRepos, String query, String searchMode,
        List<String> tags, int pageNum, int pageSize) {
        String knowledgeRepoId = knowledgeRepos.get(0).getKnowledgeRepoId();
        SearchTextResp searchTextResp;
        try {
            // 调用LakeSearch接口检索知识库文档
            searchTextResp = cssUniSearchClient.searchText(getUri(knowledgeRepos.get(0).getMetadata()),
                getHeaders(knowledgeRepos.get(0).getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                SearchTextReq.builder()
                    .repoId(knowledgeRepoId)
                    .content(query)
                    .scope(searchMode)
                    .pageNum(pageNum)
                    .pageSize(pageSize)
                    .filterString(buildFilterStrForTags(tags))
                    .extraRepoIds(knowledgeRepos.stream()
                        .map(KnowledgeRepo::getKnowledgeRepoId)
                        .filter(item -> !item.equals(knowledgeRepoId))
                        .toList())
                    .build());
            log.info("Success to search knowledge repo: {}", knowledgeRepoId);
        } catch (Exception exception) {
            log.error("Fail to search text from knowledge repo, knowledgeRepoId: {}.", knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        return searchTextResp;
    }

    /**
     * 根据标签列表生成过滤条件
     *
     * @param tags
     * @return
     */
    private String buildFilterStrForTags(List<String> tags) {
        if (CollectionUtils.isEmpty(tags)) {
            return null;
        }
        String tagStr = String.join(" OR ", tags);
        return "tags:(" + tagStr + ")";
    }

    @Override
    public String createFaq(KnowledgeFaq knowledgeFaq) {
        try {
            // 调用LakeSearch接口创建FAQ
            FaqResp faqResp = cssUniSearchClient.createFaq(getUri(null), getHeaders(null), lakeSearchProjectId,
                lakeSearchApplicationId, new FaqReq(knowledgeFaq));
            log.info("Success to create faq: {}", faqResp);
            return faqResp.getFaqId();
        } catch (Exception exception) {
            log.error("Fail to createFaq, repo: {}.", knowledgeFaq.getKnowledgeRepoId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void deleteFaq(String repoId, String faqId) {
        try {
            // 调用LakeSearch接口删除FAQ
            cssUniSearchClient.deleteFaq(getUri(null), getHeaders(null), lakeSearchProjectId, lakeSearchApplicationId,
                repoId, faqId);
            log.info("Success to delete faq: {}", faqId);
        } catch (Exception exception) {
            log.error("Fail to delete faq, repo: {}.", repoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public Integer deleteFaqBatch(String repoId, List<String> faqIds) {
        FaqListReq req = FaqListReq.builder().repoId(repoId).faqIds(faqIds).build();
        FaqDeleteBatchResp faqResp;
        try {
            // 调用LakeSearch接口批量删除FAQ
            faqResp = cssUniSearchClient.deleteFaqBatch(getUri(null), getHeaders(null), lakeSearchProjectId,
                lakeSearchApplicationId, req);
            log.info("Success to batch delete faq: {}", faqResp.getDeletedCount());
            return faqResp.getDeletedCount();
        } catch (Exception exception) {
            log.error("Fail to batch delete faq, repo: {}.", repoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public String modifyFaq(KnowledgeFaq knowledgeFaq) {
        try {
            // 调用LakeSearch接口修改FAQ
            cssUniSearchClient.updateFaq(getUri(null), getHeaders(null), lakeSearchProjectId,
                lakeSearchApplicationId, new FaqReq(knowledgeFaq));
            log.info("Success to update faq: {}", knowledgeFaq.getFaqId());
            return knowledgeFaq.getFaqId();
        } catch (Exception exception) {
            log.error("Fail to update faq: {}.", knowledgeFaq.getFaqId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public KnowledgeFaq retrieveFaq(String faqId, String repoId) {
        try {
            // 调用LakeSearch接口查询FAQ详情
            FaqInfo faqInfo = cssUniSearchClient.showFaq(getUri(null), getHeaders(null), lakeSearchProjectId,
                lakeSearchApplicationId, repoId, faqId);
            log.info("Success to retrieve faq: {}", faqId);
            return faqInfo.convertToDto();
        } catch (Exception exception) {
            log.error("Fail to retrieve faq: {}.", faqId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public ListFaqResp listFaq(FaqSearchCriteria faqSearchCriteria) {
        try {
            // 调用LakeSearch接口查询FAQ列表
            ListFaqResponse listFaqResponse = cssUniSearchClient.listFaq(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, faqSearchCriteria.getRepoId(),
                faqSearchCriteria.getPageNum(), faqSearchCriteria.getPageSize(), faqSearchCriteria.getQuestion());
            log.info("Success to list faq: {}", listFaqResponse.getTotal());
            List<KnowledgeFaq> knowledgeFaqs = Optional.ofNullable(listFaqResponse.getRecords())
                .map(faqInfos -> faqInfos.stream().map(FaqInfo::convertToDto).toList())
                .orElse(Collections.emptyList());
            return new ListFaqResp().setFaqList(knowledgeFaqs).setCount(listFaqResponse.getTotal());
        } catch (Exception exception) {
            log.error("Fail to list faq, repo: {}.", faqSearchCriteria.getRepoId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void startKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口启用知识库
            cssUniSearchClient.startKnowledgeRepo(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId);
            log.info("Success to start knowledge repo: {}", knowledgeRepoId);
        } catch (Exception exception) {
            log.error("Fail to start knowledge repo, knowledgeRepoId: {}.", knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void stopKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口停用知识库
            cssUniSearchClient.stopKnowledgeRepo(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId);
            log.info("Success to stop knowledge repo: {}", knowledgeRepoId);
        } catch (Exception exception) {
            log.error("Fail to stop knowledge repo, knowledgeRepoId: {}.", knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public KnowledgeSegRuleInfo createSegmentRule(KnowledgeSegmentRule segmentRule, String repoId) {
        SegmentRule rule = SegmentRule.builder().regexs(segmentRule.getRuleRegexs()).build();
        String connectionId = StringUtils.isBlank(repoId)
            ? knowledgeConnectionRouterService.findConnectionIdByContext()
            : lakeSearchConnectionProvider.getConnectionIdByRepoId(repoId);
        try {
            // 调用LakeSearch接口创建知识分层规则
            String ruleId = cssUniSearchClient.createSegmentRule(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, rule).getId();
            log.info("Success to create segment rule: {}", ruleId);
            KnowledgeSegRuleInfo knowledgeSegRuleInfo = new KnowledgeSegRuleInfo();
            knowledgeSegRuleInfo.setRuleId(ruleId);
            knowledgeSegRuleInfo.setKnowledgeBaseConnectionId(connectionId);
            return knowledgeSegRuleInfo;
        } catch (Exception exception) {
            log.error("Fail to create segment rule.", exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public String modifySegmentRule(KnowledgeSegmentRule segmentRule) {
        SegmentRule rule = SegmentRule.builder().regexs(segmentRule.getRuleRegexs()).build();
        try {
            // 调用LakeSearch接口修改知识分层规则
            String ruleId = cssUniSearchClient.modifySegmentRule(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, segmentRule.getId(), rule).getId();
            log.info("Success to modify segment rule: {}", ruleId);
            return ruleId;
        } catch (Exception exception) {
            log.error("Fail to modify segment rule: {}.", segmentRule.getId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void deleteSegmentRule(String ruleId) {
        try {
            // 调用LakeSearch接口删除知识分层规则
            cssUniSearchClient.deleteSegmentRule(getUri(null), getHeaders(null), lakeSearchProjectId,
                lakeSearchApplicationId, ruleId);
            log.info("Success to delete segment rule: {}", ruleId);
        } catch (Exception exception) {
            log.error("Fail to delete segment rule: {}.", ruleId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public List<ModelInfo> listModels(ModelSearchCriteria searchCriteria, String connectionId) {
        try {
            // 调用KooSearch接口查询模型列表
            ListModelResp listModelResp = cssUniSearchClient.listModels(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, searchCriteria.getModelName(),
                searchCriteria.getModelType(), searchCriteria.getModelStatus(), searchCriteria.getPageNum(),
                searchCriteria.getPageSize());
            log.info("Success to list models: {}", listModelResp.getTotal());
            List<ListModelResp.CssModelInfo> models = listModelResp.getModels();
            if (CollectionUtils.isEmpty(models)) {
                return Collections.emptyList();
            }
            return models.stream().map(model -> {
                return new ModelInfo().setName(model.getName()).setType(model.getType()).setStatus(model.getStatus());
            }).toList();
        } catch (AgentBaseException exception) {
            // 已带明确错误码。若为“知识库默认连接信息缺失”（即未配置知识库连接），
            // 重新映射为更面向用户的“知识库连接失败”码；其余 AgentBaseException 原样抛出，不丢失错误码。
            if (ErrorCode.FAILED_TO_FIND_DEFAULT_CONNECTION_INFO.equals(exception.getErrorCode())) {
                log.error("Fail to list models, knowledge base connection not configured.");
                throw new AgentBaseException(ErrorCode.KNOWLEDGE_BASE_NOT_CONFIGURED);
            }
            throw exception;
        } catch (Exception exception) {
            log.error("Fail to list models.", exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public CreateKnowledgeTaskResponseBody createTask(String repoId, String taskType, List<String> fileIds) {
        try {
            // 调用lakeSearch接口创建任务
            BatchCreateResponse task = cssUniSearchClient.createTask(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, repoId,
                CreateKnowledgeTaskRequestBody.builder().taskType(taskType).fileIds(fileIds).build());
            log.info("Success to create task, repo: {}", repoId);
            return new CreateKnowledgeTaskResponseBody().setCreatedCount(task.getCreatedCount())
                .setTotalCount(task.getTotalCount());
        } catch (Exception exception) {
            log.error("Fail to create task, repo: {}", repoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);

        }
    }

    @Override
    public ListKnowledgeTasksResponseBody listKnowledgeTask(String repoId, ListTaskCriteria listTaskCriteria) {
        ListKnowledgeTasksResponseBody listKnowledgeTaskResp;
        try {
            // 调用lakeSearch接口查询任务列表
            listKnowledgeTaskResp = cssUniSearchClient.listKnowledgeTask(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, repoId, listTaskCriteria.getPageNum(),
                listTaskCriteria.getPageSize(), listTaskCriteria.getTaskType(), listTaskCriteria.getTaskStatus(),
                listTaskCriteria.getFileName());
            log.info("Success to list tasks: {}", listKnowledgeTaskResp.getTotal());
        } catch (Exception exception) {
            log.error("Fail to list tasks!", exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);

        }
        return listKnowledgeTaskResp;
    }

    @Override
    public CommonBatchDeleteRsp deleteKnowledgeTask(String repoId, List<String> taskIds) {
        try {
            // 调用lakeSearch接口删除任务
            DeleteKnowledgeTaskReq deleteKnowledgeTaskReq = new DeleteKnowledgeTaskReq().setTaskIds(taskIds);
            BatchDeleteFaqResp resp = cssUniSearchClient.deleteKnowledgeTask(getUri(null), getHeaders(null),
                lakeSearchProjectId, lakeSearchApplicationId, repoId, deleteKnowledgeTaskReq);
            log.info("Success to delete task: {}", taskIds);
            return new CommonBatchDeleteRsp().setTotalCount(resp.getTotalCount())
                .setDeletedCount(resp.getDeletedCount());
        } catch (Exception exception) {
            log.error("Fail to delete tasks: {}.", taskIds, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);

        }
    }

    @Override
    public ListKnowledgeTagsResp listKnowledgeRepoTags(KnowledgeRepo knowledgeRepo, int pageNum, int pageSize) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口查询知识库标签列表
            ListKnowledgeLabelsResp listKnowledgeLabelsResp = cssUniSearchClient.listLabels(
                getUri(knowledgeRepo.getMetadata()), getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId,
                lakeSearchApplicationId, knowledgeRepoId, INTERNAL_TAG_PAGE_NUM, INTERNAL_TAG_PAGE_SIZE);
            log.info("Success to list knowledge repo labels: {}", listKnowledgeLabelsResp.getTotal());
            List<KnowledgeTagInfo> tagList = listKnowledgeLabelsResp.getLabelList().stream().map(labelInfo -> {
                    KnowledgeTagInfo tagInfo = new KnowledgeTagInfo();
                    tagInfo.setId(labelInfo.getId());
                    tagInfo.setName(labelInfo.getName());
                    tagInfo.setColor(labelInfo.getColor());
                    tagInfo.setCreateTime(Long.parseLong(labelInfo.getCreateTime()));

                    return tagInfo;
                })
                // 全局排序：按创建时间降序
                .sorted(Comparator.comparingLong(KnowledgeTagInfo::getCreateTime).reversed())
                // 内存分页：计算跳过的行数并截取
                // pageNum 通常从 1 开始，skip 需要 (pageNum - 1) * pageSize
                .skip((long) (pageNum - 1) * pageSize).limit(pageSize).collect(Collectors.toList());

            return new ListKnowledgeTagsResp().setCount(listKnowledgeLabelsResp.getTotal()).setTagList(tagList);
        } catch (Exception exception) {
            log.error("Fail to list knowledge repo labels, knowledgeRepoId: {}.", knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);

        }
    }

    @Override
    public CreateKnowledgeRepoTagsRsp createKnowledgeRepoTags(KnowledgeRepo knowledgeRepo,
        CreateKnowledgeRepoTagsReq body) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
        ListKnowledgeLabelsResp listKnowledgeLabelsResp = cssUniSearchClient.listLabels(getUri(null),
            getHeaders(null), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId,
            INTERNAL_TAG_PAGE_NUM, INTERNAL_TAG_PAGE_SIZE);
        // 检查标签是否达到上限
        if (listKnowledgeLabelsResp.getTotal() >= MAX_TAG_NUM) {
            log.error("Fail to create knowledge repo labels, knowledgeRepoId: {}, error: {}.", knowledgeRepoId,
                "the number of labels exceeds the limit.");
            throw new AgentBaseException(ErrorCode.RESOURCE_CAPACITY_LIMIT_ERROR);
        }
        // 检查标签是否已存在
        boolean isExist = listKnowledgeLabelsResp.getLabelList()
            .stream()
            .anyMatch(item -> Objects.equals(item.getName(), body.getName()));
        if (isExist) {
            throw new AgentBaseException(ErrorCode.TAG_NAME_ALREADY_EXIST);
        }
        try {
            // 调用接口创建知识库标签
            CreateKnowledgeLabelsRsp createKnowledgeLabelsRsp = cssUniSearchClient.createLabel(getUri(null),
                getHeaders(null), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId, body);
            log.info("Success to create knowledge repo label, id: {}", createKnowledgeLabelsRsp.getLabelId());
            return new CreateKnowledgeRepoTagsRsp().setTagId(createKnowledgeLabelsRsp.getLabelId());
        } catch (Exception exception) {
            log.error("Fail to create knowledge repo labels, knowledgeRepoId: {}, error: {}.", knowledgeRepoId,
                exception.getMessage(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public DeleteKnowledgeRepoTagsRsp deleteKnowledgeRepoTags(KnowledgeRepo knowledgeRepo, String tagId,
        DeleteKnowledgeRepoTagsReq body) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();

            // 调用LakeSearch接口删除知识库标签
            DeleteKnowledgeLabelsReq deleteKnowledgeLabelsReq = DeleteKnowledgeLabelsReq.builder()
                .labelName(body.getTagName())
                .build();
            DeleteKnowledgeLabelsRsp deleteKnowledgeLabelsRsp = cssUniSearchClient.deleteLabel(getUri(null),
                getHeaders(null), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId, tagId,
                deleteKnowledgeLabelsReq);
            log.info("Success to delete knowledge repo label, id: {}", deleteKnowledgeLabelsRsp.getLabelId());
            return new DeleteKnowledgeRepoTagsRsp().setTagId(deleteKnowledgeLabelsRsp.getLabelId());
        } catch (Exception exception) {
            log.error("Fail to delete repo labels, knowledgeRepoId: {}, error: {}.", knowledgeRepoId,
                exception.getMessage(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    private HttpHeaders getHeaders(String metadata) {
        KnowledgeRepoMetadata knowledgeRepoMetadata = null;
        if (StringUtils.isNotBlank(metadata)) {
            knowledgeRepoMetadata = JacksonUtils.readValue(metadata, KnowledgeRepoMetadata.class);
        }
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
        LakeSearchConnection lakeSearchConnection = new LakeSearchConnection();
        if (!KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            lakeSearchConnection = lakeSearchConnectionProvider.getKnowledgeSourceConnection(connectionId);
            lakeSearchEndpoint = lakeSearchConnection.getEndpoint();
            authMode = lakeSearchConnection.getAuthMode();
        }
        HttpHeaders headers = new HttpHeaders();
        String userId = RequestContextUtils.getRequestUserId();
        headers.add(CommonConstant.X_USER_ID, userId);

        // LakeSearch header rename — cust-userid→userid, cust-token→token
        Map<String, String> captured = RequestContextUtils.getCustomerHeaders();
        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        if (profile != null && profile.isEnabled() && !captured.isEmpty()) {
            Map<String, String> renamed = HeaderRename.resolve(captured, profile);
            for (Map.Entry<String, String> entry : renamed.entrySet()) {
                headers.add(entry.getKey(), entry.getValue());
            }
            log.info("[customer-header] Customer header rename applied: target=LAKESEARCH, capturedKeys={}, renamedKeys={}", captured.keySet(), renamed.keySet());
        } else if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            // 向后兼容：Profile 未启用时，保持原有 CUSTOM 模式从 HTTP 请求直接读取的行为
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                headers.add(CommonConstant.CustomModel.USER_ID, request.getHeader(CommonConstant.CustomModel.CUSTOM_USER_ID));
                headers.add(CommonConstant.CustomModel.TOKEN, request.getHeader(CommonConstant.CustomModel.CUSTOM_TOKEN));
            }
        }
        // 无需认证，直接返回
        if (RagAuthMode.NONE.toString().equalsIgnoreCase(authMode)) {
            return headers;
        }
        String lakeSearchAuthorization = lakeSearchConnection.getLsBasicAuth().getLakeSearchAuthorization();
        // Basic认证，获取lakeSearch的authorization，密文
        String authorization = Optional.ofNullable(knowledgeRepoMetadata)
            .map(KnowledgeRepoMetadata::getAuthorization)
            .orElse(lakeSearchAuthorization);
        if (StringUtils.isBlank(authorization)) {
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, "authorization");
        }
        // 解密
        String realAuth = CryptoUtils.decrypt(authorization);
        headers.add(CommonConstant.AUTHORIZATION, realAuth);
        return headers;
    }

    private URI getUri(String metadata) {
        KnowledgeRepoMetadata knowledgeRepoMetadata = null;
        if (StringUtils.isNotBlank(metadata)) {
            knowledgeRepoMetadata = JacksonUtils.readValue(metadata, KnowledgeRepoMetadata.class);
        }
        String connectionId = knowledgeConnectionRouterService.findConnectionIdByContext();
        LakeSearchConnection lakeSearchConnection = new LakeSearchConnection();
        if (!KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            lakeSearchConnection = lakeSearchConnectionProvider.getKnowledgeSourceConnection(connectionId);
            lakeSearchEndpoint = lakeSearchConnection.getEndpoint();
            authMode = lakeSearchConnection.getAuthMode();
        }
        // 获取lakeSearch的endpoint
        String endpoint = Optional.ofNullable(knowledgeRepoMetadata)
            .map(KnowledgeRepoMetadata::getEndpoint)
            .orElse(lakeSearchEndpoint);
        if (StringUtils.isBlank(endpoint)) {
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, "endpoint");
        }
        return URI.create(endpoint);
    }

    private FileInfo getFileInfoFromCssFileInfo(CssFileInfo cssFileInfo) {
        FileInfo fileInfo = new FileInfo();
        fileInfo.setFileId(cssFileInfo.getId());
        fileInfo.setFileName(cssFileInfo.getName());
        fileInfo.setFileType(cssFileInfo.getType());
        fileInfo.setFileSize(cssFileInfo.getSize());
        fileInfo.setProjectId(RequestContextUtils.getRequestProjectId());
        fileInfo.setFileStatus(cssFileInfo.getStatus());
        fileInfo.setFileTags(cssFileInfo.getTags());
        fileInfo.setFailureReason(cssFileInfo.getUploadDesc());
        fileInfo.setCreateTime(Long.parseLong(cssFileInfo.getCreateTime()));
        fileInfo.setUpdateTime(Long.parseLong(cssFileInfo.getCreateTime()));
        return fileInfo;
    }

    private List<FileChunkInfo> getFileChunkInfoFromFileDocInfo(List<FileDocInfo> fileDocInfos) {
        List<FileChunkInfo> fileChunkInfos = new ArrayList<>();
        if (CollectionUtils.isEmpty(fileDocInfos)) {
            return fileChunkInfos;
        }
        for (FileDocInfo fileDocInfo : fileDocInfos) {
            FileChunkInfo fileChunkInfo = new FileChunkInfo();
            fileChunkInfo.setId(fileDocInfo.getId());
            fileChunkInfo.setTimestamp(fileDocInfo.getTimestamp());
            fileChunkInfo.setContent(fileDocInfo.getContent());
            fileChunkInfo.setTitle(fileDocInfo.getTitle());
            fileChunkInfo.setPageNum(fileDocInfo.getPageNum());
            fileChunkInfo.setComponentNum(fileDocInfo.getComponentNum());
            fileChunkInfos.add(fileChunkInfo);
        }
        return fileChunkInfos;
    }

    @Override
    public String uploadFaqFile(KnowledgeRepo knowledgeRepo, MultipartFile resource) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        UploadFaqFileRsp uploadFaqFileResp;
        try {
            // 调用LakeSearch接口上传文档
            uploadFaqFileResp = cssUniSearchClient.uploadFaqFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId,
                resource);
            log.info("Success to upload FAQ File: {}", uploadFaqFileResp);
        } catch (Exception exception) {
            log.error("Fail to upload FAQ file to knowledge repo, projectId: {}, knowledgeRepoId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        return uploadFaqFileResp.getFileId();
    }

    @Override
    public void deleteFaqFile(KnowledgeRepo knowledgeRepo, String fileId) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口删除文档，只支持删除自建知识库下的FAQ文档
            cssUniSearchClient.deleteFaqFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId,
                fileId);
        } catch (Exception exception) {
            log.error("Fail to delete FAQ file from knowledge repo, projectId: {}, knowledgeRepoId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);

        }
    }

    @Override
    public FaqFileInfoListRsp listFaqFiles(KnowledgeRepo knowledgeRepo, ListFaqFileReq listFaqFileReq) {
        ListFilesRsp listFilesRsp;
        try {
            // 调用LakeSearch接口查询知识库文档列表
            listFilesRsp = cssUniSearchClient.searchFaqFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), listFaqFileReq.getPageNum(), listFaqFileReq.getPageSize(),
                listFaqFileReq.getFileName(), listFaqFileReq.getFileStatus(), listFaqFileReq.getIds());
            log.info("Success to list FAQ Files: {}", listFilesRsp.getTotal());
        } catch (Exception exception) {
            log.error("Fail to list FAQ file from knowledge repo, projectId: {}, knowledgeRepoId: {}, fileName: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getKnowledgeRepoId(),
                listFaqFileReq.getFileName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        List<FileInfo> fileInfos = new ArrayList<>();
        for (CssFileInfo cssFileInfo : listFilesRsp.getFiles()) {
            fileInfos.add(getFileInfoFromCssFileInfo(cssFileInfo));
        }
        return new FaqFileInfoListRsp().setFileInfoList(fileInfos).setCount(listFilesRsp.getTotal());
    }

    @Override
    public ResponseEntity<byte[]> downloadFaqFile(KnowledgeRepo knowledgeRepo, String fileId) {
        ResponseEntity<byte[]> responseEntity;
        try {
            // 调用LakeSearch接口下载知识库文档
            responseEntity = cssUniSearchClient.downloadFaqFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId);
            log.info("Success to download FAQ file: {}", fileId);
        } catch (Exception exception) {
            log.error("Fail to download FAQ file from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        return responseEntity;
    }

    @Override
    public void createFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, FaqFileChunkReq faqFileChunkReq) {
        try {
            cssUniSearchClient.createFaqFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, faqFileChunkReq);
        } catch (Exception exception) {
            log.error("Fail to create FAQ file chunk from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void deleteFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId) {
        try {
            cssUniSearchClient.batchDeleteFaqFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, Collections.singletonList(chunkId));
        } catch (Exception exception) {
            log.error("Fail to delete FAQ file chunk from knowledge repo, projectId: {}, fileId: {}, chunkId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, chunkId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public Resource queryImage(KnowledgeRepo knowledgeRepo, String imageId) {
        try {
            return cssUniSearchClient.queryImage(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), null, imageId);
        } catch (Exception exception) {
            log.error("Fail to query image, projectId: {}, knowledgeRepoId: {}, imageId: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepo.getKnowledgeRepoId(), imageId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public void updateFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId,
        FaqFileChunkReq faqFileChunkReq) {
        try {
            cssUniSearchClient.updateFaqFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), fileId, chunkId, faqFileChunkReq);
        } catch (Exception exception) {
            log.error("Fail to update FAQ file chunk from knowledge repo, projectId: {}, fileId: {}, chunkId: {}.",
                RequestContextUtils.getRequestProjectId(), fileId, chunkId, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    @Override
    public FaqFileChunkListRsp listFaqFileChunks(KnowledgeRepo knowledgeRepo,
        ListFaqFileChunksReq listFaqFileChunksReq) {
        ListFileDocsRsp listFileDocsRsp;
        try {
            listFileDocsRsp = cssUniSearchClient.listFaqFileDocs(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId,
                knowledgeRepo.getKnowledgeRepoId(), listFaqFileChunksReq.getFileId(), listFaqFileChunksReq.getPageNum(),
                listFaqFileChunksReq.getPageSize());
        } catch (Exception exception) {
            log.error("Fail to list FAQ file chunks from knowledge repo, projectId: {}, fileId: {}.",
                RequestContextUtils.getRequestProjectId(), listFaqFileChunksReq.getFileId(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
        FaqFileChunkListRsp faqFileChunkListRsp = new FaqFileChunkListRsp();
        faqFileChunkListRsp.setCount(listFileDocsRsp.getTotal());
        faqFileChunkListRsp.setFileChunkList(getFileChunkInfoFromFileDocInfo(listFileDocsRsp.getDocs()));
        return faqFileChunkListRsp;
    }

    @Override
    public BatchDeleteKnowledgeFilesResponseBody batchDeleteFile(KnowledgeRepo knowledgeRepo,
        BatchDeleteKnowledgeFilesRequestBody deleteFileReq) {
        String knowledgeRepoId = knowledgeRepo.getKnowledgeRepoId();
        try {
            // 调用LakeSearch接口批量删除文档，只支持删除自建知识库下的文档
            return cssUniSearchClient.batchDeleteFiles(getUri(knowledgeRepo.getMetadata()),
                getHeaders(knowledgeRepo.getMetadata()), lakeSearchProjectId, lakeSearchApplicationId, knowledgeRepoId,
                deleteFileReq);
        } catch (Exception exception) {
            log.error("Fail to batch delete file from knowledge repo, projectId: {}, knowledgeRepoId: {}, fileIds: {}.",
                RequestContextUtils.getRequestProjectId(), knowledgeRepoId, deleteFileReq, exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    public Boolean testConnection(LakeSearchConnection lakeSearchConnection) {
        ListKnowledgeRepoReq req = new ListKnowledgeRepoReq();
        req.setName(null);
        req.setPageNum(1);
        req.setPageSize(1);
        try {
            ListKnowledgeRepoResp knowledgeRepoInfos = cssUniSearchClient.listKnowledgeRepos(
                getUriByConnectionInfo(lakeSearchConnection), getHeadersByConnectionInfo(lakeSearchConnection),
                lakeSearchProjectId, lakeSearchApplicationId, req.getPageNum(), req.getPageSize(), req.getName(), null,
                null, null, null, null);
            log.info("Success to list KnowledgeRepos: {}", knowledgeRepoInfos.getTotal());
            return true;
        } catch (Exception exception) {
            log.error("Fail to list knowledge repos, projectId: {}, knowledgeRepoName: {}.",
                RequestContextUtils.getRequestProjectId(), req.getName(), exception);
            throw new AgentBaseException(ErrorCode.LAKE_SEARCH_SERVICE_EXCEPTION, exception);
        }
    }

    private URI getUriByConnectionInfo(LakeSearchConnection lakeSearchConnection) {
        String endpoint = lakeSearchConnection.getEndpoint();
        if (StringUtils.isBlank(endpoint)) {
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, "endpoint");
        }
        return URI.create(endpoint);
    }

    private HttpHeaders getHeadersByConnectionInfo(LakeSearchConnection lakeSearchConnection) {
        String authMode = lakeSearchConnection.getAuthMode();
        HttpHeaders headers = new HttpHeaders();
        String userId = RequestContextUtils.getRequestUserId();
        headers.add(CommonConstant.X_USER_ID, userId);
        log.info("Call lakeSearch request with userId:{}", userId);
        // 无需认证，直接返回
        if (RagAuthMode.NONE.toString().equalsIgnoreCase(authMode)) {
            return headers;
        }
        String authorization = lakeSearchConnection.getLsBasicAuth().getLakeSearchAuthorization();
        if (StringUtils.isBlank(authorization)) {
            throw new AgentBaseException(ErrorCode.INVALID_KNOWLEDGE_REPO_REQUEST, "authorization");
        }
        // 解密
        String realAuth = CryptoUtils.decrypt(authorization);
        headers.add(CommonConstant.AUTHORIZATION, realAuth);
        return headers;
    }

}
