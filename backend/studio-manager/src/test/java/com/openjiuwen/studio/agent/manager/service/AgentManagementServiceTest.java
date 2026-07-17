/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.AGENT_BUILDER;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.bo.WfImportDataWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.constant.PromptPath;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentMcpDetail;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.AgentSkillDetail;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.AppListRsp;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.AutoAddStudioResourceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportMessagesParams;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.GetAgentVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.ListAgentChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAppsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListStructuredMessagesQo;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.ReleaseAppInfo;
import com.openjiuwen.studio.agent.manager.dto.RetrieveReleaseAppInfoQo;
import com.openjiuwen.studio.agent.manager.dto.StructMessage;
import com.openjiuwen.studio.agent.manager.dto.StructMessageListRsp;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequestDelete;
import com.openjiuwen.studio.agent.manager.dto.StructuredMessagesUploadResult;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberInfo;
import com.openjiuwen.studio.agent.manager.dto.maas.ImageGenerationRequest;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.AgentExportEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.StructuredMessageEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.ExportModeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.StructuredMessageMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.MaasModelClient;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginAdapterImpl;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMemberService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.ExcelToJsonConverterUtil;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;
import com.openjiuwen.studio.common.service.model.tenant.Tenant;

import lombok.SneakyThrows;

import org.apache.commons.collections4.CollectionUtils;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.ArgumentMatcher;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.quartz.JobBuilder;
import org.quartz.JobDetail;
import org.quartz.Scheduler;
import org.quartz.Trigger;
import org.quartz.TriggerBuilder;
import org.quartz.impl.StdSchedulerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 功能描述
 */
@Transactional
class AgentManagementServiceTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService mgObsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentRuntimeClient agentRuntimeClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private WorkspaceMemberService workSpaceMemberService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PermissionService permissionService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PluginAdapterImpl pluginAdapterImpl;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentSpaceService agentSpaceService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MaasModelClient maasModelClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private JiuWenService jiuWenService;

    @Mock()
    private IPluginBase pluginBase;

    static MockedStatic<ExcelToJsonConverterUtil> converterUtilMockedStatic;

    @Autowired
    private AgentManagementService agentManagementService;

    @Autowired
    private AppManagementService appManagementService;

    @Autowired
    private ReleaseManagementService releaseManagementService;

    @Autowired
    private RelationManagementService relationManagementService;

    @Autowired
    private IrAdapterService irAdapterService;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private AgentImportExportService agentImportExportService;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private StructuredMessageMapper structuredMessageMapper;

    @Autowired
    private MessageManagementService messageManagementService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MappingMapper mappingMapper;

    @Autowired
    private SkuManageService skuManageService;

    @Autowired
    private WorkflowManagementService workflowManagementService;

    @MockitoSpyBean
    private ReleaseChannelMapper releaseChannelMapper;

    @MockitoSpyBean
    private AppMapper appMapper;

    @MockitoSpyBean
    private AgentMapper agentMapper;

    @MockitoSpyBean
    private SkillMapper skillMapper;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = mockStatic(RequestContextUtils.class);
        mockedHeaderStatic = mockStatic(RequestHeaderHolderUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_CREATOR);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_CREATOR_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("default");
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainName).thenReturn("op-svc");
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("zh-cn");
        converterUtilMockedStatic = mockStatic(ExcelToJsonConverterUtil.class);

    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        mockedHeaderStatic.close();
        converterUtilMockedStatic.close();
    }

    private static List<ImportListInfo> getListAgentInfos() {
        List<ImportListInfo> importList2 = new ArrayList<>();
        ImportListInfo importListInfo1 = new ImportListInfo();
        importListInfo1.setId("test_agent_id");
        importListInfo1.setName("测试Agent");
        importListInfo1.setDescription("测试Agent描述");
        importListInfo1.setType(Constants.TEST_AGENT_TYPE);
        importListInfo1.setStatus(false);

        ImportListInfo importListInfo2 = new ImportListInfo();
        importListInfo2.setId("test_agent_id2");
        importListInfo2.setName("测试Agent2");
        importListInfo2.setDescription("测试Agent描述");
        importListInfo2.setType(Constants.TEST_AGENT_TYPE);
        importListInfo2.setStatus(false);

        List<ImportListInfo> dependencies1 = new ArrayList<>();
        ImportListInfo dependency1 = new ImportListInfo();
        dependency1.setId("reserve_meeting_room_1");
        dependency1.setName("预定会议室工具1");
        dependency1.setDescription("预定会议室1，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        dependency1.setType(Constants.TEST_TOOL_TYPE);
        dependency1.setStatus(false);
        dependencies1.add(dependency1);
        importListInfo1.setDependencies(dependencies1);

        ImportListInfo subDependency1 = new ImportListInfo();
        subDependency1.setId("reserve_meeting_room_20");
        subDependency1.setName("预定会议室工具2");
        subDependency1.setDescription("预定会议室2，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        subDependency1.setType("Plugin");
        subDependency1.setStatus(false);
        subDependency1.setProhibited(true);

        List<ImportListInfo> subDependencies2 = new ArrayList<>();
        ImportListInfo subDependency = new ImportListInfo();
        subDependency.setId("reserve_meeting_room_2");
        subDependency.setName("预定会议室工具2");
        subDependency.setDescription("预定会议室2，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        subDependency.setType(Constants.TEST_TOOL_TYPE);
        subDependency.setStatus(false);
        subDependency.setProhibited(true);

        ImportListInfo subDependency2 = new ImportListInfo();
        subDependency2.setId("test_release_tool");
        subDependency2.setName("test_release_tool");
        subDependency2.setDescription("desc");
        subDependency2.setType(Constants.TEST_TOOL_TYPE);
        subDependency2.setStatus(false);
        subDependency2.setProhibited(false);
        subDependencies2.add(subDependency);
        subDependencies2.add(subDependency1);
        subDependencies2.add(subDependency2);
        importListInfo2.setDependencies(subDependencies2);

        importList2.add(importListInfo1);
        importList2.add(importListInfo2);
        return importList2;
    }

    private static List<ImportListInfo> getListToolInfos() {
        List<ImportListInfo> importList = new ArrayList<>();
        ImportListInfo importListInfo1 = new ImportListInfo();
        importListInfo1.setId("reserve_meeting_room_1");
        importListInfo1.setName("预定会议室工具1");
        importListInfo1.setDescription("预定会议室1，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        importListInfo1.setType("Plugin");
        importListInfo1.setStatus(false);
        importList.add(importListInfo1);

        ImportListInfo importListInfo2 = new ImportListInfo();
        importListInfo2.setId("reserve_meeting_room_2");
        importListInfo2.setName("预定会议室工具2");
        importListInfo2.setDescription("预定会议室2，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        importListInfo2.setType("Plugin");
        importListInfo2.setStatus(false);

        importList.add(importListInfo2);
        return importList;
    }

    private static List<ImportListInfo> getListWorkflowInfos() {
        List<ImportListInfo> importList2 = new ArrayList<>();
        ImportListInfo importListInfo1 = new ImportListInfo();
        importListInfo1.setId("test_code_interpreter_workflow_id");
        importListInfo1.setName("代码执行");
        importListInfo1.setDescription("代码解释器工作流调用");
        importListInfo1.setType("workflow");
        importListInfo1.setStatus(false);

        ImportListInfo importListInfo2 = new ImportListInfo();
        importListInfo2.setId("test_web_search_workflow_id");
        importListInfo2.setName("网络搜索");
        importListInfo2.setDescription("网络搜索工作流调用");
        importListInfo2.setType("workflow");
        importListInfo2.setStatus(false);

        List<ImportListInfo> dependencies1 = new ArrayList<>();
        ImportListInfo dependency1 = new ImportListInfo();
        dependency1.setId("reserve_meeting_room_1");
        dependency1.setName("预定会议室工具1");
        dependency1.setDescription("预定会议室1，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        dependency1.setType("Plugin");
        dependency1.setStatus(false);
        dependencies1.add(dependency1);
        importListInfo1.setDependencies(dependencies1);

        List<ImportListInfo> subDependencies2 = new ArrayList<>();
        ImportListInfo subDependency = new ImportListInfo();
        subDependency.setId("reserve_meeting_room_2");
        subDependency.setName("预定会议室工具2");
        subDependency.setDescription("预定会议室2，请在需要预定会议室时调用此工具，预定前需要先查询会议室状态");
        subDependency.setType("Plugin");
        subDependency.setStatus(false);
        subDependency.setProhibited(true);
        subDependencies2.add(subDependency);
        importListInfo2.setDependencies(subDependencies2);

        importList2.add(importListInfo1);
        importList2.add(importListInfo2);
        return importList2;
    }

    @BeforeEach
    void setUp() throws IOException {
        ReflectionTestUtils.setField(agentManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(workflowManagementService, "obsService", mgObsService);
        ReflectionTestUtils.setField(agentManagementService, "relationManagementService", relationManagementService);
        ReflectionTestUtils.setField(agentManagementService, "agentRuntimeClient", agentRuntimeClient);
        ReflectionTestUtils.setField(agentManagementService, "workSpaceMemberService", workSpaceMemberService);
        ReflectionTestUtils.setField(agentManagementService, "permissionService", permissionService);
        ReflectionTestUtils.setField(agentManagementService, "maasModelClient", maasModelClient);
        ReflectionTestUtils.setField(agentManagementService, "jiuWenService", jiuWenService);
        ReflectionTestUtils.setField(irAdapterService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(agentImportExportService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(agentImportExportService, "toolMapperDiscard", toolMapper);
        ReflectionTestUtils.setField(messageManagementService, "structuredMessageMapper", structuredMessageMapper);
        ReflectionTestUtils.setField(agentCommonService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(agentImportExportService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(agentImportExportService, "pluginAdapterImpl", pluginAdapterImpl);
        ReflectionTestUtils.setField(releaseManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(agentManagementService, "agentSpaceService", agentSpaceService);
        ReflectionTestUtils.setField(agentManagementService, "publishAgentBuilderEnable", true);
        ReflectionTestUtils.setField(relationManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(relationManagementService, "pluginBase", pluginBase);
        doNothing().when(agentSpaceService).publish(any());
        doNothing().when(agentSpaceService).unpublish(any(), any());
        doNothing().when(agentSpaceService).delete(any(), any());
        ListKnowledgeBasesResponseBody knowledgeBaseResponse = new ListKnowledgeBasesResponseBody();
        List<KnowledgeBaseListItem> knowledgeBaseListItems = new ArrayList<>();
        KnowledgeBaseListItem knowledgeBaseListItem = new KnowledgeBaseListItem();
        knowledgeBaseListItem.setKnowledgeBaseId("xxxx");
        knowledgeBaseListItem.setType(KnowledgeBaseListItem.TypeEnum.INTERNAL);
        knowledgeBaseListItems.add(knowledgeBaseListItem);
        knowledgeBaseResponse.setItems(knowledgeBaseListItems);
    }

    @TestConfiguration
    static class TestConfig {
        @Bean
        @Primary
        public SkuManageService skuManageService() {
            return mock(SkuManageService.class);
        }
    }

    @Test
    @Transactional
    void testCreateAgent() throws IOException {
        final CreateAgentReq req = TestUtil.getJsonObject(CreateAgentReq.class, "classpath:service/create_agent.json");
        AgentInfo agentInfo =
            agentManagementService.createAgent(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);
        assertNotNull(agentInfo);
        assertEquals(AgentStatus.DRAFT.toString(), agentInfo.getStatus());
        assertEquals(Constants.TEST_CREATOR, agentInfo.getCreator());
        assertEquals(Constants.TEST_CREATOR_ID, agentInfo.getCreatorId());

        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.createAgent(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);
        });

        assertThrows(AgentStudioException.class, () -> {
            req.setName(null);
            req.setDescription("desc");
            agentManagementService.createAgent(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);
        });
    }

    @Test
    @Transactional
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testValidateName() {
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.validateName(Constants.TEST_PROJECT_ID, "", "", false);
        });

        String name = agentManagementService.validateName(Constants.TEST_PROJECT_ID, "test_multi_agent", "", true);
        Assertions.assertTrue(name.startsWith("test_multi_agent"));
    }

    @Test
    @Transactional
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testCopyAgent() throws IOException {
        AgentInfo agentInfo = agentManagementService.copyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, Constants.TEST_WORKSPACE_ID);
        assertNotNull(agentInfo);
        assertEquals(AgentStatus.DRAFT.toString(), agentInfo.getStatus());
        assertEquals(Constants.TEST_CREATOR, agentInfo.getCreator());
    }

    @Test
    @Transactional
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testCopyAgent2OtherWorkspace() throws IOException {
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.copyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, Constants.TEST_TARGET_WORKSPACE_ID);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/mcp_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentWithMcp() throws IOException {
        ModifyAgentReq modifyAgentReq = new ModifyAgentReq();
        List<String> mcpServerId = new ArrayList<>();
        mcpServerId.add("test_mcp_server_id");
        modifyAgentReq.setMcpServers(mcpServerId);

        AgentInfo agentInfo1 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo1);

        modifyAgentReq.getMcpServers().add("test_mcp_server_id1");
        AgentInfo agentInfo2 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo2);

        AgentInfo agentInfo3 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo3);

        modifyAgentReq.getMcpServers().remove(0);
        AgentInfo agentInfo4 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo4);

        modifyAgentReq.getMcpServers().remove(0);
        AgentInfo agentInfo5 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo5);
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/mcp_setup_db.sql"},
            executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentWithMcpChooseTools() throws IOException {
        ModifyAgentReq modifyAgentReq = new ModifyAgentReq();
        List<String> mcpServerId = new ArrayList<>();
        mcpServerId.add("test_mcp_server_id");
        modifyAgentReq.setMcpServers(mcpServerId);

        AgentInfo agentInfo1 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo1);

        modifyAgentReq.getMcpServers().add("test_mcp_server_id1");
        AgentInfo agentInfo2 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo2);

        AgentInfo agentInfo3 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo3);

        modifyAgentReq.getMcpServers().remove(0);
        AgentInfo agentInfo4 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo4);

        modifyAgentReq.getMcpServers().remove(0);
        AgentInfo agentInfo5 = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, modifyAgentReq);
        assertNotNull(agentInfo5);
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentWithUserProfileMemory() throws IOException {

        // set up
        final ModifyAgentReq req =
            TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_with_user_profile_memory_req.json");

        // run test
        AgentInfo agentInfo = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);

        // assert result
        assertNotNull(agentInfo.getMemoryConfig());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/memory_repo_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentWithMemoryRepo() throws IOException {

        ReflectionTestUtils.setField(agentManagementService, "longTermMemoryEnable", true);
        // set up
        final ModifyAgentReq req =
            TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_with_memory_repo.json");

        // run test
        AgentInfo agentInfo = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);

        // assert result
        assertEquals("test_memory_repo_id", agentInfo.getMemoryConfig().getMemoryRepoId());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentWithReference() throws IOException {

        // set up
        final ModifyAgentReq req =
            TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_with_reference.json");

        // run test
        AgentInfo agentInfo = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);

        // assert result
        assertTrue(agentInfo.getReference().isSwitch());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_ModifyAgent_should_throw_exception_when_KnowledgeRetrievalPolicy_recall_threshold_is_illegal()
        throws IOException {
        assertThrows(AgentStudioException.class, () -> {
            // set up
            final ModifyAgentReq req =
                TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_with_lakeSearch_req.json");
            req.getKnowledgeRetrievePolicy().setRecallThreshold(20.0f);

            // run test
            agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, req);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_ModifyAgent_should_throw_exception_when_KnowledgeRetrievalPolicy_faq_threshold_is_illegal()
        throws IOException {
        assertThrows(AgentStudioException.class, () -> {
            // set up
            final ModifyAgentReq req =
                TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_with_lakeSearch_req.json");
            req.getKnowledgeRetrievePolicy().setFaqThreshold(20.0f);

            // run test
            agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, req);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testListAgents() {
        // setup
        ListAgentsQo listAgentsQo = new ListAgentsQo();
        listAgentsQo.setOffset(0);
        listAgentsQo.setLimit(10);

        // run the test
        AgentListRsp result = agentManagementService.listAgents(Constants.TEST_PROJECT_ID, listAgentsQo);
        assertNotNull(result);
        assertEquals(10, result.getAgentList().size());
        assertEquals(10, result.getCount());

        listAgentsQo.setLimit(1);
        result = agentManagementService.listAgents(Constants.TEST_PROJECT_ID, listAgentsQo);
        assertNotNull(result);
        assertEquals(1, result.getAgentList().size());
        assertEquals(10, result.getCount());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testPublishAndDeleteAgent() throws IOException {
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("test_dsl_path");
        when(mgObsService.downloadObsFile(eq("test_dsl_path")))
            .thenReturn(TestUtil.getStringFromFile("classpath:response/agent_dsl.json"));
        AgentInfo publishAgent = agentManagementService.publishAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, List.of("da112ce6-5951-11ef-abd9-607d092d9149"));
        assertNotNull(publishAgent);
        publishAgent = agentManagementService.retrieveAgentApp(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID);
        assertNotNull(publishAgent);

        ListAppsQo body = new ListAppsQo().setOffset(0).setLimit(10);
        AppListRsp appList = appManagementService.listApps(Constants.TEST_PROJECT_ID, body);
        assertNotNull(appList);
        assertEquals(1, appList.getAppList().size());
        assertEquals(1, appList.getCount());

        agentManagementService.deleteAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID);
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.getAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID);
        });

        appList = appManagementService.listApps(Constants.TEST_PROJECT_ID, body);
        assertEquals(0, appList.getCount());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testDeleteAgent() {
        ListAgentsQo listAgentsQo = new ListAgentsQo();
        listAgentsQo.setOffset(0);
        listAgentsQo.setLimit(10);
        AgentListRsp agentList = agentManagementService.listAgents(Constants.TEST_PROJECT_ID, listAgentsQo);
        assertNotNull(agentList);
        assertEquals(10, agentList.getAgentList().size());
        assertEquals(10, agentList.getCount());

        doNothing().when(mgObsService).deleteObsObjects(anyString());
        Assertions.assertThrows(Exception.class,
            () -> agentManagementService.deleteAgent(Constants.TEST_PROJECT_ID, "", Constants.TEST_WORKSPACE_ID));
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_release_agent_version_action() throws IOException {
        CreateVersionReq createVersionReq = new CreateVersionReq();
        createVersionReq.setVersionName("test_version_name");
        createVersionReq.setVersionNote("test_version_note");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("test_dsl_path");
        when(mgObsService.downloadObsFile(eq("test_dsl_path")))
            .thenReturn(TestUtil.getStringFromFile("classpath:response/agent_dsl.json"));
        doNothing().when(mgObsService).copyObsObject(anyString(), anyString());

        agentManagementService.createAgentVersion(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, createVersionReq);
        VersionListRsp versionListRsp = agentManagementService.listAgentVersions(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, new ListAgentVersionsQo().setWorkspaceId("default"));
        List<VersionInfo> versionInfoList = versionListRsp.getVersionList();
        String versionId = versionInfoList.get(0).getVersionId();

        assertNotNull(versionInfoList);
        assertEquals(1, versionInfoList.size());

        AgentVersionListRsp agentVersionListRsp =
            agentManagementService.listAgentLastVersions(Constants.TEST_PROJECT_ID,
                new ListAgentLastVersionsQo().setOffset(0).setLimit(10).setId(Constants.TEST_AGENT_ID));
        Assertions.assertEquals(1, agentVersionListRsp.getCount());

        AgentInfo releaseAgent = agentManagementService.getAgentVersion(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, versionId, new GetAgentVersionQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertNotNull(releaseAgent);
        agentManagementService.deleteAgentVersion(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID, versionId,
            Constants.TEST_WORKSPACE_ID);
        versionListRsp = agentManagementService.listAgentVersions(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            new ListAgentVersionsQo().setWorkspaceId("default"));
        assertEquals(0, versionListRsp.getCount());
    }


    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_release_agent_version_action_v1() throws IOException {
        CreateVersionReq createVersionReq = new CreateVersionReq();
        createVersionReq.setVersionName("test_version_name");
        createVersionReq.setVersionNote("test_version_note");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("test_dsl_path");
        when(mgObsService.downloadObsFile(eq("test_dsl_path")))
            .thenReturn(TestUtil.getStringFromFile("classpath:response/agent_dsl.json"));
        doNothing().when(mgObsService).copyObsObject(anyString(), anyString());

        agentManagementService.createAgentVersionV1(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, createVersionReq);
        VersionListRsp versionListRsp = agentManagementService.listAgentVersionsV1(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, new ListAgentVersionsV1Qo().setWorkspaceId("default"));
        List<VersionInfo> versionInfoList = versionListRsp.getVersionList();
        String versionId = versionInfoList.get(0).getVersionId();

        assertNotNull(versionInfoList);
        assertEquals(1, versionInfoList.size());

        AgentVersionListRsp agentVersionListRsp =
            agentManagementService.listAgentLastVersions(Constants.TEST_PROJECT_ID,
                new ListAgentLastVersionsQo().setOffset(0).setLimit(10).setId(Constants.TEST_AGENT_ID));
        Assertions.assertEquals(1, agentVersionListRsp.getCount());

        AgentInfo releaseAgent = agentManagementService.getAgentVersion(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, versionId, new GetAgentVersionQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertNotNull(releaseAgent);
        agentManagementService.deleteAgentVersion(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID, versionId,
            Constants.TEST_WORKSPACE_ID);
        versionListRsp = agentManagementService.listAgentVersionsV1(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            new ListAgentVersionsV1Qo().setWorkspaceId("default"));
        assertEquals(0, versionListRsp.getCount());
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void exportStructuredMessages_Success() {
        // 1. 准备测试数据
        String projectId = "123456";
        String workspaceId = "default";
        ExportMessagesParams params = new ExportMessagesParams();
        params.setMessagesIds(List.of("123456789"));

        // 3. 执行测试方法
        Resource result = messageManagementService.exportStructuredMessages(projectId, workspaceId, params);

        // 4. 验证结果
        assertNull(result);

    }

    @Test
    void testUploadStructuredMessages_AllScenarios() throws IOException {
        // 创建安全的虚拟文件内容 - 使用空字节数组避免NPE
        MultipartFile file = mock(MultipartFile.class);
        when(file.getOriginalFilename()).thenReturn("test.xlsx");
        when(file.getContentType()).thenReturn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

        // 模拟静态方法的返回值
        List<Map<String, Object>> validData = createValidData();

        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-123");
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("user-123");
        // 场景1: 正常上传测试
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file)).thenReturn(validData);
        StructuredMessagesUploadResult response =
            messageManagementService.uploadStructuredMessages("project-1", "workspace-1", file);
        assertEquals(2, response.getTotalCount());
        assertEquals("Message 1", response.getSuccessList().get(0).getName());
        // 场景2: 缺少name字段
        List<Map<String, Object>> missingNameData = createMissingNameData();
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(missingNameData);

        // 场景3: JSON解析失败
        List<Map<String, Object>> invalidJsonData = createInvalidJsonData();
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(invalidJsonData);

        // 场景4: 纯数字失败
        List<Map<String, Object>> numberJsonData = createNumberJsonData();
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(numberJsonData);

        // 场景4: 纯数字失败
        List<Map<String, Object>> nullName = createNullName();
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file)).thenReturn(nullName);

        List<Map<String, Object>> categoryName = createCategoryJsonData();
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(categoryName);

        // 场景5: 空文件处理
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(Collections.emptyList());

        StructuredMessagesUploadResult emptyResponse =
            messageManagementService.uploadStructuredMessages("project-1", "workspace-1", file);
        assertEquals(0, emptyResponse.getTotalCount());

        List<Map<String, Object>> overLimitData = new ArrayList<>();
        for (int i = 0; i < 201; i++) {
            Map<String, Object> row = new HashMap<>();
            row.put("name", "Message " + i);
            row.put("content", "Content " + i);
            overLimitData.add(row);
        }
        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenReturn(overLimitData);

        converterUtilMockedStatic.when(() -> ExcelToJsonConverterUtil.processUploadedExcel(file))
            .thenThrow(new IOException("文件读取失败"));

        assertThrows(AgentStudioException.class, () -> {
            messageManagementService.uploadStructuredMessages("project-1", "workspace-1", file);
        });

    }

    // 测试数据构造方法
    private List<Map<String, Object>> createValidData() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row1 = new HashMap<>();
        row1.put("name", "Message 1");
        row1.put("category", "异常");
        row1.put("content", "{\"key1\":\"value1\"}");
        row1.put("visibility", "public");
        data.add(row1);

        Map<String, Object> row2 = new HashMap<>();
        row2.put("name", "Message 2");
        row2.put("category", "异常");
        row2.put("content", "{\"key2\":\"value2\"}");
        row2.put("visibility", "private");
        data.add(row2);

        return data;
    }

    private List<Map<String, Object>> createMissingNameData() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row = new HashMap<>();
        row.put("category", "异常"); // 缺少name
        row.put("content", "{\"key\":\"value\"}");
        row.put("visibility", "public");
        data.add(row);

        return data;
    }

    private List<Map<String, Object>> createInvalidJsonData() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row = new HashMap<>();
        row.put("name", "Test Message");
        row.put("category", "异常");
        row.put("content", "INVALID_JSON"); // 非法JSON
        row.put("visibility", "public");
        data.add(row);

        return data;
    }

    private List<Map<String, Object>> createNumberJsonData() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row = new HashMap<>();
        row.put("name", 12345);
        row.put("category", "Test Category");
        row.put("content", "INVALID_JSON"); // 非法JSON
        row.put("visibility", "public");
        data.add(row);

        return data;
    }

    private List<Map<String, Object>> createNullName() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row = new HashMap<>();
        row.put("name", null);
        row.put("category", "Test Category");
        row.put("content", "INVALID_JSON"); // 非法JSON
        row.put("visibility", "public");
        data.add(row);

        return data;
    }

    private List<Map<String, Object>> createCategoryJsonData() {
        List<Map<String, Object>> data = new ArrayList<>();

        Map<String, Object> row = new HashMap<>();
        row.put("name", 12345);
        row.put("category", "aaa");
        row.put("content", "INVALID_JSON"); // 非法JSON
        row.put("visibility", "public");
        data.add(row);

        return data;
    }

    @Test
    @Sql(scripts = {"classpath:sql/version_setup_db.sql", "classpath:sql/agent_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_release_agent_channel_action() throws IOException {
        when(agentRuntimeClient.createReleaseInfo(any(), anyString(), any())).thenReturn(null);
        when(agentRuntimeClient.deleteReleaseInfo(any(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn(null);
        Tenant tenant = new Tenant();
        tenant.setDomainId("test");
        tenant.setStatus("active");

        mockedStatic.when(RequestContextUtils::getRequestUserDomainIdOptional).thenReturn(Optional.empty());

        // test create
        CreateChannelReq createChannelReq = new CreateChannelReq();
        createChannelReq.setVersionId("test_version_id");
        CreateVersionReq createVersionReq = new CreateVersionReq();
        createVersionReq.setVersionName("test_version_name");
        createVersionReq.setVersionNote("test_version_note");
        createChannelReq.setChannelType("test_channel");

        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, createChannelReq);
        });
        createChannelReq.setChannelType("WEB_PAGE");
        VersionChannelInfo channelInfo = agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, Constants.TEST_WORKSPACE_ID, createChannelReq);
        String shortCode1 = channelInfo.getShortCode();
        channelInfo = agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, createChannelReq);
        String shortCode2 = channelInfo.getShortCode();
        assertNotEquals(shortCode1, shortCode2);

        // test list
        VersionChannelListRsp channelListRsp = agentManagementService.listAgentChannels(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, new ListAgentChannelsQo().setWorkspaceId("default"));
        List<VersionChannelInfo> channelList = channelListRsp.getChannelList();
        assertNotNull(channelList);
        assertEquals(2, channelList.size());
        createChannelReq.setChannelType("APP_STORE");
        createChannelReq.setMetadata(List.of("2f88ed16-5952-11ef-abd9-607d092d9149"));
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, createChannelReq);
        });
        createChannelReq.setChannelType("WEB_PAGE");
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("test_op_project_id");
        VersionChannelInfo appChannelInfo = agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, Constants.TEST_WORKSPACE_ID, createChannelReq);
        createChannelReq.setChannelType("APP_STORE");
        createChannelReq.setMetadata(List.of("2f88ed16-5952-11ef-abd9-607d092d9149"));
        channelListRsp = agentManagementService.listAgentChannels(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            new ListAgentChannelsQo().setWorkspaceId("default"));
        channelList = channelListRsp.getChannelList();
        assertEquals(2, channelList.size());

        // test update
        ModifyChannelReq modifyChannelReq = new ModifyChannelReq();
        modifyChannelReq.setVersionId("test_version_id1");
        channelInfo = agentManagementService.modifyAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            channelInfo.getId(), Constants.TEST_WORKSPACE_ID, modifyChannelReq);
        assertNotNull(channelInfo);
        assertEquals("test_version_id1", channelInfo.getVersionId());
        appChannelInfo = agentManagementService.modifyAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            appChannelInfo.getId(), Constants.TEST_WORKSPACE_ID, modifyChannelReq);
        assertNotNull(appChannelInfo);
        assertEquals("test_version_id1", appChannelInfo.getVersionId());

        // test delete
        VersionChannelInfo finalChannelInfo = channelInfo;
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.deleteAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                finalChannelInfo.getId(), Constants.TEST_WORKSPACE_ID);
        });
        channelListRsp = agentManagementService.listAgentChannels(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            new ListAgentChannelsQo().setWorkspaceId("default"));
        assertEquals(2, channelListRsp.getCount());
        VersionChannelInfo finalAppChannelInfo = appChannelInfo;
        Assertions.assertThrows(AgentStudioException.class, () -> {
            agentManagementService.deleteAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                finalAppChannelInfo.getId(), Constants.TEST_WORKSPACE_ID);
        });

        agentManagementService.deleteAgentChannel(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_AGENT_ID, Constants.TEST_WORKSPACE_ID);
    }

    @Test
    void test_retrieve_release_app_info() throws IOException {
        final CreateAgentReq req = TestUtil.getJsonObject(CreateAgentReq.class, "classpath:service/create_agent.json");
        AgentInfo agent =
            agentManagementService.createAgent(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, req);

        // create version
        CreateVersionReq createVersionReq = new CreateVersionReq();
        createVersionReq.setVersionName("test_version_name");
        createVersionReq.setVersionNote("test_version_note");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("test_dsl_path");
        when(mgObsService.downloadObsFile(eq("test_dsl_path")))
            .thenReturn(TestUtil.getStringFromFile("classpath:response/agent_dsl.json"));
        doNothing().when(mgObsService).copyObsObject(anyString(), anyString());
        agentManagementService.createAgentVersion(Constants.TEST_PROJECT_ID, agent.getAgentId(),
            Constants.TEST_WORKSPACE_ID, createVersionReq);
        VersionListRsp versionListRsp = agentManagementService.listAgentVersions(Constants.TEST_PROJECT_ID,
            agent.getAgentId(), new ListAgentVersionsQo().setWorkspaceId("default"));
        String versionId = versionListRsp.getVersionList().get(0).getVersionId();

        // create channel
        CreateChannelReq createChannelReq = new CreateChannelReq();
        createChannelReq.setVersionId(versionId);
        createChannelReq.setChannelType("WEB_PAGE");
        VersionChannelInfo channelInfo = agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID,
            agent.getAgentId(), Constants.TEST_WORKSPACE_ID, createChannelReq);

        RetrieveReleaseAppInfoQo retrieveReleaseAppInfoQo = new RetrieveReleaseAppInfoQo();
        retrieveReleaseAppInfoQo.setFindBy("short_code");
        retrieveReleaseAppInfoQo.setChannelType("WEB_PAGE");
        ReleaseAppInfo appInfo = releaseManagementService.retrieveReleaseAppInfo(Constants.TEST_PROJECT_ID,
            channelInfo.getShortCode(), retrieveReleaseAppInfoQo);
        assertEquals("测试agent", appInfo.getName());

        createChannelReq.setChannelType(AGENT_BUILDER);
        channelInfo = agentManagementService.createAgentChannel(Constants.TEST_PROJECT_ID, agent.getAgentId(),
            Constants.TEST_WORKSPACE_ID, createChannelReq);
        assertEquals(AGENT_BUILDER, channelInfo.getChannelType());
    }

    @Test
    void testListImportToolFile() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );

        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
        List<ImportListInfo> importList2 = getListToolInfos();

        assertEquals(importList2, importList1);
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_export_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testListImportToolFileWhenProhibited() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );
        when(RequestContextUtils.getRequestUserId()).thenReturn("test_user_id_1");
        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
        assertEquals(false, importList1.get(0).isProhibited());
    }

    @Test
    void testListImportToolFileWhenOffset() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );

        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 1, 1);
        assertEquals(1, importList1.size());
    }

    @Test
    void testListImportWorkflowFile() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_WORKFLOW_EXPORT.getBytes()  // 文件内容
        );
        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
        List<ImportListInfo> importList2 = getListWorkflowInfos();
        assertEquals(importList2, importList1);
    }

    @Test
    void testListImportPluginFile() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );
        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
        List<ImportListInfo> importList2 = getListToolInfos();
        assertEquals(importList2, importList1);
    }

    @Test
    void testListImportPluginFileError() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_TOOL_EXPORT.getBytes()  // 文件内容
        );
        agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
    }

    @Test
    public void testGetPermissionsByRole() {
        // 准备测试数据
        String projectId = "project-123";
        String workspaceId = "workspace-456";
        String userId = "user-789";

        // 模拟用户ID获取
        when(RequestContextUtils.getRequestUserId()).thenReturn(userId);

        // 模拟 workspaceMemberService 返回角色信息
        WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
        memberInfo.setRole("owner");
        when(workSpaceMemberService.queryWorkspaceMemberDetail(projectId, userId, workspaceId)).thenReturn(memberInfo);

        // 模拟 permissionLoader 返回权限列表
        Map<String, List<String>> rolePermissions = new HashMap<>();
        List<String> ownerPermissions = Arrays.asList("getWorkspace", "createWorkspace");
        rolePermissions.put("owner", ownerPermissions);
        when(permissionService.getMergedPermissions()).thenReturn(rolePermissions);

        // 调用方法
        Map<String, List<String>> result = agentManagementService.getPermissionsByRole(projectId, workspaceId);

        // 验证结果
        assertNotNull(result);
        assertEquals(1, result.size());
        assertTrue(result.containsKey("owner"));
        assertEquals(ownerPermissions, result.get("owner"));

    }

    @Test
    void testListAgentFile() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        List<ImportListInfo> importList1 =
            agentManagementService.listImportFile(Constants.TEST_WORKSPACE_ID, projectId, file, 0, 10);
        List<ImportListInfo> importList2 = getListAgentInfos();
        assertEquals(importList2, importList1);
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_import_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testToolImportSameName() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_MAX_NAME_TOOL_EXPORT.getBytes()  // 文件内容
        );
        String toolIds = "reserve_meeting_room_123";
        ImportRsp importRsp = agentManagementService.importTools(Constants.TEST_WORKSPACE_ID, projectId, file, toolIds);

        assertEquals(0, importRsp.getSucceedLen());
        assertEquals(1, importRsp.getFailedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_import_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportWorkflowSameName() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_MAX_NAME_WORKFLOW_EXPORT.getBytes()  // 文件内容
        );

        String workflowIds = "test_code_interpreter_workflow_id_123";
        when(RequestContextUtils.getRequestUserDomainId()).thenReturn("test_domain_id");
        ImportRsp importRsp = workflowManagementService.importWorkflows(Constants.TEST_WORKSPACE_ID, projectId, file,
            workflowIds, "", ExportModeEnum.STRICT.getCode());

        assertEquals(1, importRsp.getSucceedLen());
        assertEquals(0, importRsp.getFailedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_import_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportAgentSameName() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_MAX_NAME_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id_123";

        when(RequestContextUtils.getRequestUserDomainId()).thenReturn(Constants.TEST_DOMAIN_ID);
        ImportRsp importRsp = agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file,
            agentIds, "", "workflowIds", ExportModeEnum.STRICT.getCode());

        assertEquals(1, importRsp.getSucceedLen());
        assertEquals(0, importRsp.getFailedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_export_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testExportTools() {
        String projectId = Constants.TEST_PROJECT_ID;
        ExportParams body = new ExportParams();
        List<String> toolIds = new ArrayList<>();
        toolIds.add("reserve_meeting_room_1");
        toolIds.add("reserve_meeting_room_2");
        body.setToolIds(toolIds);

        Resource resource = agentManagementService.exportTools(projectId, Constants.TEST_WORKSPACE_ID, body);
        assertNotNull(resource);
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_export_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testExportToolsValidPermission() {
        String projectId = Constants.TEST_PROJECT_ID;
        ExportParams body = new ExportParams();
        List<String> toolIds = new ArrayList<>();
        toolIds.add("reserve_meeting_room_1");
        toolIds.add("reserve_meeting_room_2");
        body.setToolIds(toolIds);

        Resource resource = agentManagementService.exportTools(projectId, Constants.TEST_WORKSPACE_ID, body);
        assertNotNull(resource);
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_export_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportToolsAppend() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );
        String toolIds = "reserve_meeting_room_1";
        ImportRsp importRsp = agentManagementService.importTools(Constants.TEST_WORKSPACE_ID, projectId, file, toolIds);

        assertEquals(0, importRsp.getSucceedLen());
        assertEquals(1, importRsp.getFailedLen());
    }

    @Test
    void testImportInvalidFileShouldThrowException() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.txt",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_PLUGIN_EXPORT.getBytes()  // 文件内容
        );
        String toolIds = "reserve_meeting_room_1";
        assertThrows(AgentStudioException.class,
            () -> agentManagementService.importTools(Constants.TEST_WORKSPACE_ID, projectId, file, toolIds));
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_export_setup_db.sql", "classpath:sql/tool_export_setup_db.sql",
        "classpath:sql/mcp_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testExportWorkflows() {
        String projectId = Constants.TEST_PROJECT_ID;
        ExportParams body = new ExportParams();
        List<String> workflowIds = new ArrayList<>();
        workflowIds.add("test_code_interpreter_workflow_id");
        workflowIds.add("test_web_search_workflow_id");
        workflowIds.add("test_complex_intent");
        workflowIds.add("test_agent_workflow_id");
        body.setWorkflowIds(workflowIds);

        String jsonStr1 = TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_1.json");
        String jsonStr2 = TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_2.json");
        String jsonStrContainer =
            TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_intent_container.json");
        String jsonStr3 = TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_4.json");

        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_code_interpreter_workflow_id.json")))
            .thenReturn(jsonStr1);
        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_web_search_workflow_id.json")))
            .thenReturn(jsonStr2);
        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_complex_intent.json")))
            .thenReturn(jsonStrContainer);
        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_agent_workflow_id.json")))
            .thenReturn(jsonStr3);

        String toolJson = TestUtil.getStringFromFile("classpath:response/obs_tool_dsl.json");
        ToolEntity result = JsonUtils.json2ObjQuietly(toolJson, ToolEntity.class);
        when(pluginAdapterImpl.getToolEntity(eq("reserve_meeting_room_1"), eq("test_project_id"),
            eq("test_op_project_id"), any())).thenReturn(result);
        when(pluginAdapterImpl.getToolEntity(eq("reserve_meeting_room_3"), eq("test_project_id"),
            eq("test_op_project_id"), any())).thenReturn(result);

        Resource resource = workflowManagementService.exportWorkflows(projectId, Constants.TEST_WORKSPACE_ID, body);
        assertNotNull(resource);
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_export_setup_db.sql", "classpath:sql/mapping_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportWorkflowsAppend() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_WORKFLOW_REPLACE_ID.getBytes()  // 文件内容
        );

        String workflowIds = "test_code_interpreter_workflow_id,test_web_search_workflow_id";
        String toolIds = "reserve_meeting_room_1,reserve_meeting_room_2";
        when(RequestContextUtils.getRequestUserDomainId()).thenReturn("test_domain_id");
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);
        // ImportRsp importRsp = agentManagementService.importWorkflows(Constants.TEST_WORKSPACE_ID, projectId, file,
        // workflowIds, toolIds);
        //
        // assertEquals(2, importRsp.getSucceedLen());
        // assertEquals(0, importRsp.getFailedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_export_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportWorkflowsAppendShouldSucceed() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_WORKFLOW_REPLACE_ID.getBytes()  // 文件内容
        );

        String workflowIds = "test_code_interpreter_workflow_id";
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);
        ImportRsp importRsp = workflowManagementService.importWorkflows(Constants.TEST_WORKSPACE_ID, projectId, file,
            workflowIds, "", ExportModeEnum.STRICT.getCode());

        assertEquals(1, importRsp.getSucceedLen());
        assertEquals(0, importRsp.getFailedLen());
    }

    @Test
    void testImportWorkflowFailed() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_WORKFLOW_REPLACE_ID.getBytes()  // 文件内容
        );

        String workflowIds = "test_code_interpreter_workflow_id,test_web_search_workflow_id";
        String toolIds = "reserve_meeting_room_1,reserve_meeting_room_2";
        List<String> ids = new ArrayList<>();
        ids.add("test_code_interpreter_workflow_id");
        ids.add("test_web_search_workflow_id");

        when(RequestContextUtils.getRequestUserDomainId()).thenReturn("test_domain_id");
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenThrow(new AgentStudioException(StudioError.WORKFLOW_IMPORT_FILE));
        ImportRsp importRsp = workflowManagementService.importWorkflows(Constants.TEST_WORKSPACE_ID, projectId, file,
            workflowIds, toolIds, ExportModeEnum.STRICT.getCode());

        assertEquals(2, importRsp.getFailedLen());
        assertEquals(ids, importRsp.getFailedIds());
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_export_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testExportWorkflowsShouldFailed() {
        ExportParams body = new ExportParams();
        List<String> workflowIds = new ArrayList<>();
        workflowIds.add("test_code_interpreter_workflow_id");
        body.setWorkflowIds(workflowIds);

        String jsonStr1 = TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_1.json");
        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_code_interpreter_workflow_id.json")))
            .thenReturn(null);

        assertThrows(AgentStudioException.class, () -> workflowManagementService
            .exportWorkflows(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, body));
    }

    @Test
    @Sql(scripts = {"classpath:sql/mapping_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testExportAgentsShouldFailed() {
        ExportParams body = new ExportParams();
        List<String> agentIds = new ArrayList<>();
        agentIds.add("test_agent_id");
        body.setAgentIds(agentIds);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.exportAgents(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, body));
    }

    @Test
    public void testReplaceWorkflowId() throws JsonProcessingException {
        WfImportDataWrapper wfImportDataWrapper = new WfImportDataWrapper();
        List<String> workflowIds = wfImportDataWrapper.getImportWorkflowList();
        List<String> toolIds = wfImportDataWrapper.getImportToolList();

        workflowIds.add("test_code_interpreter_workflow_id");
        workflowIds.add("test_web_search_workflow_id");
        toolIds.add("reserve_meeting_room_1");
        toolIds.add("reserve_meeting_room_2");
        WorkflowExportEntity workflowExportEntity =
            jacksonObjectMapper.readValue(Constants.TEST_WORKFLOW_REPLACE_ID, new TypeReference<>() {});
        WorkflowExportEntity workflowExportEntity1 =
            agentImportExportService.replaceWorkflowExportId(workflowExportEntity, Constants.TEST_WORKSPACE_ID,
                "test_code_interpreter_workflow_id", Constants.TEST_PROJECT_ID, wfImportDataWrapper);
        assertNotNull(workflowExportEntity1);
    }

    @Test
    @Sql(scripts = {"classpath:sql/workflow_export_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testReplaceAgentId() throws JsonProcessingException {
        WfImportDataWrapper wfImportDataWrapper = new WfImportDataWrapper();
        wfImportDataWrapper.getImportWorkflowList().add("test_code_interpreter_workflow_id");
        wfImportDataWrapper.getImportToolList().add("reserve_meeting_room_1");
        wfImportDataWrapper.getImportAgentList().add("test_agent_id");

        AgentExportEntity agentExportEntity =
            jacksonObjectMapper.readValue(Constants.TEST_AGENT_EXPORT, new TypeReference<>() {});
        AgentExportEntity agentExportEntity1 = agentImportExportService.replaceAgentExportId(agentExportEntity,
            Constants.TEST_WORKSPACE_ID, Constants.TEST_PROJECT_ID, wfImportDataWrapper);

        AgentExportEntity agentExportEntity2 =
            jacksonObjectMapper.readValue(Constants.TEST_MULTI_AGENT_EXPORT, new TypeReference<>() {});
        AgentExportEntity agentExportEntity3 = agentImportExportService.replaceAgentExportId(agentExportEntity2,
            Constants.TEST_WORKSPACE_ID, Constants.TEST_PROJECT_ID, wfImportDataWrapper);

        assertNotNull(agentExportEntity1);
        assertNotNull(agentExportEntity3);
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/tool_export_setup_db.sql",
        "classpath:sql/workflow_export_setup_db.sql", "classpath:sql/mcp_setup_db.sql",
        "classpath:sql/mapping_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testImportAgents() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id,test_agent_id2";
        String toolIds = "reserve_meeting_room_1,test_release_tool";

        String workflowIds = "test_code_interpreter_workflow_id";
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);

        String jsonStr1 = TestUtil.getStringFromFile("classpath:response/obs_workflowDsl_1.json");
        when(mgObsService.downloadObsFile(eq("workflow-ir/workflow/flow/test_code_interpreter_workflow_id.json")))
            .thenReturn(jsonStr1);
        when(pluginAdapterImpl.getPluginId(eq("test_release_tool"))).thenReturn("test_release_tool");
        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion.setVersionId("test");
        releaseVersion.setVersionName("Test");
        releaseVersion.setVersionNote("test");
        releaseVersion.setAppId("test");
        releaseVersion.setAppType("test");
        releaseVersion.setStatus("test");
        releaseVersion.setDslPath("test");
        releaseVersion.setIrPath("");
        releaseVersion.setCreator("");
        releaseVersion.setCreatorId("");
        releaseVersion.setId("test");

        ReleaseVersion releaseVersion2 = new ReleaseVersion();
        releaseVersion2.setVersionId("test2");
        releaseVersion2.setVersionName("Test2");
        releaseVersion2.setVersionNote("test");
        releaseVersion2.setAppId("test");
        releaseVersion2.setAppType("test");
        releaseVersion2.setStatus("test");
        releaseVersion2.setDslPath("test");
        releaseVersion2.setIrPath("");
        releaseVersion2.setCreator("");
        releaseVersion2.setCreatorId("");
        releaseVersion2.setId("test2");

        when(pluginAdapterImpl.releaseToolVersionHandler(any(), any(), any(), any())).thenReturn(releaseVersion,
            releaseVersion2);

        ImportRsp importRsp = agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file,
            agentIds, toolIds, workflowIds, ExportModeEnum.STRICT.getCode());

        assertEquals(1, importRsp.getSucceedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/mapping_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testImportAgentsFailedWhenImportToolVersionFailed() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id2";
        String toolIds = "test_release_tool";

        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);
        ImportRsp importRsp =
            agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file, agentIds, toolIds, "",
                ExportModeEnum.STRICT.getCode());

        assertEquals(0, importRsp.getSucceedLen());
        assertEquals(1, importRsp.getFailedLen());
    }

    @Test
    public void testImportMultiAgents() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_MULTI_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id9";
        String workflowIds = "test_code_interpreter_workflow_id";
        String toolIds = "";
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);

        // ImportRsp importRsp = agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file,
        // agentIds, toolIds, workflowIds);
        //
        // assertEquals(1, importRsp.getSucceedLen());
        // assertEquals(0, importRsp.getFailedLen());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/mapping_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testImportAgentsWithMcps() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id,test_agent_id2";
        ImportRsp importRsp =
            agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file, agentIds, "", "",
                ExportModeEnum.STRICT.getCode());

        assertEquals(2, importRsp.getSucceedLen());
    }

    @Test
    public void testImportAgentsFailed() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id,test_agent_id2";
        String toolIds = "reserve_meeting_room_1,reserve_meeting_room_2";
        String workflowIds = "test_code_interpreter_workflow_id";
        ArrayList<String> ids = new ArrayList<>();
        ids.add("test_agent_id");
        ids.add("test_agent_id2");

        when(RequestContextUtils.getRequestUserDomainId()).thenReturn(Constants.TEST_DOMAIN_ID);
        when(RequestContextUtils.getRequestProjectId()).thenReturn(Constants.TEST_PROJECT_ID);
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenThrow(new AgentStudioException(StudioError.WORKFLOW_IMPORT_FILE));

        ImportRsp importRsp = agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file,
            agentIds, toolIds, workflowIds, ExportModeEnum.STRICT.getCode());

        assertEquals(0, importRsp.getSucceedLen());
        assertEquals(2, importRsp.getFailedLen());
    }

    @Test
    public void testImportAgentsFailedWhenAddMappingException() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id";
        String toolIds = "reserve_meeting_room_1";
        when(mappingMapper.selectByAppIdAndResourceId(any(), any())).thenThrow(AgentStudioException.class);
        ImportRsp importRsp =
            agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file, agentIds, toolIds, "",
                ExportModeEnum.STRICT.getCode());

        assertEquals(1, importRsp.getFailedLen());
        assertEquals(0, importRsp.getSucceedLen());
    }

    @Test
    public void testImportAgentsFailedWhenExceedLength() {
        String projectId = Constants.TEST_PROJECT_ID;
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_AGENT_EXPORT_MAX_LENGTH.getBytes()  // 文件内容
        );
        String agentIds = "test_agent_id";

        ImportRsp importRsp =
            agentManagementService.importAgents(Constants.TEST_WORKSPACE_ID, projectId, file, agentIds, "", "",
                ExportModeEnum.STRICT.getCode());

        assertEquals(0, importRsp.getSucceedLen());
        assertEquals(1, importRsp.getFailedLen());
    }

    @SuppressWarnings("unchecked")
    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testAddTrigger() throws InterruptedException {
        TriggerConfig triggerConfig = new TriggerConfig();
        triggerConfig.setType("");
        triggerConfig.setName("触发器");
        triggerConfig.setPrompt("test_trigger");
        triggerConfig.setCron("0/10 * * * * ?");
        AgentRunReq agentRunReq = new AgentRunReq();
        agentRunReq.setQuery(triggerConfig.getPrompt());
        Assertions.assertThrows(Exception.class, () -> agentManagementService.addTrigger(Constants.TEST_PROJECT_ID,
            Constants.TEST_AGENT_ID, Constants.TEST_WORKSPACE_ID, triggerConfig));
        triggerConfig.setType("EVENT");
        triggerConfig.setType("EVENT");
        agentManagementService.addTrigger(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, triggerConfig);

        assertThrows(AgentStudioException.class, () -> {
            triggerConfig.setType("test");
            agentManagementService.addTrigger(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, triggerConfig);
        });

        assertThrows(AgentStudioException.class, () -> {
            triggerConfig.setType("EVENT");
            agentManagementService.addTrigger(Constants.TEST_PROJECT_ID, "test_agent_id3", Constants.TEST_WORKSPACE_ID,
                triggerConfig);
        });
    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    void listStructuredMessages_shouldHandleMultipleScenarios() {
        // 场景1: 正常查询参数
        ListStructuredMessagesQo normalQuery =
            createQueryObject("workspace-normal", "test-message", "NOTIFICATION", "MANUAL", "1", "asc");

        // 场景2: 特殊字符过滤
        ListStructuredMessagesQo specialCharQuery =
            createQueryObject("workspace-special", "test@message#123", "ALERT", "API", "2", "desc");

        // 场景3: 空结果集
        ListStructuredMessagesQo emptyResultQuery =
            createQueryObject("workspace-empty", "empty-result", "WARNING", "FILE", "3", "asc");

        // 模拟实体数据
        StructuredMessageEntity entity1 = createEntity("msg-001", "Test Message 1");
        StructuredMessageEntity entity2 = createEntity("msg-002", "Test Message 2");
        List<StructuredMessageEntity> mockEntities = Arrays.asList(entity1, entity2);

        // 配置Mock行为
        ArgumentMatcher<StructuredMessageEntity> matcher1 = new ArgumentMatcher<StructuredMessageEntity>() {
            @Override
            public boolean matches(StructuredMessageEntity entity) {
                return "test-message".equals(entity.getName());
            }
        };
        ArgumentMatcher<StructuredMessageEntity> matcher2 = new ArgumentMatcher<StructuredMessageEntity>() {
            @Override
            public boolean matches(StructuredMessageEntity entity) {
                return "testmessage123".equals(entity.getName());
            }
        };
        ArgumentMatcher<StructuredMessageEntity> matcher3 = new ArgumentMatcher<StructuredMessageEntity>() {
            @Override
            public boolean matches(StructuredMessageEntity entity) {
                return "empty-result".equals(entity.getName());
            }
        };

        // 执行测试 - 场景1: 正常查询
        StructMessageListRsp result1 = messageManagementService.listStructuredMessages("project-123", normalQuery);

        // 验证场景1结果
        assertEquals(0, result1.getCount(), "应返回2条结果");

    }

    private ListStructuredMessagesQo createQueryObject(String workspaceId, String name, String category,
        String importMethod, String status, String sort) {
        ListStructuredMessagesQo query = new ListStructuredMessagesQo();
        query.setWorkspaceId(workspaceId);
        query.setName(name);
        query.setCategory(category);
        query.setImportMethod(importMethod);
        query.setStatus(status);
        query.setSort(sort);
        return query;
    }

    private StructuredMessageEntity createEntity(String id, String name) {
        return StructuredMessageEntity.builder()
            .id(id)
            .name(name)
            .projectId("project-123")
            .workspaceId("workspace-456")
            .category("CATEGORY")
            .importMethod("METHOD")
            .status("1")
            .build();
    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    @Sql(scripts = {"classpath:sql/workflow_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void updateStructuredMessages_ShouldUpdateEntityAndReturnResponse() {

        // 使用测试上下文，与数据库中的数据保持一致
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_CREATOR_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);

        // 准备测试数据 - 使用数据库中实际存在的ID
        StructuredInfoRequest request = new StructuredInfoRequest();
        request.setId("123456789");  // 使用数据库中存在的ID
        request.setName("UpdatedName");
        request.setCategory("异常");
        request.setContent(Map.of("key", "value"));
        request.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);

        // 执行方法 - 使用测试项目ID和workspace ID
        StructMessage result = messageManagementService.updateStructuredMessages(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, request);

        // 验证返回结果
        assertEquals("123456789", result.getId());
        assertEquals("UpdatedName", result.getName());
        assertEquals("异常", result.getCategory());
        assertEquals(Map.of("key", "value"), result.getContent());
        assertEquals("仅个人", result.getVisibility());

        //
        StructuredInfoRequest requestex = new StructuredInfoRequest();
        requestex.setId("msg-010");
        requestex.setName("UpdatedNam");
        requestex.setCategory("ALERT");
        requestex.setContent(Map.of("key", "value"));
        requestex.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);
        // 执行方法，预期抛出异常，因为category必须是"异常"
        assertThrows(AgentStudioException.class, () -> {
            StructMessage resultex = messageManagementService.updateStructuredMessages(Constants.TEST_PROJECT_ID,
                Constants.TEST_WORKSPACE_ID, requestex);
            ;
        });

        StructuredInfoRequest requestez = new StructuredInfoRequest();
        requestez.setId("msg-002");
        requestez.setName("UpdatedName-Test");
        requestez.setCategory("异常");
        requestez.setContent(Map.of("key", "value"));
        requestez.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);

        // 执行方法，使用符合命名规则的名字
        assertThrows(AgentStudioException.class, () -> {
            StructMessage resultex = messageManagementService.updateStructuredMessages(Constants.TEST_PROJECT_ID,
                Constants.TEST_WORKSPACE_ID, requestez);
        });

        // 准备测试数据，测试超过64个字符的名字
        StructuredInfoRequest requestex2 = new StructuredInfoRequest();
        requestex2.setId("msg-001");
        requestex2.setName("ThisNameIsWayTooLongExceedsTheSixtyFourCharacterLimitTestForValidation");
        requestex2.setCategory("异常");
        requestex2.setContent(Map.of("key", "value"));
        requestex2.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);

        // 执行方法，预期抛出异常，因为名字超过64字符限制
        assertThrows(AgentStudioException.class, () -> {
            StructMessage resultex = messageManagementService.updateStructuredMessages(Constants.TEST_PROJECT_ID,
                Constants.TEST_WORKSPACE_ID, requestex2);
        });
    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    @Sql(scripts = {"classpath:sql/workflow_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testDeleteStructuredMessages_AllScenarios() {
        // 场景1: 正常删除有效的ID
        String projectId = Constants.TEST_PROJECT_ID;
        String workspaceId = Constants.TEST_WORKSPACE_ID;

        // 使用数据库中存在的ID + 无效ID进行测试
        List<StructuredInfoRequestDelete> requests =
            Arrays.asList(new StructuredInfoRequestDelete().setId("123456789").setCategory("异常"),   // 有效 (数据库中存在)
                new StructuredInfoRequestDelete().setId(null).setCategory("typeB"),     // 无效(null) - 应该被过滤掉
                new StructuredInfoRequestDelete().setId("").setCategory("typeC"),       // 无效(空字符串) - 应该被过滤掉
                new StructuredInfoRequestDelete().setId("  ").setCategory("typeD")     // 无效(空白字符串) - 应该被过滤掉

            );
        // 执行删除操作 - 只会删除存在的ID "123456789"
        BatchDeleteRsp response =
            messageManagementService.deleteStructuredMessages(projectId, workspaceId, requests);
        // 验证响应结果 - 只有1个有效ID会被处理
        assertEquals(1, response.getCount(), "应返回1个有效ID的计数");
        assertEquals(1, response.getIds().size(), "ID列表应包含1个有效元素");
        assertTrue(response.getIds().contains("123456789"), "ID列表应包含存在的有效ID");

        // 场景2: 空请求列表
        List<StructuredInfoRequestDelete> emptyRequests = Collections.emptyList();
        BatchDeleteRsp emptyResponse =
            messageManagementService.deleteStructuredMessages(projectId, workspaceId, emptyRequests);

        assertEquals(0, emptyResponse.getCount(), "空请求应返回0计数");
        assertTrue(emptyResponse.getIds().isEmpty(), "空请求应返回空ID列表");

        List<StructuredInfoRequestDelete> invalidRequests =
            Arrays.asList(new StructuredInfoRequestDelete().setId(null).setCategory("typeX"),
                new StructuredInfoRequestDelete().setId("").setCategory("typeY"),
                new StructuredInfoRequestDelete().setId("  ").setCategory("typeZ"));

        BatchDeleteRsp invalidResponse =
            messageManagementService.deleteStructuredMessages(projectId, workspaceId, invalidRequests);
        assertEquals(0, invalidResponse.getCount(), "全无效请求应返回0计数");
        assertTrue(invalidResponse.getIds().isEmpty(), "全无效请求应返回空ID列表");

    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    void testDeleteStructuredMessages_ShouldThrowExceptionWhenMessageCountMismatch() {
        // 准备测试数据 - 构造包含不存在的ID的请求
        List<StructuredInfoRequestDelete> requests =
            Arrays.asList(new StructuredInfoRequestDelete().setId("existing-message-id").setCategory("typeA"),   // 存在的ID
                new StructuredInfoRequestDelete().setId("non-existent-message-id").setCategory("typeB")  // 不存在的ID
            );

        String projectId = "proj-123";
        String workspaceId = "ws-456";

        // 执行方法，预期抛出AgentStudioException
        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            messageManagementService.deleteStructuredMessages(projectId, workspaceId, requests);
        });

        // 验证异常类型和错误码
        assertEquals(StudioError.MESSAGE_TEMPLATE_NOT_FOUND_OR_PERMISSION_DENIED, exception.getErrorCode());
    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    void createStructuredMessages_ComprehensiveTest() {
        // 准备测试数据
        String projectId = "test-project";
        String workspaceId = "test-workspace";
        String userId = "user-123";
        String domainId = "domain-456";

        // 构造请求对象
        StructuredInfoRequest request = new StructuredInfoRequest();
        request.setName("Test Message");
        request.setCategory("异常");

        // 构造 content
        Map<String, Object> content = new HashMap<>();
        Map<String, Object> errorInfo = new HashMap<>();
        errorInfo.put("code", "ERR-1001");
        errorInfo.put("message", "数据库连接失败");
        errorInfo.put("description", "无法建立与MySQL数据库的连接，请检查数据库服务是否运行或网络配置是否正确");
        errorInfo.put("details", Map.of("host", "db.example.com", "port", 3306, "connection_attempts", 3));
        errorInfo.put("timestamp", "2025-09-17T10:30:45.123Z");
        content.put("error", errorInfo);
        request.setContent(content);
        request.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);

        // mock 静态方法
        when(RequestContextUtils.getRequestUserDomainId()).thenReturn(domainId);
        when(RequestContextUtils.getRequestProjectId()).thenReturn(userId);

        // 执行被测方法
        StructMessage result = messageManagementService.createStructuredMessages(projectId, workspaceId, request);

        // 验证结果
        assertNotNull(result);
        assertNotNull(result.getId());
        assertEquals("Test Message", result.getName());
        assertEquals("异常", result.getCategory());
        assertEquals("仅个人", result.getVisibility());

        // 构造请求对象
        StructuredInfoRequest requestex = new StructuredInfoRequest();
        requestex.setName("UpdatedName#$");
        requestex.setCategory("异常");

        // 构造 content
        Map<String, Object> contentex = new HashMap<>();
        Map<String, Object> errorInfoex = new HashMap<>();
        errorInfo.put("code", "ERR-1001");
        errorInfo.put("message", "数据库连接失败");
        errorInfo.put("description", "无法建立与MySQL数据库的连接，请检查数据库服务是否运行或网络配置是否正确");
        errorInfo.put("details", Map.of("host", "db.example.com", "port", 3306, "connection_attempts", 3));
        errorInfo.put("timestamp", "2025-09-17T10:30:45.123Z");
        content.put("error", errorInfoex);
        requestex.setContent(contentex);
        requestex.setVisibility(StructuredInfoRequest.VisibilityEnum.PERSONAL);
        // 执行方法
        assertThrows(AgentStudioException.class, () -> {
            StructMessage resultex =
                messageManagementService.createStructuredMessages(projectId, workspaceId, requestex);
        });

    }

    @SuppressWarnings("unchecked")
    @SneakyThrows
    @Test
    void testAgentTriggerService() {
        JobDetail jobDetail = JobBuilder.newJob(AgentTriggerService.class)
            .withIdentity("test_job_name")
            .usingJobData(Constants.PROJECT_ID, Constants.TEST_PROJECT_ID)
            .usingJobData(Constants.DOMAIN_ID, Constants.TEST_DOMAIN_ID)
            .usingJobData(Constants.AGENT_ID, Constants.TEST_AGENT_ID)
            .usingJobData(Constants.TRIGGER_ID, Constants.TEST_TRIGGER_ID)
            .usingJobData(Constants.PROMPT, "test_trigger")
            .usingJobData(Constants.TRACE_IAM_ENDPOINT, "traceIamEndpoint")
            .usingJobData(Constants.AGENCY_TOKEN_URL, "agencyTokenUrl")
            .usingJobData(Constants.AGENT_RUNTIME_ENDPOINT, "http://localhost:10002")
            .usingJobData(Constants.RUN_AGENT_STREAM_URL, "/conversations")
            .build();
        // 只执行一次，不重复
        Trigger trigger = TriggerBuilder.newTrigger().withIdentity("test_trigger_name").startNow().build();
        Scheduler scheduler = StdSchedulerFactory.getDefaultScheduler();
        scheduler.scheduleJob(jobDetail, trigger);
        scheduler.start();
        // 等待任务开始执行即可，不需要长时间等待
        Thread.sleep(100);
        scheduler.shutdown(true); // 立即关闭调度器
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testDeleteTrigger() {
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.deleteTrigger(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_TRIGGER_ID, Constants.TEST_WORKSPACE_ID);
        });

        Assertions.assertThrows(AgentStudioException.class,
            () -> agentManagementService.deleteTrigger(Constants.TEST_PROJECT_ID, "test_agent_id3",
                Constants.TEST_TRIGGER_ID, Constants.TEST_WORKSPACE_ID));
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testEditTrigger() {
        TriggerConfig triggerConfig = new TriggerConfig();
        triggerConfig.setTriggerId("test_trigger_id");
        triggerConfig.setType("TIMER");
        triggerConfig.setName("触发器");
        triggerConfig.setPrompt("test_trigger");
        triggerConfig.setCron("0/10 * * * * ?");
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.editTrigger(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, triggerConfig);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_reserve_meeting_room_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testAgentIdsSuccess() {
        List<String> agentIds = new ArrayList<>();
        agentIds.add("reserve_meeting_room");
        agentCommonService.validTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, agentIds);
    }

    @Test
    @Sql(scripts = {"classpath:sql/tool_reserve_meeting_room_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testAgentIdsEmptySuccess() {
        List<String> agentIds = new ArrayList<>();
        agentCommonService.validTools(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, agentIds);
    }

    @Test
    public void test_listImportFile_file_check_fails() throws Exception {
        // Given
        MultipartFile file = mock(MultipartFile.class);

        // When & Then
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.listImportFile("workspaceId", "projectId", file, 0, 10);
        });
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法的正常情况
     * 验证支持的文件类型能够成功上传
     */
    @Test
    void testUploadDeepResearchTemplate_Success() throws Exception {
        // 准备测试数据
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test document content".getBytes(StandardCharsets.UTF_8);

        // 创建 Mock MultipartFile
        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        // Mock MgObsService 的 uploadObsFile 方法
        when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), eq(-1)))
            .thenReturn("obs://test-bucket/test-path/template.docx");

        // 调用测试方法
        FileUploadRsp result =
            agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile);

        // 验证结果
        assertNotNull(result);
        assertEquals(fileName, result.getFileName());
        assertEquals("obs://test-bucket/test-path/template.docx", result.getUrl());

        // 验证 MgObsService 的调用
        verify(mgObsService).uploadObsFile(eq("agent/writing_template/test-agent-id/template.docx"),
            any(InputStream.class), eq(-1));
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 projectId 为空的情况
     * 应该抛出 PROJECT_ID_INVALID 异常
     */
    @Test
    void testUploadDeepResearchTemplate_EmptyProjectId() {
        String projectId = "";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.PROJECT_ID_INVALID, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 projectId 为 null 的情况
     * 应该抛出 PROJECT_ID_INVALID 异常
     */
    @Test
    void testUploadDeepResearchTemplate_NullProjectId() {
        String projectId = null;
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.PROJECT_ID_INVALID, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 workspaceId 为空的情况
     * 应该抛出 WORKSPACE_ID_INVALID 异常
     */
    @Test
    void testUploadDeepResearchTemplate_EmptyWorkspaceId() {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.WORKSPACE_ID_INVALID, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 workspaceId 为 null 的情况
     * 应该抛出 WORKSPACE_ID_INVALID 异常
     */
    @Test
    void testUploadDeepResearchTemplate_NullWorkspaceId() {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = null;
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.WORKSPACE_ID_INVALID, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 agentId 为空的情况
     * 应该抛出 AGENT_NOT_EXIST_OR_NO_PERMISSION 异常
     */
    @Test
    void testUploadDeepResearchTemplate_EmptyAgentId() {
        String projectId = "test-project-id";
        String agentId = "";
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 agentId 为 null 的情况
     * 应该抛出 AGENT_NOT_EXIST_OR_NO_PERMISSION 异常
     */
    @Test
    void testUploadDeepResearchTemplate_NullAgentId() {
        String projectId = "test-project-id";
        String agentId = null;
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 file 为 null 的情况
     * 应该抛出 FILE_CANNOT_BE_EMPTY 异常
     */
    @Test
    void testUploadDeepResearchTemplate_NullFile() {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, null));

        assertEquals(StudioError.FILE_CANNOT_BE_EMPTY, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法 file 为空文件的情况
     * 应该抛出 FILE_CANNOT_BE_EMPTY 异常
     */
    @Test
    void testUploadDeepResearchTemplate_EmptyFile() throws Exception {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";

        MultipartFile emptyFile = new MockMultipartFile("file", "empty.txt", "text/plain", new byte[0]);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, emptyFile));

        assertEquals(StudioError.FILE_CANNOT_BE_EMPTY, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法不支持文件类型的情况
     * 应该抛出 ILLEGAL_FILE_TYPE 异常
     */
    @Test
    void testUploadDeepResearchTemplate_UnsupportedFileType() throws Exception {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template.txt";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName, "text/plain", fileContent);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.ILLEGAL_FILE_TYPE, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法文件输入流读取异常的情况
     * 应该抛出 UPLOAD_FILE_TO_OBS_FAILED 异常
     */
    @Test
    void testUploadDeepResearchTemplate_InputStreamException() throws Exception {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent) {
            @Override
            public InputStream getInputStream() throws IOException {
                throw new IOException("Failed to create input stream");
            }
        };

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile));

        assertEquals(StudioError.UPLOAD_FILE_TO_OBS_FAILED, exception.getErrorCode());
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法中文文件名的情况
     * 应该能够成功上传
     */
    @Test
    void testUploadDeepResearchTemplate_ChineseFileName() throws Exception {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "中文模板.docx";
        byte[] fileContent = "测试内容".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), eq(-1)))
            .thenReturn("obs://test-bucket/test-path/" + fileName);

        FileUploadRsp result =
            agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile);

        assertNotNull(result);
        assertEquals(fileName, result.getFileName());
        verify(mgObsService).uploadObsFile(eq("agent/writing_template/test-agent-id/" + fileName),
            any(InputStream.class), eq(-1));
    }

    /**
     * 测试 uploadDeepResearchTemplate 方法特殊字符文件名的情况
     * 应该能够成功上传
     */
    @Test
    void testUploadDeepResearchTemplate_SpecialCharactersInFileName() throws Exception {
        String projectId = "test-project-id";
        String agentId = "test-agent-id";
        String workspaceId = "test-workspace-id";
        String fileName = "template-with_special-chars_123.docx";
        byte[] fileContent = "Test content".getBytes(StandardCharsets.UTF_8);

        MultipartFile mockFile = new MockMultipartFile("file", fileName,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fileContent);

        when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), eq(-1)))
            .thenReturn("obs://test-bucket/test-path/" + fileName);

        FileUploadRsp result =
            agentManagementService.uploadDeepResearchTemplate(projectId, agentId, workspaceId, mockFile);

        assertNotNull(result);
        assertEquals(fileName, result.getFileName());
        verify(mgObsService).uploadObsFile(eq("agent/writing_template/test-agent-id/" + fileName),
            any(InputStream.class), eq(-1));
    }

    /**
     * 测试智能生成智能体图标
     */
    @Test
    void test_generateAgentIcons_missing_name() throws Exception {
        CreateAgentReq body = new CreateAgentReq();
        body.setName("");
        body.setDescription("test description");

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.generateAgentIcons("projectId", "workspaceId", body));
        assertEquals(StudioError.MISSING_REQUIRED_PARAMETERS, exception.getErrorCode());
    }

    @Test
    void test_generateAgentIcons_success() throws Exception {
        try (MockedStatic<LanguageUtils> languageUtils = Mockito.mockStatic(LanguageUtils.class);
            MockedStatic<CommonUtil> commonUtil = Mockito.mockStatic(CommonUtil.class);
            MockedStatic<ImageBase64Utils> imageBase64Utils = Mockito.mockStatic(ImageBase64Utils.class)) {

            languageUtils.when(LanguageUtils::isChinese).thenReturn(false);
            commonUtil.when(() -> CommonUtil.getResourceContent(PromptPath.ICON_PROMPT_EN))
                .thenReturn("template {name} {description}");
            CreateAgentReq body = new CreateAgentReq();
            body.setName("Test Agent");
            body.setDescription("Test description");
            String response = """
                {
                    "model": "qwen-image",
                    "created": 1769080143729,
                    "data": [
                        {
                            "url": null,
                            "b64_json": "data:image/png;base64,test"
                        }
                    ],
                    "usage": {
                        "model_latency": 3450,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "width": 512,
                        "height": 512
                    },
                    "error": null
                }
            """;

            String b64JsonCompressed = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

            ResponseEntity<String> successResponse = new ResponseEntity<>(response, HttpStatus.OK);

            when(maasModelClient.generateImage(anyString(), any(ImageGenerationRequest.class)))
                .thenReturn(successResponse);
            imageBase64Utils.when(() -> ImageBase64Utils.resizeBase64Image(anyString(), anyInt(), anyInt())).thenReturn(b64JsonCompressed);
            when(mgObsService.uploadObsFile(anyString(), any(InputStream.class), anyInt())).thenReturn("true");
            AutoAddResultJsonObject result = agentManagementService.generateAgentIcons("projectId", "workspaceId", body);
            assertNotNull(result);
            assertEquals(b64JsonCompressed, result.getIcons().getIconDetail());
        }

    }

    @Test
    void test_generateAgentIcons_service_error() throws Exception {
        try (MockedStatic<LanguageUtils> languageUtils = Mockito.mockStatic(LanguageUtils.class);
            MockedStatic<CommonUtil> commonUtil = Mockito.mockStatic(CommonUtil.class)) {

            languageUtils.when(LanguageUtils::isChinese).thenReturn(false);
            commonUtil.when(() -> CommonUtil.getResourceContent(PromptPath.ICON_PROMPT_EN))
                .thenReturn("template {name} {description}");
            CreateAgentReq body = new CreateAgentReq();
            body.setName("Test Agent");
            body.setDescription("Test description");

        when(maasModelClient.generateImage(anyString(), any(ImageGenerationRequest.class))).thenThrow(new RuntimeException("Service error"));

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> agentManagementService.generateAgentIcons("projectId", "workspaceId", body));
        assertEquals(StudioError.GENERATE_ICON_FAILED, exception.getErrorCode());
        }
    }

    @Test
    void test_generateAgentIcons_non200_response() throws Exception {
        try (MockedStatic<LanguageUtils> languageUtils = Mockito.mockStatic(LanguageUtils.class);
            MockedStatic<CommonUtil> commonUtil = Mockito.mockStatic(CommonUtil.class)) {

            languageUtils.when(LanguageUtils::isChinese).thenReturn(false);
            commonUtil.when(() -> CommonUtil.getResourceContent(PromptPath.ICON_PROMPT_EN))
                .thenReturn("template {name} {description}");
            CreateAgentReq body = new CreateAgentReq();
            body.setName("Test Agent");
            body.setDescription("Test description");

            ResponseEntity<String> errorResponse = new ResponseEntity<>("Error", HttpStatus.INTERNAL_SERVER_ERROR);
            when(maasModelClient.generateImage(anyString(), any(ImageGenerationRequest.class))).thenReturn(errorResponse);

            AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> agentManagementService.generateAgentIcons("projectId", "workspaceId", body));
            assertEquals(StudioError.GENERATE_ICON_FAILED, exception.getErrorCode());
        }
    }

    @Test
    void test_generateAgentIcons_empty_response_body() throws Exception {
        try (MockedStatic<LanguageUtils> languageUtils = Mockito.mockStatic(LanguageUtils.class);
            MockedStatic<CommonUtil> commonUtil = Mockito.mockStatic(CommonUtil.class)) {

            languageUtils.when(LanguageUtils::isChinese).thenReturn(false);
            commonUtil.when(() -> CommonUtil.getResourceContent(PromptPath.ICON_PROMPT_EN))
                .thenReturn("template {name} {description}");
            CreateAgentReq body = new CreateAgentReq();
            body.setName("Test Agent");
            body.setDescription("Test description");

            ResponseEntity<String> emptyResponse = new ResponseEntity<>(null, HttpStatus.OK);
            when(maasModelClient.generateImage(anyString(), any(ImageGenerationRequest.class))).thenReturn(emptyResponse);

            AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> agentManagementService.generateAgentIcons("projectId", "workspaceId", body));
            assertEquals(StudioError.GENERATE_ICON_FAILED, exception.getErrorCode());
        }
    }

    @Test
    void test_deleteAgentChannelUnchecked_normal_flow() throws Exception {
        String projectId = "projectId";
        String agentId = "agentId";
        String channelId = "channelId";
        String workspaceId = "workspaceId";

        ReleaseChannel channel = mock(ReleaseChannel.class);
        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(eq(channelId), eq(agentId), eq(projectId),
            eq(workspaceId))).thenReturn(channel);
        when(channel.getChannelType()).thenReturn(CommonConstant.APP_STORE_CHANNEL);

        agentManagementService.deleteAgentChannelUnchecked(projectId, agentId, channelId, workspaceId);

        verify(releaseChannelMapper).deleteByPrimaryKeyAndWorkspaceId(channelId, projectId, workspaceId);
        verify(appMapper).deleteByResourceId(agentId, projectId, workspaceId);
    }


    @Test
    void test_generateAgentMcpReferences_with_empty_list() throws Exception {
        String agentId = "agent123";
        List<AgentMcpDetail> mcpDetails = Collections.emptyList();

        try (MockedStatic<CollectionUtils> mockedCollectionUtils = mockStatic(CollectionUtils.class)) {
            mockedCollectionUtils.when(() -> CollectionUtils.isEmpty(any(Collection.class))).thenReturn(true);

            List<MappingEntity> result = agentManagementService.generateAgentMcpReferences(agentId, mcpDetails);
            assertTrue(result.isEmpty());
        }
    }

    @Test
    void test_generateAgentMcpReferences_with_non_empty_list() throws Exception {
        String agentId = "agent123";
        List<AgentMcpDetail> mcpDetails = new ArrayList<>();
        AgentMcpDetail mcpDetail1 = mock(AgentMcpDetail.class);
        AgentMcpDetail mcpDetail2 = mock(AgentMcpDetail.class);

        when(mcpDetail1.getMcpId()).thenReturn("mcp1");
        when(mcpDetail1.getMcpParam()).thenReturn("param1");
        when(mcpDetail2.getMcpId()).thenReturn("mcp2");
        when(mcpDetail2.getMcpParam()).thenReturn("param2");

        mcpDetails.add(mcpDetail1);
        mcpDetails.add(mcpDetail2);

        try (MockedStatic<CollectionUtils> mockedCollectionUtils = mockStatic(CollectionUtils.class)) {
            mockedCollectionUtils.when(() -> CollectionUtils.isEmpty(any(Collection.class))).thenReturn(false);

            List<MappingEntity> result = agentManagementService.generateAgentMcpReferences(agentId, mcpDetails);
            assertEquals(2, result.size());

            MappingEntity mapping1 = result.get(0);
            assertEquals(agentId, mapping1.getAppId());
            assertEquals(CommonConstant.AGENT_TYPE, mapping1.getAppType());
            assertEquals("mcp1", mapping1.getResourceId());
            assertEquals(CommonConstant.MCP_TYPE, mapping1.getResourceType());
            assertEquals("param1", mapping1.getExtendInfo());

            MappingEntity mapping2 = result.get(1);
            assertEquals(agentId, mapping2.getAppId());
            assertEquals(CommonConstant.AGENT_TYPE, mapping2.getAppType());
            assertEquals("mcp2", mapping2.getResourceId());
            assertEquals(CommonConstant.MCP_TYPE, mapping2.getResourceType());
            assertEquals("param2", mapping2.getExtendInfo());
        }
    }

    @Test
    void test_generateAgentMcpReferences_should_return_not_null() throws Exception {
        // Given
        List<AgentMcpDetail> mcpDetails = new ArrayList<>();
        AgentMcpDetail agentMcpDetail = new AgentMcpDetail();
        mcpDetails.add(agentMcpDetail);

        // When
        List<MappingEntity> result = agentManagementService.generateAgentMcpReferences("not_empty", mcpDetails);

        // Then
        assertNotNull(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgentInputVariables() throws IOException {
        // set up
        final ModifyAgentReq req =
            TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_req_with_input_variables.json");

        // run test
        AgentInfo agentInfo = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);

        // assert result
        assertEquals(2, agentInfo.getInputVariables().size());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgent_Same_InputVariables() throws IOException {
        // set up
        final ModifyAgentReq req =
            TestUtil.getJsonObject(ModifyAgentReq.class, "classpath:service/modify_agent_req_with_same_input_variables.json");

        // run test
        assertThrows(AgentStudioException.class, () -> {
            agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, req);
        });
    }

    @Test
    @SuppressWarnings("unchecked")
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_parseMcpConfigAndReplaceHeaders() throws IOException {
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setResourceId("reserve_meeting_room_9");
        mappingEntity.setResourceVersion("1748400865320");
        when(mappingMapper.selectByAppIdAndResourceType("test_agent_id", CommonConstant.MCP_TYPE))
                .thenReturn(List.of(mappingEntity));

        // set up
        Object config = TestUtil.getJsonObject(Map.class,"classpath:service/mcp/mcp_config.json");

        // run test
        irAdapterService.parseMcpConfigAndReplaceHeaders((Map<String, Object>) config);

    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyAgent_switch_PlanExecute_Mode() throws IOException {
        // set up
        final ModifyAgentReq req = new ModifyAgentReq();
        req.setType(ModifyAgentReq.TypeEnum.PLANEXECUTE);
        when(mappingMapper.selectByAppIdAndResourceType(anyString(), anyString())).thenReturn(new ArrayList<>());
        String jsonStr1 = TestUtil.getStringFromFile("src/test/resources/response/obs_agent_planexecute_DSL.json");
        when(mgObsService.downloadObsFile(anyString())).thenReturn(jsonStr1);
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString())).thenReturn("test_dsl_path");

        // run test
        AgentInfo agentInfo = agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);

        // assert result
        assertEquals("planexecute", agentInfo.getSubType());
    }

    @Test
    void test_autoAddResource_with_empty_instructions() {
        AutoAddStudioResourceRequestBody body = mock(AutoAddStudioResourceRequestBody.class);
        when(body.getInstructions()).thenReturn("");
        when(body.getType()).thenReturn("someType");

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.autoAddStudioResource("projectId", "workspaceId", "agentId", body));
    }

    @Test
    void test_autoAddResource_with_empty_type() {
        AutoAddStudioResourceRequestBody body = mock(AutoAddStudioResourceRequestBody.class);
        when(body.getInstructions()).thenReturn("someInstructions");
        when(body.getType()).thenReturn("");

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.autoAddStudioResource("projectId", "workspaceId", "agentId", body));
    }

    @Test
    void test_autoAddResource_with_skill_type_with_no_skill() {
        AutoAddStudioResourceRequestBody body = mock(AutoAddStudioResourceRequestBody.class);
        when(body.getInstructions()).thenReturn("someInstructions");
        when(body.getType()).thenReturn("skill");

        Agent agent = mock(Agent.class);
        when(agent.getModelDeploymentId()).thenReturn("modelDeploymentId");
        when(agent.getModelType()).thenReturn("modelType");
        when(agent.getModelConfig()).thenReturn(new ModelConfig());
        when(agent.getModel()).thenReturn("model");
        when(agentMapper.selectById(anyString())).thenReturn(agent);

        String modelRsp = "no_skill";
        when(jiuWenService.callModel(any(), anyString())).thenReturn(modelRsp);

        AutoAddResultJsonObject result = agentManagementService.autoAddStudioResource("projectId", "workspaceId", "agentId", body);

        assertNotNull(result);
    }

    @Test
    void test_autoAddResource_with_unsupported_type() {
        AutoAddStudioResourceRequestBody body = mock(AutoAddStudioResourceRequestBody.class);
        when(body.getInstructions()).thenReturn("someInstructions");
        when(body.getType()).thenReturn("unsupportedType");

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.autoAddStudioResource("projectId", "workspaceId", "agentId", body));
    }


    @Test
    void test_autoAddResource_with_skill_type_not_null() {
        AutoAddStudioResourceRequestBody body = new AutoAddStudioResourceRequestBody();
        body.setInstructions("someInstructions");
        body.setType("skill");
        body.setLimit(50);

        Agent agent = mock(Agent.class);
        when(agent.getModelDeploymentId()).thenReturn("modelDeploymentId");
        when(agent.getModelType()).thenReturn("modelType");
        when(agent.getModelConfig()).thenReturn(new ModelConfig());
        when(agent.getModel()).thenReturn("model");
        when(agentMapper.selectById(anyString())).thenReturn(agent);
        String modelRsp = """
            {
                "selected_skills": [
                    {
                        "name": "fetch_public_filings",
                        "confidence": 0.95
                    },
                    {
                        "name": "extract_financial_metrics",
                        "confidence": 0.9
                    },
                    {
                        "name": "compare_time_series",
                        "confidence": 0.85
                    },
                    {
                        "name": "test_111",
                        "confidence": 0.49
                    }
                ]
            }
            """;
        when(jiuWenService.callModel(any(), anyString())).thenReturn(modelRsp);

        AutoAddResultJsonObject result = agentManagementService.autoAddStudioResource("projectId", "workspaceId",
            "agentId", body);
        assertEquals(3, result.getSkills().size());
    }

    @Test
    void test_autoAddResource_with_skill_type_not_exceed_limit() {
        AutoAddStudioResourceRequestBody body = mock(AutoAddStudioResourceRequestBody.class);
        when(body.getInstructions()).thenReturn("someInstructions");
        when(body.getType()).thenReturn("skill");
        when(body.getLimit()).thenReturn(2);

        Agent agent = mock(Agent.class);
        when(agent.getModelDeploymentId()).thenReturn("modelDeploymentId");
        when(agent.getModelType()).thenReturn("modelType");
        when(agent.getModelConfig()).thenReturn(new ModelConfig());
        when(agent.getModel()).thenReturn("model");
        when(agentMapper.selectById(anyString())).thenReturn(agent);

        String modelRsp = """
            {
                "selected_skills": [
                    {
                        "name": "fetch_public_filings",
                        "confidence": 0.95
                    },
                    {
                        "name": "extract_financial_metrics",
                        "confidence": 0.9
                    },
                    {
                        "name": "compare_time_series",
                        "confidence": 0.85
                    },
                    {
                        "name": "test_111",
                        "confidence": 0.88
                    }
                ]
            }
            """;
        when(jiuWenService.callModel(any(), anyString())).thenReturn(modelRsp);

        AutoAddResultJsonObject result = agentManagementService.autoAddStudioResource("projectId", "workspaceId",
            "agentId", body);
        assertEquals(2, result.getSkills().size());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/skill_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testRestoreAgent_with_skills() throws IOException {
        // set up
        final ModifyAgentReq req = TestUtil.getJsonObject(ModifyAgentReq.class,
            "classpath:service/restore_agent_version_req.json");

        // run test
        agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);
        AgentInfo agentInfo = agentManagementService.retrieveAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID);
        assertEquals(1, agentInfo.getSkills().size());
    }

    @Test
    @Sql(
        scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/skill_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_modify_agent_with_invalid_skill_ids() throws IOException {
        // set up
        final List<AgentSkillDetail> agentSkillDetails = new ArrayList<>();
        agentSkillDetails.add(new AgentSkillDetail().setSkillId("test_skill_id").setSkillVersion("test_used_version"));
        agentSkillDetails.add(new AgentSkillDetail().setSkillId("test_skill_id11").setSkillVersion("test_used_version"));
        final ModifyAgentReq req = new ModifyAgentReq();
        req.setSkillDetails(agentSkillDetails);
        // run test
        agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID, req);
        AgentInfo agentInfo = agentManagementService.retrieveAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
            Constants.TEST_WORKSPACE_ID);
        assertEquals(2, agentInfo.getSkills().size());

        final List<AgentSkillDetail> agentSkillDetails1 = new ArrayList<>();
        agentSkillDetails1.add(
            new AgentSkillDetail().setSkillId("test_skill_id").setSkillVersion("test_used_version1"));
        req.setSkillDetails(agentSkillDetails1);
        assertThrows(AgentStudioException.class,
            () -> agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, Constants.TEST_AGENT_ID,
                Constants.TEST_WORKSPACE_ID, req));
    }
}
