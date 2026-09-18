/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.type.TypeReference;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerAgentIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIRGlobalIntents;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIRGlobalVariables;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIRIntentIdentification;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIRModelConfig;
import com.openjiuwen.studio.agent.manager.dto.ControllerConfigIRModelConfigHyperParameters;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOAgents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOGlobalIntents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOWorkflows;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerParamIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerWorkflowIR;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.MemoryConfigIR;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.dto.ModelConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.SubControllerNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldIR;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeConfigVOIntent;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.enums.JsonSchemaType;
import com.openjiuwen.studio.agent.manager.enums.ModelTypeV2;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.controller.ActionAfterCompletion;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentMode;
import com.openjiuwen.studio.agent.manager.enums.controller.IntentHandlerType;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentNodeType;
import com.openjiuwen.studio.agent.manager.enums.controller.WorkflowType;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

/**
 * 控制器管理服务
 *
 */
@Service
@Slf4j
public class ControllerManagementService {

    @Value("${controller.show-intent-param.enable}")
    private boolean showIntentParamEnable;

    @Value("${controller.init-intent-dsl}")
    private String controllerInitIntentDsl;

    @Value("${controller.init-intent-dsl-en}")
    private String controllerInitIntentDslEn;

    @Value("${controller.init-dsl}")
    private String controllerInitDsl;

    @Value("${controller.init-dsl-en}")
    private String controllerInitDslEn;

    @Value("${controller.init-ir}")
    private String controllerInitIr;

    @Value("${controller.unique-workflow-types}")
    private String uniqueWorkflowTypes;

    @Value("${controller.configs.max-iteration}")
    private int maxIterationConf;

    @Value("${controller.configs.chat-history-max-turn}")
    private int chatHistoryMaxTurnConf;

    @Value("${controller.global-intend-default-action}")
    private String globalIntendDefaultAction;

    @Value("${controller.workflow-limit}")
    private int controllerWorkflowLimit;

    @Value("${controller.sub-agent-limit}")
    private int controllerSubAgentLimit;

    @Value("${controller.sub-agent-max-depth}")
    private int controllerSubAgentMaxDepth;

    @Value("${workflow.node.interactive-types:}")
    private String workflowInteractiveTypes;

    private Set<String> workflowInteractiveTypesSet;

    private Set<String> uniqueWorkflowTypeSet;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowManagementService workflowManagementService;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Resource
    private MgObsService mgObsService;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private RelationManagementService relationManagementService;

    @Autowired
    private AgentMemoryConfigService agentMemoryConfigService;

    @Autowired
    private IrAdapterService irAdapterService;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    /**
     * 获取控制器主节点
     *
     * @param nodesGroupByTypeId 分组信息
     * @return 控制器主节点
     */
    public ControllerNodeVO getControllerNode(Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        log.debug("Entering getControllerNode with nodesGroupByTypeId={}", nodesGroupByTypeId);

        Map<String, ControllerNodeVO> controllerNodeMap = nodesGroupByTypeId.get(AgentNodeType.CONTROLLER.getType());
        if (MapUtils.isEmpty(controllerNodeMap)) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_LACK_CONTROLLER_NODE);
        }
        ControllerNodeVO controllerNodeVo = controllerNodeMap.values().stream().toList().get(0);
        log.debug("Exiting getControllerNode successfully with result={}", controllerNodeVo);

        return controllerNodeVo;
    }

    @PostConstruct
    private void init() {
        uniqueWorkflowTypeSet =
            Arrays.stream(uniqueWorkflowTypes.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
        workflowInteractiveTypesSet =
            Arrays.stream(workflowInteractiveTypes.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
    }

    /**
     * 创建controller
     *
     * @param projectId 项目id
     * @param body 创建请求体
     * @return 返回控制器
     */
    public AgentInfo createController(String projectId, String workspaceId, CreateAgentReq body) {
        Agent agent = agentCommonService.initAgent(projectId, workspaceId, body);

        // 设置初始化信息
        Boolean isChinese = LanguageUtils.isChinese();
        ControllerVO controllerVo = JSONObject.parseObject(isChinese
            ? (showIntentParamEnable ? controllerInitIntentDsl : controllerInitDsl)
            : (showIntentParamEnable ? controllerInitIntentDslEn : controllerInitDslEn), ControllerVO.class);
        return createController(controllerVo, agent);
    }

    private AgentInfo createController(ControllerVO controllerVo, Agent agent) {
        // 设置controllerId为新agentId
        controllerVo.setId(agent.getAgentId());
        controllerVo.setName(agent.getName());
        controllerVo.setDescription(agent.getDescription());
        controllerVo.setProjectId(agent.getProjectId());
        controllerVo.setWorkspaceId(agent.getWorkspaceId());
        controllerVo.setUpdateTime(String.valueOf(System.currentTimeMillis()));

        // 节点根据type和id分组
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = groupDslNodes(controllerVo);

        // 设置初始模型
        setInitModel(agent.getProjectId(), agent.getWorkspaceId(), nodesGroupByTypeId);

        // dsl转ir
        ControllerIR ir = dslToIr(controllerVo, nodesGroupByTypeId);

        String dslPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.FLOW);
        agent.setDslPath(dslPath);
        String irPath = agentCommonService.getAgentObsPath(agent.getAgentId(), CommonConstant.Workflow.IR);
        agent.setIrPath(irPath);

        // 记录工作流关联关系
        recordRefWorkflow(controllerVo, nodesGroupByTypeId);

        // 记录模型和agent关系
        recordRefModel(controllerVo, nodesGroupByTypeId);

        // 记录子控制器关联关系
        recordRefSubController(controllerVo, nodesGroupByTypeId);

        // 记录单智能体关联关系
        recordRefAgent(controllerVo, nodesGroupByTypeId);

        agentMapper.insert(agent);

        // 上传DSL文件
        agentCommonService.uploadToObs(agent, controllerVo, CommonConstant.Workflow.FLOW);

        // 上传IR文件
        agentCommonService.uploadToObsNoNull(agent, ir, CommonConstant.Workflow.IR);

        return agentCommonService.getAgent(agent.getProjectId(), agent.getWorkspaceId(), agent.getAgentId())
            .convertToDto(controllerVo);
    }

    private void setInitModel(String projectId, String workspaceId,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<>() {});
        if (controllerNodeConfigVo != null && controllerNodeConfigVo.getModel() != null) {
            return;
        }
        List<ModelServiceData> modelList =
            modelServiceManager.queryAvailableServices(projectId, workspaceId, ModelTypeV2.LLM.toString(), true);
        ModelServiceData model = modelList.stream()
            .filter(m -> CommonConstant.ModelParam.MODEL_PUBLISH_STATUS_ONLINE.equals(m.getPublishStatus()))
            .findFirst()
            .orElse(null);
        if (model != null && controllerNodeConfigVo != null) {
            controllerNodeConfigVo.setModel(new ModelConfigVO().setModelDeploymentId(model.getId())
                .setModelName(model.getModelName())
                .setModelType(model.getModelType()));
            controllerNode.setConfigs(controllerNodeConfigVo);
        }
    }

    public void recordRefModel(ControllerVO controllerVo,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});
        if (controllerNodeConfigVo == null) {
            return;
        }
        ModelConfigVO model = controllerNodeConfigVo.getModel();
        if (model == null || model.getModelDeploymentId() == null) {
            mappingMapper.deleteBatchByAppIdAndResourceType(controllerVo.getId(), ResourceTypeEnum.MODEL.toString());
            return;
        }
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());

        // 设置app信息
        mappingEntity.setAppId(controllerVo.getId());
        mappingEntity.setAppName(controllerVo.getName());
        mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
        mappingEntity.setResourceType(ResourceTypeEnum.MODEL.toString());
        if (Strings.CS.equals(ResourceTypeEnum.STRATEGY.toString(), model.getModelType())) {
            mappingEntity.setResourceType(ResourceTypeEnum.STRATEGY.toString());
        }
        mappingEntity.setResourceId(model.getModelDeploymentId());
        mappingEntity.setResourceName(model.getModelName());

        List<MappingEntity> mappingEntities = mappingMapper.selectAllByAppId(controllerVo.getId());
        MappingEntity oldMapping = mappingEntities.stream()
            .filter(
                p -> Strings.CS.equals(p.getResourceType(), ResourceTypeEnum.STRATEGY.toString()) || Strings.CS.equals(
                    p.getResourceType(), ResourceTypeEnum.MODEL.toString()))
            .findFirst()
            .orElse(null);
        if (Objects.nonNull(oldMapping)) {
            mappingEntity.setMappingId(oldMapping.getMappingId());
            mappingMapper.updateById(mappingEntity);
        } else {
            mappingEntity.setMappingId(UUID.randomUUID().toString());
            mappingMapper.insert(mappingEntity);
        }
    }

    /**
     * dsl转IR
     *
     * @return 返回IR内容
     */
    public ControllerIR dslToIr(ControllerVO controllerVo,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        ControllerIR controllerIr;
        try {
            // 数据校验
            valid(controllerVo, nodesGroupByTypeId);

            controllerIr = JSONObject.parseObject(controllerInitIr, ControllerIR.class);
            controllerIr.setAgentId(controllerVo.getId());
            controllerIr.setAgentName(controllerVo.getName());
            controllerIr.setDescription(controllerVo.getDescription());
            List<ControllerParamIR> controllerParamIr = parseInputParam(controllerVo);
            if (!CollectionUtils.isEmpty(controllerParamIr)) {
                controllerIr.setInputs(controllerParamIr);
            }

            // 配置控制器metadata信息，用于合法性校验
            Map<String, Object> metadataMap = new HashMap<>();
            metadataMap.put("projectId", controllerVo.getProjectId());
            metadataMap.put("workspaceId", controllerVo.getWorkspaceId());
            metadataMap.put("updatedAt", controllerVo.getUpdateTime());
            controllerIr.setMetadata(metadataMap);

            buildIrConfigs(controllerVo, controllerIr, nodesGroupByTypeId);
        } catch (AgentStudioException e) {
            log.error("dsl to ir error", e);
            throw e;
        } catch (Exception e) {
            log.error("dsl to ir error", e);
            throw new AgentStudioException(StudioError.CONVERT_NODE_FAILED);
        }
        return controllerIr;
    }

    private List<ControllerParamIR> parseInputParam(ControllerVO controllerVo) {
        List<ControllerParamIR> inputs = new ArrayList<>();

        // 获取输入参数值
        List<WorkflowFieldVO> vars = controllerVo.getInputs();

        if (!CollectionUtils.isEmpty(vars)) {
            for (WorkflowFieldVO dslVar : vars) {
                if (WorkflowFieldVO.SourceEnum.USER.equals(dslVar.getSource())) {
                    ControllerParamIR varIr = new ControllerParamIR().setName(dslVar.getName())
                        .setType(dslVar.getType())
                        .setDescription(dslVar.getDescription())
                        .setRequired(dslVar.isRequired());
                    if (dslVar.getValue() != null && dslVar.getValue().getDefault() != null) {
                        varIr.setDefault(
                            StrUtils.toObjByType(dslVar.getValue().getDefault().toString(), dslVar.getType()));
                    }
                    inputs.add(varIr);
                }
            }
        }
        return inputs;
    }

    private void valid(ControllerVO controllerVo, Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        log.debug("Entering valid with controllerVo={}, nodesGroupByTypeId={}", controllerVo, nodesGroupByTypeId);

        if (controllerVo == null || CollectionUtils.isEmpty(controllerVo.getNodes())) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_NODES_IS_EMPTY);
        }

        // 校验输入参数默认值长度
        for (WorkflowFieldVO controllerVoInput : controllerVo.getInputs()) {
            if (!irAdapterService.validMaxDefaultValueLength(controllerVoInput.getValue().getDefault())) {
                log.error(
                    "The default values of input parameters for multi-agent global configuration have reached the maximum length limit, agentId: {}, fieldName: {}",
                    controllerVo.getId(), controllerVoInput.getName());
                throw new AgentStudioException(StudioError.MULTI_AGENT_INPUT_DEFAULT_VALUE_MAX_LENGTH);
            }
        }

        // 校验全局变量默认值长度
        for (WorkflowFieldVO controllerVoGlobalVariable : controllerVo.getGlobalVariables()) {
            if (!irAdapterService.validMaxDefaultValueLength(controllerVoGlobalVariable.getValue().getDefault())) {
                log.error(
                    "The default value of the global variable for multiple agents has reached the maximum length limit, agentId: {}, fieldName: {}",
                    controllerVo.getId(), controllerVoGlobalVariable.getName());
                throw new AgentStudioException(StudioError.MULTI_AGENT_GLOBAL_VARIABLE_VALUE_MAX_LENGTH);
            }
        }

        // dsl root->nodes->node:type=Controller, controller node 不能为空
        ControllerNodeVO controllerNodeVo = getControllerNode(nodesGroupByTypeId);
        log.debug("Attempting to get controller node from nodesGroupByTypeId");

        // 校验子Agent嵌套最大深度
        Map<String, ControllerNodeVO> controllerNodeIds = nodesGroupByTypeId.get(AgentNodeType.SUB_CONTROLLER.getType());
        if (controllerNodeIds != null) {
            Map<String, ControllerNodeVO> controllerNodeMap = new HashMap<>(controllerNodeIds);
            controllerNodeMap.put(controllerNodeVo.getId(), controllerNodeVo);
            validateMaxControllerDepth(controllerNodeVo.getId(), 0, controllerNodeMap);
        }

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNodeVo.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});
        log.debug("Parsed controller node config: {}", controllerNodeConfigVo);

        if (controllerNodeConfigVo == null) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_CONTROLLER_CONFIGS_NULL);
        }

        // 校验控制器只能挂载一个Plan&Execute模式的子Agent
        validatePlanExecuteAgentCount(controllerNodeConfigVo);

        // 校验Plan&Execute模式的子Agent只能挂在顶层控制器
        validatePlanExecuteAgentParentNode(nodesGroupByTypeId);

        // 检查工作流不能重复
        List<ControllerNodeConfigVOWorkflows> workflows = controllerNodeConfigVo.getWorkflows();
        log.debug("Found {} workflows in controller node config", workflows.size());

        // 校验意图识别工作流和模型配置必须存在一个
        List<ControllerNodeConfigVOWorkflows> intentWorkflows = workflows.stream().filter(workflow -> Strings.CI.equals(WorkflowType.INTENT.getType(), workflow.getType())).toList();
        if (Optional.ofNullable(controllerNodeConfigVo.getModel()).map(ModelConfigVO::getModelDeploymentId).isEmpty() && CollectionUtils.isEmpty(intentWorkflows)) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_MODEL_OR_INTENT_IS_NULL);
        }

        if (!CollectionUtils.isEmpty(workflows)) {
            Set<String> tempWfSet = new HashSet<>();
            workflows.forEach(wf -> {
                if (uniqueWorkflowTypeSet.contains(wf.getType()) && !tempWfSet.add(wf.getId())) {
                    String error = String.format("Duplicate workflow name : %s", wf.getName());
                    log.error(error);
                    throw new AgentStudioException(StudioError.MULTI_AGENT_HAVE_DUPLICATE_SON_WORKFLOW);
                }
            });

            // 校验意图工作流以及子工作流不能包含交互类节点
            validateIntentWorkflow(nodesGroupByTypeId, workflows);
        }
        log.debug("Successfully validated intent workflows and sub workflows");

        // 检查Agent流不能重复
        List<ControllerNodeConfigVOAgents> agents = controllerNodeConfigVo.getAgents();
        if (!CollectionUtils.isEmpty(agents)) {
            Set<String> tempAgentSet = new HashSet<>();
            agents.forEach(agent -> {
                if (!tempAgentSet.add(agent.getId())) {
                    String error = String.format("Duplicate agent name : %s", agent.getName());
                    log.error(error);
                    throw new AgentStudioException(StudioError.MULTI_AGENT_HAVE_DUPLICATE_SON_AGENT, agent.getName());
                }
            });
        }
    }

    private boolean validateMaxControllerDepth(String nodeId, int currentDepth,
        Map<String, ControllerNodeVO> subControllerNodeIds) {
        // 超过最大层级限制，抛出异常
        if (currentDepth > controllerSubAgentMaxDepth) {
            return false;
        }
        ControllerNodeVO node = subControllerNodeIds.get(nodeId);

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(node.getConfigs(), new TypeReference<>() {});
        if (controllerNodeConfigVo == null) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_CONTROLLER_CONFIGS_NULL);
        }
        List<ControllerNodeConfigVOAgents> agents = Optional.ofNullable(controllerNodeConfigVo.getAgents())
                .orElseGet(Collections::emptyList) // 如果是 null，转为空列表，防止后面 .stream() 报错
                .stream()
                .filter(agent -> AgentMode.CONTROLLER.getMode().equals(agent.getMode()))
                .collect(Collectors.toList());
        if (!CollectionUtils.isEmpty(agents)) {
            agents.forEach(agent -> {
                boolean validateRes = validateMaxControllerDepth(agent.getNodeId(), currentDepth + 1,
                    subControllerNodeIds);
                if (!validateRes) {
                    log.error("validateMaxControllerDepth error, agentId: {}", controllerNodeConfigVo.getId());
                    throw new AgentStudioException(StudioError.MULTI_AGENT_EXCEED_MAX_DEPTH,
                        controllerNodeConfigVo.getName(), controllerNodeConfigVo.getId());
                }
            });
        }
        return true;
    }


    /**
     * 校验控制器只能挂载一个Plan&Execute模式的子Agent
     */
    private void validatePlanExecuteAgentCount(ControllerNodeConfigVO controllerNodeConfigVo) {
        List<ControllerNodeConfigVOAgents> agents = controllerNodeConfigVo.getAgents();
        if (CollectionUtils.isEmpty(agents)) {
            return;
        }

        long planExecuteAgentCount = agents.stream()
                .filter(agent -> AgentMode.PLANEXECUTE.getMode().equals(agent.getMode()))
                .count();

        if (planExecuteAgentCount > 1) {
            log.error("Controller only supports one PlanExecute mode agent, but found {}", planExecuteAgentCount);
            throw new AgentStudioException(StudioError.MULTI_AGENT_ONLY_ONE_PLAN_EXECUTE_AGENT);
        }
    }

    /**
     * 校验Plan&Execute模式的子Agent只能挂在顶层控制器
     * 只需检查所有SubController节点本身是否挂载了PlanExecute模式的Agent
     */
    private void validatePlanExecuteAgentParentNode(Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        // 获取所有SubController节点
        Map<String, ControllerNodeVO> subControllerNodes = nodesGroupByTypeId.get(AgentNodeType.SUB_CONTROLLER.getType());
        if (CollectionUtils.isEmpty(subControllerNodes)) {
            return;
        }

        // 检查每个SubController节点是否直接挂载了PlanExecute模式的Agent
        for (ControllerNodeVO subControllerNode : subControllerNodes.values()) {
            ControllerNodeConfigVO controllerNodeConfigVo = JsonUtils.objectToClassRef(
                    subControllerNode.getConfigs(), new TypeReference<>() {}
            );

            if (controllerNodeConfigVo == null) {
                log.error("SubController {} configs is null", subControllerNode.getId());
                throw new AgentStudioException(StudioError.MULTI_AGENT_CONTROLLER_CONFIGS_NULL);
            }

            List<ControllerNodeConfigVOAgents> agents = controllerNodeConfigVo.getAgents();
            if (!CollectionUtils.isEmpty(agents)) {
                // 检查当前SubController是否挂载了PlanExecute模式的Agent
                List<ControllerNodeConfigVOAgents> planExecuteAgents = agents.stream()
                        .filter(agent -> AgentMode.PLANEXECUTE.getMode().equals(agent.getMode()))
                        .collect(Collectors.toList());

                if (!planExecuteAgents.isEmpty()) {
                    List<String> planExecuteAgentNames = planExecuteAgents.stream()
                            .map(ControllerNodeConfigVOAgents::getName)
                            .collect(Collectors.toList());
                    log.error("SubController {} has forbidden PlanExecute agents: {}",
                            subControllerNode.getName(), planExecuteAgentNames);
                    throw new AgentStudioException(StudioError.MULTI_AGENT_PLAN_EXECUTE_ONLY_IN_TOP_CONTROLLER);
                }
            }
        }
    }

    private void validateIntentWorkflow(Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId,
        List<ControllerNodeConfigVOWorkflows> workflows) {
        log.debug("Entering validateIntentWorkflow with nodesGroupByTypeId={}, workflows={}", nodesGroupByTypeId,
            workflows);

        ControllerNodeVO intentNode = getIntentNode(nodesGroupByTypeId, workflows);
        if (intentNode == null) {
            return;
        }
        Map<String, Object> intentConfig = JsonUtils.objectToClass(intentNode.getConfigs());
        log.debug("Parsed intent configuration: {}", intentConfig);

        if (intentConfig == null) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_CONFIG_VALID);
        }
        String workflowId = intentConfig.get("id").toString();
        String versionId = intentConfig.get("version_id").toString();
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);
        log.debug("Fetched release version: {}", releaseVersion);

        if (releaseVersion == null) {
            throw new AgentStudioException(StudioError.WORKFLOW_VERSION_NOT_FOUND);
        }
        String workflowJson = mgObsService.downloadObsFile(releaseVersion.getDslPath());
        WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);
        List<WorkflowNodeVO> workflowNode = workflowVo.getNodes();
        WorkflowNodeVO workflowNodeID =
            WorkflowUtils.getWorkflowNodeID(CommonConstant.ControllerConstants.INPUT_KEY, workflowNode);
        List<WorkflowFieldVO> workflowFieldList = workflowNodeID == null ? null : workflowNodeID.getOutputs();

        if (workflowFieldList != null) {
            workflowFieldList =
                workflowFieldList.stream().filter(m -> !Strings.CS.equals(CommonConstant.SYS, m.getName())).toList();
        }

        WorkflowNodeVO endNode =
            WorkflowUtils.getWorkflowNodeID(CommonConstant.ControllerConstants.OUTPUT_KEY, workflowNode);
        log.debug("Retrieved output node: {}", endNode);

        List<WorkflowFieldVO> outputs = endNode == null ? null : endNode.getOutputs();
        if (workflowFieldList == null || outputs == null) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_INPUT_EMPTY);
        }

        // 校验意图工作流输入输出.
        validateIntentInputs(workflowFieldList);
        validateIntentOutputs(outputs);

        // 校验工作流以及子工作流是否包含交互式节点
        validateWorkflowHasInteractiveNode(workflowVo);
        log.debug("Exiting validateIntentWorkflow successfully");
    }

    private ControllerNodeVO getIntentNode(Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId,
        List<ControllerNodeConfigVOWorkflows> workflows) {
        Map<String, ControllerNodeVO> workflowNodeMap = nodesGroupByTypeId.get(AgentNodeType.WORKFLOW.getType());

        if (MapUtils.isEmpty(workflowNodeMap)) {
            return null;
        }
        String intentWorkflowId = null;
        for (ControllerNodeConfigVOWorkflows workflow : workflows) {
            boolean isIntent = Strings.CS.equals(workflow.getType(), WorkflowType.INTENT.getType());

            if (!isIntent) {
                continue;
            }
            if (StringUtils.isNotEmpty(intentWorkflowId)) {
                throw new AgentStudioException(StudioError.MULTI_AGENT_DUPLICATED_NODE);
            }
            intentWorkflowId = workflow.getNodeId();
        }
        return StringUtils.isEmpty(intentWorkflowId) ? null : workflowNodeMap.get(intentWorkflowId);
    }

    private void validateIntentInputs(List<WorkflowFieldVO> inputs) {
        Set<String> requiredFields = new HashSet<>(Arrays.asList("query", "messages", "intents"));
        for (WorkflowFieldVO workflowField : inputs) {
            switch (workflowField.getName()) {
                case "query" -> {
                    log.debug("Validating query parameter");

                    if (!JsonSchemaType.STRING.type.equals(workflowField.getType()) || !workflowField.isRequired()) {
                        throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_PARAM_VALID);
                    }
                }
                case "messages" -> validateMessagesParam(workflowField);
                case "intents" -> validateIntentsParam(workflowField);
                case "minScore" -> {
                    log.debug("Validating minScore parameter");

                    if (!JsonSchemaType.NUMBER.type.equals(workflowField.getType()) || workflowField.isRequired()) {
                        throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_MIN_SCORE_VALID);
                    }
                }
                default -> {
                }
            }
            requiredFields.remove(workflowField.getName());
        }
        if (requiredFields.size() > 0) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_MISSING, requiredFields);
        }
    }

    private void validateIntentOutputs(List<WorkflowFieldVO> outputs) {

        Set<String> requiredFields = new HashSet<>(List.of("intent_id"));
        for (WorkflowFieldVO param : outputs) {

            if (param.getName().equals("intent_id")) {
                if (!JsonSchemaType.INTEGER.type.equals(param.getType())) {
                    throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_INTENT_VALID);
                }
            }
            requiredFields.remove(param.getName());
        }
        if (requiredFields.size() > 0) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_OUTPUT_MISSING, requiredFields);
        }
    }

    private void validateMessagesParam(WorkflowFieldVO messagesParam) {
        String errorMessage = "intent workflow input param messages is not valid";
        List<Map<String, Object>> schemaList = extractSubSchemaList(messagesParam, errorMessage);
        Set<String> requiredFields = new HashSet<>(List.of("role", "content"));
        for (Map<String, Object> subParam : schemaList) {
            String subParamName = subParam.getOrDefault("name", StringUtils.EMPTY).toString();

            switch (subParamName) {
                case "role", "content" -> {
                    if (!JsonSchemaType.STRING.type.equals(subParam.get("type"))
                        || !Boolean.TRUE.equals(subParam.get("required"))) {
                        throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_INPUT_SUB_PARAM_VALID,
                            subParamName);
                    }
                }
                default -> {
                }
            }
            requiredFields.remove(subParamName);
        }
        if (requiredFields.size() > 0) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_MESSAGE_MISSING, requiredFields);
        }
    }

    private void validateIntentsParam(WorkflowFieldVO intentsParam) {
        String errorMessage = "intent workflow input param intents is not valid";
        List<Map<String, Object>> schemaList = extractSubSchemaList(intentsParam, errorMessage);
        Set<String> requiredFields = new HashSet<>(List.of("id", "name"));
        for (Map<String, Object> subParams : schemaList) {
            String subParamName = subParams.getOrDefault("name", StringUtils.EMPTY).toString();
            switch (subParamName) {
                case "id", "name" -> {
                    if (!JsonSchemaType.STRING.type.equals(subParams.get("type"))
                        || !Boolean.TRUE.equals(subParams.get("required"))) {
                        throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_INTENT_PARAM_VALID,
                            subParamName);
                    }
                }
                default -> {
                }
            }
            requiredFields.remove(subParamName);
        }
        if (requiredFields.size() > 0) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_PROPERTY_MISS, requiredFields);
        }
    }

    private List<Map<String, Object>> extractSubSchemaList(WorkflowFieldVO messageParam, String errorMessage) {
        // 类型为array，必选参数
        if (!JsonSchemaType.ARRAY.type.equals(messageParam.getType())
            || !Boolean.TRUE.equals(messageParam.isRequired())) {
            throw new AgentStudioException(StudioError.CONTROLLER_INVALID_WORKFLOW);
        }

        // 校验schema类型
        Map<String, Object> schema = JsonUtils.objectToClass(messageParam.getSchema());
        if (schema == null) {
            throw new AgentStudioException(StudioError.CONTROLLER_INVALID_WORKFLOW);
        }
        if (!JsonSchemaType.OBJECT.type.equals(schema.get("type"))) {
            throw new AgentStudioException(StudioError.CONTROLLER_INVALID_WORKFLOW);
        }
        List<Object> schemaListObject = JsonUtils.objectToClass(schema.get("schema"));
        if (schemaListObject == null) {
            throw new AgentStudioException(StudioError.CONTROLLER_INVALID_WORKFLOW);
        }
        // json类型转换, 转换失败或元素不对齐直接失败
        return schemaListObject.stream().map(JsonUtils::<Map<String, Object>> objectToClass).toList();
    }

    private void validateWorkflowHasInteractiveNode(WorkflowVO workflowVo) {
        if (workflowVo == null || CollectionUtils.isEmpty(workflowVo.getNodes())) {
            return;
        }
        for (WorkflowNodeVO nodeInfo : workflowVo.getNodes()) {
            if (workflowInteractiveTypesSet.contains(nodeInfo.getType())) {
                throw new AgentStudioException(StudioError.MULTI_AGENT_WORKFLOW_CONTAIN_NODE);
            }
            // 工作流节点，递归校验
            if (NodeType.WORKFLOW.getType()
                .equals(nodeInfo.getType())) {
                String workflowId = nodeInfo.getConfigs().get("id").toString();
                String versionId = nodeInfo.getConfigs().get("version_id").toString();
                ReleaseVersion releaseVersions = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);
                if (releaseVersions == null) {
                    throw new AgentStudioException(StudioError.MULTI_AGENT_SUB_WORKFLOW_VERSION_NOT_FOUND, versionId);
                }
                String workflowJson = mgObsService.downloadObsFile(releaseVersions.getDslPath());
                WorkflowVO subWorkflowsVo = JSON.parseObject(workflowJson, WorkflowVO.class);
                validateWorkflowHasInteractiveNode(subWorkflowsVo);
            }
        }
    }

    private void buildIrConfigs(ControllerVO controllerVo, ControllerIR controllerIr,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        // 1.设置 mode 在init-ir已设置

        // ir controller configs | root -> configs
        ControllerConfigIR controllerIrConfigs = controllerIr.getConfigs();

        // dsl Controller节点 | root -> nodes -> node:type=Controller
        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);

        // dsl Workflow节点 | root -> nodes -> node:type=Workflow
        Map<String, ControllerNodeVO> nodeMap = nodesGroupByTypeId.get(AgentNodeType.WORKFLOW.getType());

        // dsl controller节点configs | root -> nodes -> node:type=Controller -> configs
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});

        // controllerNode.configs必须存在才有效，如果没有不做后续转ir，转了也没用
        if (controllerNodeConfigVo == null) {
            log.error("controllerNode.Configs is null");
            return;
        }

        // 设置意图识别类型工作流
        ControllerNodeVO intentNodes = getIntentNode(nodesGroupByTypeId, controllerNodeConfigVo.getWorkflows());
        if (intentNodes != null) {
            ControllerConfigIRIntentIdentification intentIdentification = new ControllerConfigIRIntentIdentification();
            intentIdentification.setId(intentNodes.getId());
            intentIdentification.setType(ControllerConfigIRIntentIdentification.TypeEnum.WORKFLOW);
            controllerIrConfigs.setIntentIdentification(intentIdentification);
        }

        // 3.设置 modelConfig
        buildIrModelConfig(controllerNodeConfigVo, controllerIrConfigs);

        // 4.设置 workflows
        buildIrWorkflows(controllerIrConfigs, controllerNodeConfigVo, nodeMap);

        // 获取子agent节点配置：包括AGENT和SUB_CONTROLLER类型的节点
        Map<String, ControllerNodeVO> agentNodeMap = nodesGroupByTypeId.computeIfAbsent(AgentNodeType.SUB_CONTROLLER.getType(), k -> new HashMap<>());
        Map<String, ControllerNodeVO> agentTypeNodeMap = nodesGroupByTypeId.get(AgentNodeType.AGENT.getType());
        if (!CollectionUtils.isEmpty(agentTypeNodeMap)) {
            agentNodeMap.putAll(agentTypeNodeMap);
        }

        // 4.1设置 agents
        buildIrAgents(controllerIrConfigs, controllerNodeConfigVo, agentNodeMap);

        // 5.设置 maxIteration
        Integer maxIteration = controllerNodeConfigVo.getMaxIteration();
        controllerIrConfigs.setMaxIteration(maxIteration != null ? maxIteration : maxIterationConf);

        // 6.设置 global_intents
        buildIrGlobalIntents(controllerNodeConfigVo, controllerIrConfigs);

        // 7.设置 global_variables
        buildGlobalVars(controllerVo, controllerIrConfigs);

        // 8.设置prompt
        controllerIrConfigs.setSysPromptTemplate(controllerNodeConfigVo.getPrompt());

        // 不设置引擎报错
        controllerIrConfigs.setPlugins(new ArrayList<>());

        // 9.设置 chatHistoryMaxTurn
        Integer chatHistoryMaxTurn = controllerNodeConfigVo.getChatHistoryMaxTurn();
        controllerIrConfigs
            .setChatHistoryMaxTurn(chatHistoryMaxTurn != null ? chatHistoryMaxTurn : chatHistoryMaxTurnConf);
    }

    /**
     * 按类型 id ControllerNodeVO分组
     *
     * @param controllerVo 控制器参数
     * @return 返回分组内容
     */
    public Map<String, Map<String, ControllerNodeVO>> groupDslNodes(ControllerVO controllerVo) {
        Map<String, Map<String, ControllerNodeVO>> groupMap = new HashMap<>();
        if (CollectionUtils.isEmpty(controllerVo.getNodes())) {
            return groupMap;
        }

        for (ControllerNodeVO nodeVo : controllerVo.getNodes()) {
            Map<String, ControllerNodeVO> idMaps = groupMap.computeIfAbsent(nodeVo.getType(), k -> new HashMap<>());
            idMaps.put(nodeVo.getId(), nodeVo);
        }
        return groupMap;
    }

    private void buildIrModelConfig(ControllerNodeConfigVO controllerNodeConfigVo, ControllerConfigIR irConfigs) {
        // ir 设置modelConfig |root->configs->modelConfig

        // ir 构建hyperParameters | root->configs->modelConfig->hyperParameters
        ControllerConfigIRModelConfigHyperParameters irHyperParameters =
            new ControllerConfigIRModelConfigHyperParameters().setTemperature(controllerNodeConfigVo.getTemperature())
                .setTopP(controllerNodeConfigVo.getTopP());
        // ir 构架modelConfig其他参数

        // dsl 获取Controller节点上的模型配置| root -> nodes -> node:type=Controller->configs->model
        ModelConfigVO controllerNodeConfigVoModel = controllerNodeConfigVo.getModel();
        if (controllerNodeConfigVoModel != null && !StringUtils.isEmpty(controllerNodeConfigVoModel.getModelDeploymentId())) {
            irConfigs.setModelConfig(
                new ControllerConfigIRModelConfig().setModelName(controllerNodeConfigVoModel.getModelDeploymentId())
                    .setModelType(controllerNodeConfigVoModel.getModelType())
                    .setDeploymentId(controllerNodeConfigVoModel.getModelDeploymentId())
                    .setHyperParameters(irHyperParameters)
                    .setExtension(modelServiceManager.parseModelExtension(
                        controllerNodeConfigVoModel.getModelDeploymentId(), RequestContextUtils.getRequestProjectId(),
                        RequestContextUtils.getRequestWorkspaceId(), false)));
        }
    }

    private void buildGlobalVars(ControllerVO controllerVo, ControllerConfigIR irConfigs) {
        // dsl| root->global_variables
        List<WorkflowFieldVO> vars = controllerVo.getGlobalVariables();
        // ir| root -> configs -> global_variables
        List<ControllerConfigIRGlobalVariables> globalVarsIr = irConfigs.getGlobalVariables();
        if (!CollectionUtils.isEmpty(vars)) {
            for (WorkflowFieldVO dslVar : vars) {
                ControllerConfigIRGlobalVariables varIr = new ControllerConfigIRGlobalVariables();
                globalVarsIr.add(varIr);

                varIr.setName(dslVar.getName());
                varIr.setType(dslVar.getType());
                varIr.setDescription(dslVar.getDescription());
                if (dslVar.getValue() != null && dslVar.getValue().getDefault() != null) {
                    varIr.setDefault(StrUtils.toObjByType(dslVar.getValue().getDefault().toString(), dslVar.getType()));
                }
            }
        }
    }

    private void buildIrGlobalIntents(ControllerNodeConfigVO controllerNodeConfigVo, ControllerConfigIR irConfigs) {
        // dsl | root -> nodes -> node:type=Controller
        List<ControllerNodeConfigVOGlobalIntents> globalIntents = controllerNodeConfigVo.getGlobalIntents();

        // ir | root->configs->global_intents
        List<ControllerConfigIRGlobalIntents> irIntents = irConfigs.getGlobalIntents();
        if (!CollectionUtils.isEmpty(globalIntents)) {
            for (ControllerNodeConfigVOGlobalIntents controllerNodeConfigVoGlobalIntents : globalIntents) {
                ControllerConfigIRGlobalIntents irGlobalIntents = new ControllerConfigIRGlobalIntents();
                irIntents.add(irGlobalIntents);

                irGlobalIntents.setName(controllerNodeConfigVoGlobalIntents.getName());
                irGlobalIntents.setDescription(controllerNodeConfigVoGlobalIntents.getName());
                irGlobalIntents.setIntentId(controllerNodeConfigVoGlobalIntents.getId());
                irGlobalIntents
                    .setHandlerType(IntentHandlerType.dslToIr(controllerNodeConfigVoGlobalIntents.getHandlerType()));

                // 兼容处理从terminal换成action
                if (!StringUtils.isEmpty(controllerNodeConfigVoGlobalIntents.getAction())) {
                    irGlobalIntents.setActionAfterCompletion(controllerNodeConfigVoGlobalIntents.getAction());
                } else {
                    if (controllerNodeConfigVoGlobalIntents.isTermination() != null
                        && controllerNodeConfigVoGlobalIntents.isTermination()) {
                        irGlobalIntents.setActionAfterCompletion(ActionAfterCompletion.TERMINAL.getAction());
                    } else {
                        irGlobalIntents.setActionAfterCompletion(globalIntendDefaultAction);
                    }
                }
                if (IntentHandlerType.WORKFLOW.getDsl()
                    .equalsIgnoreCase(controllerNodeConfigVoGlobalIntents.getHandlerType())) {
                    ControllerWorkflowIR workflowIr = new ControllerWorkflowIR();
                    irGlobalIntents.setHandler(workflowIr);
                    ControllerNodeVO intentWorkflowVo = JsonUtils
                        .objectToClassType(controllerNodeConfigVoGlobalIntents.getHandler(), ControllerNodeVO.class);

                    WorkflowNodeConfigVO workflowNodeConfigVo = null;
                    if (intentWorkflowVo != null) {
                        workflowNodeConfigVo =
                            JsonUtils.objectToClassType(intentWorkflowVo.getConfigs(), WorkflowNodeConfigVO.class);
                    }
                    if (workflowNodeConfigVo != null) {
                        workflowIr.setId(workflowNodeConfigVo.getId());
                        workflowIr.setName(workflowNodeConfigVo.getName());
                        workflowIr.setDescription(workflowNodeConfigVo.getDescription());
                        workflowIr.setIrPath(workflowManagementService.getWorkflowObsPath(intentWorkflowVo.getId(),
                            CommonConstant.Workflow.IR, workflowNodeConfigVo.getVersionId()));

                        // 输入输出字段转ir
                        wfFieldsToIr(intentWorkflowVo, workflowIr);
                    }
                } else {
                    irGlobalIntents.setHandler(controllerNodeConfigVoGlobalIntents.getHandler());
                }
            }
        }
    }

    private void wfFieldsToIr(ControllerNodeVO intentWorkflowVo, ControllerWorkflowIR workflowIr) {
        List<WorkflowFieldVO> inputs = intentWorkflowVo.getInputs();
        if (!CollectionUtils.isEmpty(inputs)) {
            workflowIr.setArguments(inputs.stream()
                .filter(input -> !Objects.isNull(input.getName()) && !Objects.isNull(input.getType()))
                .map(this::inputToIr)
                .toList());
        }
        List<WorkflowFieldVO> outputs = intentWorkflowVo.getOutputs();
        if (!CollectionUtils.isEmpty(outputs)) {
            workflowIr.setResponse(outputs.stream()
                .filter(output -> !Objects.isNull(output.getName()) && !Objects.isNull(output.getType()))
                .map(this::outputToIr)
                .toList());
        }
    }

    private WorkflowFieldIR inputToIr(WorkflowFieldVO workflowFieldVo) {
        WorkflowFieldIR fieldIR = new WorkflowFieldIR();
        fieldIR.setName(workflowFieldVo.getName());
        fieldIR.setType(workflowFieldVo.getType());
        fieldIR.setDescription(workflowFieldVo.getDescription());
        fieldIR.setDefaultValue(workflowFieldVo.getValue() == null ? null : workflowFieldVo.getValue().getDefault());
        fieldIR.setRequired(workflowFieldVo.isRequired());
        fieldIR.setSchema(workflowFieldVo.getSchema());
        // 默认body
        fieldIR.setMethod(CommonConstant.ControllerConstants.IR_ARG_BODY_METHOD);
        // 默认true
        fieldIR.setVisible(true);
        return fieldIR;
    }

    private WorkflowFieldIR outputToIr(WorkflowFieldVO workflowFieldVo) {
        WorkflowFieldIR fieldIR = new WorkflowFieldIR();
        fieldIR.setName(workflowFieldVo.getName());
        fieldIR.setType(workflowFieldVo.getType());
        fieldIR.setDescription(workflowFieldVo.getDescription());
        fieldIR.setSchema(workflowFieldVo.getSchema());
        return fieldIR;
    }

    private void buildIrWorkflows(ControllerConfigIR irConfigs, ControllerNodeConfigVO controllerNodeConfigVo,
        Map<String, ControllerNodeVO> nodeMap) {
        // ir 工作流列表获取 | root->configs->workflows
        List<ControllerWorkflowIR> irConfigsWorkflows = irConfigs.getWorkflows();

        // dsl 工作流controller节点，configs下的workflows | root->nodes->node:type=Controller->configs->workflows
        List<ControllerNodeConfigVOWorkflows> controllerWorkflows = controllerNodeConfigVo.getWorkflows();
        if (!CollectionUtils.isEmpty(controllerWorkflows)) {
            for (ControllerNodeConfigVOWorkflows dslConfigWorkflow : controllerWorkflows) {
                // ir 新建工作流IR对象 | root->configs->workflows->workflow
                ControllerWorkflowIR irWorkflow = new ControllerWorkflowIR();
                irConfigsWorkflows.add(irWorkflow);

                ControllerNodeVO workflowNode = nodeMap.get(dslConfigWorkflow.getNodeId());
                if (workflowNode == null) {
                    log.error("workflow node not found by nodeId: {}", dslConfigWorkflow.getNodeId());
                    continue;
                }
                WorkflowNodeConfigVO wfNodeConfigs =
                    JsonUtils.objectToClassType(workflowNode.getConfigs(), WorkflowNodeConfigVO.class);

                wfFieldsToIr(workflowNode, irWorkflow);

                // ir 构建workflow | root->configs->workflows->workflow
                if (wfNodeConfigs != null) {
                    irWorkflow.setId(dslConfigWorkflow.getNodeId())
                        .setName(wfNodeConfigs.getName())
                        .setDescription(wfNodeConfigs.getDescription())
                        .setWorkflowType(workflowNode.getType())
                        .setIrPath(workflowManagementService.getWorkflowObsPath(wfNodeConfigs.getId(),
                            CommonConstant.Workflow.IR, wfNodeConfigs.getVersionId()))
                        .setWorkflowType(dslConfigWorkflow.getType());
                    WorkflowNodeConfigVOIntent intent = wfNodeConfigs.getIntent();
                    String name = intent != null && !StringUtils.isEmpty(intent.getName()) ? intent.getName()
                        : wfNodeConfigs.getName();

                    // 1027新增，中间过渡版本intent下description为空，兼容后，根据description判断是否为用户存量手动修改
                    String description = intent != null && !StringUtils.isEmpty(intent.getDescription())
                            ? intent.getDescription() : StringUtils.EMPTY;
                    if (StringUtils.isNotEmpty(description)) {
                        irWorkflow.setDescription(description);
                    }
                    irWorkflow.setIntent(new WorkflowNodeConfigVOIntent().setName(name).setDescription(description));
                }

                // 设置ActionAfterCompletion，end时为terminal
                WorkflowType workflowType = WorkflowType.typeOf(dslConfigWorkflow.getType());
                switch (workflowType) {
                    case START -> irWorkflow.setActionAfterCompletion(ActionAfterCompletion.CONTINUE.getAction());
                    case END -> irWorkflow.setActionAfterCompletion(ActionAfterCompletion.TERMINAL.getAction());
                    default -> irWorkflow.setActionAfterCompletion(StringUtils.isEmpty(dslConfigWorkflow.getAction())
                        ? ActionAfterCompletion.CONTINUE.getAction() : dslConfigWorkflow.getAction());
                }
            }
        }
    }

    private void buildIrAgents(ControllerConfigIR irConfigs, ControllerNodeConfigVO controllerNodeConfigVo,
        Map<String, ControllerNodeVO> nodeMap) {
        List<ControllerAgentIR> irConfigsAgents = irConfigs.getAgents();

        List<ControllerNodeConfigVOAgents> controllerAgents = controllerNodeConfigVo.getAgents();
        if (!CollectionUtils.isEmpty(controllerAgents)) {
            for (ControllerNodeConfigVOAgents dslConfigAgent : controllerAgents) {
                ControllerAgentIR irAgent = new ControllerAgentIR();
                irConfigsAgents.add(irAgent);

                ControllerNodeVO agentNode = nodeMap.get(dslConfigAgent.getNodeId());
                if (agentNode == null) {
                    log.error("agent node not found by nodeId: {}", dslConfigAgent.getNodeId());
                    continue;
                }
                SubControllerNodeConfigVO nodeConfigs =
                    JsonUtils.objectToClassType(agentNode.getConfigs(), SubControllerNodeConfigVO.class);

                List<WorkflowFieldVO> inputs = agentNode.getInputs();
                if (!CollectionUtils.isEmpty(inputs)) {
                    irAgent.setArguments(inputs.stream().map(this::inputToIr).toList());
                }
                List<WorkflowFieldVO> outputs = agentNode.getOutputs();
                if (!CollectionUtils.isEmpty(outputs)) {
                    irAgent.setResponse(outputs.stream().map(this::outputToIr).toList());
                }

                if (nodeConfigs != null) {
                    irAgent.setId(dslConfigAgent.getNodeId())
                        .setName(nodeConfigs.getName())
                        .setDescription(nodeConfigs.getDescription())
                        .setMode(dslConfigAgent.getMode())
                        .setIrPath(agentCommonService.getAgentObsPath(nodeConfigs.getId(), CommonConstant.Workflow.IR,
                            nodeConfigs.getVersionId()));
                    WorkflowNodeConfigVOIntent intent = nodeConfigs.getIntent();
                    String name = intent != null && !StringUtils.isEmpty(intent.getName()) ? intent.getName()
                        : nodeConfigs.getName();

                    // 1027新增，中间过渡版本intent下description为空，兼容后，根据description判断是否为用户存量手动修改
                    String description = intent != null && !StringUtils.isEmpty(intent.getDescription())
                        ? intent.getDescription() : StringUtils.EMPTY;
                    if (StringUtils.isNotEmpty(description)) {
                        irAgent.setDescription(description);
                    }
                    irAgent.setIntent(new WorkflowNodeConfigVOIntent().setName(name).setDescription(description));
                }
            }
        }
    }

    /**
     * 更新controller型Agent
     *
     * @param agent 应用
     * @param body 修改消息体
     * @return 返回修改后的应用
     */
    public AgentInfo modify(Agent agent, String projectId, String workspaceId, ModifyAgentReq body) {
        ControllerVO controllerVo = body.getDetails();
        controllerVo.setId(agent.getAgentId());
        controllerVo.setName(agent.getName());
        controllerVo.setDescription(agent.getDescription());
        controllerVo.setProjectId(projectId);
        controllerVo.setWorkspaceId(workspaceId);
        controllerVo.setUpdateTime(String.valueOf(System.currentTimeMillis()));

        // 节点根据type和id分组
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = groupDslNodes(controllerVo);

        // 修改时系统参数
        replaceDefaultSystemInput(controllerVo);

        // dsl转ir
        ControllerIR ir = dslToIr(controllerVo, nodesGroupByTypeId);

        // dsl中的记忆配置转ir
        convertControllerMemoryToIr(body, ir);

        // 记录工作流关联关系
        recordRefWorkflow(controllerVo, nodesGroupByTypeId);

        // 记录子控制器关联关系
        recordRefSubController(controllerVo, nodesGroupByTypeId);

        // 记录单智能体关联关系
        recordRefAgent(controllerVo, nodesGroupByTypeId);

        // 记录模型和agent关系
        recordRefModel(controllerVo, nodesGroupByTypeId);

        // 处理agent和memory的关联信息入库
        if (body.getMemoryConfig() != null && body.getMemoryConfig().getMemoryRepoId() != null) {
            relationManagementService.handleAgentMemoryRepo(projectId, workspaceId, agent.getAgentId(), body.getMemoryConfig().getMemoryRepoId(), CommonConstant.CONTROLLER_TYPE);
        }
        agentMapper.updateByPrimaryKeySelective(agent);
        mappingMapper.updateAppNameByAppId(agent.getAgentId(), agent.getName());

        // dsl只存储了controllerVo对象的内容，只能把记忆相关配置再放到controllerVo中一次
        controllerVo.setMemoryConfig(body.getMemoryConfig());
        // 上传dsl
        agentCommonService.uploadToObs(agent, controllerVo, CommonConstant.Workflow.FLOW);

        // 上传ir
        agentCommonService.uploadToObsNoNull(agent, ir, CommonConstant.Workflow.IR);

        return agentCommonService.getAgent(agent.getProjectId(), workspaceId, agent.getAgentId())
            .convertToDto(controllerVo);
    }

    private static @NotNull String getRefKey(MappingEntity entity) {
        return entity.getResourceId() + "_" + entity.getResourceVersion() + "_" + entity.getResourceType();
    }

    /**
     * dsl中的记忆配置转ir
     *
     * @param body
     * @param ir
     */
    private void convertControllerMemoryToIr(ModifyAgentReq body, ControllerIR ir) {
        if (body.getMemoryConfig() == null) {
            return;
        }
        String repoId = body.getMemoryConfig().getMemoryRepoId();
        if (repoId == null || repoId.isEmpty()) {
            return;
        }
        MemoryConfigIR memoryConfigIR = new MemoryConfigIR();
        memoryConfigIR.setMemoryRepoId(repoId);
        memoryConfigIR.setEnable(true);

        // 从 DB 查询完整的策略和提取频率配置，与 workflow/agent IR 路径保持一致
        MemoryRepoEntity repoEntity = null;
        try {
            repoEntity = memoryRepoMapper.selectById(repoId);
        } catch (Exception e) {
            // 查询失败时使用基础配置，不阻断流程
        }
        if (repoEntity != null) {
            if (repoEntity.getConversationRound() != null || repoEntity.getTimeSpan() != null) {
                MemoryConfigIR.ExtractConfig extractConfig = new MemoryConfigIR.ExtractConfig();
                extractConfig.setMaxChatTurn(repoEntity.getConversationRound());
                extractConfig.setTimeWindow(repoEntity.getTimeSpan());
                memoryConfigIR.setExtractConfig(extractConfig);
            }
            if (repoEntity.getLongTermMemoryStrategies() != null && !repoEntity.getLongTermMemoryStrategies().isEmpty()) {
                memoryConfigIR.setStrategies(repoEntity.getLongTermMemoryStrategies());
            }
        }
        ir.getConfigs().setMemory(memoryConfigIR);
    }

    /**
     * controller 复制
     *
     * @param oldAgent 旧controller agent
     * @param newAgent 新controller agent
     * @return 返回agent
     */
    public AgentInfo copy(Agent oldAgent, Agent newAgent) {
        String controllerJson = mgObsService.downloadObsFile(oldAgent.getDslPath());
        ControllerVO controllerVo = JSONObject.parseObject(controllerJson, ControllerVO.class);

        // 复制时刷新系统参数
        replaceDefaultSystemInput(controllerVo);
        return createController(controllerVo, newAgent);
    }

    private void recordRefWorkflow(ControllerVO controllerVo,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        log.debug("Entering recordRefWorkflow with controllerVo: id={}, name={}", controllerVo.getId(),
            controllerVo.getName());

        List<MappingEntity> relateWorkflows = new ArrayList<>();

        // 工作流nodeMap
        Map<String, ControllerNodeVO> workflowNodeMap = nodesGroupByTypeId.get(AgentNodeType.WORKFLOW.getType());

        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<>() {});

        // 检查工作流不能重复
        List<ControllerNodeConfigVOWorkflows> workflows = null;
        if (controllerNodeConfigVo != null) {
            workflows = controllerNodeConfigVo.getWorkflows();
        }

        // 校验权限并关联工作流节点
        Set<String> tempWfSet = new HashSet<>();
        if (!CollectionUtils.isEmpty(workflows)) {
            workflows.forEach(wf -> {
                ControllerNodeVO wfNode = workflowNodeMap.get(wf.getNodeId());

                MappingEntity wfMapping = filterResourceAndAddMappings(controllerVo.getId(), controllerVo.getName(),
                    CommonConstant.WORKFLOW_TYPE, tempWfSet, wfNode);
                if (wfMapping != null) {
                    wfMapping.setAppType(CommonConstant.CONTROLLER);
                    relateWorkflows.add(wfMapping);
                }
            });
        }

        // 关联类型是工作流的全局意图
        List<ControllerNodeConfigVOGlobalIntents> globalIntents = null;
        if (controllerNodeConfigVo != null) {
            globalIntents = controllerNodeConfigVo.getGlobalIntents();
        }

        if (!CollectionUtils.isEmpty(globalIntents)) {
            globalIntents.forEach(intent -> {
                if (!intent.getHandlerType().equalsIgnoreCase(IntentHandlerType.WORKFLOW.getDsl())) {
                    return;
                }
                ControllerNodeVO intentNode = JsonUtils.objectToClassType(intent.getHandler(), ControllerNodeVO.class);
                if (intentNode != null) {
                    // 获取nodeConfig信息
                    MappingEntity intentMapping = filterResourceAndAddMappings(controllerVo.getId(),
                        controllerVo.getName(), CommonConstant.WORKFLOW_TYPE, tempWfSet, intentNode);
                    if (intentMapping != null) {
                        relateWorkflows.add(intentMapping);
                    }
                }
            });
        }

        if (relateWorkflows.size() > controllerWorkflowLimit) {
            throw new AgentStudioException(StudioError.WORKFLOW_NUMBER_EXCEED_LIMIT);
        }

        // 过滤已失效引用
        List<MappingEntity> relateWorkflowsFiltered = filterInvalidRef(relateWorkflows, controllerVo.getId());

        // 先清空关联关系
        mappingMapper.deleteBatchByAppIdType(controllerVo.getId(), null, CommonConstant.WORKFLOW_TYPE);
        if (!CollectionUtils.isEmpty(relateWorkflowsFiltered)) {
            mappingMapper.insertBatch(relateWorkflowsFiltered);
        }
    }

    private List<MappingEntity> filterInvalidRef(List<MappingEntity> ref, String controllerId) {
        if (ref.isEmpty()) {
            return new ArrayList<>();
        }
        // 去除重复,过滤未绑定的资产
        Map<String, MappingEntity> newRefs = ref.stream()
            .filter(v -> StringUtils.isNotEmpty(v.getResourceId()))
            .collect(
                Collectors.toMap(ControllerManagementService::getRefKey, entity -> entity, (oldVal, newVal) -> oldVal));

        // 查询草稿态版本应用中，所有已失效的引用
        List<MappingEntity> oldRefs = mappingMapper.selectByAppIdAndAppVersion(controllerId, null, null, false);

        if (!oldRefs.isEmpty()) {
            Set<String> invalidateRefs =
                oldRefs.stream().map(ControllerManagementService::getRefKey).collect(Collectors.toSet());
            // 新的引用，如果已失效，依然为已失效
            newRefs.entrySet().stream()
                .filter(entry -> invalidateRefs.contains(entry.getKey()))
                .forEach(entry -> entry.getValue().setValid(false));
        }
        return newRefs.values().stream().toList();
    }

    public void validPermission(ControllerVO controllerVo, List<ControllerNodeVO> nodeList) {
        // 权限校验
        List<Object> configList = nodeList.stream()
            .filter(node -> node.getType().equalsIgnoreCase(AgentNodeType.WORKFLOW.getType()))
            .map(ControllerNodeVO::getConfigs)
            .toList();
        List<String> idList = configList.stream().map(obj -> {
            JSONObject outPutObj = JSON.parseObject(JSONObject.toJSONString(obj));
            return outPutObj.getString("id");
        })
            .distinct()  // 对流中的元素去重
            .collect(Collectors.toList());
        if (!CollectionUtils.isEmpty(idList)) {
            List<WorkflowEntity> workflowEntities = workflowMapper.getWorkflowEntityByIds(controllerVo.getProjectId(),
                controllerVo.getWorkspaceId(), idList);
            if (idList.size() != workflowEntities.size()) {
                throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
            }
        }
    }

    private MappingEntity filterResourceAndAddMappings(String id, String name, String type, Set<String> uniqueSet,
        ControllerNodeVO node) {
        // 获取nodeConfig信息
        WorkflowNodeConfigVO wfNodeConfigs = JsonUtils.objectToClassType(node.getConfigs(), WorkflowNodeConfigVO.class);
        if (wfNodeConfigs != null) {
            // 按id和version过滤版本，不重复导入
            String uniqueKey = wfNodeConfigs.getId() + "_" + wfNodeConfigs.getVersionId();
            if (!uniqueSet.contains(uniqueKey)) {
                uniqueSet.add(uniqueKey);
                return nodeToMapping(id, name, type, node);
            }
        }
        return null;
    }

    private void recordRefSubController(ControllerVO controllerVo,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        List<MappingEntity> relateAgents = new ArrayList<>();

        // 工作流nodeMap
        Map<String, ControllerNodeVO> controllerNodeMap = nodesGroupByTypeId.get(AgentNodeType.SUB_CONTROLLER.getType());

        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<>() {});

        // 检查Agents不能重复
        List<ControllerNodeConfigVOAgents> agents = null;
        if (controllerNodeConfigVo != null) {
            agents = controllerNodeConfigVo.getAgents();
        }
        // 关联子控制器节点
        Set<String> tempAgentsSet = new HashSet<>();
        if (!CollectionUtils.isEmpty(agents)) {
            agents.forEach(agent -> {
                if (Objects.equals(agent.getId(), controllerVo.getId())) {
                    throw new AgentStudioException(StudioError.MULTI_AGENT_CANNOT_ASSOCIATE_SELF);
                }
                if (agent.getMode().equals(AgentMode.CONTROLLER.getMode())) {
                    ControllerNodeVO agentNode = controllerNodeMap.get(agent.getNodeId());
                    MappingEntity wfMapping = filterResourceAndAddMappings(controllerVo.getId(), controllerVo.getName(),
                            CommonConstant.CONTROLLER_TYPE, tempAgentsSet, agentNode);
                    if (wfMapping != null) {
                        wfMapping.setAppType(CommonConstant.CONTROLLER);
                        relateAgents.add(wfMapping);
                    }
                }
            });
        }

        if (relateAgents.size() > controllerSubAgentLimit) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_NUMBER_EXCEED_LIMIT);
        }

        // 过滤已失效引用
        List<MappingEntity> relateAgentsFiltered = filterInvalidRef(relateAgents, controllerVo.getId());
        // 先清空关联关系
        mappingMapper.deleteBatchByAppIdType(controllerVo.getId(), null, CommonConstant.CONTROLLER_TYPE);
        if (!CollectionUtils.isEmpty(relateAgentsFiltered)) {
            mappingMapper.insertBatch(relateAgentsFiltered);
        }
    }

    private void recordRefAgent(ControllerVO controllerVo,
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId) {
        List<MappingEntity> relateAgents = new ArrayList<>();

        // 工作流nodeMap
        Map<String, ControllerNodeVO> controllerNodeMap = nodesGroupByTypeId.get(AgentNodeType.AGENT.getType());

        ControllerNodeVO controllerNode = getControllerNode(nodesGroupByTypeId);

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
                JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<>() {});

        // 检查Agents不能重复
        List<ControllerNodeConfigVOAgents> agents = null;
        if (controllerNodeConfigVo != null) {
            agents = controllerNodeConfigVo.getAgents();
        }
        // 关联子控制器节点
        Set<String> tempAgentsSet = new HashSet<>();
        if (!CollectionUtils.isEmpty(agents)) {
            agents.forEach(agent -> {
                if (agent.getMode().equals(AgentMode.PLANEXECUTE.getMode())) {
                    ControllerNodeVO agentNode = controllerNodeMap.get(agent.getNodeId());
                    MappingEntity wfMapping = filterResourceAndAddMappings(controllerVo.getId(), controllerVo.getName(),
                            CommonConstant.AGENT_TYPE, tempAgentsSet, agentNode);
                    if (wfMapping != null) {
                        wfMapping.setAppType(CommonConstant.CONTROLLER);
                        relateAgents.add(wfMapping);
                    }
                }
            });
        }

        // 过滤已失效引用
        List<MappingEntity> relateAgentsFiltered = filterInvalidRef(relateAgents, controllerVo.getId());
        // 先清空关联关系
        mappingMapper.deleteBatchByAppIdType(controllerVo.getId(), null, CommonConstant.AGENT_TYPE);
        if (!CollectionUtils.isEmpty(relateAgentsFiltered)) {
            mappingMapper.insertBatch(relateAgentsFiltered);
        }
    }

    private MappingEntity nodeToMapping(String appId, String appName, String type, ControllerNodeVO controllerNodeVo) {
        WorkflowNodeConfigVO wfNodeConfigs =
            JsonUtils.objectToClassType(controllerNodeVo.getConfigs(), WorkflowNodeConfigVO.class);
        if (wfNodeConfigs == null) {
            return null;
        }
        MappingEntity mappingEntity = new MappingEntity();

        // 设置主键
        mappingEntity.setMappingId(UUID.randomUUID().toString());

        // 设置app信息
        mappingEntity.setAppId(appId);
        mappingEntity.setAppName(appName);
        mappingEntity.setAppType(CommonConstant.AGENT_TYPE);

        // 设置关联resource信息
        mappingEntity.setResourceType(type);
        mappingEntity.setResourceId(wfNodeConfigs.getId());
        mappingEntity.setResourceName(wfNodeConfigs.getName());
        mappingEntity.setResourceDesc(wfNodeConfigs.getDescription());
        mappingEntity.setResourceVersion(wfNodeConfigs.getVersionId());
        mappingEntity.setAppWorkspaceId(RequestContextUtils.getRequestWorkspaceId());

        if (CommonConstant.WORKFLOW_TYPE.equals(type) || CommonConstant.CONTROLLER.equals(type)) {
            List<ShareResourceEntity> shareResourceEntities =
                shareResourceMapper.selectShareResourceByResourceIds(Collections.singletonList(wfNodeConfigs.getId()));
            if (!CollectionUtils.isEmpty(shareResourceEntities)) {
                ShareResourceEntity shareResourceEntity = shareResourceEntities.get(0);
                mappingEntity.setReferenceType(
                    RequestContextUtils.getRequestWorkspaceId().equals(shareResourceEntity.getWorkspaceId()) ? ReferenceTypeEnum.DIRECT.getValue()
                        : ReferenceTypeEnum.SHARE.getValue());
                mappingEntity.setResourceWorkspaceId(shareResourceEntity.getWorkspaceId());
            } else {
                mappingEntity.setReferenceType("direct");
                mappingEntity.setResourceWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
            }
        }
        return mappingEntity;
    }

    /**
     * 转换默认的dsl输入参数，老版本参数强刷为false
     */
    public void replaceDefaultSystemInput(ControllerVO controllerVo) {
        boolean isChinese = LanguageUtils.isChinese();
        ControllerVO newController = JSONObject.parseObject(isChinese
            ? (showIntentParamEnable ? controllerInitIntentDsl : controllerInitDsl)
            : (showIntentParamEnable ? controllerInitIntentDslEn : controllerInitDslEn), ControllerVO.class);
        List<WorkflowFieldVO> inputs = newController.getInputs();

        // 过滤系统参数
        List<WorkflowFieldVO> filteredInputs = controllerVo.getInputs()
            .stream()
            .filter(input -> !WorkflowFieldVO.SourceEnum.SYSTEM.equals(input.getSource()))
            .toList();
        inputs.addAll(filteredInputs);
        controllerVo.setInputs(inputs);
    }

}
