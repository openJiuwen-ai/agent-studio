/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.PluginIAMAuthInfo;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateToolOpenAPIResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreateToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyToolReq;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.JsonSchemaUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import io.swagger.v3.oas.models.security.SecurityScheme;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.MessageSource;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ToolManagementServiceTest {

    @Mock
    private ToolMapper toolMapper;
    @Mock
    private MappingMapper mappingMapper;
    @Mock
    private UrlCheckUtils urlCheckUtils;
    @Mock
    private MgObsService obsService;
    @Mock
    private ReleaseVersionMapper releaseVersionMapper;
    @Mock
    private AgentCommonService agentCommonService;
    @Mock
    private ToolCredentialMapper toolCredentialMapper;
    @Mock
    private MessageSource messageSource;
    @Mock
    private AgentMapper agentMapper;
    @Mock
    private WorkflowMapper workflowMapper;
    @Mock
    private I18nUtil i18nUtil;
    @Mock
    private PluginMapper pluginMapper;
    @Mock
    private AgentServiceProxyService agentServiceProxyService;
    @Mock
    private IPluginBase pluginBase;
    @Mock
    private ShareResourceMapper shareResourceMapper;
    @Mock
    private ShareScopeMapper shareScopeMapper;
    @Mock
    private ShareInnerService shareInnerService;
    @Mock
    private EncryptionAdapter encryptionAdapter;

    @InjectMocks
    private ToolManagementService toolManagementService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(toolManagementService, "opSvcProjectId", "op-project-id");
        ReflectionTestUtils.setField(toolManagementService, "maxPropNum", 50);
        ReflectionTestUtils.setField(toolManagementService, "maxPropDepth", 5);
        ReflectionTestUtils.setField(toolManagementService, "toolNameBlackList", "blacklisted");
        ReflectionTestUtils.setField(toolManagementService, "defaultIcon", "default-icon");
        ReflectionTestUtils.setField(toolManagementService, "excludeInnerTools", "");
        ReflectionTestUtils.setField(toolManagementService, "releaseMaxSize", 10);
        ReflectionTestUtils.setField(toolManagementService, "presetPlugin", "preset_mock");
        ReflectionTestUtils.setField(toolManagementService, "isSoftDelete", true);
        ReflectionTestUtils.setField(toolManagementService, "pluginBase", pluginBase);
        ReflectionTestUtils.setField(toolManagementService, "shareResourceMapper", shareResourceMapper);
        ReflectionTestUtils.setField(toolManagementService, "shareScopeMapper", shareScopeMapper);
        ReflectionTestUtils.setField(toolManagementService, "shareInnerService", shareInnerService);
        ReflectionTestUtils.setField(toolManagementService, "encryptionAdapter", encryptionAdapter);
    }

    @Test
    void testCreateToolV1_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");

            when(toolMapper.selectByDisplayNameAndWorkspaceId(anyString(), anyString())).thenReturn(0);

            CreateToolReq req = new CreateToolReq();
            req.setToolDisplayName("MyTool");
            req.setRequestInfo(validHttpRequestInfo());

            CreateToolRsp result = toolManagementService.createToolV1("p1", "w1", req);

            assertNotNull(result);
            verify(toolMapper).insert(any(ToolEntity.class));
        }
    }

    @Test
    void testCreateToolV1_DefaultsVisibilityToProjectWhenMissing() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");

            when(toolMapper.selectByDisplayNameAndWorkspaceId(anyString(), anyString())).thenReturn(0);

            CreateToolReq req = new CreateToolReq();
            req.setToolDisplayName("NoVisTool");
            req.setRequestInfo(validHttpRequestInfo());
            // visibility 不传，保持 null

            CreateToolRsp result = toolManagementService.createToolV1("p1", "w1", req);

            assertNotNull(result);
            ArgumentCaptor<ToolEntity> captor = ArgumentCaptor.forClass(ToolEntity.class);
            verify(toolMapper).insert(captor.capture());
            assertEquals("project", captor.getValue().getVisibility());
        }
    }

    @Test
    void testCreateToolV1_RejectsNullRequestInfo() {
        CreateToolReq req = new CreateToolReq();
        req.setToolDisplayName("NoRiTool");
        req.setRequestInfo(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.createToolV1("p1", "w1", req));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
        assertEquals("request_info is required.", ex.getDetails().get(0));
        verify(toolMapper, never()).insert(any(ToolEntity.class));
    }

    @Test
    void testCreateToolV1_RejectsIncompleteRequestInfo() {
        CreateToolReq req = new CreateToolReq();
        req.setToolDisplayName("BadRiTool");
        req.setRequestInfo(new RequestInfo()); // url/method 缺失

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.createToolV1("p1", "w1", req));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
        assertEquals("request_info.url and request_info.method are required.", ex.getDetails().get(0));
        verify(toolMapper, never()).insert(any(ToolEntity.class));
    }

    @Test
    void testCreateToolV1_DuplicateDisplayName() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");

            when(toolMapper.selectByDisplayNameAndWorkspaceId(anyString(), anyString())).thenReturn(1);

            CreateToolReq req = new CreateToolReq();
            req.setToolDisplayName("ExistingTool");
            req.setRequestInfo(validHttpRequestInfo());

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.createToolV1("p1", "w1", req));
            assertEquals(StudioError.TOOL_EN_NAME_ALREADY_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testCreateToolV1_DuplicateKeyException() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");

            when(toolMapper.selectByDisplayNameAndWorkspaceId(anyString(), anyString())).thenReturn(0);
            doThrow(new DuplicateKeyException("duplicate")).when(toolMapper).insert(any(ToolEntity.class));

            CreateToolReq req = new CreateToolReq();
            req.setToolDisplayName("DupTool");
            req.setRequestInfo(validHttpRequestInfo());

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.createToolV1("p1", "w1", req));
            assertEquals(StudioError.TOOL_NAME_ALREADY_EXIST, ex.getErrorCode());
        }
    }

    private static RequestInfo validHttpRequestInfo() {
        RequestInfo ri = new RequestInfo();
        ri.setUrl("https://example.com/api/x");
        ri.setMethod(RequestInfo.MethodEnum.POST);
        return ri;
    }

    @Test
    void testCheckToolIsUsed_NotUsed() {
        when(agentMapper.selectByAgentIdAndResourceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(0);
        when(workflowMapper.selectByWorkflowIdAndResourceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(0);

        Boolean result = toolManagementService.checkToolIsUsed("p1", "w1", "tool-1");
        assertFalse(result);
    }

    @Test
    void testCheckToolIsUsed_UsedByAgent() {
        when(agentMapper.selectByAgentIdAndResourceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(3);

        Boolean result = toolManagementService.checkToolIsUsed("p1", "w1", "tool-1");
        assertTrue(result);
    }

    @Test
    void testCheckToolIsUsed_UsedByWorkflow() {
        when(agentMapper.selectByAgentIdAndResourceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(0);
        when(workflowMapper.selectByWorkflowIdAndResourceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(2);

        Boolean result = toolManagementService.checkToolIsUsed("p1", "w1", "tool-1");
        assertTrue(result);
    }

    @Test
    void testDeleteToolV1_SoftDelete() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("p1");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);

        CommonDeleteRsp result = toolManagementService.deleteToolV1("p1", "tool-1", "w1");

        assertNotNull(result);
        assertEquals("tool-1", result.getId());
        verify(mappingMapper).updateValidByResourceIdAndVersionId("tool-1", null);
        verify(releaseVersionMapper).deleteByAppId("tool-1");
        verify(toolMapper).copyToHistoryTool(eq("tool-1"), eq("p1"), anyString());
        verify(toolMapper).deleteByPrimaryKey("tool-1", "p1");
    }

    @Test
    void testDeleteToolV1_HardDelete() {
        ReflectionTestUtils.setField(toolManagementService, "isSoftDelete", false);

        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("p1");

        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("/dsl/path");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);
        when(releaseVersionMapper.selectByAppId("tool-1")).thenReturn(List.of(rv));

        CommonDeleteRsp result = toolManagementService.deleteToolV1("p1", "tool-1", "w1");

        assertNotNull(result);
        assertEquals("tool-1", result.getId());
        verify(obsService).deleteObsFile("/dsl/path");
        verify(toolMapper).deleteByPrimaryKey("tool-1", "p1");
    }

    @Test
    void testDeleteToolV1_ToolNotFound() {
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(null);

        CommonDeleteRsp result = toolManagementService.deleteToolV1("p1", "tool-1", "w1");

        assertNull(result);
        verify(toolMapper, never()).deleteByPrimaryKey(anyString(), anyString());
    }

    @Test
    void testRetrieveToolV1_NotFound() {
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.retrieveToolV1("p1", "tool-1", "w1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testRetrieveToolV1_PermissionDenied() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("other-project");
        toolEntity.setWorkspaceId("other-ws");
        toolEntity.setType("custom");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(toolEntity);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.retrieveToolV1("p1", "tool-1", "w1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testRetrieveToolV1_InnerToolAccessible() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("other-project");
        toolEntity.setWorkspaceId("other-ws");
        toolEntity.setType("inner");
        toolEntity.setTestStatus(0);

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(toolEntity);

        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);

            assertDoesNotThrow(() -> toolManagementService.retrieveToolV1("p1", "tool-1", "w1"));
        }
    }

    @Test
    void testRetrieveToolV1_SameProjectWorkspace() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("p1");
        toolEntity.setWorkspaceId("w1");
        toolEntity.setType("custom");
        toolEntity.setTestStatus(0);

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(toolEntity);

        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);

            assertDoesNotThrow(() -> toolManagementService.retrieveToolV1("p1", "tool-1", "w1"));
        }
    }

    @Test
    void testListToolVersions_Success() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);
        when(agentCommonService.listVersions("tool-1", 10)).thenReturn(new VersionListRsp());

        VersionListRsp result = toolManagementService.listToolVersions("p1", "tool-1", "w1");

        assertNotNull(result);
        verify(agentCommonService).listVersions("tool-1", 10);
    }

    @Test
    void testListToolVersions_ToolNotExist() {
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.listToolVersions("p1", "tool-1", "w1"));
        assertEquals(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testCheckToolPermission_Exists() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);

        assertDoesNotThrow(() -> toolManagementService.checkToolPermission("p1", "w1", "tool-1"));
    }

    @Test
    void testCheckToolPermission_NotExists() {
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkToolPermission("p1", "w1", "tool-1"));
        assertEquals(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testCheckInnerToolPermission_Exists() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);

        assertDoesNotThrow(() -> toolManagementService.checkInnerToolPermission("tool-1"));
    }

    @Test
    void testCheckInnerToolPermission_NotExists() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkInnerToolPermission("tool-1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testRequireHttpRequestInfo_Null() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.requireHttpRequestInfo(null));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
        assertEquals("request_info is required.", ex.getDetails().get(0));
    }

    @Test
    void testRequireHttpRequestInfo_MissingUrlOrMethod() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.requireHttpRequestInfo(new RequestInfo()));
        assertEquals(StudioError.TOOL_INPUT_INVALID, ex.getErrorCode());
        assertEquals("request_info.url and request_info.method are required.", ex.getDetails().get(0));
    }

    @Test
    void testRequireHttpRequestInfo_Valid() {
        assertDoesNotThrow(() -> toolManagementService.requireHttpRequestInfo(validHttpRequestInfo()));
    }

    @Test
    void testCheckUrl_NullRequestInfo() {
        assertDoesNotThrow(() -> toolManagementService.checkUrl(null, "p1"));
    }

    @Test
    void testCheckUrl_EmptyUrl() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("");

        assertDoesNotThrow(() -> toolManagementService.checkUrl(requestInfo, "p1"));
    }

    @Test
    void testCheckUrl_UrlWithPlaceholder() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("http://example.com/{param}");

        assertDoesNotThrow(() -> toolManagementService.checkUrl(requestInfo, "p1"));
        verify(urlCheckUtils, never()).checkUrl(anyString(), anyString());
    }

    @Test
    void testCheckUrl_ValidUrl() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("http://example.com/api");

        assertDoesNotThrow(() -> toolManagementService.checkUrl(requestInfo, "p1"));
        verify(urlCheckUtils).checkUrl("p1", "http://example.com/api");
    }

    @Test
    void testCheckToolInfo_InvalidVisibility() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkToolInfo("name", null, null, "invalid_visibility", null));
        assertEquals(StudioError.INVALID_VISIBILITY, ex.getErrorCode());
    }

    @Test
    void testCheckToolInfo_NameInBlackList() {
        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.checkToolInfo("blacklisted", null, null, null, null));
            assertEquals(StudioError.TOOL_NAME_ALREADY_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testCheckToolInfo_InvalidInputSchema() {
        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(eq("bad_schema"), anyInt(), anyInt(), eq(true)))
                .thenReturn(false);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.checkToolInfo("name", "bad_schema", null, null, null));
            assertEquals(StudioError.TOOL_INPUT_SCHEMA_INVALID, ex.getErrorCode());
        }
    }

    @Test
    void testCheckToolInfo_InvalidLocationNamesParameter() {
        String input =
            "{\"type\":\"object\",\"properties\":{\"city\":{\"type\":\"string\",\"description\":\"城市\",\"location\":\"Invalid\"}},\"required\":[\"city\"]}";
        String output =
            "{\"type\":\"object\",\"properties\":{\"ok\":{\"type\":\"boolean\",\"description\":\"ok\"}}}";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkToolInfo("name", input, output, null, "blocking"));
        assertEquals(StudioError.TOOL_INPUT_SCHEMA_INVALID, ex.getErrorCode());
        assertTrue(ex.getDetails().get(0).contains("[city]"));
        assertTrue(ex.getDetails().get(0).contains("[location]"));
    }

    @Test
    void testCheckToolInfo_NestedArrayNamesParameter() {
        String input =
            "{\"type\":\"object\",\"properties\":{\"matrix\":{\"type\":\"array\",\"description\":\"二维\",\"location\":\"Body\",\"items\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}}}},\"required\":[\"matrix\"]}";
        String output =
            "{\"type\":\"object\",\"properties\":{\"ok\":{\"type\":\"boolean\",\"description\":\"ok\"}}}";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkToolInfo("name", input, output, null, "blocking"));
        assertEquals(StudioError.TOOL_INPUT_SCHEMA_INVALID, ex.getErrorCode());
        assertEquals("The parameter [matrix] cannot be nested array.", ex.getDetails().get(0));
    }

    @Test
    void testCheckToolInfo_EmptyOutputProperties() {
        String input =
            "{\"type\":\"object\",\"properties\":{\"city\":{\"type\":\"string\",\"description\":\"城市\",\"location\":\"Body\"}},\"required\":[\"city\"]}";
        String output = "{\"type\":\"object\",\"properties\":{}}";
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.checkToolInfo("name", input, output, null, "blocking"));
        assertEquals(StudioError.TOOL_OUTPUT_SCHEMA_INVALID, ex.getErrorCode());
        assertEquals("The schema root field [properties] cannot be empty.", ex.getDetails().get(0));
    }

    @Test
    void testCheckToolInfo_InvalidOutputSchema() {
        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(eq("bad_output"), anyInt(), anyInt(), eq(false)))
                .thenReturn(false);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.checkToolInfo("name", null, "bad_output", null, null));
            assertEquals(StudioError.TOOL_OUTPUT_SCHEMA_INVALID, ex.getErrorCode());
        }
    }

    @Test
    void testCheckToolInfo_StreamingSkipsOutputValidation() {
        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);

            assertDoesNotThrow(() ->
                toolManagementService.checkToolInfo("name", null, "bad_output", null, "streaming"));
        }
    }

    @Test
    void testCheckToolInfo_ValidAll() {
        try (MockedStatic<JsonSchemaUtils> jsMock = mockStatic(JsonSchemaUtils.class)) {
            jsMock.when(() -> JsonSchemaUtils.isJsonSchemaValid(any(), anyInt(), anyInt(), anyBoolean()))
                .thenReturn(true);

            assertDoesNotThrow(() ->
                toolManagementService.checkToolInfo("name", null, null, "user", null));
        }
    }

    @Test
    void testCreateToolOpenAPIByIdV1_ToolNotExist() {
        when(pluginBase.buildToolByPlugin("p1", "w1", "tool-1", "0")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> toolManagementService.createToolOpenAPIByIdV1("p1", "tool-1", "w1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }



    @Test
    void testDeleteToolCredential_NotExist() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);
        when(toolCredentialMapper.selectByToolId("p1", "tool-1", "w1")).thenReturn(null);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.deleteToolCredential("p1", "tool-1", "w1"));
            assertEquals(StudioError.TOOL_CREDENTIAL_NOT_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testDeleteToolCredential_Success() {
        PluginEntity pluginEntity = new PluginEntity();
        ToolCredential credential = new ToolCredential();

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);
        when(toolCredentialMapper.selectByToolId("p1", "tool-1", "w1")).thenReturn(credential);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            CommonDeleteRsp result = toolManagementService.deleteToolCredential("p1", "tool-1", "w1");

            assertNotNull(result);
            assertEquals("tool-1", result.getId());
            verify(toolCredentialMapper).deleteByToolId("p1", "uid-1", "tool-1", "w1");
            verify(obsService).deleteObsFile(anyString());
        }
    }

    @Test
    void testReleaseToolVersionHandler_Success() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("p1");

        when(obsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("/obs/dsl/path");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class);
             MockedStatic<JsonUtils> jsonMock = mockStatic(JsonUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            jsonMock.when(() -> JsonUtils.toJson(any())).thenReturn("{}");

            ReleaseVersion result = toolManagementService.releaseToolVersionHandler(
                toolEntity, null, "v1", "note");

            assertNotNull(result);
            assertEquals("v1", result.getVersionName());
            assertEquals("note", result.getVersionNote());
            assertEquals("tool-1", result.getAppId());
            verify(releaseVersionMapper).insert(any(ReleaseVersion.class));
            verify(toolMapper).updateByPrimaryKeySelective(any(ToolEntity.class));
        }
    }

    @Test
    void testReleaseToolVersion_NoPermission() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setCreatorId("other-user");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.releaseToolVersion("p1", "tool-1", "w1", new CreateVersionReq()));
            assertEquals(StudioError.NO_CREATOR_PERMISSION, ex.getErrorCode());
        }
    }

    @Test
    void testReleaseToolVersion_ExceedMaxSize() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setCreatorId("uid-1");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);
        when(releaseVersionMapper.selectByAppId("tool-1")).thenReturn(
            Collections.nCopies(15, new ReleaseVersion()));

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.releaseToolVersion("p1", "tool-1", "w1", new CreateVersionReq()));
            assertEquals(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT, ex.getErrorCode());
        }
    }

    @Test
    void testReleaseToolVersion_OpTenantSuccess() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("op-project-id");
        toolEntity.setCreatorId("other-user");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "op-project-id", "w1")).thenReturn(toolEntity);
        when(releaseVersionMapper.selectByAppId("tool-1")).thenReturn(Collections.emptyList());
        when(obsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("/obs/path");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class);
             MockedStatic<JsonUtils> jsonMock = mockStatic(JsonUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            jsonMock.when(() -> JsonUtils.toJson(any())).thenReturn("{}");

            CreateVersionReq req = new CreateVersionReq();
            req.setVersionName("v1");
            req.setVersionNote("note");

            VersionInfo result = toolManagementService.releaseToolVersion("op-project-id", "tool-1", "w1", req);

            assertNotNull(result);
        }
    }

    @Test
    void testDeleteToolVersion_NoPermission() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setCreatorId("other-user");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(toolEntity);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.deleteToolVersion("p1", "v1", "tool-1", "w1"));
            assertEquals(StudioError.NO_PERMISSION_DELETE_TOOL, ex.getErrorCode());
        }
    }

    @Test
    void testDeleteToolVersion_ToolNotFound() {
        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "p1", "w1")).thenReturn(null);

        CommonDeleteRsp result = toolManagementService.deleteToolVersion("p1", "v1", "tool-1", "w1");

        assertNull(result);
    }

    @Test
    void testDeleteToolVersion_OpTenantSuccess() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setCreatorId("other-user");

        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("/dsl/path");
        rv.setVersionId("v1");

        when(toolMapper.selectByPrimaryKeyAndWorkspace("tool-1", "op-project-id", "w1")).thenReturn(toolEntity);
        when(shareInnerService.cancelPluginVersionShared(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(true);
        when(releaseVersionMapper.selectByAppIdAndVersionId("tool-1", "v1")).thenReturn(rv);
        when(releaseVersionMapper.selectByAppId("tool-1")).thenReturn(List.of(rv));

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            CommonDeleteRsp result =
                toolManagementService.deleteToolVersion("op-project-id", "v1", "tool-1", "w1");

            assertNotNull(result);
            assertEquals("tool-1", result.getId());
            assertEquals("v1", result.getVersionId());
            verify(obsService).deleteObsFile("/dsl/path");
            verify(mappingMapper).updateValidByResourceIdAndVersionId("tool-1", "v1");
            verify(releaseVersionMapper).deleteByAppIdAndVersionId("tool-1", "v1");
        }
    }

    @Test
    void testBuildIAMSecurityScheme_NullCredentials() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setCustomIamCredentials(null);
        SecurityScheme scheme = new SecurityScheme();

        toolManagementService.buildIAMSecurityScheme(authInfo, scheme);

        assertTrue(scheme.getExtensions() == null || scheme.getExtensions().isEmpty());
    }

    @Test
    void testBuildIAMSecurityScheme_WithCredentials() {
        PluginIAMAuthInfo iamInfo = new PluginIAMAuthInfo();
        iamInfo.setIamUrl("http://iam.example.com");
        iamInfo.setIamDomain("domain-1");
        iamInfo.setIamProject("project-1");
        iamInfo.setIamUser("user1");
        iamInfo.setIamPassword("pass1");
        iamInfo.setIamAk("ak-1");
        iamInfo.setIamSk("sk-1");

        AuthInfo authInfo = new AuthInfo();
        authInfo.setCustomIamCredentials(iamInfo);
        SecurityScheme scheme = new SecurityScheme();

        toolManagementService.buildIAMSecurityScheme(authInfo, scheme);

        assertNotNull(scheme.getExtensions());
        assertEquals(7, scheme.getExtensions().size());
    }



    @Test
    void testAddToolCredential_AlreadyExist() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setType(ToolType.INNER.type);
        pluginEntity.setAuthRequired(true);

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);
        when(toolCredentialMapper.selectByToolId("p1", "tool-1", "w1")).thenReturn(new ToolCredential());

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ToolCredential body = new ToolCredential();
            body.setAuthKeys(List.of(new AuthKeyInfo()));

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.addToolCredential("p1", "tool-1", "w1", false, body));
            assertEquals(StudioError.TOOL_CREDENTIAL_ALREADY_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testAddToolCredential_NullAuthKeys() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            ToolCredential body = new ToolCredential();
            body.setAuthKeys(null);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.addToolCredential("p1", "tool-1", "w1", false, body));
            assertEquals(StudioError.TOOL_AUTHENTICATION_FAILED, ex.getErrorCode());
        }
    }

    @Test
    void testAddToolCredential_PluginNotExist() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(pluginEntity);
        when(toolCredentialMapper.selectByToolId("p1", "tool-1", "w1")).thenReturn(null);
        when(pluginMapper.selectPluginEntityWithCredential(eq("tool-1"), eq("op-project-id"), anyString()))
            .thenReturn(null);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ToolCredential body = new ToolCredential();
            body.setAuthKeys(List.of(new AuthKeyInfo()));

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.addToolCredential("p1", "tool-1", "w1", false, body));
            assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testAddToolCredential_NotInnerType() {
        PluginEntity innerPlugin = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("tool-1", null, null)).thenReturn(innerPlugin);
        when(toolCredentialMapper.selectByToolId("p1", "tool-1", "w1")).thenReturn(null);

        PluginEntity credPlugin = new PluginEntity();
        credPlugin.setType(ToolType.CUSTOM.type);
        when(pluginMapper.selectPluginEntityWithCredential(eq("tool-1"), eq("op-project-id"), anyString()))
            .thenReturn(credPlugin);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ToolCredential body = new ToolCredential();
            body.setAuthKeys(List.of(new AuthKeyInfo()));

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> toolManagementService.addToolCredential("p1", "tool-1", "w1", false, body));
            assertEquals(StudioError.TOOL_AUTHENTICATION_FAILED, ex.getErrorCode());
        }
    }
}
