/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.service.knowledgerepo;

import com.alibaba.fastjson.JSON;
import com.openjiuwen.studio.agent.agentbase.entity.KnowledgeBaseEntity;
import com.openjiuwen.studio.agent.agentbase.mapper.KnowledgeBaseMapper;
import com.openjiuwen.studio.agent.agentbase.model.CreateKnowledgeRepoInfo;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeRepo;
import com.openjiuwen.studio.agent.agentbase.model.ListKnowledgeRepoResp;
import com.openjiuwen.studio.agent.agentbase.model.SearchTextResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FaqSearchCriteria;
import com.openjiuwen.studio.agent.agentbase.model.KnowledgeSegRuleInfo;
import com.openjiuwen.studio.agent.agentbase.model.ListTaskCriteria;
import com.openjiuwen.studio.agent.agentbase.model.ModelSearchCriteria;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesRequestBody;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ChatReferenceInfo;
import com.openjiuwen.studio.agent.manager.dto.CommonBatchDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeTaskResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FaqFileInfoListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSegmentRule;
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
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoReq;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.KBModelConfig;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenCreateKBReq;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenDeleteKBReq;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenKBResponse;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenSearchReq;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenSearchResp;
import com.openjiuwen.studio.agent.manager.dto.openjiuwen.OpenJiuwenUploadResp;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.common.dto.knowledge.KnowledgeFaq;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * OpenJiuwen本地知识库服务实现
 *
 * @since 2026-08-06
 */
@Slf4j
@Service("MgOpenJiuwen")
public class OpenJiuwenKBService implements KnowledgeRepoService {

    private final AgentRuntimeClient agentRuntimeClient;
    private final KnowledgeBaseMapper knowledgeBaseMapper;

    @Autowired
    public OpenJiuwenKBService(AgentRuntimeClient agentRuntimeClient, KnowledgeBaseMapper knowledgeBaseMapper) {
        this.agentRuntimeClient = agentRuntimeClient;
        this.knowledgeBaseMapper = knowledgeBaseMapper;
    }

    private KBModelConfig loadModelConfig(String kbId) {
        KnowledgeBaseEntity entity = knowledgeBaseMapper.selectById(null, kbId);
        if (entity == null) {
            return null;
        }
        return KBModelConfig.builder()
            .modelServiceId(entity.getEmbeddingModelServiceId())
            .workspaceId(entity.getWorkspaceId())
            .build();
    }

    @Override
    public CreateKnowledgeRepoInfo createKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        String kbId = knowledgeRepo.getKnowledgeRepoId();
        try {
            KBModelConfig modelConfig = loadModelConfig(kbId);
            OpenJiuwenCreateKBReq req = OpenJiuwenCreateKBReq.builder()
                .kbId(kbId)
                .kbName(knowledgeRepo.getDisplayName())
                .modelConfig(modelConfig)
                .build();
            ResponseEntity<OpenJiuwenKBResponse> resp = agentRuntimeClient.createOpenJiuwenKB(req);
            log.info("Success to create openjiuwen KB, kbId: {}, resp: {}", kbId, resp.getBody());
            CreateKnowledgeRepoInfo info = new CreateKnowledgeRepoInfo();
            info.setKnowledgeBaseId(kbId);
            info.setKnowledgeBaseConnectionId(kbId);
            return info;
        } catch (Exception e) {
            log.error("Fail to create openjiuwen knowledge repo, kbId: {}", kbId, e);
            throw new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, e);
        }
    }

    @Override
    public String modifyKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        log.warn("do not support modifyKnowledgeRepo yet");
        throw new AgentBaseException("do not support modifyKnowledgeRepo yet");
    }

    @Override
    public void deleteKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        String kbId = knowledgeRepo.getKnowledgeRepoId();
        try {
            OpenJiuwenDeleteKBReq req = new OpenJiuwenDeleteKBReq(kbId);
            agentRuntimeClient.deleteOpenJiuwenKB(req);
            log.info("Success to delete openjiuwen KB, kbId: {}", kbId);
        } catch (Exception e) {
            log.error("Fail to delete openjiuwen knowledge repo, kbId: {}", kbId, e);
            throw new AgentBaseException(ErrorCode.SERVER_INTERNAL_ERROR, e);
        }
    }

    @Override
    public KnowledgeRepo retrieveKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        return knowledgeRepo;
    }

    @Override
    public ListKnowledgeRepoResp listKnowledgeRepos(ListKnowledgeRepoReq listKnowledgeRepoReq) {
        return null;
    }

    @Override
    public String uploadFile(KnowledgeRepo knowledgeRepo, MultipartFile file, List<String> tags) {
        String kbId = knowledgeRepo.getKnowledgeRepoId();
        try {
            KBModelConfig modelConfig = loadModelConfig(kbId);
            String modelConfigJson = modelConfig != null ? JSON.toJSONString(modelConfig) : null;
            ResponseEntity<OpenJiuwenUploadResp> resp = agentRuntimeClient.uploadOpenJiuwenKBFile(
                kbId, file, modelConfigJson);
            log.info("Success to upload file to openjiuwen KB, kbId: {}, resp: {}", kbId, resp.getBody());
            return resp.getBody() != null && resp.getBody().getDocCount() != null
                ? resp.getBody().getDocCount().toString() : "0";
        } catch (Exception e) {
            log.error("Fail to upload file to openjiuwen KB, kbId: {}", kbId, e);
            throw new AgentBaseException(ErrorCode.FAIL_TO_UPLOAD_KNOWLEDGE_REPO_FILE, e);
        }
    }

    @Override
    public void deleteFile(KnowledgeRepo knowledgeRepo, String fileId) {
        log.warn("do not support deleteFile yet");
        throw new AgentBaseException("do not support deleteFile yet");
    }

    @Override
    public BatchDeleteKnowledgeFilesResponseBody batchDeleteFile(KnowledgeRepo knowledgeRepo,
        BatchDeleteKnowledgeFilesRequestBody deleteFileReq) {
        log.warn("do not support batchDeleteFile yet");
        throw new AgentBaseException("do not support batchDeleteFile yet");
    }

    @Override
    public ListKnowledgeFilesResponseBody listFiles(KnowledgeRepo knowledgeRepo, ListFileReq listFileReq) {
        return new ListKnowledgeFilesResponseBody().setCount(0).setFileInfoList(new ArrayList<>());
    }

    @Override
    public ResponseEntity<byte[]> downloadFile(KnowledgeRepo knowledgeRepo, String fileId) {
        log.warn("do not support downloadFile yet");
        throw new AgentBaseException("do not support downloadFile yet");
    }

    @Override
    public void createFileChunk(KnowledgeRepo knowledgeRepo, String fileId, FileChunkReq fileChunkReq) {
        log.warn("do not support createFileChunk yet");
        throw new AgentBaseException("do not support createFileChunk yet");
    }

    @Override
    public void updateFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId,
        FileChunkReq fileChunkReq) {
        log.warn("do not support updateFileChunk yet");
        throw new AgentBaseException("do not support updateFileChunk yet");
    }

    @Override
    public void updateFileMetaInfo(KnowledgeRepo knowledgeRepo, String fileId,
        UpdateFileMetaInfoReq updateFileMetaInfoReq) {
        log.warn("do not support updateFileMetaInfo yet");
        throw new AgentBaseException("do not support updateFileMetaInfo yet");
    }

    @Override
    public void deleteFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId) {
        log.warn("do not support deleteFileChunk yet");
        throw new AgentBaseException("do not support deleteFileChunk yet");
    }

    @Override
    public FileChunkListRsp listFileChunks(KnowledgeRepo knowledgeRepo, ListFileChunksReq listFileChunksReq) {
        log.warn("do not support listFileChunks yet");
        throw new AgentBaseException("do not support listFileChunks yet");
    }

    private static final Map<String, String> SEARCH_MODE_MAP = Map.of(
        "doc", "vector",
        "keyword", "bm25",
        "mix", "hybrid"
    );

    @Override
    public SearchTextResp searchText(List<KnowledgeRepo> knowledgeRepos, String query, String searchMode,
        List<String> tags, int pageNum, int pageSize) {
        String kbId = knowledgeRepos.get(0).getKnowledgeRepoId();
        try {
            KBModelConfig modelConfig = loadModelConfig(kbId);
            String indexType = SEARCH_MODE_MAP.getOrDefault(searchMode, "vector");
            OpenJiuwenSearchReq req = OpenJiuwenSearchReq.builder()
                .kbId(kbId)
                .query(query)
                .topK(pageSize)
                .indexType(indexType)
                .modelConfig(modelConfig)
                .build();
            ResponseEntity<OpenJiuwenSearchResp> resp = agentRuntimeClient.searchOpenJiuwenKB(req);
            OpenJiuwenSearchResp body = resp.getBody();
            List<ChatReferenceInfo> docList = new ArrayList<>();
            if (body != null && body.getResults() != null) {
                docList = body.getResults().stream()
                    .map(item -> {
                        ChatReferenceInfo info = new ChatReferenceInfo();
                        info.setContent(item.getText());
                        info.setScore(item.getScore() != null ? item.getScore().floatValue() : null);
                        info.setRepoId(kbId);
                        return info;
                    })
                    .toList();
            }
            log.info("Success to search openjiuwen KB, kbId: {}, resultCount: {}", kbId, docList.size());
            return new SearchTextResp(docList.size(), docList);
        } catch (Exception e) {
            log.error("Fail to search text from openjiuwen KB, kbId: {}", kbId, e);
            throw new AgentBaseException("Fail to search text from openjiuwen knowledge repo, kbId: " + kbId);
        }
    }

    @Override
    public String createFaq(KnowledgeFaq knowledgeFaq) {
        log.warn("do not support createFaq yet");
        throw new AgentBaseException("do not support createFaq yet");
    }

    @Override
    public void deleteFaq(String repoId, String faqId) {
        log.warn("do not support deleteFaq yet");
        throw new AgentBaseException("do not support deleteFaq yet");
    }

    @Override
    public Integer deleteFaqBatch(String repoId, List<String> faqIds) {
        log.warn("do not support deleteFaqBatch yet");
        throw new AgentBaseException("do not support deleteFaqBatch yet");
    }

    @Override
    public String modifyFaq(KnowledgeFaq knowledgeFaq) {
        log.warn("do not support modifyFaq yet");
        throw new AgentBaseException("do not support modifyFaq yet");
    }

    @Override
    public KnowledgeFaq retrieveFaq(String faqId, String repoId) {
        log.warn("do not support retrieveFaq yet");
        throw new AgentBaseException("do not support retrieveFaq yet");
    }

    @Override
    public ListFaqResp listFaq(FaqSearchCriteria faqSearchCriteria) {
        log.warn("do not support listFaq yet");
        throw new AgentBaseException("do not support listFaq yet");
    }

    @Override
    public void startKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        // openjiuwen不需要启停
    }

    @Override
    public void stopKnowledgeRepo(KnowledgeRepo knowledgeRepo) {
        // openjiuwen不需要启停
    }

    @Override
    public KnowledgeSegRuleInfo createSegmentRule(KnowledgeSegmentRule segmentRule, String repoId) {
        log.warn("do not support createSegmentRule yet");
        throw new AgentBaseException("do not support createSegmentRule yet");
    }

    @Override
    public String modifySegmentRule(KnowledgeSegmentRule segmentRule) {
        log.warn("do not support modifySegmentRule yet");
        throw new AgentBaseException("do not support modifySegmentRule yet");
    }

    @Override
    public void deleteSegmentRule(String ruleId) {
        log.warn("do not support deleteSegmentRule yet");
        throw new AgentBaseException("do not support deleteSegmentRule yet");
    }

    @Override
    public List<ModelInfo> listModels(ModelSearchCriteria searchCriteria, String connectionId) {
        log.warn("do not support listModels yet");
        throw new AgentBaseException("do not support listModels yet");
    }

    @Override
    public CreateKnowledgeTaskResponseBody createTask(String repoId, String taskType, List<String> fileIds) {
        log.warn("do not support createTask yet");
        throw new AgentBaseException("do not support createTask yet");
    }

    @Override
    public ListKnowledgeTasksResponseBody listKnowledgeTask(String repoId, ListTaskCriteria listTaskCriteria) {
        log.warn("do not support listKnowledgeTask yet");
        throw new AgentBaseException("do not support listKnowledgeTask yet");
    }

    @Override
    public CommonBatchDeleteRsp deleteKnowledgeTask(String repoId, List<String> taskIds) {
        log.warn("do not support deleteKnowledgeTask yet");
        throw new AgentBaseException("do not support deleteKnowledgeTask yet");
    }

    @Override
    public String uploadFaqFile(KnowledgeRepo knowledgeRepo, MultipartFile file) {
        log.warn("do not support uploadFaqFile yet");
        throw new AgentBaseException("do not support uploadFaqFile yet");
    }

    @Override
    public void deleteFaqFile(KnowledgeRepo knowledgeRepo, String fileId) {
        log.warn("do not support deleteFaqFile yet");
        throw new AgentBaseException("do not support deleteFaqFile yet");
    }

    @Override
    public FaqFileInfoListRsp listFaqFiles(KnowledgeRepo knowledgeRepo, ListFaqFileReq listFaqFileReq) {
        log.warn("do not support listFaqFiles yet");
        throw new AgentBaseException("do not support listFaqFiles yet");
    }

    @Override
    public ResponseEntity<byte[]> downloadFaqFile(KnowledgeRepo knowledgeRepo, String fileId) {
        log.warn("do not support downloadFaqFile yet");
        throw new AgentBaseException("do not support downloadFaqFile yet");
    }

    @Override
    public void createFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, FaqFileChunkReq faqFileChunkReq) {
        log.warn("do not support createFaqFileChunk yet");
        throw new AgentBaseException("do not support createFaqFileChunk yet");
    }

    @Override
    public void updateFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId,
        FaqFileChunkReq faqFileChunkReq) {
        log.warn("do not support updateFaqFileChunk yet");
        throw new AgentBaseException("do not support updateFaqFileChunk yet");
    }

    @Override
    public void deleteFaqFileChunk(KnowledgeRepo knowledgeRepo, String fileId, String chunkId) {
        log.warn("do not support deleteFaqFileChunk yet");
        throw new AgentBaseException("do not support deleteFaqFileChunk yet");
    }

    @Override
    public FaqFileChunkListRsp listFaqFileChunks(KnowledgeRepo knowledgeRepo,
        ListFaqFileChunksReq listFaqFileChunksReq) {
        log.warn("do not support listFaqFileChunks yet");
        throw new AgentBaseException("do not support listFaqFileChunks yet");
    }

    @Override
    public ListKnowledgeTagsResp listKnowledgeRepoTags(KnowledgeRepo knowledgeRepo, int pageNum, int pageSize) {
        log.warn("do not support listKnowledgeRepoTags yet");
        throw new AgentBaseException("do not support listKnowledgeRepoTags yet");
    }

    @Override
    public CreateKnowledgeRepoTagsRsp createKnowledgeRepoTags(KnowledgeRepo knowledgeRepo,
        CreateKnowledgeRepoTagsReq body) {
        log.warn("do not support createKnowledgeRepoTags yet");
        throw new AgentBaseException("do not support createKnowledgeRepoTags yet");
    }

    @Override
    public DeleteKnowledgeRepoTagsRsp deleteKnowledgeRepoTags(KnowledgeRepo knowledgeRepo, String tagId,
        DeleteKnowledgeRepoTagsReq body) {
        log.warn("do not support deleteKnowledgeRepoTags yet");
        throw new AgentBaseException("do not support deleteKnowledgeRepoTags yet");
    }

    @Override
    public Resource queryImage(KnowledgeRepo knowledgeRepo, String imageId) {
        log.warn("do not support queryImage yet");
        throw new AgentBaseException("do not support queryImage yet");
    }
}
