/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

@MockitoSettings(strictness = Strictness.LENIENT)
class WorkflowManagementTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PluginBaseImpl pluginBaseImpl;

    @InjectMocks
    private WorkflowManagementService workflowManagementService;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(workflowManagementService, "opSvcProjectId", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultChatFlow", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultTaskFlow", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultChatFlowEnglish", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultTaskFlowEnglish", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultSystemParam", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "workflowDefaultSystemParamEnglish", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "defaultModelType", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "endpointTemplate", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "defaultIcon", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "releaseMaxSize", 0);
        ReflectionTestUtils.setField(workflowManagementService, "nestedLevel", 0);
        ReflectionTestUtils.setField(workflowManagementService, "webpageEndpoint", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "agentRuntimeEndpoint", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "runWorkflowStreamUrl", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "knowledgeRepoLimit", 0);
        ReflectionTestUtils.setField(workflowManagementService, "envType", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "knowledgeSource", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "publishAgentBuilderEnable", true);
        ReflectionTestUtils.setField(workflowManagementService, "publishCrossWorkspace", true);
        ReflectionTestUtils.setField(workflowManagementService, "isSoftDelete", true);
        ReflectionTestUtils.setField(workflowManagementService, "publishAppEnable", true);
        ReflectionTestUtils.setField(workflowManagementService, "contentReviewConfigs", "not_empty");
        ReflectionTestUtils.setField(workflowManagementService, "assetAppFreeTrialQuotaLimit", 0);
        ReflectionTestUtils.setField(workflowManagementService, "fileMaxSize", 0L);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_getReferenceType_inner_type() {
        ShareResourceEntity shareResourceEntity = mock(ShareResourceEntity.class);
        when(shareResourceEntity.getResourceId()).thenReturn("resourceId");
        when(pluginBaseImpl.isInnerType(eq("resourceId"))).thenReturn(true);

        String result = workflowManagementService.getReferenceType(ResourceTypeEnum.TOOL, shareResourceEntity);
        assertEquals(ReferenceTypeEnum.DIRECT.getValue(), result);
    }

    @Test
    void test_getReferenceType_direct_type() {
        ShareResourceEntity shareResourceEntity = mock(ShareResourceEntity.class);
        when(shareResourceEntity.getResourceId()).thenReturn("resourceId");
        when(shareResourceEntity.getWorkspaceId()).thenReturn("workspaceId");
        when(pluginBaseImpl.isInnerType(eq("resourceId"))).thenReturn(false);

        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("workspaceId");

            String result = workflowManagementService.getReferenceType(ResourceTypeEnum.TOOL, shareResourceEntity);
            assertEquals(ReferenceTypeEnum.DIRECT.getValue(), result);
        }
    }

    @Test
    void test_getReferenceType_share_type() {
        ShareResourceEntity shareResourceEntity = mock(ShareResourceEntity.class);
        when(shareResourceEntity.getResourceId()).thenReturn("resourceId");
        when(shareResourceEntity.getWorkspaceId()).thenReturn("workspaceId");
        when(pluginBaseImpl.isInnerType(eq("resourceId"))).thenReturn(false);

        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("differentWorkspaceId");

            String result = workflowManagementService.getReferenceType(ResourceTypeEnum.TOOL, shareResourceEntity);
            assertEquals(ReferenceTypeEnum.SHARE.getValue(), result);
        }
    }

    @Test
    void test_getReferenceType_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRequestContextUtils.when(() -> RequestContextUtils.getRequestWorkspaceId())
                    .thenReturn(null);

                when(pluginBaseImpl.isInnerType(anyString())).thenReturn(true);

                // When
                String result = workflowManagementService.getReferenceType(ResourceTypeEnum.TOOL, null);
            }
        });
    }
}
