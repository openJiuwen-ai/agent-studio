/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.foundation.connection.connection.ragflow;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.nullable;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.foundation.connection.ConnectorDefinition;
import com.openjiuwen.studio.agent.foundation.connection.ConnectorParamDefinition;
import com.openjiuwen.studio.agent.foundation.connection.IRestAuthHandler;
import com.openjiuwen.studio.agent.foundation.connection.constants.ConnectorParamConstants;
import com.openjiuwen.studio.agent.foundation.connection.constants.QueryModeEnum;
import com.openjiuwen.studio.agent.foundation.connection.httpclient.BasicRequest;
import com.openjiuwen.studio.agent.foundation.connection.httpclient.ConnectorClient;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalKnowledgeBaseInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.ExternalRetrieveResultInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.KnowledgeBaseTagInfo;
import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.agent.foundation.connection.model.KnowledgeBaseRetrieval;
import com.openjiuwen.studio.agent.foundation.connection.model.RetrieveKnowledgeBaseReq;
import com.openjiuwen.studio.agent.foundation.connection.ragflow.RagFlowConnector;
import com.openjiuwen.studio.agent.foundation.connection.ragflow.entity.response.ListDatasetResponseBody;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.common.dto.knowledge.ragflow.response.RagFlowCommonResponseBody;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.http.HttpEntity;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.List;

@MockitoSettings(strictness = Strictness.LENIENT)
class RagFlowConnectorTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ConnectorClient connectorClient;

    @InjectMocks
    private RagFlowConnector ragFlowConnector;

    @Mock
    private IRestAuthHandler restAuthHandler;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(ragFlowConnector, "authHandler", restAuthHandler);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_listKnowledgeBase_should_return_not_null_when_condition() throws Exception {
        // 产品按 ListDatasetResponseBody.class 反序列化，stub 需与之一致
        ListDatasetResponseBody listDatasetResponseBody = new ListDatasetResponseBody();
        listDatasetResponseBody.setCode(0);
        listDatasetResponseBody.setData(new ArrayList<>());
        listDatasetResponseBody.setMessage("string");
        when(connectorClient.doRequest(any(), any(), eq(ListDatasetResponseBody.class))).thenReturn(
            listDatasetResponseBody);

        // When
        PageResult<ExternalKnowledgeBaseInfo> result1 = ragFlowConnector.listKnowledgeBase(null, "string", 0, 10);

        // Then
        assertNotNull(result1);
    }

    @Test
    void test_listKnowledgeBase_should_throw_business_exception_when_response_body_is_null() throws Exception {
        // 下游空体（doRequest 返回 null）按 RAG_FLOW_CONNECT_ERROR 收口，而非 NPE。
        // generateAuthRequest 经 mock 的 authHandler 返回 null，第二实参为 null，
        // 须用 nullable() 匹配（any(HttpEntity.class) 不匹配 null，stub 会静默失效）
        when(connectorClient.doRequest(any(BasicRequest.class), nullable(HttpEntity.class),
            eq(ListDatasetResponseBody.class))).thenReturn(null);

        assertThrows(AgentBaseException.class, () -> {
            ragFlowConnector.listKnowledgeBase(null, null, 0, 10);
        });
    }

    @Test
    void test_retrieveKnowledgeBase_should_throw_business_exception_when_response_body_is_null() {
        // retrieveChunks 对 toJson(null) 反序列化回 null 同样按连接错误收口
        when(connectorClient.doRequest(any(BasicRequest.class), nullable(HttpEntity.class),
            eq(RagFlowCommonResponseBody.class))).thenReturn(null);

        RetrieveKnowledgeBaseReq request = new RetrieveKnowledgeBaseReq();
        request.setQuery("string");
        request.setQueryMode(QueryModeEnum.DOC);
        List<KnowledgeBaseRetrieval> knowledgeBaseRetrievals = new ArrayList<>();
        KnowledgeBaseRetrieval knowledgeBaseRetrieval = new KnowledgeBaseRetrieval();
        knowledgeBaseRetrieval.setKnowledgeBaseId("string");
        knowledgeBaseRetrieval.setTagName(new ArrayList<>());
        knowledgeBaseRetrievals.add(knowledgeBaseRetrieval);
        request.setKnowledgeBaseRetrievals(knowledgeBaseRetrievals);

        assertThrows(AgentBaseException.class, () -> {
            ragFlowConnector.retrieveKnowledgeBase(null, request, 0, 10);
        });
    }

    @Test
    void test_retrieveKnowledgeBase_should_return_not_null_when_condition() throws Exception {
        RagFlowCommonResponseBody ragFlowCommonResponseBody = new RagFlowCommonResponseBody();
        ragFlowCommonResponseBody.setCode(0);
        Object data1 = new Object();
        ragFlowCommonResponseBody.setData(data1);
        ragFlowCommonResponseBody.setMessage("string");
        when(connectorClient.doRequest(any(), any(), eq(RagFlowCommonResponseBody.class))).thenReturn(
            ragFlowCommonResponseBody);

        RetrieveKnowledgeBaseReq request = new RetrieveKnowledgeBaseReq();
        List<String> knowledgeBaseId = new ArrayList<>();
        knowledgeBaseId.add("string");
        request.setQuery("string");
        request.setQueryMode(QueryModeEnum.DOC);
        List<KnowledgeBaseRetrieval> knowledgeBaseRetrievals = new ArrayList<>();
        KnowledgeBaseRetrieval knowledgeBaseRetrieval = new KnowledgeBaseRetrieval();
        knowledgeBaseRetrieval.setKnowledgeBaseId("string");
        knowledgeBaseRetrieval.setTagName(new ArrayList<>());
        knowledgeBaseRetrievals.add(knowledgeBaseRetrieval);
        request.setKnowledgeBaseRetrievals(knowledgeBaseRetrievals);
        // When
        PageResult<ExternalRetrieveResultInfo> result1 = ragFlowConnector.retrieveKnowledgeBase(null, request, 0, 10);

        // Then
        assertNotNull(result1);
    }

    @Test
    void test_retrieveKnowledgeBase_should_throws__null_pointer_exception_when_objects_is_null() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            when(connectorClient.doRequest(any(BasicRequest.class), any(HttpEntity.class),
                eq(RagFlowCommonResponseBody.class))).thenReturn(null);

            // When
            PageResult<ExternalRetrieveResultInfo> result = ragFlowConnector.retrieveKnowledgeBase(null, null,
                (Integer) null, (Integer) null);
        });
    }

    @Test
    void test_listKnowledgeBaseTags_should_return_not_null_when_condition() throws Exception {

        // When
        List<KnowledgeBaseTagInfo> result = ragFlowConnector.listKnowledgeBaseTags(null, "string");

        // Then
        assertTrue(result.isEmpty());
    }

    @Test
    void test_getRagFlowConsoleHost_should_equal_result_when_condition() throws Exception {
        // Given
        List<ConnectorParamDefinition> paramDefinitions = new ArrayList<>();
        ConnectorParamDefinition paramDefinition = new ConnectorParamDefinition();
        paramDefinition.setCode(ConnectorParamConstants.DETAIL_PAGE_PARAM);
        paramDefinition.setValue("http://127.0.0.1/knowledge/dataset?id={{id}}");
        paramDefinitions.add(paramDefinition);
        ConnectorDefinition connectorDefinition = ConnectorDefinition.builder()
            .paramDefinitions(paramDefinitions)
            .build();

        // When
        String result = ReflectionTestUtils.invokeMethod(ragFlowConnector, "getRagFlowConsoleHost",
            connectorDefinition);

        // Then
        assertEquals("http://127.0.0.1", result);
    }
}