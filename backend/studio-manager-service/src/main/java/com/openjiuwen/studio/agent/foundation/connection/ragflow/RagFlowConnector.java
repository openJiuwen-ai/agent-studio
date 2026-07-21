/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.connection.ragflow;

import com.fasterxml.jackson.core.type.TypeReference;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.openjiuwen.studio.agent.common.dto.knowledge.lakeserach.request.RequestParamConstants;
import com.openjiuwen.studio.agent.common.dto.knowledge.ragflow.request.RetrieveChunksRequestBody;
import com.openjiuwen.studio.agent.common.dto.knowledge.ragflow.response.RagFlowCommonResponseBody;
import com.openjiuwen.studio.agent.common.dto.knowledge.ragflow.response.ResponseConstants;
import com.openjiuwen.studio.agent.common.dto.knowledge.ragflow.response.RetrieveChunksResponseBody;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;
import com.openjiuwen.studio.agent.foundation.base.utils.JacksonUtils;
import com.openjiuwen.studio.agent.foundation.connection.AbstractKnowledgeBaseConnector;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorDefinition;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorParamDefinition;
import com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorParamConstants;
import com.openjiuwen.studio.agent.foundation.connection.httpclient.BasicRequest;
import com.openjiuwen.studio.agent.foundation.connection.httpclient.ConnectorClient;
import com.openjiuwen.studio.agent.foundation.base.http.RequestEntity;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalKnowledgeBaseInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalRetrieveResultInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.KnowledgeBaseTagInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.agent.foundation.connection.model.RetrieveKnowledgeBaseReq;
import com.openjiuwen.studio.agent.common.dto.knowledge.RetrieveChunkInfo;
import com.openjiuwen.studio.agent.foundation.connection.ragflow.entity.response.DatasetBasicInfo;
import com.openjiuwen.studio.agent.foundation.connection.ragflow.entity.response.ListDatasetResponseBody;
import com.openjiuwen.studio.agent.foundation.connection.utils.ConnectorParamUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;

import java.net.URI;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 对接RAGFlow的连接实现
 *
 * @since 2025-08-22
 */
@Slf4j
public class RagFlowConnector extends AbstractKnowledgeBaseConnector {

    private final static String LIST_DATA_SET_URI = "/api/v1/datasets";

    private final static String RETRIEVE_CHUNKS_URI = "/api/v1/retrieval";

    private final static String IMAGE_PATH_URI = "/v1/document/image/";

    private final static String PAGE = "page";

    public RagFlowConnector(ConnectorClient connectorClient) {
        super(connectorClient, new RagFlowAuthHandler());
    }

    @Override
    public PageResult<ExternalKnowledgeBaseInfo> listKnowledgeBase(ConnectorDefinition connectorDefinition, String name,
        Integer offset, Integer limit) {
        // RagFlow的数据集查询接口支持服务端分页，并返回满足过滤条件的总数total_datasets，此处按offset/limit换算成page/page_size交给服务端分页
        int pageNum = offset / limit + 1;
        int pageSize = limit;
        Map<String, Object> queryParam = Maps.newHashMap();
        queryParam.put(RequestParamConstants.NAME, name);
        queryParam.put(PAGE, pageNum);
        queryParam.put(RequestParamConstants.PAGE_SIZE, pageSize);

        RequestEntity requestEntity = RequestEntity.builder().requestParams(queryParam).build();
        BasicRequest basicRequest = BasicRequest.builder()
            .uri(LIST_DATA_SET_URI)
            .method(HttpMethod.GET)
            .requestEntity(requestEntity)
            .build();
        HttpEntity<Object> request = generateAuthRequest(basicRequest, connectorDefinition);

        ListDatasetResponseBody result = this.connectorClient.doRequest(basicRequest, request,
            ListDatasetResponseBody.class);

        if (ResponseConstants.SUCCESS_CODE != result.getCode()) {
            log.error("Call rag flow to list dataset failed. Because of {}", result.getMessage());
            throw new AgentBaseException(ErrorCode.RAG_FLOW_CONNECT_ERROR);
        }

        PageResult<ExternalKnowledgeBaseInfo> response = new PageResult<>();
        response.setTotalCount(Optional.ofNullable(result.getTotalDatasets()).orElse(0L));
        List<DatasetBasicInfo> dataRes = Optional.ofNullable(result.getData())
            .orElse(Collections.<DatasetBasicInfo>emptyList());
        response.setItems(dataRes.stream().map(item -> {
            ExternalKnowledgeBaseInfo externalKnowledgeBaseInfo = new ExternalKnowledgeBaseInfo();
            externalKnowledgeBaseInfo.setKnowledgeBaseId(item.getId());
            externalKnowledgeBaseInfo.setKnowledgeBaseName(item.getName());
            externalKnowledgeBaseInfo.setDescription(item.getDescription());
            return externalKnowledgeBaseInfo;
        }).toList());
        return response;
    }

    @Override
    public PageResult<ExternalRetrieveResultInfo> retrieveKnowledgeBase(ConnectorDefinition connectorDefinition,
        RetrieveKnowledgeBaseReq request, Integer offset, Integer limit) {
        RetrieveChunksRequestBody retrieveChunksRequestBody = new RetrieveChunksRequestBody();
        retrieveChunksRequestBody.setQuestion(request.getQuery());
        retrieveChunksRequestBody.setDatasetIds(request.getKnowledgeBaseIds());
        int pageNum = offset / limit + 1;
        int pageSize = limit;
        retrieveChunksRequestBody.setPage(pageNum);
        retrieveChunksRequestBody.setPageSize(pageSize);
        RequestEntity requestEntity = RequestEntity.builder()
            .body(JacksonUtils.toJson(retrieveChunksRequestBody))
            .build();
        BasicRequest basicRequest = BasicRequest.builder()
            .uri(RETRIEVE_CHUNKS_URI)
            .method(HttpMethod.POST)
            .requestEntity(requestEntity)
            .build();
        HttpEntity<Object> httpEntity = generateAuthRequest(basicRequest, connectorDefinition);
        RagFlowCommonResponseBody<RetrieveChunksResponseBody> result = JacksonUtils.readValue(JacksonUtils.toJson(
                this.connectorClient.doRequest(basicRequest, httpEntity, RagFlowCommonResponseBody.class)),
            new TypeReference<>() { });

        if (ResponseConstants.SUCCESS_CODE == result.getCode()) {
            PageResult<ExternalRetrieveResultInfo> response = new PageResult<>();
            int total = Optional.ofNullable(result.getData()).map(RetrieveChunksResponseBody::getTotal).orElse(0);
            response.setTotalCount((long) total);
            String ragFlowConsoleUrl = getRagFlowConsoleHost(connectorDefinition);
            List<ExternalRetrieveResultInfo> retrieveRes = Optional.ofNullable(result.getData())
                .map(RetrieveChunksResponseBody::getChunks)
                .orElse(Collections.<RetrieveChunkInfo>emptyList())
                .stream()
                .map(item -> {
                    ExternalRetrieveResultInfo retrieveResultInfo = new ExternalRetrieveResultInfo();
                    retrieveResultInfo.setTitle(item.getDocumentKeyword());
                    retrieveResultInfo.setContent(item.getContent());
                    retrieveResultInfo.setScore(item.getSimilarity());
                    retrieveResultInfo.setKnowledgeBaseId(item.getDatasetId());
                    retrieveResultInfo.setFileId(item.getDocumentId());
                    retrieveResultInfo.setChunkId(item.getId());
                    if (RequestParamConstants.DOC_TYPE_KWD_IMAGE.equals(item.getDocTypeKwd())) {
                        retrieveResultInfo.setImageIds(
                            StringUtils.isEmpty(item.getImageId()) ? null : Lists.newArrayList(item.getImageId()));
                        retrieveResultInfo.setImagePaths(StringUtils.isEmpty(item.getImageId())
                            ? null
                            : Lists.newArrayList(generateImagePath(ragFlowConsoleUrl, item.getImageId())));
                    }
                    return retrieveResultInfo;
                })
                .toList();
            response.setItems(retrieveRes);
            return response;
        } else {
            log.error("Call rag flow to retrieve chunk failed. Because of {}", result.getMessage());
            throw new AgentBaseException(ErrorCode.RAG_FLOW_CONNECT_ERROR);
        }
    }

    @Override
    public List<KnowledgeBaseTagInfo> listKnowledgeBaseTags(ConnectorDefinition connectorDefinition,
        String knowledgeBaseId) {
        return Collections.emptyList();
    }

    /**
     * 获取RagFlow的console访问地址
     *
     * @param connectorDefinition
     * @return
     */
    private String getRagFlowConsoleHost(ConnectorDefinition connectorDefinition) {
        Optional<ConnectorParamDefinition> detailPageUrlOption = Optional.ofNullable(connectorDefinition)
            .map(ConnectorDefinition::getParamDefinitions)
            .orElse(Collections.<ConnectorParamDefinition>emptyList())
            .stream()
            .filter(item -> ConnectorParamConstants.DETAIL_PAGE_PARAM.equals(item.getCode()))
            .findFirst();
        if (detailPageUrlOption.isEmpty()) {
            return null;
        }
        String detailPageUrl = detailPageUrlOption.get()
            .getValue()
            .replace(ConnectorParamUtil.EXTERNAL_ID_PLACE_HOLDER, "");
        URI uri = URI.create(detailPageUrl);
        return uri.getScheme() + "://" + uri.getAuthority();
    }

    /**
     * 生成图片的查看路径
     *
     * @param consoleUrl
     * @param imageId
     * @return
     */
    private String generateImagePath(String consoleUrl, String imageId) {
        return consoleUrl + IMAGE_PATH_URI + imageId;
    }
}
