/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2018-2020. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceVersion;
import com.openjiuwen.studio.agent.manager.enums.ExportModeEnum;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;

import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.context.jdbc.Sql;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Sql(scripts = {"classpath:sql/resource_export_delete_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_CLASS)
public class AgentExportServiceTest extends BaseTest {

    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    private AutoCloseable mockitoCloseable;

    @MockitoSpyBean
    private AgentExportService agentExportService;

    @MockitoBean
    private MgObsService mgObsService;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(Constants.TEST_WORKSPACE_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("test_copy_user_id");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
    }

    @Test
    @Sql(scripts = {
        "classpath:sql/resource_export_setup_db.sql"
    }, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testAgentExportV2() throws IOException {
        String projectId = Constants.TEST_PROJECT_ID;
        ExportResourceParams body = new ExportResourceParams();
        List<ExportResourceVersion> exportWfVersions = new ArrayList<>();
        ExportResourceVersion workflowVersion = new ExportResourceVersion();
        workflowVersion.setResourceId("9c770dc5-3151-4ae1-ad56-69804f35fca5");
        exportWfVersions.add(workflowVersion);
        body.setResourceVersions(exportWfVersions);
        body.setResourceType("workflow");

        String jsonAgent = TestUtil.getStringFromFile("classpath:response/export_agent_dsl.json");
        String jsonCard = TestUtil.getStringFromFile("classpath:response/export_card_dsl.json");
        String jsonWf = TestUtil.getStringFromFile("classpath:response/export_workflow_dsl.json");

        when(mgObsService.downloadObsFile(
            eq("card/dsl/505ae1ee-9147-444c-a5f0-d1342203cee2/505ae1ee-9147-444c-a5f0-d1342203cee2_1763623857387.json"))).thenReturn(
            jsonCard);
        when(mgObsService.downloadObsFile(
            eq("workflow/flow/505ae1ee-9147-444c-a5f0-d1342203cee2/505ae1ee-9147-444c-a5f0-d1342203cee2_1763623857387.json"))).thenReturn(
            jsonWf);
        when(mgObsService.downloadObsFile(
            eq("workflow/flow/9c770dc5-3151-4ae1-ad56-69804f35fca5/9c770dc5-3151-4ae1-ad56-69804f35fca5.json"))).thenReturn(
            jsonWf);
        when(mgObsService.downloadObsFile(
            eq("agent/dsl/b51efca2-1cd4-47c6-9f72-58732ec08235/b51efca2-1cd4-47c6-9f72-58732ec08235.json"))).thenReturn(
            jsonAgent);
        when(mgObsService.downloadObsFile(
            "agent/flow/235542f8-473f-40ff-9fb1-87a19ecbbe09/235542f8-473f-40ff-9fb1-87a19ecbbe09_1770111082736.json")).thenReturn(
            jsonAgent);
        when(mgObsService.downloadObsFile(
            "agent/flow/4381b681-d8fd-4169-a301-61cf3947a0b6/4381b681-d8fd-4169-a301-61cf3947a0b6.json")).thenReturn(
            jsonAgent);
        when(mgObsService.getTemporaryGetRsp(anyBoolean(), anyString(), anyLong())).thenReturn("testurl");
        when(mgObsService.uploadStreamStagingBucket(anyString(), any(), anyInt())).thenReturn(StringUtils.EMPTY);
        when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), anyInt())).thenReturn(StringUtils.EMPTY);

        ExportResourceRsp exportWfResourceRsp = agentExportService.exportResource(projectId,
            Constants.TEST_WORKSPACE_ID, body);
        assertNotNull(exportWfResourceRsp);

        // 测试agent导出
        List<ExportResourceVersion> exportAgentVersions = new ArrayList<>();
        ExportResourceVersion agentVersion = new ExportResourceVersion();
        agentVersion.setResourceId("b51efca2-1cd4-47c6-9f72-58732ec08235");
        exportAgentVersions.add(agentVersion);
        body.setResourceVersions(exportAgentVersions);
        body.setResourceType("agent");
        body.setMode(ExportModeEnum.STRICT.getCode());

        ExportResourceRsp exportAgentResourceRsp = agentExportService.exportResource(projectId,
            Constants.TEST_WORKSPACE_ID, body);
        assertNotNull(exportAgentResourceRsp);

        // 测试多agent导出
        List<ExportResourceVersion> exportControllerVersions = new ArrayList<>();
        ExportResourceVersion controllerVersion = new ExportResourceVersion();
        controllerVersion.setResourceId("4381b681-d8fd-4169-a301-61cf3947a0b6");
        exportControllerVersions.add(controllerVersion);
        body.setResourceVersions(exportControllerVersions);
        body.setResourceType("controller");
        body.setMode(ExportModeEnum.STRICT.getCode());

        ExportResourceRsp exportControllerResourceRsp = agentExportService.exportResource(projectId,
            Constants.TEST_WORKSPACE_ID, body);
        assertEquals(exportControllerResourceRsp,null);

        // 测试validResource分支：指定不存在的版本号，validResource返回true，资源被跳过并记录错误
        List<ExportResourceVersion> exportInvalidVersions = new ArrayList<>();
        ExportResourceVersion invalidVersion = new ExportResourceVersion();
        invalidVersion.setResourceId("9c770dc5-3151-4ae1-ad56-69804f35fca5");
        invalidVersion.setResourceVersion("nonexistent_version");
        exportInvalidVersions.add(invalidVersion);
        body.setResourceVersions(exportInvalidVersions);
        body.setResourceType("workflow");
        body.setMode(ExportModeEnum.STRICT.getCode());

        ExportResourceRsp exportInvalidRsp = agentExportService.exportResource(projectId, Constants.TEST_WORKSPACE_ID,
            body);
        assertNotNull(exportInvalidRsp);
        assertNotNull(exportInvalidRsp.getExportResult());

        // 测试validResource分支：指定存在的版本号，validResource返回false，继续导出流程
        List<ExportResourceVersion> exportExistVersions = new ArrayList<>();
        ExportResourceVersion existVersion = new ExportResourceVersion();
        existVersion.setResourceId("8192c574-c2a1-42de-be5f-10f2d55e95d2");
        existVersion.setResourceVersion("1770004066150");
        exportExistVersions.add(existVersion);
        body.setResourceVersions(exportExistVersions);
        body.setResourceType("workflow");
        body.setMode(ExportModeEnum.STRICT.getCode());

        ExportResourceRsp exportExistRsp = agentExportService.exportResource(projectId, Constants.TEST_WORKSPACE_ID,
            body);
        assertNotNull(exportExistRsp);
        assertNotNull(exportExistRsp.getExportResult());

        // 测试buildExportFile中parents合并：同时导出两个引用同一子资源的agent
        List<ExportResourceVersion> exportMergeVersions = new ArrayList<>();
        ExportResourceVersion agentV1 = new ExportResourceVersion();
        agentV1.setResourceId("b51efca2-1cd4-47c6-9f72-58732ec08235");
        exportMergeVersions.add(agentV1);
        ExportResourceVersion agentV2 = new ExportResourceVersion();
        agentV2.setResourceId("4381b681-d8fd-4169-a301-61cf3947a0b6");
        exportMergeVersions.add(agentV2);
        body.setResourceVersions(exportMergeVersions);
        body.setResourceType("agent");

        ExportResourceRsp exportMergeRsp = agentExportService.exportResource(projectId, Constants.TEST_WORKSPACE_ID,
            body);
        assertNotNull(exportMergeRsp);
        assertNotNull(exportMergeRsp.getExportResult());
    }

}
