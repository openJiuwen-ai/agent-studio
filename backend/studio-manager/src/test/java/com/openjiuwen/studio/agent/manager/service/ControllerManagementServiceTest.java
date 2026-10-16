/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;

import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * controller单元测试类
 *
 */
@Transactional
@Slf4j
public class ControllerManagementServiceTest extends BaseTest {
    // 顺序执行类型
    private static final String ORDER = "order";

    // 动态执行类型
    private static final String DYNAMIC = "dynamic";

    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    @Autowired
    private AgentManagementService agentManagementService;

    @Autowired
    private ControllerManagementService controllerManagementService;

    @MockitoBean
    private MgObsService obsService;

    @MockitoBean
    private ModelServiceManager modelServiceManager;

    @MockitoSpyBean
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @MockitoSpyBean
    private WorkflowMapper workflowMapper;

    @BeforeAll
    public static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedHeaderStatic = Mockito.mockStatic(RequestHeaderHolderUtils.class);
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("zh-CN");
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_USER_ID);
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        mockedHeaderStatic.close();
    }

    @BeforeEach
    void setUp() throws Exception {
        Map<String, String> map = new HashMap<>();

        when(obsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString())).thenAnswer(
            invocation -> {
                String pathKey = invocation.getArgument(0, String.class);
                String objectKey = invocation.getArgument(1, String.class);
                String type = invocation.getArgument(2, String.class);
                String fileInfo = invocation.getArgument(3, String.class);
                String prefix = invocation.getArgument(4, String.class);
                String key = String.format("%s/%s/%s/%s.json", type, prefix, pathKey, objectKey);
                map.put(key, fileInfo);
                return key;
            });

        when(obsService.downloadObsFile(anyString())).thenAnswer(invocation -> {
            String key = invocation.getArgument(0, String.class);
            return map.get(key);
        });

    }

    @Test
    @SneakyThrows
    @Sql(scripts = {"classpath:sql/controller_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testCreateControllerAgentOrder() {
        testCreateControllerAgent(ORDER);
    }

    @Test
    @SneakyThrows
    @Sql(scripts = {"classpath:sql/controller_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testCreateControllerAgentDynamic() {
        testCreateControllerAgent(DYNAMIC);
    }

    @SneakyThrows
    void testCreateControllerAgent(String type) {
        String uuidStr = createController();

        // 2.修改controller
        ModifyAgentReq body = TestUtil.getJsonObject(ModifyAgentReq.class,
            String.format("classpath:service/modify_controller_%s_agent_req.json", type));
        agentManagementService.modifyAgent(Constants.TEST_PROJECT_ID, uuidStr, "0", body);

        String dsl = obsService.downloadObsFile(String.format("agent/flow/%s/%s.json", uuidStr, uuidStr));
        String ir = obsService.downloadObsFile(String.format("agent/ir/%s/%s.json", uuidStr, uuidStr));

        // 更新时间戳为动态值，需要特殊处理
        JSONObject dslObject = JSONObject.parseObject(dsl);
        dslObject.put("update_time", "test_updated_on");
        dsl = JSONObject.toJSONString(dslObject);
        JSONObject irObject = JSONObject.parseObject(ir);
        irObject.getJSONObject("metadata").put("updatedAt", "test_updated_on");
        ir = JSONObject.toJSONString(irObject);

        Assertions.assertEquals(
            TestUtil.prettyJsonFile(String.format("classpath:flow_dsl/controller_%s_dsl.json", type)),
            TestUtil.prettyJson(dsl));
        Assertions.assertEquals(
            TestUtil.prettyJsonFile(String.format("classpath:flow_dsl/controller_%s_ir.json", type)),
            TestUtil.prettyJson(ir));

        // 3.获取controller
        AgentInfo agentInfo = agentManagementService.retrieveAgent(Constants.TEST_PROJECT_ID, uuidStr, "0");
        agentInfo.setCreateTime(null);
        agentInfo.setUpdateTime(null);
        agentInfo.getDetails().setUpdateTime(null);
        Assertions.assertNotNull(agentInfo);

        // 4.copy controller
        AgentInfo copyAgent = agentManagementService.copyAgent(Constants.TEST_PROJECT_ID, uuidStr, "0", "0");
        ControllerVO expectController = JSONObject.parseObject(
            TestUtil.getStringFromFile(String.format("classpath:service/get_controller_%s_agent_res.json", type)),
            AgentInfo.class).getDetails();
        ControllerVO copyControllerVO = copyAgent.getDetails();
        String copyId = copyControllerVO.getId();
        Assertions.assertNotEquals(expectController.getId(), copyControllerVO.getId());
        Assertions.assertNotEquals(expectController.getName(), copyControllerVO.getName());
        Assertions.assertEquals(TestUtil.prettyJson(expectController.setId(null).setName(null)),
            TestUtil.prettyJson(copyAgent.getDetails().setUpdateTime(null).setId(null).setName(null)));
        // 校验记录关联工作流
        if (type.equalsIgnoreCase(ORDER)) {
            Assertions.assertEquals(4,
                mappingMapper.selectByAppIdAndResourceType(copyId, CommonConstant.WORKFLOW_TYPE).size());
        } else {
            Assertions.assertEquals(5,
                mappingMapper.selectByAppIdAndResourceType(copyId, CommonConstant.WORKFLOW_TYPE).size());
        }

    }

    private @NotNull String createController() throws IOException {
        String uuidStr = "125bb1fd-1a74-48a2-97a9-6416cc603999";
        UUID uuid = UUID.fromString(uuidStr);
        ModelServiceData model = (ModelServiceData) new ModelServiceData().setModelName("testDeployName")
            .setId("testDeploymentId")
            .setModelType("openai")
            .setPublishStatus("online");
        List<ModelServiceData> modelList = new ArrayList<>();
        modelList.add(model);
        when(modelServiceManager.queryAvailableServices(anyString(), anyString(), anyString(),
            Mockito.anyBoolean())).thenReturn(modelList);
        try (MockedStatic<UUID> uuidMock = Mockito.mockStatic(UUID.class)) {
            uuidMock.when(UUID::randomUUID).thenReturn(uuid);

            // 1. 创建controller
            final CreateAgentReq req = TestUtil.getJsonObject(CreateAgentReq.class,
                "classpath:service/create_controller_agent_req.json");
            AgentInfo agentInfo = agentManagementService.createAgent(Constants.TEST_PROJECT_ID, "0", req);
            agentInfo.setCreateTime(null);
            agentInfo.setUpdateTime(null);
            agentInfo.getDetails().setUpdateTime(null);
            Assertions.assertEquals(TestUtil.prettyJsonFile("classpath:service/create_controller_agent_res.json"),
                TestUtil.prettyJson(agentInfo));
        }
        return uuidStr;
    }

    @Test
    public void testIntentDslToIr() {
        ModifyAgentReq req = JsonUtils.json2ObjQuietly(
            TestUtil.getStringFromFile("classpath:request/controller_modify_request.json"), ModifyAgentReq.class);
        ControllerVO controllerVO = req.getDetails();
        controllerVO.setId("agentId");
        controllerVO.setName("agentName");
        controllerVO.setDescription("Intent test");
        controllerVO.setProjectId("project_mock");
        controllerVO.setWorkspaceId("workspace_mock");
        controllerVO.setUpdateTime(String.valueOf(System.currentTimeMillis()));

        ReleaseVersion releaseVersion = new ReleaseVersion();
        releaseVersion.setDslPath("controller_intent_dsl_path");
        when(releaseVersionMapper.selectByAppIdAndVersionId("afbd1b1b-74de-43d0-a8d3-147256740906",
            "1754273140406")).thenReturn(releaseVersion);

        // 业务子工作流（node_4ad0c897，type=Normal）版本存在性校验的 mock：
        // 版本表命中 + 工作流属于本空间（project_id + workspace_id 双维度，同保存链路），
        // 即可通过可见性判定
        ReleaseVersion businessReleaseVersion = new ReleaseVersion();
        when(releaseVersionMapper.selectByAppIdAndVersionId("83a951bc-27d7-4ccc-9131-268e93267365",
            "1753499008637")).thenReturn(businessReleaseVersion);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("workspace_mock");
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("project_mock");
        WorkflowEntity businessWorkflow = new WorkflowEntity();
        businessWorkflow.setWorkspaceId("workspace_mock");
        businessWorkflow.setProjectId("project_mock");
        when(workflowMapper.getWorkflowById("83a951bc-27d7-4ccc-9131-268e93267365")).thenReturn(businessWorkflow);

        String intentWorkflowDsl = TestUtil.getStringFromFile("classpath:flow_dsl/intent_for_controller_dsl.json");
        when(obsService.downloadObsFile("controller_intent_dsl_path")).thenReturn(intentWorkflowDsl);

        // 节点根据type和id分组
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = controllerManagementService.groupDslNodes(
            controllerVO);
        ControllerIR ir = controllerManagementService.dslToIr(controllerVO, nodesGroupByTypeId);
        Assertions.assertNotNull(ir);
        Assertions.assertNotNull(ir.getConfigs().getIntentIdentification());
    }

    @Test
    void test_validPermission_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            List<WorkflowEntity> workflowEntities = new ArrayList<>();
            WorkflowEntity workflowEntity = new WorkflowEntity();
            workflowEntities.add(workflowEntity);
            when(workflowMapper.getWorkflowEntityByIds(anyString(), anyString(), anyList())).thenReturn(
                workflowEntities);

            ControllerVO controllerVO = new ControllerVO();
            controllerVO.setProjectId("projectId");
            controllerVO.setWorkspaceId("default");

            List<ControllerNodeVO> nodeList = new ArrayList<>();
            ControllerNodeVO controllerNodeVO = new ControllerNodeVO();
            controllerNodeVO.setConfigs(
                "{\"id\":\"23d196aa-adbf-49b2-a6e6-d2ef37254905\",\"name\":\"gttest_sub3\",\"description\":\"吃饭\",\"version_id\":\"1755607182228\",\"version_name\":\"v20250819203940\",\"code\":\"gttest_sub3\"}");
            controllerNodeVO.setType("Workflow");
            nodeList.add(controllerNodeVO);

            // When
            controllerManagementService.validPermission(controllerVO, nodeList);
        });
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testRecordRefModel() {
        ModifyAgentReq req = JsonUtils.json2ObjQuietly(
            TestUtil.getStringFromFile("classpath:request/controller_modify_request.json"), ModifyAgentReq.class);
        ControllerVO controllerVO = req.getDetails();
        controllerVO.setId("test_agent_id10");
        controllerVO.setName("agentName");
        controllerVO.setDescription("Intent test");
        controllerVO.setProjectId("test_project_id");
        controllerVO.setWorkspaceId("default");
        controllerVO.setUpdateTime(String.valueOf(System.currentTimeMillis()));
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = controllerManagementService.groupDslNodes(
            controllerVO);
        controllerManagementService.recordRefModel(controllerVO, nodesGroupByTypeId);
    }
}
