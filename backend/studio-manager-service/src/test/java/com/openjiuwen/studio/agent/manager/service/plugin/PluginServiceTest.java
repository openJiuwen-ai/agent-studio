/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.plugin;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.HisIamInfo;
import com.openjiuwen.studio.agent.common.dto.auth.HisSgov;
import com.openjiuwen.studio.agent.common.dto.auth.PluginIAMAuthInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.GetPluginVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginRsp;
import com.openjiuwen.studio.agent.manager.dto.ParsePluginReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateRsp;
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
import com.openjiuwen.studio.agent.manager.dto.RequestInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.plugin.BasicInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.PluginDTO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.UrlInfo;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.OldPluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.AgentCommonService;
import com.openjiuwen.studio.agent.manager.service.ToolManagementService;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginAdapterImpl;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.MessageSource;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PluginServiceTest {

    @Mock
    private MgObsService mgObsService;
    @Mock
    private UrlCheckUtils urlCheckUtils;
    @Mock
    private AgentCommonService agentCommonService;
    @Mock
    private ToolManagementService toolManagementService;
    @Mock
    private PluginMapper pluginMapper;
    @Mock
    private ToolMapper toolMapper;
    @Mock
    private OldPluginMapper oldPluginMapper;
    @Mock
    private ReleaseVersionMapper releaseVersionMapper;
    @Mock
    private MappingMapper mappingMapper;
    @Mock
    private MessageSource messageSource;
    @Mock
    private I18nUtil i18nUtil;
    @Mock
    private RedisClient redisClient;
    @Mock
    private EncryptionAdapter encryptionAdapter;
    @Mock
    private com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase pluginBase;
    @Mock
    private PluginAdapterImpl pluginAdapterImpl;
    @Mock
    private com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper shareResourceMapper;
    @Mock
    private com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper shareScopeMapper;
    @Mock
    private ShareInnerService shareInnerService;

    @InjectMocks
    private PluginService pluginService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(pluginService, "opSvcProjectId", "op-project-id");
        ReflectionTestUtils.setField(pluginService, "toolNameBlackList", "blacklisted");
        ReflectionTestUtils.setField(pluginService, "defaultIcon", "default-icon");
        ReflectionTestUtils.setField(pluginService, "toolMaxNum", 30);
        ReflectionTestUtils.setField(pluginService, "excludeInnerTools", "");
        ReflectionTestUtils.setField(pluginService, "importMaxLen", 100);
        ReflectionTestUtils.setField(pluginService, "releaseMaxSize", 10);
        ReflectionTestUtils.setField(pluginService, "pluginChoice", false);
        ReflectionTestUtils.setField(pluginService, "allowPluginCrossPermissionQuery", false);
        ReflectionTestUtils.setField(pluginService, "isSoftDelete", true);
        ReflectionTestUtils.setField(pluginService, "isHcs", false);
        ReflectionTestUtils.setField(pluginService, "pluginMaxFreeTrialTimes", 10);
    }

    @Test
    void testCheckPluginPermission_Exists() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);

        assertDoesNotThrow(() -> pluginService.checkPluginPermission("proj-1", "ws-1", "p-1"));
    }

    @Test
    void testCheckPluginPermission_NotExists() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.checkPluginPermission("proj-1", "ws-1", "p-1"));
        assertEquals(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testIsPluginExist_True() {
        PluginEntity plugin = new PluginEntity();
        plugin.setTraceId("trace-1");
        when(pluginMapper.selectByTraceIdAndWorkspaceId("proj-1", "ws-1", "trace-1"))
            .thenReturn(List.of(plugin));

        Boolean result = pluginService.isPluginExist("proj-1", "ws-1", plugin);
        assertTrue(result);
    }

    @Test
    void testIsPluginExist_False() {
        PluginEntity plugin = new PluginEntity();
        plugin.setTraceId("trace-1");
        when(pluginMapper.selectByTraceIdAndWorkspaceId("proj-1", "ws-1", "trace-1"))
            .thenReturn(Collections.emptyList());

        Boolean result = pluginService.isPluginExist("proj-1", "ws-1", plugin);
        assertFalse(result);
    }

    @Test
    void testListPluginVersions_Success() {
        PluginEntity pluginEntity = new PluginEntity();
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);
        when(agentCommonService.listVersions("p-1", 10)).thenReturn(new VersionListRsp());

        VersionListRsp result = pluginService.listPluginVersions("proj-1", "p-1", "ws-1");
        assertNotNull(result);
    }

    @Test
    void testListPluginVersions_PluginNotExist() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.listPluginVersions("proj-1", "p-1", "ws-1"));
        assertEquals(StudioError.TOOL_PROJECT_DONE_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testDeletePlugin_NotFound() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        CommonDeleteRsp result = pluginService.deletePlugin("proj-1", "p-1", "ws-1");
        assertNull(result);
    }

    @Test
    void testDeletePlugin_SoftDelete() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("p-1");
        pluginEntity.setProjectId("proj-1");

        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("/dsl/path1");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);
        when(releaseVersionMapper.selectByAppId("p-1")).thenReturn(List.of(rv));

        CommonDeleteRsp result = pluginService.deletePlugin("proj-1", "p-1", "ws-1");

        assertNotNull(result);
        assertEquals("p-1", result.getId());
        verify(shareInnerService).cancelPluginShared("proj-1", "ws-1", "p-1");
        verify(mappingMapper).updateValidByResourceId("p-1");
        verify(agentCommonService).softDeleteReleaseVersionByAppId("p-1");
        verify(pluginMapper).copyToHistoryTool(eq("p-1"), eq("proj-1"), anyString());
        verify(mgObsService).deleteObsFile("/dsl/path1");
        verify(pluginMapper).deleteByPrimaryKey("p-1", "proj-1");
    }

    @Test
    void testDeletePlugin_HardDelete() {
        ReflectionTestUtils.setField(pluginService, "isSoftDelete", false);

        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("p-1");
        pluginEntity.setProjectId("proj-1");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);
        when(releaseVersionMapper.selectByAppId("p-1")).thenReturn(Collections.emptyList());

        CommonDeleteRsp result = pluginService.deletePlugin("proj-1", "p-1", "ws-1");

        assertNotNull(result);
        verify(releaseVersionMapper).deleteByAppId("p-1");
        verify(pluginMapper).deleteByPrimaryKey("p-1", "proj-1");
    }

    @Test
    void testDeletePluginVersion_NotFound() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        CommonDeleteRsp result = pluginService.deletePluginVersion("proj-1", "v1", "p-1", "ws-1");
        assertNull(result);
    }

    @Test
    void testDeletePluginVersion_NoPermission() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setCreatorId("other-user");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> pluginService.deletePluginVersion("proj-1", "v1", "p-1", "ws-1"));
            assertEquals(StudioError.NO_PERMISSION_DELETE_TOOL, ex.getErrorCode());
        }
    }

    @Test
    void testDeletePluginVersion_OpTenantSuccess() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setCreatorId("other-user");

        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("/dsl/path");
        rv.setVersionId("v1");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "op-project-id", "ws-1")).thenReturn(pluginEntity);
        when(shareInnerService.cancelPluginVersionShared(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(true);
        when(releaseVersionMapper.selectByAppIdAndVersionId("p-1", "v1")).thenReturn(rv);
        when(releaseVersionMapper.selectByAppId("p-1")).thenReturn(List.of(rv));

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            CommonDeleteRsp result = pluginService.deletePluginVersion("op-project-id", "v1", "p-1", "ws-1");

            assertNotNull(result);
            assertEquals("p-1", result.getId());
            assertEquals("v1", result.getVersionId());
            verify(mgObsService).deleteObsFile("/dsl/path");
            verify(mappingMapper).updateValidByResourceIdAndVersionId("p-1", "v1");
            verify(releaseVersionMapper).deleteByAppIdAndVersionId("p-1", "v1");
        }
    }

    @Test
    void testDeleteTool_PluginNotExist() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.deleteTool("proj-1", "p-1", "t-1", "ws-1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testDeleteTool_Success() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("p-1");
        pluginEntity.setProjectId("proj-1");

        PluginDTO pluginDTO = new PluginDTO();
        pluginDTO.setPluginId("p-1");
        pluginDTO.setToolRequestInfo(ToolRequestInfo.builder()
            .basicInfo(BasicInfo.builder().host("host").protocol("https").build())
            .toolsInfoList(new ArrayList<>(List.of(ToolInfo.builder().toolId("0").build())))
            .build());
        pluginDTO.setToolInputSchemaList(new ArrayList<>());
        pluginDTO.setToolOutputSchemaList(new ArrayList<>());
        pluginDTO.setToolIntfTypeList(new ArrayList<>());
        pluginDTO.setToolTestStatusList(new ArrayList<>());
        pluginDTO.setIsInputList(new ArrayList<>());
        pluginDTO.setIsOutputList(new ArrayList<>());

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(pluginEntity);
        when(pluginBase.transformEntityToDTO(pluginEntity)).thenReturn(pluginDTO);

        BaseResp result = pluginService.deleteTool("proj-1", "p-1", "t-1", "ws-1");

        assertNotNull(result);
        assertEquals(200, result.getCode());
        verify(mappingMapper).updateValidByResourceIdAndVersionId("p-1#t-1", null);
    }

    @Test
    void testCheckUrl_NullRequestInfo() {
        assertDoesNotThrow(() -> pluginService.checkUrl(null, "proj-1"));
    }

    @Test
    void testCheckUrl_EmptyUrl() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("");

        assertDoesNotThrow(() -> pluginService.checkUrl(requestInfo, "proj-1"));
    }

    @Test
    void testCheckUrl_UrlWithPlaceholder() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("http://example.com/{param}");

        assertDoesNotThrow(() -> pluginService.checkUrl(requestInfo, "proj-1"));
        verify(urlCheckUtils, never()).checkUrl(anyString(), anyString());
    }

    @Test
    void testCheckUrl_ValidUrl() {
        RequestInfo requestInfo = new RequestInfo();
        requestInfo.setUrl("http://example.com/api");

        assertDoesNotThrow(() -> pluginService.checkUrl(requestInfo, "proj-1"));
        verify(urlCheckUtils).checkUrl("proj-1", "http://example.com/api");
    }

    @Test
    void testValidPlugins_Success() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setType(ToolType.INNER.type);
        pluginEntity.setWorkspaceId("ws-1");

        when(pluginMapper.selectByPrimaryKey("p-1", null)).thenReturn(pluginEntity);

        Set<String> ids = new HashSet<>();
        ids.add("p-1");
        assertDoesNotThrow(() -> pluginService.validPlugins(ids, "proj-1", "ws-1"));
    }

    @Test
    void testValidPlugins_NoPermission() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setType(ToolType.CUSTOM.type);
        pluginEntity.setWorkspaceId("other-ws");

        when(pluginMapper.selectByPrimaryKey("p-1", null)).thenReturn(pluginEntity);

        Set<String> ids = new HashSet<>();
        ids.add("p-1");
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.validPlugins(ids, "proj-1", "ws-1"));
        assertEquals(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION, ex.getErrorCode());
    }

    @Test
    void testAnonymizeAuthInfo_NullAuthInfo() {
        AuthInfo result = pluginService.anonymizeAuthInfo(null);
        assertNull(result);
    }

    @Test
    void testAnonymizeAuthInfo_ServiceScope() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setAuthKey("cipher-key");
        authInfo.setAuthKeys(List.of(keyInfo));

        when(encryptionAdapter.decrypt("cipher-key")).thenReturn("decrypted-val");

        AuthInfo result = pluginService.anonymizeAuthInfo(authInfo);
        assertNotNull(result);
        assertNotEquals("cipher-key", result.getAuthKeys().get(0).getAuthKey());
    }

    @Test
    void testAnonymizeAuthInfo_HisIamScope() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.HIS_IAM);
        HisIamInfo hisIamInfo = new HisIamInfo();
        hisIamInfo.setIamSecret("cipher-secret");
        authInfo.setHisIamInfo(hisIamInfo);

        when(encryptionAdapter.decrypt("cipher-secret")).thenReturn("decrypted-secret");

        AuthInfo result = pluginService.anonymizeAuthInfo(authInfo);
        assertNotNull(result);
        assertNotEquals("cipher-secret", result.getHisIamInfo().getIamSecret());
    }

    @Test
    void testAnonymizeAuthInfo_CustomIamScope() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.CUSTOM_IAM);
        PluginIAMAuthInfo iamInfo = new PluginIAMAuthInfo();
        iamInfo.setIamPassword("cipher-pass");
        authInfo.setCustomIamCredentials(iamInfo);

        when(encryptionAdapter.decrypt("cipher-pass")).thenReturn("decrypted-pass");

        AuthInfo result = pluginService.anonymizeAuthInfo(authInfo);
        assertNotNull(result);
        assertNotEquals("cipher-pass", result.getCustomIamCredentials().getIamPassword());
    }

    @Test
    void testEncryptedAuthInfo_ServiceScope() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setAuthKey("raw-key");
        authInfo.setAuthKeys(List.of(keyInfo));

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            when(encryptionAdapter.encrypt("raw-key", "domain-1")).thenReturn("enc-key");

            AuthInfo result = pluginService.encryptedAuthInfo(authInfo);
            assertNotNull(result);
            assertEquals("enc-key", result.getAuthKeys().get(0).getAuthKey());
        }
    }

    @Test
    void testEncryptedAuthInfo_ServiceScope_BlankKey() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setAuthKey("");
        authInfo.setAuthKeys(List.of(keyInfo));

        AuthInfo result = pluginService.encryptedAuthInfo(authInfo);
        assertNull(result);
    }

    @Test
    void testEncryptedAuthInfo_HisIamScope() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.HIS_IAM);
        HisIamInfo hisIamInfo = new HisIamInfo();
        hisIamInfo.setIamSecret("raw-secret");
        authInfo.setHisIamInfo(hisIamInfo);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            when(encryptionAdapter.encrypt("raw-secret", "domain-1")).thenReturn("enc-secret");

            AuthInfo result = pluginService.encryptedAuthInfo(authInfo);
            assertNotNull(result);
            assertEquals("enc-secret", result.getHisIamInfo().getIamSecret());
        }
    }

    @Test
    void testEncryptedAuthInfo_CustomIamScope_Password() {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.CUSTOM_IAM);
        PluginIAMAuthInfo iamInfo = new PluginIAMAuthInfo();
        iamInfo.setIamPassword("raw-pass");
        iamInfo.setIamAk("raw-ak");
        authInfo.setCustomIamCredentials(iamInfo);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            when(encryptionAdapter.encrypt("raw-pass", "domain-1")).thenReturn("enc-pass");

            AuthInfo result = pluginService.encryptedAuthInfo(authInfo);
            assertNotNull(result);
            assertEquals("enc-pass", result.getCustomIamCredentials().getIamPassword());
        }
    }



    @Test
    void testCreateTool_PluginNotExist() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        CreatePluginToolReq req = new CreatePluginToolReq();
        req.setPluginId("p-1");

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.createTool("proj-1", "ws-1", req));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testAdapterOldPlugin_FillMissingFields() {
        PluginEntity target = new PluginEntity();
        target.setPluginId("p-1");
        target.setWorkspaceId("");
        target.setType("");

        PluginEntity source = new PluginEntity();
        source.setWorkspaceId("ws-1");
        source.setType("custom");

        when(pluginMapper.selectInfo("p-1")).thenReturn(source);

        pluginService.adapterOldPlugin(target);

        assertEquals("ws-1", target.getWorkspaceId());
        assertEquals("custom", target.getType());
    }

    @Test
    void testAdapterOldPlugin_NoMissingFields() {
        PluginEntity target = new PluginEntity();
        target.setPluginId("p-1");
        target.setWorkspaceId("ws-1");
        target.setType("inner");

        PluginEntity source = new PluginEntity();
        source.setWorkspaceId("other-ws");
        source.setType("custom");

        when(pluginMapper.selectInfo("p-1")).thenReturn(source);

        pluginService.adapterOldPlugin(target);

        assertEquals("ws-1", target.getWorkspaceId());
        assertEquals("inner", target.getType());
    }

    @Test
    void testAdapterPlugin_NullAuthInfo() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("p-1");
        pluginEntity.setAuthInfo(null);

        pluginService.adapterPlugin(pluginEntity);

        verify(encryptionAdapter, never()).encrypt(anyString(), anyString());
    }

    @Test
    void testAdapterPlugin_PlaintextKey() {
        AuthInfo authInfo = new AuthInfo();
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setAuthKey("plaintext-key");
        authInfo.setAuthKeys(List.of(keyInfo));

        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("p-1");
        pluginEntity.setAuthInfo(authInfo);

        when(encryptionAdapter.decrypt("plaintext-key")).thenReturn("plaintext-key");
        when(encryptionAdapter.encrypt(eq("plaintext-key"), anyString())).thenReturn("encrypted-key");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            pluginService.adapterPlugin(pluginEntity);

            assertEquals("encrypted-key", pluginEntity.getAuthInfo().getAuthKeys().get(0).getAuthKey());
        }
    }

    @Test
    void testAdaptPluginUrlWhenCreateOrModify_TrailingSlash() {
        BasicInfo basicInfo = BasicInfo.builder().path("/api/").build();
        UrlInfo urlInfo = UrlInfo.builder().basePath("/api/").build();

        pluginService.adaptPluginUrlWhenCreateOrModify(basicInfo, urlInfo);

        assertEquals("/api", basicInfo.getPath());
    }

    @Test
    void testAdaptPluginUrlWhenCreateOrModify_NoTrailingSlash() {
        BasicInfo basicInfo = BasicInfo.builder().path("/api").build();
        UrlInfo urlInfo = UrlInfo.builder().basePath("/api").build();

        pluginService.adaptPluginUrlWhenCreateOrModify(basicInfo, urlInfo);

        assertEquals("/api", basicInfo.getPath());
    }

    @Test
    void testAdaptDescOfToolInfo_BlankEnDesc() {
        ToolInfo toolInfo = ToolInfo.builder()
            .toolDesc("中文描述")
            .toolDescEn("")
            .build();
        ToolRequestInfo toolRequestInfo = ToolRequestInfo.builder()
            .toolsInfoList(List.of(toolInfo))
            .build();

        pluginService.adaptDescOfToolInfo(toolRequestInfo);

        assertEquals("中文描述", toolRequestInfo.getToolsInfoList().get(0).getToolDescEn());
    }

    @Test
    void testAdaptDescOfToolInfo_EnDescPresent() {
        ToolInfo toolInfo = ToolInfo.builder()
            .toolDesc("中文描述")
            .toolDescEn("English desc")
            .build();
        ToolRequestInfo toolRequestInfo = ToolRequestInfo.builder()
            .toolsInfoList(List.of(toolInfo))
            .build();

        pluginService.adaptDescOfToolInfo(toolRequestInfo);

        assertEquals("English desc", toolRequestInfo.getToolsInfoList().get(0).getToolDescEn());
    }

    @Test
    void testAdaptDescOfPluginInfo_BlankEnDesc() {
        PluginDTO pluginDTO = PluginDTO.builder()
            .pluginDesc("中文描述")
            .pluginDescEn("")
            .build();

        pluginService.adaptDescOfPluginInfo(pluginDTO);

        assertEquals("中文描述", pluginDTO.getPluginDescEn());
    }

    @Test
    void testAdaptDescOfPluginInfo_EnDescPresent() {
        PluginDTO pluginDTO = PluginDTO.builder()
            .pluginDesc("中文描述")
            .pluginDescEn("English desc")
            .build();

        pluginService.adaptDescOfPluginInfo(pluginDTO);

        assertEquals("English desc", pluginDTO.getPluginDescEn());
    }

    @Test
    void testParsePlugin_BlankContent() {
        ParsePluginReq req = new ParsePluginReq();
        req.setContent("");

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.parsePlugin("proj-1", "ws-1", req));
        assertEquals(StudioError.OPENAPI_FILE_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testGenerate16BitId() {
        String id = PluginService.generate16BitId();
        assertNotNull(id);
        assertEquals(16, id.length());
    }

    @Test
    void testReleasePluginVersion_NoPermission() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setCreatorId("other-user");

        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential("p-1", "proj-1", "ws-1"))
            .thenReturn(pluginEntity);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> pluginService.releasePluginVersion("proj-1", "p-1", "ws-1", new CreateVersionReq()));
            assertEquals(StudioError.NO_CREATOR_PERMISSION, ex.getErrorCode());
        }
    }

    @Test
    void testReleasePluginVersion_ExceedMaxSize() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setCreatorId("uid-1");

        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential("p-1", "proj-1", "ws-1"))
            .thenReturn(pluginEntity);
        when(releaseVersionMapper.selectByAppId("p-1")).thenReturn(Collections.nCopies(15, new ReleaseVersion()));

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> pluginService.releasePluginVersion("proj-1", "p-1", "ws-1", new CreateVersionReq()));
            assertEquals(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT, ex.getErrorCode());
        }
    }

    @Test
    void testRetrievePlugin_PluginNotExist() {
        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential("p-1", null, "ws-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.retrievePlugin("proj-1", "p-1", "ws-1"));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testRetrievePlugin_InnerNotPublished() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setType(ToolType.INNER.type);
        pluginEntity.setWorkspaceId("other-ws");
        pluginEntity.setPublished(0);

        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential("p-1", null, "ws-1")).thenReturn(pluginEntity);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.retrievePlugin("proj-1", "p-1", "ws-1"));
        assertEquals(StudioError.PLUGIN_NO_PERMISSION_VIEW, ex.getErrorCode());
    }

    @Test
    void testRetrievePlugin_CustomNoPermission() {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setType(ToolType.CUSTOM.type);
        pluginEntity.setWorkspaceId("other-ws");

        when(pluginMapper.selectByPrimaryKeyAndWorkspaceAndCredential("p-1", null, "ws-1")).thenReturn(pluginEntity);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.retrievePlugin("proj-1", "p-1", "ws-1"));
        assertEquals(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION, ex.getErrorCode());
    }

    @Test
    void testBatchCreateTool_PluginNotExist() {
        CreatePluginToolReq toolReq = new CreatePluginToolReq();
        toolReq.setPluginId("p-1");

        BatchCreatePluginToolReq batchReq = new BatchCreatePluginToolReq();
        batchReq.setTools(List.of(toolReq));

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("p-1", "proj-1", "ws-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> pluginService.batchCreateTool("proj-1", "ws-1", batchReq));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testIncrementPluginFreeTrialUsageQuota_NoRecord() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(lock.tryLock(any())).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(redisClient.get(anyString())).thenReturn(null);

        BaseResp result = pluginService.incrementPluginFreeTrialUsageQuota("proj-1", "domain-1", "p-1", "ws-1");

        assertNotNull(result);
        assertEquals(1, result.getCode());
        verify(lock).unlock();
    }

    @Test
    void testIncrementPluginFreeTrialUsageQuota_ExceedLimit() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(lock.tryLock(any())).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(lock);
        when(redisClient.get(anyString())).thenReturn("15");

        BaseResp result = pluginService.incrementPluginFreeTrialUsageQuota("proj-1", "domain-1", "p-1", "ws-1");

        assertNotNull(result);
        assertEquals(0, result.getCode());
        verify(lock).unlock();
    }

    @Test
    void testIncrementPluginFreeTrialUsageQuota_LockFailed() throws Exception {
        RedisLock lock = mock(RedisLock.class);
        when(lock.tryLock(any())).thenReturn(false);
        when(redisClient.getLock(anyString())).thenReturn(lock);

        BaseResp result = pluginService.incrementPluginFreeTrialUsageQuota("proj-1", "domain-1", "p-1", "ws-1");

        assertNotNull(result);
        assertEquals(0, result.getCode());
        verify(lock).unlock();
    }

    @Test
    void testUpdateHost() {
        PluginDTO pluginDTO = PluginDTO.builder()
            .toolRequestInfo(ToolRequestInfo.builder()
                .basicInfo(BasicInfo.builder().host("host").protocol("https").build())
                .toolsInfoList(List.of(
                    ToolInfo.builder().toolId("0").url("http://host/api").build()
                ))
                .build())
            .build();

        pluginService.updateHost(pluginDTO);

        assertEquals("******", pluginDTO.getToolRequestInfo().getToolsInfoList().get(0).getUrl());
    }

    @Test
    void testUpdatePluginVersionByVersionId_Success() {
        String projectId = "project-123";
        String pluginId = "plugin-456";
        String versionId = "version-789";
        String workspaceId = "workspace-001";

        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId(pluginId);
        pluginEntity.setVersionId(versionId);
        pluginEntity.setPluginChineseName("Test Plugin");

        PluginDTO pluginDTO = new PluginDTO();
        pluginDTO.setPluginId(pluginId);
        pluginDTO.setVersionId(versionId);
        pluginDTO.setPluginChineseName("Test Plugin");

        when(pluginBase.getPluginEntityByVersion(pluginId, versionId)).thenReturn(pluginEntity);
        when(pluginBase.transformEntityToDTO(pluginEntity)).thenReturn(pluginDTO);
        when(pluginMapper.updateByPrimaryKeySelective(pluginEntity)).thenReturn(1);

        BaseResp result = pluginService.updatePluginVersionByVersionId(projectId, pluginId, versionId, workspaceId);

        assertEquals(200, result.getCode());
        assertEquals("success", result.getMessage());
    }

    @Test
    void testUpdatePluginVersionByVersionId_PluginNotFound() {
        String projectId = "project-123";
        String pluginId = "plugin-456";
        String versionId = "version-789";
        String workspaceId = "workspace-001";

        when(pluginBase.getPluginEntityByVersion(pluginId, versionId)).thenReturn(null);

        BaseResp result = pluginService.updatePluginVersionByVersionId(projectId, pluginId, versionId, workspaceId);

        assertEquals(200, result.getCode());
    }
}
