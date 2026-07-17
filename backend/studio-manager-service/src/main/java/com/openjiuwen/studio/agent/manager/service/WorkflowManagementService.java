/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.ModelParam.MODEL_NAME;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.ModelParam.MODEL_TYPE;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.SYS;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.Workflow.MODEL;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.Workflow.REF_VAR_NAME;
import static com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum.MCP;
import static com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum.MEMORY;
import static com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum.TOOL;
import static com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum.WORKFLOW;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.alibaba.fastjson2.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.annotation.DistributedLock;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.FileCommonUtils;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.PromptPath;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CopyWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExternalKnowledgeBaseSource;
import com.openjiuwen.studio.agent.manager.dto.FreeTrialQuota;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowEnvsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowParamsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsV1Qo;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionDomainObject;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionWorkflow;
import com.openjiuwen.studio.agent.manager.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.ValidateWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowEnv;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowEnvs;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFrontParam;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFrontParamInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.common.dto.run.WorkflowListItem;
import com.openjiuwen.studio.agent.common.dto.run.WorkflowListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowSceneRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVersionListItem;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVersionListRsp;
import com.openjiuwen.studio.agent.manager.entity.App;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.Tag;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowVersionEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.enums.BoolQueryNodeType;
import com.openjiuwen.studio.agent.manager.enums.BoolQueryOperatorType;
import com.openjiuwen.studio.agent.manager.enums.ModelTypeV2;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.TriggerType;
import com.openjiuwen.studio.agent.manager.enums.VisibilityEnum;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.TagMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.JiuWenClient;
import com.openjiuwen.studio.agent.manager.rce.models.knowledge.BoolQueryNode;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.serializer.YamlSerializer;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMemberService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.utils.IconNameCheckUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.AdapterService;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.ThirdpartyWorkflowAdapter;
import com.openjiuwen.studio.agent.manager.workflow.models.WorkflowConfigVariable;

import jakarta.annotation.Resource;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.quartz.CronScheduleBuilder;
import org.quartz.JobBuilder;
import org.quartz.JobDetail;
import org.quartz.JobKey;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.quartz.Trigger;
import org.quartz.TriggerBuilder;
import org.quartz.TriggerKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

/**
 * workflow管理面service
 *
 */
@Slf4j
@Service
public class WorkflowManagementService implements IWorkflowManagementService {
    /**
     * 最大递归深度
     */
    private static final int NESTED_DEEP = 10;

    /**
     * 开始节点ID
     */
    private static final String INPUT_KEY = "node_start";

    /**
     * 结束节点ID
     */
    private static final String OUTPUT_KEY = "node_end";

    /**
     * 工作流obs路径模板
     */
    private static final String WORKFLOW_OBS_PATH_TEMPLATE = "%s/%s/%s/%s.json";

    /**
     * 工作流复制名称模板
     */
    private static final String NAME_FORMAT = "%s_%s";

    /**
     * 工作流全局变量scope
     */
    private static final String SCOPE_REQUEST = "request";

    /**
     * dsl id
     */
    private static final String WORKFLOW_ID = "workflow_id";

    /**
     * dsl name
     */
    private static final String WORKFLOW_NAME = "workflow_name";

    /**
     * dsl version id
     */
    private static final String WORKFLOW_VERSION_ID = "workflow_version_id";

    /**
     * 分隔符
     */
    private static final String SEPARATOR = "|";

    /**
     * 最大嵌套深度
     */
    private static final int MAX_NESTED_LEVEL = 10;

    /**
     * workflow发布状态
     */
    private static final String RELEASED = "released";

    /**
     * 工作流开场白
     */
    private static final String PROLOGUE = "prologue";

    /**
     * 工作流推荐问
     */
    private static final String SUGGEST_QUERIES = "suggest_queries";

    /**
     * 领域对象
     */
    private static final String DOMAIN_OBJECTS = "domain_objects";

    /**
     * 拓展工作流
     */
    private static final String EXTENSION_WORKFLOWS = "extension_workflows";

    public static final int TEST_SUCCESS = 1;

    public static  final  String ACTIVE = "active";

    /**
     * 任务型工作流
     */
    private static  final  String WORKFLOW_TYPE_TASK = "task";

    /**
     * Agent节点
     */
    private static  final  String AGENT = "Agent";

    /**
     * Message节点
     */
    private static  final  String MESSAGE = "Message";

    /**
     * Input节点
     */
    private static  final  String INPUT = "Input";

    /**
     * Question节点
     */
    private static  final  String QUESTION = "QA";

    /**
     * Questioner节点
     */
    private static  final  String QUESTIONER = "Questioner";

    /**
     * ParamExtraction 节点
     */
    private static  final  String PARAM_EXTRACTION = "ParamExtraction";

    /**
     * 在类中定义常量映射
     */
    private final Map<String, String> NODE_TYPE_NAMES = Map.of(
            AGENT, "Agent",
            MESSAGE, "消息",
            INPUT, "输入",
            QUESTION, "问答",
            QUESTIONER, "提问器",
            PARAM_EXTRACTION, "对象提取"
    );

    @Autowired
    MessageSource messageSource;

    @Autowired
    WorkflowMapper workflowMapper;

    @Autowired
    MgObsService obsService;

    @Autowired
    Scheduler scheduler;

    @Autowired
    SkuManageService skuManageService;

    @Autowired
    WorkflowValidationService workflowValidationService;

    @Autowired
    IrAdapterService irAdapterService;

    @Autowired
    AppMapper appMapper;

    @Autowired
    MappingMapper mappingMapper;

    @Autowired
    TagMapper tagMapper;

    @Autowired
    ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    JiuWenClient jiuWenClient;

    @Autowired
    PublishUtils publishUtils;

    @Autowired
    AgentCommonService agentCommonService;

    @Autowired
    private AgentSpaceService agentSpaceService;

    @Resource
    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    @Autowired
    private ThirdpartyWorkflowAdapter thirdpartyWorkflowAdapter;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${workflow.default-chat-flow:}")
    private String workflowDefaultChatFlow;

    @Value("${workflow.default-task-flow:}")
    private String workflowDefaultTaskFlow;

    @Value("${workflow.default-chat-flow-english:}")
    private String workflowDefaultChatFlowEnglish;

    @Value("${workflow.default-task-flow-english:}")
    private String workflowDefaultTaskFlowEnglish;

    @Value("${workflow.default-system-param:}")
    private String workflowDefaultSystemParam;

    @Value("${workflow.default-system-param-english:}")
    private String workflowDefaultSystemParamEnglish;

    @Value("${workflow.model.default-model-type:poc_agentBuilder}")
    @Getter
    private String defaultModelType;

    @Value("${workflow.endpoint-template:}")
    private String endpointTemplate;

    @Value("${front-page.runtime-host:}")
    private String runtimeHost;

    @Value("${server.ssl.enabled:}")
    private String serverSslEnabled;

    @Value("${workflow.default-icon}")
    private String defaultIcon;

    @Value("${workflow.max-release-version-size}")
    private int releaseMaxSize;

    @Value("${workflow.sub-workflow.nested-level}")
    private int nestedLevel;

    @Value("${release.channel.webpage-endpoint}")
    private String webpageEndpoint;

    @Value("${inner.agent-runtime.endpoint}")
    private String agentRuntimeEndpoint;

    @Value("${inner.agent-runtime.run-workflow.uri}")
    private String runWorkflowStreamUrl;

    /**
     * 工作流最多选择3个知识库
     */
    @Value("${workflow.knowledge-repo.limit:3}")
    private int knowledgeRepoLimit;

    @Value("${env.type}")
    @Getter
    private String envType;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${publish.agent-builder.enable}")
    private boolean publishAgentBuilderEnable;

    @Value("${agent-builder.publish-cross-workspace.enable:false}")
    private boolean publishCrossWorkspace;

    @Value("${prr.is-soft-delete: true}")
    private Boolean isSoftDelete;

    @Value("${publish.app-store.enable:false}")
    private boolean publishAppEnable;

    @Value("${content-review.configs}")
    private String contentReviewConfigs;

    @Value("${asset.app.free.trial-quota-limit:10}")
    private int assetAppFreeTrialQuotaLimit;

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    private static final String DIFY_FILE_TYPE = ".yml";

    @Autowired
    private ReleaseChannelMapper releaseChannelMapper;

    @Autowired
    private AgentRuntimeClient agentRuntimeClient;

    @Resource
    @Lazy
    private AgentImportExportService agentImportExportService;

    @Resource
    @Lazy
    private AgentImportService agentImportService;

    @Resource
    @Lazy
    private AgentManagementService agentManagementService;

    @Autowired
    private WorkflowCommonService workflowCommonService;

    @Autowired
    private ObjectMapper mapper;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private RouterStrategyMapper routerStrategyMapper;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private WorkspaceMemberService workSpaceMemberService;

    @Autowired
    private EnvironmentServiceManagerService environmentServiceManagerService;


    @Autowired
    private AiGenService aiGenerateService;

    @Autowired
    private AgentMemoryConfigService agentMemoryConfigService;

    @Autowired
    private YamlSerializer yamlSerializer;

    @Autowired
    private PluginBaseImpl pluginBaseImpl;

    @Autowired
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    private static @NotNull String getRefKey(MappingEntity entity) {
        return entity.getResourceId() + "_" + entity.getResourceVersion() + "_" + entity.getResourceType();
    }

    @NotNull
    private MappingEntity buildReference(ResourceTypeEnum type, WorkflowVO workflowVo, String appVersionId,
        Map<String, Object> configs) {
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());
        mappingEntity.setAppId(workflowVo.getId());
        mappingEntity.setAppType(WORKFLOW.toString());
        mappingEntity.setAppName(workflowVo.getName());
        mappingEntity.setAppVersion(appVersionId);
        if (configs.get(Constants.ID) != null) {
            mappingEntity.setResourceId(configs.get(Constants.ID).toString());
        }
        if (configs.get(Constants.NAME) != null) {
            mappingEntity.setResourceName(configs.get(Constants.NAME).toString());
        }
        if (configs.get(Constants.VERSION_ID) != null) {
            mappingEntity.setResourceVersion(configs.get(Constants.VERSION_ID).toString());
        }
        mappingEntity.setResourceType(type.toString());

        // 添加共享引用相关
        if (WORKFLOW.equals(type) || TOOL.equals(type) || MCP.equals(type)) {
            String[] resourceSplit = configs.get(Constants.ID).toString().split("#");
            List<ShareResourceEntity> shareResourceEntities
                = shareResourceManagerService.queryShareResourceEntityByResourceIdList(Collections.singletonList(resourceSplit[0]));
            if (!CollectionUtils.isEmpty(shareResourceEntities)) {
                ShareResourceEntity shareResourceEntity = shareResourceEntities.get(0);
                mappingEntity.setReferenceType(getReferenceType(shareResourceEntity));
                mappingEntity.setAppWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
                mappingEntity.setResourceWorkspaceId(shareResourceEntity.getWorkspaceId());
            } else {
                mappingEntity.setReferenceType("direct");
                mappingEntity.setAppWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
                mappingEntity.setResourceWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
            }
        }

        return mappingEntity;
    }

    public String getReferenceType(ShareResourceEntity shareResourceEntity) {
        if (pluginBaseImpl.isInnerType(shareResourceEntity.getResourceId())) {
            return ReferenceTypeEnum.DIRECT.getValue();
        }
        return RequestContextUtils.getRequestWorkspaceId().equals(shareResourceEntity.getWorkspaceId())
            ? ReferenceTypeEnum.DIRECT.getValue()
            : ReferenceTypeEnum.SHARE.getValue();
    }

    @NotNull
    private static MappingEntity buildModelReference( WorkflowVO workflowVo, String appVersionId,
        Map<String, Object> configs) {
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());
        mappingEntity.setAppId(workflowVo.getId());
        mappingEntity.setAppType(WORKFLOW.toString());
        mappingEntity.setAppName(workflowVo.getName());
        mappingEntity.setAppVersion(appVersionId);
        if (configs.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID) != null) {
            mappingEntity.setResourceId(configs.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID).toString());
        }

        if (configs.get(MODEL_NAME) != null) {
            mappingEntity.setResourceName(configs.get(MODEL_NAME).toString());
        }
        if (Strings.CS.equals(String.valueOf(configs.get(MODEL_TYPE)), ResourceTypeEnum.STRATEGY.toString())) {
            mappingEntity.setResourceType(ResourceTypeEnum.STRATEGY.toString());
        }else {
            mappingEntity.setResourceType(ResourceTypeEnum.MODEL.toString());
        }
        return mappingEntity;
    }

    /**
     * 记录工作流版本关联关系
     *
     * @param workflowVo 工作流对象
     * @param appVersionId 新发布的应用版本Id
     */
    public void updateRefResources(WorkflowVO workflowVo, String appVersionId) {
        List<MappingEntity> relateComponents = new ArrayList<>();

        // 从workflow中解析所有关联关系
        for (WorkflowNodeVO node : workflowVo.getNodes()) {
            NodeType nodeType = NodeType.fromType(node.getType());
            if (nodeType == null) {
                continue;
            }

            final Map<String, Object> nodeConfigs = node.getConfigs();
            switch (nodeType) {
                case WORKFLOW -> relateComponents.add(buildReference(WORKFLOW, workflowVo, appVersionId, nodeConfigs));
                case INTENT_DETECTION_CONTAINER ->
                    addIntentContainerRef(workflowVo, appVersionId, node, relateComponents);
                case MCP -> relateComponents.add(buildReference(MCP, workflowVo, appVersionId, nodeConfigs));
                case PLUGIN -> addPluginRef(workflowVo, appVersionId, node, relateComponents);
                case KNOWLEDGE_REPO -> addKnowLedgeRepoRef(workflowVo, appVersionId, nodeConfigs, relateComponents);
                case AGENT -> addAgentRef(workflowVo, appVersionId, nodeConfigs, relateComponents);
                case LLM, QUESTIONER, INTENT_DETECTION, INTENT_COMPLEX_INTENT ->
                    addModelRef(workflowVo, appVersionId, nodeConfigs, relateComponents);
                case PARAM_EXTRACTION -> addParamExtractionRef(workflowVo, appVersionId, nodeConfigs, relateComponents);
                default -> log.debug("{} do not have binding resource", nodeType.getType());
            }

            // 后续添加细粒度的节点权限校验
        }

        // 处理工作流中的全局配置模型
        this.buildGlobalModelReference(RequestContextUtils.getRequestProjectId(),
            RequestContextUtils.getRequestWorkspaceId(), workflowVo, relateComponents, appVersionId);

        // 处理工作流中的全局配置记忆库信息
        this.buildGlobalMemoryRepo(workflowVo, relateComponents, appVersionId);

        // 去除重复,过滤未绑定的资产
        Map<String, MappingEntity> newRefs = relateComponents.stream()
            .filter(v -> StringUtils.isNotEmpty(v.getResourceId()))
            .collect(
                Collectors.toMap(WorkflowManagementService::getRefKey, entity -> entity, (oldVal, newVal) -> oldVal));

        // 查询草稿态版本应用中，所有已失效的引用
        List<MappingEntity> oldRefs = mappingMapper.selectByAppIdAndAppVersion(workflowVo.getId(), null, null, false);
        Set<String> invalidateRefs =
            oldRefs.stream().map(WorkflowManagementService::getRefKey).collect(Collectors.toSet());

        // 新的引用，如果已失效，依然为已失效
        for (Map.Entry<String, MappingEntity> entry : newRefs.entrySet()) {
            if (invalidateRefs.contains(entry.getKey())) {
                entry.getValue().setValid(false);
            }
        }

        // 清空关联关系，只有草稿态需要清空，发布新版本为新增一套
        if (appVersionId == null) {
            mappingMapper.deleteBatchByAppId(workflowVo.getId(), null, false);
        }
        // 添加新的有效的关联关系
        if (!CollectionUtils.isEmpty(newRefs)) {
            mappingMapper.insertBatch(newRefs.values().stream().toList());
        }
    }

    private void addParamExtractionRef(WorkflowVO workflowVo, String versionId, Map<String, Object> nodeConfigs,
        List<MappingEntity> relateComponents) {
        // 领域对象相关配置
        List<Object> domainObjects = JsonUtils.objectToClass(nodeConfigs.get(DOMAIN_OBJECTS));
        if (!CollectionUtils.isEmpty(domainObjects)) {
            domainObjects.forEach(item -> {
                ParamExtractionDomainObject domainObject =
                    JsonUtils.objectToClassType(item, ParamExtractionDomainObject.class);
                if (domainObject != null && !CollectionUtils.isEmpty(domainObject.getProcessingWorkflows())) {
                    // 领域对象子工作流处理
                    domainObject.getProcessingWorkflows().forEach(processingWorkflow -> {
                        Map<String, Object> configs = parseSubWorkflowConfigs(processingWorkflow);
                        relateComponents.add(buildReference(WORKFLOW, workflowVo, versionId, configs));
                    });
                }
            });
        }
        // 拓展工作量相关配置
        List<Object> extensionWorkflows = JsonUtils.objectToClass(nodeConfigs.get(EXTENSION_WORKFLOWS));
        if (!CollectionUtils.isEmpty(extensionWorkflows)) {
            extensionWorkflows.forEach(item -> {
                ParamExtractionWorkflow extensionWorkflow =
                    JsonUtils.objectToClassType(item, ParamExtractionWorkflow.class);
                if (extensionWorkflow != null) {
                    Map<String, Object> configs = parseSubWorkflowConfigs(extensionWorkflow);
                    relateComponents.add(buildReference(WORKFLOW, workflowVo, versionId, configs));
                }
            });
        }
        addModelRef(workflowVo, versionId, nodeConfigs, relateComponents);
    }

    private Map<String, Object> parseSubWorkflowConfigs(ParamExtractionWorkflow extractionWorkflow) {
        Map<String, Object> configs = new HashMap<>();
        configs.put(Constants.ID, extractionWorkflow.getId());
        configs.put(Constants.NAME, extractionWorkflow.getName());
        configs.put(Constants.VERSION_ID, extractionWorkflow.getVersionId());
        return configs;
    }

    private void addPluginRef(WorkflowVO workflowVo, String versionId, WorkflowNodeVO node,
        List<MappingEntity> relateComponents) {
        Map<String, Object> nodeConfigs = node.getConfigs();

        // 兼容旧插件nodeConfigs下无name字段
        nodeConfigs.computeIfAbsent(Constants.NAME, k -> node.getName());
        // 只改基本类型无影响
        Map<String, Object> nodeConfigsCopy = new HashMap<>(nodeConfigs);
        if (nodeConfigsCopy.get(Constants.ID) != null) {
            String resourceId = nodeConfigsCopy.get(Constants.ID).toString();
            if (nodeConfigsCopy.get(Constants.TOOL_ID) != null) {
                resourceId = resourceId + '#' + nodeConfigsCopy.get(Constants.TOOL_ID).toString();
            } else {
                resourceId = resourceId + "#0";
            }
            nodeConfigsCopy.put(Constants.ID, resourceId);
        }

        relateComponents.add(buildReference(TOOL, workflowVo, versionId, nodeConfigsCopy));
    }

    private void addAgentRef(WorkflowVO workflowVo, String versionId, Map<String, Object> nodeConfigs,
        List<MappingEntity> relateComponents) {
        // agent节点解析agent
        if (nodeConfigs.get(CommonConstant.PLUGINS) != null) {
            List<Map<String, Object>> pluginConfigs = JsonUtils.objectToClass(nodeConfigs.get(CommonConstant.PLUGINS));
            if (pluginConfigs != null) {
                pluginConfigs.forEach(pluginConfig -> {
                    adapterPluginId(pluginConfig);
                    // 插件类型资源解析，并校验合法性
                    if (!CollectionUtils.isEmpty(pluginConfig)) {
                        relateComponents.add(buildReference(TOOL, workflowVo, versionId, pluginConfig));
                    }
                });
            }
        }
        addModelRef(workflowVo, versionId, nodeConfigs, relateComponents);
    }

    private void adapterPluginId(Map<String, Object> pluginConfig) {
        if (CollectionUtils.isEmpty(pluginConfig)) {
            return;
        }
        if (pluginConfig.get(Constants.ID) != null && pluginConfig.get(Constants.TOOL_ID) != null) {
            String pluginId = pluginConfig.get(Constants.ID).toString();
            if (pluginId.contains("#")) {
                return;
            }
            String toolId = pluginConfig.get(Constants.TOOL_ID).toString();
            pluginConfig.put(Constants.ID, pluginId + "#" + toolId);
        }
    }

    private void addKnowLedgeRepoRef(WorkflowVO workflowVo, String versionId, Map<String, Object> nodeConfigs,
        List<MappingEntity> relateComponents) {
        // 知识库节点绑定知识库解析，并校验合法性
        List<Map<String, Object>> repos = JsonUtils.objectToClass(nodeConfigs.get(CommonConstant.REPOS));
        if (repos == null) {
            return;
        }
        if (repos.size() > knowledgeRepoLimit) {
            throw new AgentStudioException(StudioError.WORKFLOW_KNOWLEDGE_REPO_NUM, knowledgeRepoLimit);
        }
        repos.forEach(repoConfig -> {
            relateComponents.add(buildReference(ResourceTypeEnum.REPO, workflowVo, versionId, repoConfig));
        });
    }

    private void addIntentContainerRef(WorkflowVO workflowVo, String versionId, WorkflowNodeVO node,
        List<MappingEntity> relateComponents) {
        // 高级意图绑定子工作流资源解析
        List<String> workflowIds = new ArrayList<>();
        List<WorkflowBranchVO> branches = node.getBranches();
        for (WorkflowBranchVO branch : branches) {
            Map<String, Object> configs = branch.getConfigs();

            // 过滤没有id或重复的
            if (configs.get(WORKFLOW_ID) == null || StringUtils.isEmpty(configs.get(WORKFLOW_ID).toString())
                || workflowIds.contains(configs.get(WORKFLOW_ID).toString())) {
                continue;
            }

            // 字段映射
            workflowIds.add(configs.get(WORKFLOW_ID).toString());
            configs.put(Constants.ID, configs.get(WORKFLOW_ID));

            if (configs.get(WORKFLOW_NAME) != null) {
                configs.put(Constants.NAME, configs.get(WORKFLOW_NAME));
            }
            if (configs.get(WORKFLOW_VERSION_ID) != null) {
                configs.put(Constants.VERSION_ID, configs.get(WORKFLOW_VERSION_ID));
            }
            relateComponents.add(buildReference(WORKFLOW, workflowVo, versionId, configs));
        }
    }

    @Override
    public WorkflowValidationVO validateWorkflow(String projectId, String workflowId,
        ValidateWorkflowQo validateWorkflowQo) {
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, ThreadLocalUtils.getWorkspaceId(), workflowId);
        Long version = validateWorkflowQo.getVersion();
        String workspaceId = validateWorkflowQo.getWorkspaceId();
        if (workflowEntity == null) {
            return new WorkflowValidationVO().setSuccess(false);
        }
        if (version != null && !Objects.equals(version, workflowEntity.getUpdatedAt())) {
            throw new AgentStudioException(StudioError.WORKFLOW_VALIDATE_VERSION_ERROR);
        }
        // 从OBS中下载EI工作流配置
        String workflowInfo = obsService.downloadObsFile(workflowEntity.getDslPath());

        // 校验工作流Code节点执行方式是否合法
        WorkflowVO workflowVO = JSON.parseObject(workflowInfo, WorkflowVO.class);
        workflowValidationService.validateCodeExecMode(workflowVO.getNodes(), workflowId);

        // 全局配置校验
        if (workflowVO != null && workflowVO.getConfigs() != null) {
            Map<String, Object> configs = workflowVO.getConfigs();
            workflowValidationService.validateWorkflowConfigs(configs);
        }

        if (workflowVO != null && workflowVO.getNodes() != null) {
            List<Map<String, Object>> nodes = JsonUtils.objectToClass(workflowVO.getNodes());
            workflowValidationService.validateIdAndName(nodes, projectId, workspaceId);
            workflowValidationService.validateTools(nodes, projectId, workspaceId);
            workflowValidationService.validateQuestionerNode(nodes, workflowId);
        }

        // 任务型工作流节点校验
        if (isTaskTypeWorkflow(workflowEntity.getWorkflowType())) {
            validateTaskWorkflowNodes(workflowVO.getNodes());
        }

        WorkflowValidationVO result = workflowValidationService.validate(projectId, workspaceId, workflowVO);

        // 验证通过更新workflowVersion
        if (result.isSuccess()) {
            // 记录资源的关联关系并校验权限
            updateRefResources(workflowVO, null);
            validWorkflowWorkspace(workflowVO, projectId, workspaceId);
            // 非拖动情况下 ir转换并上传obs
            WorkflowVO workflow = JSON.parseObject(workflowInfo, WorkflowVO.class);
            String irPath = workflowDslToIr(workflowId, workflowEntity, workflow);
            workflowEntity.setIrPath(irPath);
            workflowEntity.setDeployWfVersion(workflowEntity.getUpdatedAt());
            workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        }
        // 返回验证结果
        return result;
    }

    /**
     * 判断是否为任务型工作流
     */
    private boolean isTaskTypeWorkflow(String workflowType) {
        return WORKFLOW_TYPE_TASK.equals(workflowType);
    }

    /**
     * 校验任务型工作流中的节点
     * @param nodes 工作流节点列表
     */
    private void validateTaskWorkflowNodes(List<WorkflowNodeVO> nodes) {
        if (CollectionUtils.isEmpty(nodes)) {
            return;
        }

        Set<String> forbiddenNodeTypes = Set.of(AGENT, MESSAGE, INPUT, QUESTION, QUESTIONER, PARAM_EXTRACTION);

        nodes.stream()
                .filter(node -> forbiddenNodeTypes.contains(node.getType()))
                .findFirst()
                .ifPresent(node -> {
                    String nodeName = NODE_TYPE_NAMES.getOrDefault(node.getType(), node.getType());
                    throw new AgentStudioException(StudioError.WORKFLOW_TASK_INVALID_NODE, nodeName);
                });
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "复制工作流",
        resourceId = "workflowId",
        resourceName = ""
    )
    public WorkflowInfo copyWorkflow(String projectId, String workflowId, CopyWorkflowQo copyWorkflowQo) {
        String targetWorkspaceId = copyWorkflowQo.getTargetWorkspaceId();
        if (copyWorkflowQo.getWorkspaceId().equals(targetWorkspaceId)) {
            return copyWorkflow(projectId, workflowId, targetWorkspaceId, false);
        }

        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.CROSS_SPACE_COPY);

        Set<String> currentUserJoinedWorkspaceIdSet =
            workSpaceMemberService.queryAllWorkSpaceInfoByIamUserId(RequestContextUtils.getRequestUserId())
                .stream()
                .map(WorkSpaceMemberEntity::getWorkspaceId)
                .collect(Collectors.toSet());

        if (CollectionUtils.isEmpty(currentUserJoinedWorkspaceIdSet)
            || !currentUserJoinedWorkspaceIdSet.contains(targetWorkspaceId)) {
            log.error("the user {} not in workspace {} when copy workflow", RequestContextUtils.getRequestUserId(),
                targetWorkspaceId);
            throw new AgentStudioException(StudioError.USER_NOT_IN_TARGET_WORKSPACE);
        }

        String exportWorkflowsStr =
            agentImportExportService.exportWorkflowsStr(projectId, copyWorkflowQo.getWorkspaceId(), workflowId);
        List<ImportListInfo> importListInfoList =
            agentManagementService.listImportInfoFromJson(projectId, exportWorkflowsStr);
        agentImportExportService.importWorkflowsWithStr(projectId, copyWorkflowQo.getTargetWorkspaceId(),
            exportWorkflowsStr, importListInfoList);
        return null;
    }

    /**
     * 复制工作流
     *
     * @param projectId 项目id
     * @param workflowId 工作流id
     * @param targetWorkspaceId 目标空间id
     * @param fromSquare 是否从应该广场复制
     * @return 返回复制的工作流
     */
    public WorkflowInfo copyWorkflow(String projectId, String workflowId, String targetWorkspaceId,
        boolean fromSquare) {
        skuManageService.validateInsertAppCountExceededLimitOrNot();
        WorkflowEntity workflowEntity = getWorkflowEntityById(workflowId);
        workflowEntity.setWorkspaceId(targetWorkspaceId);
        generateValidNameAndCode(workflowEntity, projectId, targetWorkspaceId);
        String newWorkflowId = String.valueOf(UUID.randomUUID());
        workflowEntity.setId(newWorkflowId);
        workflowEntity.setTraceId(newWorkflowId);
        workflowEntity.setStatus(CommonConstant.WORKFLOW_DEVELOP);
        workflowEntity.setVisibility(VisibilityEnum.PROJECT.getValue());
        long currentTime = System.currentTimeMillis();
        workflowEntity.setCreatedAt(currentTime);
        workflowEntity.setUpdatedAt(currentTime);
        String creatorName = getUserName(projectId);
        workflowEntity.setCreatedBy(creatorName);
        workflowEntity.setUpdatedBy(creatorName);
        workflowEntity.setProjectId(projectId);
        workflowEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());
        workflowEntity.setDeployWfVersion(null);
        workflowEntity.setPublishedAt(null);
        workflowEntity.setCreatorId(RequestContextUtils.getRequestUserId());
        WorkflowVO workflowVo =
            JSON.parseObject(obsService.downloadObsFile(workflowEntity.getDslPath()), WorkflowVO.class);
        workflowVo.setId(workflowEntity.getId());
        if (fromSquare) {
            if (workflowVo.getConfigs() == null) {
                workflowVo.setConfigs(new HashMap<>());
            }
            workflowVo.getConfigs()
                .put(Constants.Workflow.CONTENT_REVIEW,
                    JsonUtils.json2Obj(contentReviewConfigs, Constants.MAP_TYPE_REFERENCE));
        }

        // 当前九问提取name参数作为Agent绑定工作流，模型英文名效果更好
        workflowVo.setName(workflowEntity.getCode());
        String relativePath =
            obsService.uploadObsFile(workflowEntity.getId(), workflowEntity.getId(), CommonConstant.WORKFLOW,
                JSON.toJSONString(workflowVo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.FLOW);
        workflowEntity.setDslPath(relativePath);

        // ir转换并上传obs
        Map<String, Object> metadata = workflowCommonService.parseMetadata(workflowEntity);
        Map<String, Object> irInfo = irAdapterService.adaptWorkflow(workflowVo, metadata);

        // 记录关联关系
        updateRefResources(workflowVo, null);

        String irPath =
            obsService.uploadObsFile(workflowEntity.getId(), workflowEntity.getId(), CommonConstant.WORKFLOW,
                JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.IR);
        workflowEntity.setIrPath(irPath);
        workflowEntity.setTestStatus(0);
        workflowMapper.createWorkflowEntity(workflowEntity);
        return convertEntityToInfo(workflowEntity, JSON.toJSONString(workflowVo, JSONWriter.Feature.WriteMapNullValue));
    }

    private void generateValidNameAndCode(WorkflowEntity workflowEntity, String projectId, String workspaceId) {
        // 生成拷贝后中英文名后缀，不与已有重复
        int suffixNum = 1;
        String codePrefix = workflowEntity.getCode();
        String namePrefix = workflowEntity.getName();
        String newCode = String.format(NAME_FORMAT, codePrefix, suffixNum);
        workflowEntity.setCode(newCode);
        String newName = String.format(NAME_FORMAT, namePrefix, suffixNum);
        workflowEntity.setName(newName);

        // 获取所有英文名称
        Set<String> currentCodes = workflowValidationService.getCurrentCodes(projectId, workspaceId);

        // 获取所有中文名称
        Set<String> currentNames = workflowValidationService.getCurrentNames(projectId, workspaceId);
        while (currentCodes.contains(workflowEntity.getCode()) || currentNames.contains(workflowEntity.getName())) {
            ++suffixNum;
            workflowEntity.setCode(String.format(NAME_FORMAT, codePrefix, suffixNum));
            workflowEntity.setName(String.format(NAME_FORMAT, namePrefix, suffixNum));
        }
        workflowValidationService.validateName(workflowEntity.getName());
        workflowValidationService.validateCode(workflowEntity.getCode());
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "创建工作流",
        resourceId = "-1",
        resourceName = "body.name"
    )
    @DistributedLock(prefix = "workflow:create:")
    public WorkflowInfo createWorkflow(String projectId, String workspaceId, WorkflowInfo body) {
        // 检验合法性
        workflowValidationService.validateName(body.getName());
        workflowValidationService.validateCode(body.getCode());
        workflowValidationService.validateWorkflowType(body.getType());

        skuManageService.validateInsertAppCountExceededLimitOrNot();

        String iconName = null;
        if (body.getAvatar() == null) {
            body.setAvatar(defaultIcon);
        } else {
            IconNameCheckUtils.validaIconName(body.getAvatar());
            iconName = body.getAvatar();
            String icon = ImageBase64Utils.getImageBase64(body.getAvatar(), obsService);
            body.setAvatar(icon);
        }
        workflowValidationService.validateIcon(body.getAvatar());

        // 生成随机workflow id
        String workflowId = UUID.randomUUID().toString();

        // 创建提供的默认工作流，包含三个节点
        long currentTime = System.currentTimeMillis();
        WorkflowVO workflowVo;

        // 对话型任务型工作流默认模板区分，任务型不包含历史对话参数
        if (body.getWorkflowDetails() != null) {
            workflowVo = JSON.parseObject(JSON.toJSONString(body.getWorkflowDetails()), WorkflowVO.class);
        } else {
            String workflowTemplate = getDefaultWorkflowTemplate(body.getType());
            workflowVo = JSON.parseObject(workflowTemplate, WorkflowVO.class);
        }

        workflowVo.setId(workflowId);

        // 大模型节点和全局配置设置默认模型
        setDefaultWorkflowModel(workflowVo, projectId, workspaceId);

        // 默认打开内容审核
        if (ObjectUtils.isEmpty(workflowVo.getConfigs().get(Constants.Workflow.CONTENT_REVIEW))) {
            workflowVo.getConfigs()
                .put(Constants.Workflow.CONTENT_REVIEW,
                    JsonUtils.json2Obj(contentReviewConfigs, Constants.MAP_TYPE_REFERENCE));
        }

        // 更新用户名、描述，当前九问提取name参数作为Agent绑定工作流，模型英文名效果更好
        workflowVo.setName(body.getCode());
        workflowVo.setDescription(body.getDescription());

        body.setWorkflowId(workflowId)
            .setStatus(0)
            .setWorkflowDetails(JSONObject.from(workflowVo))
            .setCreateTime(currentTime)
            .setUpdateTime(currentTime)
            .setPublishTime(null)
            .setCreator(getUserName(projectId))
            .setUpdater(getUserName(projectId))
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setCreatorId(RequestContextUtils.getRequestUserId())
            .setDomainId(RequestContextUtils.getRequestUserDomainId());

        // 上传flow obs
        String flowPath = obsService.uploadObsFile(workflowId, workflowId, CommonConstant.WORKFLOW,
            JSON.toJSONString(workflowVo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.FLOW);
        body.setDslPath(obsService.getAbsolutePath(flowPath));

        // 上传数据库信息包含user id和是否删除
        WorkflowEntity workflowEntity = convertInfoToEntity(workspaceId, body);
        workflowEntity.setCreatorId(RequestContextUtils.getRequestUserId());
        workflowEntity.setUpdaterId(RequestContextUtils.getRequestUserId());
        workflowEntity.setDeleted(0);
        workflowEntity.setDslPath(flowPath);
        workflowEntity.setTestStatus(0);
        workflowEntity.setAvatar(body.getAvatar());
        workflowEntity.setIconName(iconName);
        workflowValidationService.validateIcon(workflowEntity.getAvatar());

        // ir转换并上传obs
        try {
            String irPath = workflowDslToIr(workflowId, workflowEntity, workflowVo);
            workflowEntity.setIrPath(irPath);
        } catch (Exception e) {
            log.info("workflow dsl import failed, dont parse ir.");
        }
        updateRefResources(workflowVo, null);
        workflowMapper.createWorkflowEntity(workflowEntity);
        if (workflowVo.getConfigs() != null && workflowVo.getConfigs().get(CommonConstant.DIFY.TRIGGER) != null) {
            addTrigger(projectId, workflowId, workspaceId, JSONObject.parseObject(workflowVo.getConfigs().get(CommonConstant.DIFY.TRIGGER).toString(), TriggerConfig.class));
        }
        return body;
    }

    private void setDefaultWorkflowModel(WorkflowVO workflowVo, String projectId, String workspaceId) {
        // 设置默认大模型
        List<ModelServiceData> models =
            modelServiceManager.queryAvailableServices(projectId, workspaceId, ModelTypeV2.LLM.toString(), true);

        Map<String, String> modelParam = new HashMap<>();
        ModelServiceData modelServiceData = models.stream()
            .filter(m -> CommonConstant.ModelParam.MODEL_PUBLISH_STATUS_ONLINE.equals(m.getPublishStatus()))
            .findFirst()
            .orElse(null);
        if (modelServiceData != null) {
            modelParam.put(CommonConstant.ModelParam.MODEL_NAME, modelServiceData.getModelName());
            modelParam.put(CommonConstant.ModelParam.MODEL_TYPE, modelServiceData.getModelType());
            modelParam.put(CommonConstant.ModelParam.MODEL_API_TYPE, modelServiceData.getInterfaceProtocol());
            modelParam.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, modelServiceData.getId());
            modelParam.put(CommonConstant.ModelParam.MODEL, modelServiceData.getId());
        }
        workflowVo.getNodes().forEach(node -> {
            if (node.getType().equals(NodeType.LLM.getType()) && ObjectUtils.isEmpty(node.getConfigs().get(CommonConstant.ModelParam.MODEL))) {
                node.getConfigs().put(CommonConstant.ModelParam.MODEL, modelParam);
            }
        });
        if (ObjectUtils.isEmpty(workflowVo.getConfigs().get(CommonConstant.ModelParam.DEFAULT_MODEL))) {
            workflowVo.getConfigs().put(CommonConstant.ModelParam.DEFAULT_MODEL, modelParam);
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Workflow",
        description = "删除工作流",
        resourceId = "workflowId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteWorkflow(String projectId, String workflowId, String workspaceId) {
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (workflowEntity == null) {
            log.info("Workflow:{} does not exist!", workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        // 权限校验
        workflowValidationService.validateModifyPrivilege(workflowEntity, projectId, workspaceId);
        shareResourceManagerService.checkResourceSharedOrNot(projectId, workflowId);
        workflowEntity.setUpdatedAt(System.currentTimeMillis());

        // 调用九问接口删除记忆变量
        try {
            // 删除记忆，待添加
            log.info("Delete memory for workflowId: {}", workflowId);
        } catch (Exception e) {
            String error = String.format("Failed to delete memory for workflowId: %s", workflowId);
            log.error(error, e);
        }
        if (!CollectionUtils.isEmpty(workflowEntity.getTriggerList())) {
            for (TriggerConfig triggerConfig : workflowEntity.getTriggerList()) {
                if (TriggerType.TIMER.name().equals(triggerConfig.getType())) {
                    try {
                        scheduler.pauseTrigger(TriggerKey.triggerKey(triggerConfig.getTriggerId()));
                        scheduler.unscheduleJob(TriggerKey.triggerKey(triggerConfig.getTriggerId()));
                        scheduler.deleteJob(new JobKey(triggerConfig.getName() + '_' + triggerConfig.getTriggerId()));
                    } catch (SchedulerException e) {
                        log.error("Scheduler delete job failed.", e);
                        throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
                    }
                }
            }
        }

        // agent-builder空间取消发布
        if (publishAgentBuilderEnable) {
            agentSpaceService.delete(workspaceId, workflowId);
        }

        // 删除资源关联数据
        if (isSoftDelete) {
            agentCommonService.softDeleteMapping(workflowId);
        } else {
            mappingMapper.deleteBatchByAppId(workflowId, null, true);
        }
        // 下线相应app
        appMapper.deleteByResourceId(workflowId, projectId, workspaceId);

        publishUtils.deletePublish(workflowId, Constants.TREASURE_PUBLISH_VERSION, obsService);

        // 删除workflow需同步删除所有发布通道版本
        releaseChannelMapper.deleteByAppId(workflowId);

        // 将引用该资源的map置为失效
        mappingMapper.updateValidByResourceIdAndVersionId(workflowId, null);

        // 先改表状态软删除后删IR和版本纪录
        workflowCommonService.softDelete(workflowEntity);

        String irPath = CommonConstant.WORKFLOW + CommonConstant.FOLDER_SEPARATOR + CommonConstant.Workflow.IR
            + CommonConstant.FOLDER_SEPARATOR + workflowId;
        String dslPath = CommonConstant.WORKFLOW + CommonConstant.FOLDER_SEPARATOR + CommonConstant.Workflow.FLOW
            + CommonConstant.FOLDER_SEPARATOR + workflowId;
        if (isSoftDelete) {
            // 软删除时ir文件增加“.deleted”后缀,其他全部删除
            obsService.appendSuffixByPrefix(irPath, CommonConstant.DELETED_SUFFIX);
            agentCommonService.softDeleteReleaseVersionByAppId(workflowId);
        } else {
            obsService.deleteObsObjects(irPath);
            releaseVersionMapper.deleteByAppId(workflowId);
        }

        // 删除触发器
        if (!CollectionUtils.isEmpty(workflowEntity.getTriggerList())) {
            for (TriggerConfig triggerConfig : workflowEntity.getTriggerList()) {
                if (TriggerType.TIMER.name().equals(triggerConfig.getType())) {
                    try {
                        scheduler.pauseTrigger(TriggerKey.triggerKey(triggerConfig.getTriggerId()));
                        scheduler.unscheduleJob(TriggerKey.triggerKey(triggerConfig.getTriggerId()));
                        scheduler.deleteJob(new JobKey(triggerConfig.getName() + '_' + triggerConfig.getTriggerId()));
                    } catch (SchedulerException e) {
                        log.error("Scheduler delete job failed.", e);
                        throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
                    }
                }
            }
        }
        // 删除此工作流下所有用户的长期记忆
        agentMemoryConfigService.clearUserMemoriesInApplication(RequestContextUtils.getRequestAuthToken(),
            LanguageUtils.getLanguage(), projectId, workflowId);
        try {
            agentRuntimeClient.clearResourceCache(RequestContextUtils.getRequestAuthToken(), projectId, workflowId,
                Constants.AppType.WORKFLOW);
        } catch (Exception e) {
            log.warn("Failed to clear runtime workflow resource: ", e);
        }

        return new CommonDeleteRsp().setId(workflowId);
    }

    @Override
    public WorkflowInfo getWorkflow(String projectId, String workflowId, String workspaceId) {
        return getWorkflowInfo(projectId, workflowId, ThreadLocalUtils.getWorkspaceId());
    }

    public WorkflowInfo getWorkflowInfo(String projectId, String workflowId, String workspaceId) {
        log.debug("Entering getWorkflow with projectId={}, workflowId={}, workspaceId={}", projectId, workflowId,
            workspaceId);
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (workflowEntity == null) {
            log.error("workflow does not exist, projectId = {}, agentId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        if (Strings.CI.equals(workflowEntity.getVisibility(), VisibilityEnum.USER.getValue())
            && !Strings.CS.equals(workflowEntity.getCreatorId(), RequestContextUtils.getRequestUserId())) {
            throw new AgentStudioException(StudioError.PRIVILEGE_ERROR);
        }

        // 从OBS中下载EI工作流配置
        String workflowJson = obsService.downloadObsFile(workflowEntity.getDslPath());

        // 获取工作流
        WorkflowInfo workflowInfo = convertEntityToInfo(workflowEntity, workflowJson);
        workflowInfo.setRefWorkflows(new ArrayList<>());
        workflowInfo.setTriggerList(workflowEntity.getTriggerList());
        return workflowInfo;
    }

    @Override
    public WorkflowSceneRsp getWorkflowScene(String projectId, String workflowId, String workspaceId) {
        ReleaseChannel releaseChannels =
            releaseChannelMapper.selectByAppIdAndChannel(workflowId, CommonConstant.APP_STORE_CHANNEL);
        if (releaseChannels == null) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_PUBLISHED);
        }
        String versionIds = releaseChannels.getVersionId();
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionIds);
        if (releaseVersion == null) {
            throw new AgentStudioException(StudioError.WORKFLOW_VERSION_NOT_FOUND);
        }
        return parseWorkflowTable(workflowId, releaseChannels.getVersionId(), releaseVersion.getDslPath());
    }

    @Override
    public WorkflowListRsp listWorkflows(String projectId, ListWorkflowsQo listWorkflowsQo) {
        return listWorkflows(projectId, listWorkflowsQo.getOffset(), listWorkflowsQo.getLimit(), listWorkflowsQo);
    }

    public WorkflowListRsp listWorkflows(String projectId, Integer offset, Integer limit,
        ListWorkflowsQo listWorkflowsQo) {
        PageHelper.offsetPage(offset, limit);
        List<WorkflowEntity> workflowEntityList;

        // 转换特殊符号 _, %, !
        listWorkflowsQo.setName(escapeSqlSpecialChars(listWorkflowsQo.getName()));
        listWorkflowsQo.setDescription(escapeSqlSpecialChars(listWorkflowsQo.getDescription()));

        // 展示workflow
        if (Strings.CS.equals(listWorkflowsQo.getGroup(), CommonConstant.WORKFLOW_INNER)) {
            listWorkflowsQo.setWorkspaceId(null);
            workflowEntityList = workflowMapper.selectByWorkflowSearchCriteria(opSvcProjectId, listWorkflowsQo);
        } else {
            // creator id相同过滤
            workflowEntityList = workflowMapper.selectByWorkflowSearchCriteria(projectId, listWorkflowsQo);
        }
        PageInfo<WorkflowEntity> workflowPageInfo = new PageInfo<>(workflowEntityList);
        List<WorkflowListItem> workflowList = new ArrayList<>();

        workflowEntityList.forEach(workflowEntity -> {
            WorkflowListItem workflowListItem = new WorkflowListItem();
            workflowListItem.setWorkflowId(workflowEntity.getId());
            workflowListItem.setName(workflowEntity.getName());
            workflowListItem.setAvatar(workflowEntity.getAvatar());
            workflowListItem.setCode(workflowEntity.getCode());
            workflowListItem.setDescription(workflowEntity.getDescription());
            workflowListItem.setLastVersionId(workflowEntity.getLastVersionId());
            workflowListItem.setGroup(Strings.CS.equals(workflowEntity.getProjectId(), opSvcProjectId)
                ? CommonConstant.WORKFLOW_INNER : CommonConstant.WORKFLOW_PERSONAL);
            workflowListItem.setCreator(workflowEntity.getCreatedBy());
            workflowListItem.setType(
                workflowEntity.getWorkflowType() == null ? CommonConstant.CHAT : workflowEntity.getWorkflowType());
            String workflowUrl = String.format(endpointTemplate, projectId, workflowEntity.getId());
            if (StringUtils.isNotEmpty(runtimeHost)) {
                String protocol = Constants.TRUE.equalsIgnoreCase(serverSslEnabled) ? "https://" : "http://";
                workflowUrl = protocol + runtimeHost.replaceFirst("^https?://", "") + workflowUrl;
            }
            workflowListItem.setUrl(workflowUrl);
            workflowListItem
                .setStatus(Strings.CS.equals(workflowEntity.getStatus(), CommonConstant.WORKFLOW_DEVELOP) ? 0 : 1);
            if (Objects.equals(workflowEntity.getCustomizeNode(), 1)) {
                workflowListItem.setCustomizeNode(true);
            }
            workflowListItem.setUpdatedOn(workflowEntity.getUpdatedAt());
            workflowListItem.setIsShare(workflowEntity.getIsShare());
            workflowList.add(workflowListItem);
        });
        WorkflowListRsp workflowListRsp = new WorkflowListRsp();
        workflowListRsp.setWorkflowList(workflowList);
        workflowListRsp.setCount(workflowPageInfo.getTotal());
        return workflowListRsp;
    }

    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "发布工作流",
        resourceId = "workflowId",
        resourceName = ""
    )
    public Void publishWorkflow(String projectId, String workflowId, List<String> tags) {
        // 兼容老发布接口
        publishWorkflow(projectId, workflowId, tags, null);
        return null;
    }

    private void publishWorkflow(String projectId, String workflowId, List<String> tags,
        CreateChannelReq createChannelReq) {
        // 获取工作流并校验权限
        WorkflowEntity workflow = checkOpWorkflowPermission(projectId, workflowId);

        App originApp = appMapper.selectByResourceId(workflowId);

        // 删除老的App，创建一个新的App对象，记录workflow发布的应用信息
        appMapper.deleteByResourceId(workflowId, projectId, ThreadLocalUtils.getWorkspaceId());
        App apps = new App(workflow);
        apps.setTags(tags);
        apps.setProjectId(projectId);
        apps.setWorkspaceId(ThreadLocalUtils.getWorkspaceId());
        if (Objects.equals(projectId, opSvcProjectId)) {
            apps.setCreator(CommonConstant.DEFAULT_USERNAME);
        }
        // 修改接口时继承原参数
        if (originApp != null) {
            apps.setInputParams(originApp.getInputParams());
            apps.setOutputParams(originApp.getOutputParams());
            apps.setPrologue(originApp.getPrologue());
            apps.setSuggestQueries(originApp.getSuggestQueries());
        }

        // 发布时刷新app表
        if (createChannelReq != null) {
            apps.setInputParams(
                createChannelReq.getInputs() != null ? JsonUtils.toJson(createChannelReq.getInputs()) : null);
            apps.setOutputParams(
                createChannelReq.getOutputs() != null ? JsonUtils.toJson(createChannelReq.getOutputs()) : null);
            apps.setPrologue(createChannelReq.getPrologue());
            apps.setSuggestQueries(createChannelReq.getSuggestQueries());
        }
        appMapper.insert(apps);

        // 设置workflow的状态为已发布且全局可见
        workflow.setStatus(CommonConstant.WORKFLOW_PUBLISHED);
        workflow.setVisibility(VisibilityEnum.GLOBAL.getValue());
        workflow.setPublishedAt(System.currentTimeMillis());

        workflowMapper.updateWorkflowEntity(projectId, workflowId, workflow);

        // 获取内容审核开关
        String workflowJson = obsService.downloadObsFile(workflow.getDslPath());

        Optional<JSONObject> jsonObject = Optional.ofNullable(JSON.parseObject(workflowJson));

        boolean isReviewEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
            .map(object -> object.getJSONObject(Constants.Workflow.CONTENT_REVIEW))
            .map(object -> object.getBoolean(Constants.Workflow.ENABLED))
            .orElse(false);

        boolean isSafetyBarrierEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
            .map(object -> object.getBoolean(Constants.Workflow.SAFETY_BARRIER))
            .orElse(false);

        // 记录百宝箱发布的版本元数据至OBS和Redis
        publishUtils.savePublish(AgentMetadata.builder()
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .projectId(projectId)
            .workspaceId(ThreadLocalUtils.getWorkspaceId())
            .agentId(workflowId)
            .versionId(workflow.getLastVersionId())
            .updatedAt(System.currentTimeMillis())
            .isContentReviewEnable(isReviewEnabled)
            .safetyBarrier(isSafetyBarrierEnabled)
            .appType(workflow.getWorkflowType())
            .build(), Constants.TREASURE_PUBLISH_VERSION, obsService);
    }

    /**
     * 创建一个工作流版本快照
     *
     * @param projectId projectId
     * @param workflowId 工作流Id
     * @return String 发布版本号
     */
    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "发布工作流版本",
        resourceId = "workflowId",
        resourceName = ""
    )
    public String releaseWorkflowVersion(String projectId, String workflowId, String workspaceId,
        CreateVersionReq createVersionReq) {
        return releaseWorkflowVersionId(projectId, workspaceId, workflowId, null, createVersionReq);
    }

    /**
     * 创建一个工作流版本快照
     *
     * @param projectId projectId
     * @param workflowId 工作流Id
     * @return String 发布版本号
     */
    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "发布工作流版本",
        resourceId = "workflowId",
        resourceName = ""
    )
    public String releaseWorkflowVersionV1(String projectId, String workflowId, String workspaceId,
        CreateVersionReq body) {
        return releaseWorkflowVersionId(projectId, workspaceId, workflowId, null, body);
    }

    /**
     * 创建一个工作流版本快照
     *
     * @param projectId projectId
     * @param workflowId 工作流Id
     * @param versionId 已发布版本号
     * @return String 发布版本号
     */
    public @NotNull String releaseWorkflowVersionId(String projectId, String workspaceId, String workflowId,
        String versionId, CreateVersionReq createVersionReq) {
        String releaseVersionIds = versionId;
        WorkflowEntity workflowEntity = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
            ThreadLocalUtils.getWorkspaceId(), workflowId);
        if (Objects.isNull(workflowEntity)) {
            log.error("Workflow:{} not exists by condition: projectId:{}, workspaceId:{}, localWorkspaceId:{} ",
                workflowId, projectId, workspaceId, ThreadLocalUtils.getWorkspaceId());
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        List<ReleaseVersion> releaseVersionList = releaseVersionMapper.selectByAppId(workflowId);

        Set<String> existedVersionNameSet =
            releaseVersionList.stream().map(ReleaseVersion::getVersionName).collect(Collectors.toSet());

        if (existedVersionNameSet.contains(createVersionReq.getVersionName())) {
            log.error("the version name of workflow {} already existed.", workflowId);
            throw new AgentStudioException(StudioError.VERSION_NAME_ALREADY_EXISTED);
        }

        if (releaseVersionList.size() > releaseMaxSize) {
            log.error("The number of application release versions exceeds the upper limit.");
            throw new AgentStudioException(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT);
        }

        ReleaseVersion releaseWorkflowVersion = new ReleaseVersion();
        if (StringUtils.isEmpty(releaseVersionIds)) {
            releaseVersionIds = String.valueOf(System.currentTimeMillis());
        }

        // 1. 创建工作流DSL和IR版本快照,把版本dsl存到版本对应dsl
        String workflowJson = obsService.downloadObsFile(workflowEntity.getDslPath());
        if (!workflowValidationService
            .validate(projectId, workspaceId, JSON.parseObject(workflowJson, WorkflowVO.class))
            .isSuccess()) {
            log.error("Workflow information validation failed");
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
        String releaseDslPath =
            obsService.uploadObsFile(workflowId, workflowId + Constants.UNDERLINE_STR + releaseVersionIds,
                CommonConstant.WORKFLOW, workflowJson, CommonConstant.Workflow.FLOW);
        releaseWorkflowVersion.setDslPath(releaseDslPath);
        String releaseIrPaths = getWorkflowObsPath(workflowId, CommonConstant.Workflow.IR, releaseVersionIds);
        obsService.copyObsObject(workflowEntity.getIrPath(), releaseIrPaths);
        releaseWorkflowVersion.setIrPath(releaseIrPaths);

        // 2. 插入版本数据到应用版本表中
        releaseWorkflowVersion.setId(UUID.randomUUID().toString());
        releaseWorkflowVersion.setVersionId(releaseVersionIds);
        releaseWorkflowVersion.setVersionName(createVersionReq.getVersionName());
        releaseWorkflowVersion.setVersionNote(createVersionReq.getVersionNote());
        releaseWorkflowVersion.setAppId(workflowId);
        releaseWorkflowVersion.setAppType(CommonConstant.WORKFLOW_TYPE);
        releaseWorkflowVersion.setStatus(CommonConstant.NORMAL);
        releaseWorkflowVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseWorkflowVersion.setCreatorId(RequestContextUtils.getRequestUserId());
        releaseWorkflowVersion.setReleasedOn(new Date());

        // 3. 记录版本关联的资源
        WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);
        if (workflowVo != null) {
            updateRefResources(workflowVo, releaseVersionIds);
            Map<String, Object> configs = workflowVo.getConfigs();
        }
        if (workflowVo != null && !CollectionUtils.isEmpty(workflowVo.getConfigs())) {
            String environmentId = workflowVo.getConfigs().get(Constants.Workflow.ENVIRONMENT) == null ? ""
                : String.valueOf(workflowVo.getConfigs().get(Constants.Workflow.ENVIRONMENT));
            try {
                this.environmentServiceManagerService.uploadEnvironmentVarToObsFile(projectId, workflowId,
                    environmentId, workspaceId, releaseVersionIds);
            } catch (Exception e) {
                log.error(
                    "Workflow version release, environment variable copy writing to obs failed; environment id is {}",
                    environmentId, e);
            }
        }
        releaseVersionMapper.insert(releaseWorkflowVersion);

        // 4. 获取内容审核开关 从IR获取内容审核开关
        Optional<JSONObject> jsonObject = Optional.ofNullable(JSON.parseObject(workflowJson));

        boolean isReviewEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
            .map(object -> object.getJSONObject(Constants.Workflow.CONTENT_REVIEW))
            .map(object -> object.getBoolean(Constants.Workflow.ENABLED))
            .orElse(false);

        boolean isSafetyBarrierEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
            .map(object -> object.getBoolean(Constants.Workflow.SAFETY_BARRIER))
            .orElse(false);

        // 记录最新发布的版本元数据至OBS和Redis
        publishUtils.savePublish(AgentMetadata.builder()
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .projectId(projectId)
            .workspaceId(workspaceId)
            .agentId(releaseWorkflowVersion.getAppId())
            .versionId(releaseWorkflowVersion.getVersionId())
            .updatedAt(System.currentTimeMillis())
            .isContentReviewEnable(isReviewEnabled)
            .safetyBarrier(isSafetyBarrierEnabled)
            .appType(workflowEntity.getWorkflowType())
            .build(), Constants.LATEST_PUBLISH_VERSION, obsService);

        // 4.更新工作流发布状态
        workflowEntity.setStatus(CommonConstant.WORKFLOW_PUBLISHED);
        workflowEntity.setPublishedAt(System.currentTimeMillis());
        workflowEntity.setLastVersionId(releaseVersionIds);
        workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        return releaseVersionIds;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "添加工作流触发器",
        resourceId = "workflowId",
        resourceName = ""
    )
    public TriggerConfig addTrigger(String projectId, String workflowId, String workspaceId, TriggerConfig body) {
        if (!TriggerType.TIMER.name().equals(body.getType()) && !TriggerType.EVENT.name().equals(body.getType())) {
            log.error("Trigger type is wrong. The wrong type is {}. projectId = {}, workflowId = {}", body.getType(),
                projectId, workflowId);
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_TYPE_INCORRECT, body.getType());
        }
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        List<TriggerConfig> triggerList = workflowEntity.getTriggerList();
        if (!org.apache.commons.collections4.CollectionUtils.isEmpty(triggerList)
            && triggerList.size() >= CommonConstant.MAX_TRIGGER_WORKFLOW_NUMS) {
            log.error("The number of triggers has reached the upper limit. projectId = {}, workflowId = {}", projectId,
                workflowId);
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_SIZE_LIMIT);
        }
        if (body.getTriggerId() == null || body.getTriggerId().isEmpty()) {
            body.setTriggerId(UUID.randomUUID().toString());
        }
        TriggerKey triggerKey = TriggerKey.triggerKey(body.getTriggerId());
        try {
            Trigger trigger = scheduler.getTrigger(triggerKey);
            if (trigger == null) {
                trigger = TriggerBuilder.newTrigger()
                    .withIdentity(triggerKey)
                    .withSchedule(CronScheduleBuilder.cronSchedule(body.getCron()))
                    .build();
                JobDetail jobDetail = JobBuilder.newJob(AgentTriggerService.class)
                    .withIdentity(body.getName() + '_' + body.getTriggerId())
                    .usingJobData(CommonConstant.PROJECT_ID, projectId)
                    .usingJobData(CommonConstant.DOMAIN_ID, RequestContextUtils.getRequestUserDomainId())
                    .usingJobData(CommonConstant.Workflow.ID, workflowId)
                    .usingJobData(CommonConstant.TRIGGER_ID, body.getTriggerId())
                    .usingJobData(CommonConstant.PROMPT, body.getPrompt())
                    .usingJobData(CommonConstant.WORKSPACE_ID, workspaceId)
                    .usingJobData(CommonConstant.AGENT_RUNTIME_ENDPOINT, agentRuntimeEndpoint)
                    .usingJobData(CommonConstant.RUN_AGENT_STREAM_URL, runWorkflowStreamUrl)
                    .build();
                scheduler.scheduleJob(jobDetail, trigger);
                if (!scheduler.isShutdown()) {
                    scheduler.start();
                }
                if (triggerList == null) {
                    workflowEntity.setTriggerList(new ArrayList<>());
                } else {
                    workflowEntity.setTriggerList(triggerList);
                }
                workflowEntity.getTriggerList().add(body);
            }
        } catch (SchedulerException e) {
            log.error("Scheduler add job failed.", e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
        workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        return body;
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Workflow",
        description = "删除工作流触发器",
        resourceId = "triggerId",
        resourceName = ""
    )
    public Void deleteTrigger(String projectId, String workflowId, String triggerId, String workspaceId) {
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, ThreadLocalUtils.getWorkspaceId(), workflowId);
        List<TriggerConfig> triggerList = workflowEntity.getTriggerList();
        if (org.apache.commons.collections4.CollectionUtils.isEmpty(triggerList)) {
            log.error("Trigger does not exist! projectId = {}, workflowId = {}, triggerId = {}", projectId, workflowId,
                triggerId);
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_EXIST, triggerId);
        }
        for (int index = 0; index < triggerList.size(); index++) {
            if (triggerId.equals(triggerList.get(index).getTriggerId())) {
                TriggerConfig triggerConfig = triggerList.get(index);
                if (TriggerType.TIMER.name().equals(triggerConfig.getType())) {
                    try {
                        scheduler.pauseTrigger(TriggerKey.triggerKey(triggerId));
                        scheduler.unscheduleJob(TriggerKey.triggerKey(triggerId));
                        scheduler.deleteJob(new JobKey(triggerConfig.getName() + '_' + triggerId));
                    } catch (SchedulerException e) {
                        log.error("Scheduler delete job failed.", e);
                        throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
                    }
                }
                triggerList.remove(index);
                workflowEntity.setTriggerList(triggerList);
                workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
                return null;
            }
        }
        log.error("Trigger does not exist! projectId = {}, workflowId = {}, triggerId = {}", projectId, workflowId,
            triggerId);
        throw new AgentStudioException(StudioError.AGENT_TRIGGER_EXIST, triggerId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Workflow",
        description = "编辑触发器",
        resourceId = "body.triggerId",
        resourceName = ""
    )
    public TriggerConfig editTrigger(String projectId, String workflowId, String workspaceId, TriggerConfig body) {
        // delete原任务
        deleteTrigger(projectId, workflowId, body.getTriggerId(), workspaceId);
        addTrigger(projectId, workflowId, workspaceId, body);
        return body;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Workflow",
        description = "设置试运行状态",
        resourceId = "workflowId",
        resourceName = ""
    )
    public WorkflowInfo setWorkflowTestStatus(String projectId, String workflowId, String workspaceId, Boolean status) {
        WorkflowEntity workflowEntity = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
            ThreadLocalUtils.getWorkspaceId(), workflowId);
        if (workflowEntity == null) {
            log.error("Workflow does not exist.");
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        // 设置试运行成功状态:1,成功; 0,失败
        workflowEntity.setTestStatus(status ? 1 : 0);
        workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        return new WorkflowInfo().setWorkflowId(workflowId).setTestStatus(workflowEntity.getTestStatus());
    }

    /**
     * 删除指定工作流版本快照
     *
     * @param projectId projectId
     * @param workflowId 工作流Id
     * @param versionId 发布版本号
     * @return Void
     */
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Workflow",
        description = "删除工作流版本",
        resourceId = "workflowId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteWorkflowVersion(String projectId, String workflowId, String versionId,
        String workspaceId) {
        // 获取工作流并校验权限
        checkWorkflowExist(projectId, workspaceId, workflowId);

        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);
        WorkflowEntity workflowEntity = workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (!Strings.CS.equals(RequestContextUtils.getRequestWorkspaceId(), workflowEntity.getWorkspaceId())) {
            log.error("No permission to delete workflow version.");
            throw new AgentStudioException(StudioError.NO_PERMISSION_DELETE_WORKFLOW_VERSION);
        }

        // 删除版本纪录
        if (isSoftDelete) {
            agentCommonService.softDeleteReleaseVersionById(releaseVersion);
            obsService.softDeleteObsFile(releaseVersion.getDslPath());
            obsService.softDeleteObsFile(releaseVersion.getIrPath());
            obsService.softDeleteObsFile(this.getEnvironmentVariableFilePath(releaseVersion.getIrPath()));
        } else {
            releaseVersionMapper.deleteByPrimaryKey(releaseVersion.getId());
            obsService.deleteObsFile(releaseVersion.getDslPath());
            obsService.deleteObsFile(releaseVersion.getIrPath());
            obsService.deleteObsFile(this.getEnvironmentVariableFilePath(releaseVersion.getIrPath()));
        }

        // 删除最新发布版本
        publishUtils.deletePublish(releaseVersion.getAppId(), Constants.LATEST_PUBLISH_VERSION, obsService);

        // 如当前版本已发布百宝箱，则删除对应百宝箱应用
        AgentMetadata metadata = null;
        try {
            metadata = publishUtils.getPublish(workflowId, Constants.TREASURE_PUBLISH_VERSION, obsService);
        } catch (AgentStudioException e) {
            log.warn("Get published metadata failed, version may have not been published yet.");
        }

        if (metadata != null && Strings.CS.equals(metadata.getVersionId(), versionId)) {
            appMapper.deleteByResourceId(workflowId, projectId, workspaceId);
            publishUtils.deletePublish(workflowId, Constants.TREASURE_PUBLISH_VERSION, obsService);
        }

        // 删除版本相关发布通道
        releaseChannelMapper.deleteByAppIdAndVersionId(workflowId, versionId);

        // 删除版本同步删除版本绑定记录
        mappingMapper.deleteBatchByAppId(workflowId, versionId, false);

        // 所有版本均删除时更新workflow发布状态
        List<ReleaseVersion> releaseVersionList = releaseVersionMapper.selectByAppId(workflowId);
        if (CollectionUtils.isEmpty(releaseVersionList)) {
            workflowEntity.setStatus(CommonConstant.WORKFLOW_DEVELOP);
            workflowEntity.setPublishedAt(null);
            workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        } else {
            // 取现存最新的版本，作为最新发布版本保存
            ReleaseVersion latestReleaseVersion =
                releaseVersionList.stream().max(Comparator.comparing(ReleaseVersion::getVersionId)).get();

            // 获取内容审核开关
            String workflowJson = obsService.downloadObsFile(latestReleaseVersion.getDslPath());
            Optional<JSONObject> jsonObject = Optional.ofNullable(JSON.parseObject(workflowJson));
            boolean isReviewEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
                .map(object -> object.getJSONObject(Constants.Workflow.CONTENT_REVIEW))
                .map(object -> object.getBoolean(Constants.Workflow.ENABLED))
                .orElse(false);

            boolean isSafetyBarrierEnabled = jsonObject.map(object -> object.getJSONObject(Constants.Workflow.CONFIGS))
                .map(object -> object.getBoolean(Constants.Workflow.SAFETY_BARRIER))
                .orElse(false);
            publishUtils.savePublish(AgentMetadata.builder()
                .domainId(RequestContextUtils.getRequestUserDomainId())
                .projectId(projectId)
                .workspaceId(workspaceId)
                .agentId(latestReleaseVersion.getAppId())
                .versionId(latestReleaseVersion.getVersionId())
                .updatedAt(latestReleaseVersion.getReleasedOn().getTime())
                .isContentReviewEnable(isReviewEnabled)
                .safetyBarrier(isSafetyBarrierEnabled)
                .appType(workflowEntity.getWorkflowType())
                .build(), Constants.LATEST_PUBLISH_VERSION, obsService);
        }

        return new CommonDeleteRsp().setId(versionId);
    }

    private String getEnvironmentVariableFilePath(String originalPath) {
        if (StringUtils.isEmpty(originalPath)) {
            return "";
        }
        File originalFile = new File(originalPath);
        String parentDir = originalFile.getParent();
        String originalName = originalFile.getName();
        int lastDotIndex = originalName.lastIndexOf('.');
        if (lastDotIndex < 0) {
            return "";
        }
        String fileName = originalName.substring(0, lastDotIndex);
        String suffix = originalName.substring(lastDotIndex);
        String newFileName = fileName + "_env" + suffix;
        File newFile = new File(parentDir, newFileName);
        return newFile.getPath();
    }

    private WorkflowEntity checkWorkflowExist(String projectId, String workspaceId, String workflowId) {
        WorkflowEntity workflow = workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (workflow == null) {
            log.error("workflow does not exist, projectId = {}, workflowId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        return workflow;
    }

    /**
     * 还原版本时获取指定版本工作流定义
     *
     * @param projectId projectId
     * @param workflowId 工作流Id
     * @param versionId 版本号
     * @return WorkflowInfo 工作流完整定义
     */
    @Override
    public WorkflowInfo getWorkflowVersion(String projectId, String workflowId, String versionId, Boolean nestedCheck,
        GetWorkflowVersionQo getWorkflowVersionQo) {
        String workspaceId = null;

        ShareResourceEntity shareResourceEntity
            = shareResourceManagerService.queryShareResourceEntityByResourceIdAndVersionId(workflowId,
            ThreadLocalUtils.getWorkspaceId(), versionId);

        if (shareResourceEntity != null) {
            workspaceId = shareResourceEntity.getWorkspaceId();
        }

        if (StringUtils.isEmpty(workspaceId) && !publishCrossWorkspace) {
            workspaceId = ThreadLocalUtils.getWorkspaceId();
        }

        // 获取工作流并校验权限
        checkWorkflowExist(projectId, workspaceId, workflowId);

        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);
        if (releaseVersion == null) {
            log.error("workflow version is not found");
            throw new AgentStudioException(StudioError.WORKFLOW_VERSION_NOT_FOUND);
        }

        // 检查工作流嵌套层级
        if (nestedCheck != null && !isNestedLevelValid(releaseVersion, nestedCheck)) {
            log.error("Workflow nested exceed max level:{}", getNestedLevelLimit());
            throw new AgentStudioException(StudioError.WORKFLOW_NESTED_CHECK);
        }

        // 获取工作流的版本详情
        WorkflowEntity workflowEntities =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, workspaceId, workflowId);
        String workflowJson = obsService.downloadObsFile(releaseVersion.getDslPath());
        WorkflowInfo workflowInfo = convertEntityToInfo(workflowEntities, workflowJson);

        workflowInfo.setRefWorkflows(new ArrayList<>()).setTriggerList(workflowEntities.getTriggerList());
        return workflowInfo;
    }

    private boolean isNestedLevelValid(ReleaseVersion releaseVersion, boolean shouldNestedCheck) {
        if (!shouldNestedCheck) {
            return true;
        }

        // 配置为0不限制
        if (getNestedLevelLimit() == 0) {
            return true;
        }

        // 配置N,进行N-1轮，子工作流查询
        List<MappingEntity> subWorkflowRef = new ArrayList<>();
        for (int i = 0; i < getNestedLevelLimit(); i++) {
            if (i == 0) {
                // 查找父工作流引用的所有子工作流
                subWorkflowRef = mappingMapper.selectByAppIdAndAppVersion(releaseVersion.getAppId(),
                    releaseVersion.getVersionId(), WORKFLOW.name(), true);
            } else {
                // 查找上一层所有子工作流引用的子工作流
                subWorkflowRef = mappingMapper.selectByRefs(subWorkflowRef, WORKFLOW.name());
            }
            // 如果到某中间层已没有子工作流，则不用继续往下查
            if (CollectionUtils.isEmpty(subWorkflowRef)) {
                break;
            }
        }

        // n-1次下钻查询后，子工作流为空则通过校验
        return CollectionUtils.isEmpty(subWorkflowRef);
    }

    private int getNestedLevelLimit() {
        return nestedLevel > MAX_NESTED_LEVEL ? MAX_NESTED_LEVEL : nestedLevel;
    }

    /**
     * 解析 refWorkflows
     *
     * @param refWorkflows 发布子工作流
     * @return 解析发布工作流列表
     */
    private List<ReleaseVersion> parseRefWorkflows(String refWorkflows) {
        List<ReleaseVersion> releaseVersionList = new ArrayList<>();
        if (!StringUtils.isEmpty(refWorkflows)) {
            String[] refWfVersionAry = StringUtils.split(refWorkflows, CommonConstant.SEPARATOR);
            for (String refWfVersion : refWfVersionAry) {
                if (!StringUtils.isEmpty(refWfVersion)) {
                    String[] refWf = StringUtils.split(refWfVersion, SEPARATOR);
                    if (refWf.length > 1) {
                        ReleaseVersion releaseVersion = new ReleaseVersion();
                        releaseVersion.setAppId(refWf[0]);
                        releaseVersion.setVersionId(refWf[1]);
                        releaseVersionList.add(releaseVersion);
                    }
                }
            }
        }
        return releaseVersionList;
    }

    @Override
    public WorkflowVersionListRsp listWorkflowLastVersions(String projectId,
        ListWorkflowLastVersionsQo listWorkflowLastVersionsQo) {
        Integer offset = listWorkflowLastVersionsQo.getOffset();
        Integer limit = listWorkflowLastVersionsQo.getLimit();
        listWorkflowLastVersionsQo.setCreator(StrUtils.filterSpecialWords(listWorkflowLastVersionsQo.getCreator()));
        listWorkflowLastVersionsQo
            .setDescription(StrUtils.filterSpecialWords(listWorkflowLastVersionsQo.getDescription()));
        listWorkflowLastVersionsQo.setName(StrUtils.filterSpecialWords(listWorkflowLastVersionsQo.getName()));
        PageHelper.offsetPage(offset, limit);

        if (publishCrossWorkspace) {
            listWorkflowLastVersionsQo.setWorkspaceId(null);
        }

        List<WorkflowVersionEntity> wfLastVersionList =
            workflowMapper.selectLastVersionByWorkflowSearchCriteria(projectId, listWorkflowLastVersionsQo);
        PageInfo<WorkflowVersionEntity> workflowVersionPageInfo = new PageInfo<>(wfLastVersionList);
        List<WorkflowVersionListItem> workflowVersionList = convertEntityToInfo(wfLastVersionList);

        return new WorkflowVersionListRsp().setCount(workflowVersionPageInfo.getTotal())
            .setWorkflowVersionList(workflowVersionList);
    }

    private List<WorkflowVersionListItem> convertEntityToInfo(List<WorkflowVersionEntity> wfLastVersionList) {
        List<WorkflowVersionListItem> list = new ArrayList<>();
        if (!CollectionUtils.isEmpty(wfLastVersionList)) {
            for (WorkflowVersionEntity workflowVersionEntity : wfLastVersionList) {
                WorkflowVersionListItem versionListItem = new WorkflowVersionListItem();
                versionListItem.setWorkflowId(workflowVersionEntity.getId());
                versionListItem.setName(workflowVersionEntity.getName());
                versionListItem.setCode(workflowVersionEntity.getCode());
                versionListItem.setCreator(workflowVersionEntity.getCreatedBy());
                versionListItem.setAvatar(workflowVersionEntity.getAvatar());
                versionListItem.setVersionId(workflowVersionEntity.getVersionId());
                versionListItem.setVersionName(workflowVersionEntity.getVersionName());
                versionListItem.setType(workflowVersionEntity.getWorkflowType());
                versionListItem.setDescription(workflowVersionEntity.getDescription());
                if (Objects.equals(workflowVersionEntity.getCustomizeNode(), 1)) {
                    versionListItem.setCustomizeNode(true);
                }
                list.add(versionListItem);
            }
        }
        return list;
    }

    private WorkflowInfo convertEntityToInfo(WorkflowEntity workflowEntity, String workflowJson) {
        return new WorkflowInfo().setWorkflowId(workflowEntity.getId())
            .setName(workflowEntity.getName())
            .setCode(workflowEntity.getCode())
            .setDescription(workflowEntity.getDescription())
            .setAvatar(workflowEntity.getAvatar())
            .setStatus(Strings.CS.equals(workflowEntity.getStatus(), CommonConstant.WORKFLOW_DEVELOP) ? 0 : 1)
            .setWorkflowDetails(JsonUtils.json2Obj(filterSpecialWorkflowNodes(workflowJson),
                new com.fasterxml.jackson.core.type.TypeReference<>() {}))
            .setCreateTime(workflowEntity.getCreatedAt() != null ? workflowEntity.getCreatedAt() : null)
            .setUpdateTime(workflowEntity.getUpdatedAt() != null ? workflowEntity.getUpdatedAt() : null)
            .setPublishTime(workflowEntity.getPublishedAt() != null ? workflowEntity.getPublishedAt() : null)
            .setCreator(workflowEntity.getCreatedBy())
            .setUpdater(workflowEntity.getUpdatedBy())
            .setProjectId(workflowEntity.getProjectId())
            .setWorkspaceId(workflowEntity.getWorkspaceId())
            .setDomainId(workflowEntity.getDomainId())
            .setCreatorId(workflowEntity.getCreatorId())
            .setDslPath(obsService.getAbsolutePath(workflowEntity.getDslPath()))
            .setTestStatus(workflowEntity.getTestStatus())
            .setCustomizeNode(Objects.equals(workflowEntity.getCustomizeNode(), 1) ? true : null)
            .setType(workflowEntity.getWorkflowType() == null ? CommonConstant.CHAT : workflowEntity.getWorkflowType())
            .setTraceId(workflowEntity.getTraceId());
    }

    /**
     * 查询workflow版本列表
     *
     * @param projectId 项目Id
     * @param workflowId 工作流Id
     * @param listWorkflowVersionsQo 查询参数对象
     * @return 工作流发布版本列表
     */
    @Override
    public VersionListRsp listWorkflowVersions(String projectId, String workflowId,
        ListWorkflowVersionsQo listWorkflowVersionsQo) {
        if (publishCrossWorkspace) {
            listWorkflowVersionsQo.setWorkspaceId(null);
        }

        checkWorkflowExist(projectId, listWorkflowVersionsQo.getWorkspaceId(), workflowId);

        return agentCommonService.listVersions(workflowId, releaseMaxSize);
    }

    /**
     * 查询workflow版本列表
     *
     * @param projectId 项目Id
     * @param workflowId 工作流Id
     * @param listWorkflowVersionsV1Qo 查询参数对象
     * @return 工作流发布版本列表
     */
    @Override
    public VersionListRsp listWorkflowVersionsV1(String projectId, String workflowId,
        ListWorkflowVersionsV1Qo listWorkflowVersionsV1Qo) {
        ListWorkflowVersionsQo qo = JSON.parseObject(JSON.toJSONString(listWorkflowVersionsV1Qo), ListWorkflowVersionsQo.class);
        return listWorkflowVersions(projectId, workflowId, qo);
    }

    /**
     * 发布一个Workflow版本通道
     *
     * @param projectId 项目Id
     * @param workflowId 工作流Id
     * @param body 工作流创建通道请求体
     * @return 工作流通道
     */
    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Workflow",
        description = "创建发布通道",
        resourceId = "workflowId",
        resourceName = ""
    )
    public VersionChannelInfo createWorkflowChannel(String projectId, String workflowId, String workspaceId,
        CreateChannelReq body) {
        // 检查工作流是否存在
        WorkflowEntity workflow = checkWorkflowExist(projectId, workspaceId, workflowId);

        ReleaseChannel releaseWorkflowChannel = new ReleaseChannel();
        releaseWorkflowChannel.setCreator(RequestContextUtils.getRequestUserName());
        releaseWorkflowChannel.setCreatorId(RequestContextUtils.getRequestUserId());
        String channelType = body.getChannelType();
        switch (channelType) {
            case CommonConstant.WEB_PAGE_CHANNEL, CommonConstant.CLOUD_STORE_CHANNEL -> {
                String shortCode = StrUtils.generateShortUuid();
                releaseWorkflowChannel.setShortCode(shortCode);
                releaseWorkflowChannel.setEntryPoint(webpageEndpoint + shortCode);
                releaseWorkflowChannel.setCallCount(body.getCallCount());
                releaseWorkflowChannel.setVisibilityScope(body.getVisibilityScope().toString());
            }
            case CommonConstant.APP_STORE_CHANNEL -> {
                if (!publishAppEnable) {
                    // 百宝箱发布通道类型不支持
                    log.error("the Appstore channel not supported, workflowId: {}.", workflowId);
                    throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_TYPE_INCORRECT);
                }
                String domainName = RequestContextUtils.getRequestUserDomainName();
                if (domainName != null && (domainName.startsWith("op-svc") || domainName.startsWith("op_svc"))) {
                    List<Object> tagList = body.getMetadata() == null ? new ArrayList<>()
                        : JSON.parseArray(JSON.toJSONString(body.getMetadata(), JSONWriter.Feature.WriteMapNullValue));
                    releaseWorkflowChannel.setMetadata(tagList.toString());

                    // 兼容老的百宝箱发布逻辑
                    publishWorkflow(projectId, workflowId, tagList.stream().map(Object::toString).toList(), body);
                }
            }
            case CommonConstant.AGENT_BUILDER -> {
                releaseWorkflowChannel.setId(workflowId);
                releaseWorkflowChannel.setProjectId(projectId);
                releaseWorkflowChannel.setWorkspaceId(workspaceId);
                releaseWorkflowChannel.setAppType(workflow.getWorkflowType());
                releaseWorkflowChannel.setReleasedOn(new Date(System.currentTimeMillis()));
                releaseWorkflowChannel.setAppId(workflowId);
                releaseWorkflowChannel.setStatus("released");
                releaseWorkflowChannel.setChannelType(channelType);
                agentSpaceService.publish(releaseWorkflowChannel);
                return releaseWorkflowChannel.convertToInfo();
            }
            default -> {
                // 发布通道类型不存在
                log.error("the channel type {} is incorrect.", channelType);
                throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_TYPE_INCORRECT);
            }
        }
        String channelId = UUID.randomUUID().toString();
        ReleaseChannel oldReleaseChannel =
            releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(workflowId, channelType, projectId, workspaceId);
        if (oldReleaseChannel != null) {
            // 检查发布通道是否已存在，已存在则表示重新生成，更新通道记录
            channelId = oldReleaseChannel.getId();
            releaseWorkflowChannel.setId(channelId);
            if (oldReleaseChannel.getReleasedOn() == null) {
                releaseWorkflowChannel.setReleasedOn(new Date(System.currentTimeMillis()));
            }
            releaseWorkflowChannel.setWorkspaceId(workspaceId);
            releaseChannelMapper.updateByPrimaryKeySelective(releaseWorkflowChannel);

            // 如果发布渠道为网页或云商店，更新通道记录需要先同步删除agent-runtime的发布信息（以老的shortCode为key）
            String releaseId = oldReleaseChannel.getShortCode();
            if (oldReleaseChannel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL)
                || oldReleaseChannel.getChannelType().equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
                agentRuntimeClient.deleteReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseId,
                    oldReleaseChannel.getChannelType(), oldReleaseChannel.getVersionId());
            }
        } else {
            // 通道不存在则新建
            releaseWorkflowChannel.setId(channelId);
            releaseWorkflowChannel.setAppId(workflowId);
            releaseWorkflowChannel.setAppType(CommonConstant.WORKFLOW_TYPE);
            releaseWorkflowChannel.setVersionId(body.getVersionId());
            releaseWorkflowChannel.setChannelType(channelType);
            releaseWorkflowChannel.setStatus(RELEASED);
            ReleaseVersion version = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, body.getVersionId());
            releaseWorkflowChannel.setVersionName(version.getVersionName());
            releaseWorkflowChannel.setReleasedOn(new Date(System.currentTimeMillis()));
            releaseWorkflowChannel.setProjectId(projectId);
            releaseWorkflowChannel.setWorkspaceId(workspaceId);
            releaseChannelMapper.insert(releaseWorkflowChannel);
        }
        // 将应用发布信息同步agent-runtime
        releaseWorkflowChannel = releaseChannelMapper.selectByPrimaryKey(channelId);
        ReleaseInfo releaseInfo = new ReleaseInfo();
        releaseInfo.setAppId(releaseWorkflowChannel.getAppId());
        releaseInfo.setAppType(releaseWorkflowChannel.getAppType());
        releaseInfo.setVersionId(releaseWorkflowChannel.getVersionId());
        releaseInfo.setChannelType(releaseWorkflowChannel.getChannelType());
        releaseInfo.setShortCode(releaseWorkflowChannel.getShortCode());
        releaseInfo.setCallCount(releaseWorkflowChannel.getCallCount());
        releaseInfo.setVisibilityScope(releaseWorkflowChannel.getVisibilityScope());
        agentRuntimeClient.createReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseInfo);

        return releaseWorkflowChannel.convertToInfo();
    }

    /**
     * 查询workflow版本通道列表
     *
     * @param projectId 项目Id
     * @param workflowId 工作流Id
     * @param listAgentChannelsQo 查询参数对象，包含分页、排序等查询条件
     * @return 工作流通道信息
     */
    @Override
    public VersionChannelListRsp listWorkflowChannels(String projectId, String workflowId,
        ListWorkflowChannelsQo listAgentChannelsQo) {
        VersionChannelListRsp channelListRsp = new VersionChannelListRsp();
        List<ReleaseChannel> releaseChannelList =
            releaseChannelMapper.selectByAppId(workflowId, listAgentChannelsQo.getWorkspaceId());
        // 查询agent-builder空间发布
        if (publishAgentBuilderEnable) {
            ReleaseChannel agentBuilderChannel =
                agentSpaceService.publishQuery(listAgentChannelsQo.getWorkspaceId(), workflowId);
            if (agentBuilderChannel != null) {
                agentBuilderChannel.setAppType(CommonConstant.WORKFLOW_TYPE);
                releaseChannelList.add(agentBuilderChannel);
            }
        }
        List<VersionChannelInfo> channelInfoList =
            releaseChannelList.stream().map(ReleaseChannel::convertToInfo).collect(Collectors.toList());
        channelListRsp.setCount(channelInfoList.size());
        channelListRsp.setChannelList(channelInfoList);

        // 获取工作流的最新发布版本
        ListWorkflowVersionsQo listWorkflowVersionsQo =
            new ListWorkflowVersionsQo().setWorkspaceId(listAgentChannelsQo.getWorkspaceId());
        VersionListRsp versionListRsp = listWorkflowVersions(projectId, workflowId, listWorkflowVersionsQo);
        if (!versionListRsp.getVersionList().isEmpty()) {
            channelListRsp.setLatestVersionId(versionListRsp.getVersionList().get(0).getVersionId());
        }
        return channelListRsp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Workflow",
        description = "删除发布通道",
        resourceId = "channelId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteWorkflowChannel(String projectId, String workflowId, String channelId,
        String workspaceId) {
        // 发布到agent-builder空间，agentId和channelId相同
        if (publishAgentBuilderEnable && workflowId.equals(channelId)) {
            agentSpaceService.unpublish(workspaceId, workflowId);
            return null;
        }

        // 获取工作流并校验权限
        ReleaseChannel releaseChannel =
            releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, workflowId, projectId, workspaceId);

        // 校验存在性
        if (ObjectUtils.isEmpty(releaseChannel)) {
            throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_NOT_EXIST);
        }

        // 越权校验
        if (!releaseChannel.getId().equals(channelId) || !releaseChannel.getWorkspaceId().equals(workspaceId)) {
            log.error(
                "Failed to delete workflow channel due to permission check. Requested - ChannelId:{}., WorkspaceId:{}",
                releaseChannel.getId(), releaseChannel.getWorkspaceId());
            throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_NOT_EXIST);
        }

        // 校验渠道类型
        // 当前页面仅应用百宝箱渠道和AgentBuilder渠道支持删除
        if (!releaseChannel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)
            && !releaseChannel.getChannelType().equals(CommonConstant.AGENT_BUILDER)) {
            throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_NOT_SUPPORT_DELETE);
        }

        if (releaseChannel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            appMapper.deleteByResourceId(workflowId, projectId, workspaceId);
            publishUtils.deletePublish(workflowId, Constants.TREASURE_PUBLISH_VERSION, obsService);
        }
        releaseChannelMapper.deleteByPrimaryKeyAndWorkspaceId(channelId, projectId, workspaceId);

        // 同步删除agent-runtime工作流发布信息
        String releaseId = null;
        if (releaseChannel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL)
            || releaseChannel.getChannelType().equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
            releaseId = releaseChannel.getShortCode();
        } else if (releaseChannel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            releaseId = releaseChannel.getAppId();
        }
        agentRuntimeClient.deleteReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseId,
            releaseChannel.getChannelType(), releaseChannel.getVersionId());
        return new CommonDeleteRsp().setId(channelId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Workflow",
        description = "修改发布通道",
        resourceId = "workflowId"
    )
    public VersionChannelInfo modifyWorkflowChannel(String projectId, String workflowId, String channelId,
        String workspaceId, ModifyChannelReq body) {
        // 校验流是否存在
        checkWorkflowExist(projectId, workspaceId, workflowId);

        ReleaseChannel oldChannel =
            releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, workflowId, projectId, workspaceId);
        if (ObjectUtils.isEmpty(oldChannel)) {
            throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_NOT_EXIST);
        }

        // 越权校验
        if (!oldChannel.getId().equals(channelId) || !oldChannel.getWorkspaceId().equals(workspaceId)) {
            log.error("Modify workflow channel failed due to authorization conflict. channelId=[{}], WorkspaceId=[{}].",
                channelId, workspaceId);
            throw new AgentStudioException(StudioError.WORKFLOW_CHANNEL_NOT_EXIST);
        }

        ReleaseChannel newChannel = new ReleaseChannel();
        newChannel.setId(oldChannel.getId());
        newChannel.setVersionId(body.getVersionId());
        ReleaseVersion version = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, body.getVersionId());
        newChannel.setVersionName(version.getVersionName());
        newChannel.setCreatorId(RequestContextUtils.getRequestUserId());
        newChannel.setCallCount(body.getCallCount());
        newChannel.setVisibilityScope(body.getVisibilityScope().toString());
        newChannel.setWorkspaceId(workspaceId);
        releaseChannelMapper.updateByPrimaryKeySelective(newChannel);
        ReleaseChannel channel = releaseChannelMapper.selectByPrimaryKey(channelId);

        // 同步更新agent-runtime应用发布信息
        String releaseId = null;
        if (oldChannel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL)
            || oldChannel.getChannelType().equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
            releaseId = oldChannel.getShortCode();
        } else if (oldChannel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            // 兼容老的百宝箱发布逻辑，修改百宝箱应用版本
            String[] strArray = JsonUtils.json2ObjQuietly(oldChannel.getMetadata(), String[].class);
            publishWorkflow(projectId, workflowId, Arrays.stream(Objects.requireNonNull(strArray)).toList());
            releaseId = oldChannel.getAppId();
        }
        agentRuntimeClient.deleteReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseId,
            oldChannel.getChannelType(), oldChannel.getVersionId());
        ReleaseInfo releaseInfo = new ReleaseInfo();
        releaseInfo.setAppId(channel.getAppId());
        releaseInfo.setAppType(channel.getAppType());
        releaseInfo.setVersionId(channel.getVersionId());
        releaseInfo.setChannelType(channel.getChannelType());
        releaseInfo.setShortCode(channel.getShortCode());
        releaseInfo.setCallCount(newChannel.getCallCount());
        releaseInfo.setVisibilityScope(newChannel.getVisibilityScope());
        agentRuntimeClient.createReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseInfo);
        return channel.convertToInfo();
    }

    @Override
    public WorkflowFrontParamInfo getWorkflowParams(String projectId, String workflowId,
        GetWorkflowParamsQo getWorkflowParamsQo) {
        String version = getWorkflowParamsQo.getVersion();

        // 获取工作流并校验权限
        WorkflowEntity workflowEntity = checkOpWorkflowPermission(projectId, workflowId);

        // 获取工作流并校验权限
        WorkflowFrontParamInfo workflowFrontParamInfo = parseWorkflowParams(workflowEntity, version);

        // 提取参数
        App app = appMapper.selectByResourceId(workflowId);
        if (app != null) {
            // 回填输入参数
            List<Object> inputParams =
                JsonUtils.json2Obj(app.getInputParams(), new com.fasterxml.jackson.core.type.TypeReference<>() {});
            if (!CollectionUtils.isEmpty(inputParams)) {
                inputParams.forEach(appParam -> {
                    WorkflowFrontParam workflowFrontParam =
                        JsonUtils.objectToClassType(appParam, WorkflowFrontParam.class);
                    workflowFrontParamInfo.getInputs().forEach(workflowParam -> {
                        if (workflowFrontParam != null
                            && Strings.CS.equals(workflowParam.getName(), workflowFrontParam.getName())
                            && Strings.CS.equals(workflowParam.getType(), workflowFrontParam.getType())) {
                            workflowParam.setFrontName(workflowFrontParam.getFrontName());
                            workflowParam.setFrontContent(workflowFrontParam.getFrontContent());
                        }
                    });
                });
            }

            // 回填输出参数
            List<Object> outputParams =
                JsonUtils.json2Obj(app.getOutputParams(), new com.fasterxml.jackson.core.type.TypeReference<>() {});
            if (!CollectionUtils.isEmpty(outputParams)) {
                outputParams.forEach(appParam -> {
                    WorkflowFrontParam param = JsonUtils.objectToClassType(appParam, WorkflowFrontParam.class);
                    workflowFrontParamInfo.getOutputs().forEach(workflowParam -> {
                        if (param != null && Strings.CS.equals(workflowParam.getName(), param.getName())
                            && Strings.CS.equals(workflowParam.getType(), param.getType())) {
                            workflowParam.setFrontName(param.getFrontName());
                            workflowParam.setFrontContent(param.getFrontContent());
                        }
                    });
                });
            }
        }
        return workflowFrontParamInfo;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Workflow",
        description = "修改工作流",
        resourceId = "workflowId"
    )
    public WorkflowInfo updateWorkflow(String projectId, String workflowId, String workspaceId, WorkflowInfo body) {
        // 设置事务锁，防止并行更新工作流数据
        log.debug("Entering updateWorkflow with projectId={}, workflowId={}, workspaceId={}", projectId, workflowId,
            workspaceId);
        workflowMapper.updateWorkflowTransactionalId(projectId, workflowId, workspaceId);

        // 更新版本时间
        long updateTime = System.currentTimeMillis();
        log.debug("Current update time: {}", updateTime);
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (workflowEntity == null) {
            log.info("Workflow:{} does not exist!", workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        // 发布为自定义节点校验
        Integer customizeNode = null;
        if (body.isCustomizeNode() != null) {
            customizeNode = body.isCustomizeNode() ? 1 : 0;
        }
        if (customizeNode != null && !Objects.equals(customizeNode, workflowEntity.getCustomizeNode())) {
            agentCommonService.publishCustomizeNodeCheck(projectId, workflowId, workflowEntity.getLastVersionId(),
                customizeNode);
            workflowEntity.setCustomizeNode(customizeNode);
        }

        // 权限校验
        workflowValidationService.validateModifyPrivilege(workflowEntity, projectId, workspaceId);
    /*    if (!Objects.equals(workflowEntity.getUpdatedAt(), body.getUpdateTime())) {
            log.error("workflow version does not match, latest = {}, now = {}", workflowEntity.getUpdatedAt(),
                body.getUpdateTime());
            if (!"hc".equals(envType)) {
                throw new AgentStudioException(StudioError.WORKFLOW_VERSION_NOT_MATCH);
            }
        }*/

        if (body.getAvatar() == null) {
            body.setAvatar(workflowEntity.getAvatar());
        } else {
            IconNameCheckUtils.validaIconName(body.getAvatar());
            workflowEntity.setIconName(body.getAvatar());
            body.setAvatar(ImageBase64Utils.getImageBase64(body.getAvatar(), obsService));
        }

        // 是否工作流基础配置（名字、英文名、描述、类型、图标）被修改
        boolean isRefreshBasicSettings =
            isWorkflowBasicSettingsRefresh(workflowEntity, body, projectId, workspaceId, updateTime);

        workflowEntity.setUpdatedBy(getUserName(projectId));
        workflowEntity.setTestStatus(0);

        // 更新视图文件
        String workflowJson;
        String originWorkflowJson = obsService.downloadObsFile(workflowEntity.getDslPath());
        if (body.getWorkflowDetails() != null) {
            workflowJson = JSON.toJSONString(body.getWorkflowDetails(), JSONWriter.Feature.WriteMapNullValue);

            // 取原工作流dsl与最新工作流dsl对比，如最新工作流auth为空（可能为get接口清理后），从原工作流取对应值填入
            WorkflowVO currentWorkflow = JSON.parseObject(workflowJson, WorkflowVO.class);
            workflowValidationService.validateWorkflowDetail(currentWorkflow, workflowId);

            // 校验记忆库id
            String memoryRepoId = fetchMemoryRepoId(currentWorkflow);
            if (StringUtils.isNotBlank(memoryRepoId)) {
                checkMemoryRepo(memoryRepoId);
            }

            // 老工作流添加系统变量
            addSysParam(currentWorkflow);

            WorkflowVO originWorkflow = JSON.parseObject(originWorkflowJson, WorkflowVO.class);

            // 全局替换默认模型
            replaceDefaultModel(currentWorkflow, originWorkflow);
            // 检查知识库节点类型
            checkKnowledge(currentWorkflow);
            extendsAuthInfo(currentWorkflow, originWorkflow);
            // 转存全局配置的记忆变量到variables字段,dsl不需增加
            addMemory2Variables(currentWorkflow);
            workflowJson = JSON.toJSONString(currentWorkflow, JSONWriter.Feature.WriteMapNullValue);
            if (shouldRefreshIr(body, isRefreshBasicSettings)) {
                // 记录资源的关联关系并校验权限
                updateRefResources(currentWorkflow, null);
                validWorkflowWorkspace(currentWorkflow, projectId, workspaceId);

            }
            // 上传flow obs
            String flowPath = obsService.uploadObsFile(workflowId, workflowId, CommonConstant.WORKFLOW, workflowJson,
                CommonConstant.Workflow.FLOW);
            workflowEntity.setDslPath(flowPath);
        } else {
            workflowJson = originWorkflowJson;
            if (shouldRefreshIr(body, isRefreshBasicSettings)) {
                // 改名情况需刷新dsl ir
                WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);

                // 当前九问提取name参数作为Agent绑定工作流，模型英文名效果更好
                workflowVo.setName(workflowEntity.getCode());
                workflowVo.setDescription(workflowEntity.getDescription());
                workflowVo.setIcon(workflowEntity.getAvatar());
                String flowPath = obsService.uploadObsFile(workflowId, workflowId, CommonConstant.WORKFLOW,
                    JSON.toJSONString(workflowVo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.FLOW);
                workflowEntity.setDslPath(flowPath);
                updateRefResources(workflowVo, null);
                String irPath = workflowDslToIr(workflowId, workflowEntity, workflowVo);
                workflowEntity.setIrPath(irPath);
            }
        }
        workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);

        return convertEntityToInfo(workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId),
            workflowJson);
    }

    private String fetchMemoryRepoId(WorkflowVO currentWorkflow) {
        if (currentWorkflow == null || currentWorkflow.getConfigs() == null || !currentWorkflow.getConfigs().containsKey(Constants.Workflow.MEMORY_CONFIG)) {
            return null;
        }
        Map<String, Object> newConfigs = JsonUtils.objectToClass(currentWorkflow.getConfigs().get(Constants.Workflow.MEMORY_CONFIG));
        if (newConfigs == null || !newConfigs.containsKey(CommonConstant.MEMORY_REPO_ID)) {
            return null;
        }
        // 校验memory_repo_id 是否存在
        return newConfigs.get(CommonConstant.MEMORY_REPO_ID).toString();
    }

    private void checkMemoryRepo(String memoryRepoId) {
        MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectById(memoryRepoId);
        if (memoryRepoEntity == null) {
            throw new AgentStudioException(StudioError.MEMORY_REPO_NOT_EXIST);
        }
    }

    private void addMemory2Variables(WorkflowVO currentWorkflow) {
        WorkflowNodeVO startNodeVO = currentWorkflow.getNodes()
            .stream()
            .filter(p -> Strings.CS.equals(p.getType(), NodeType.START.getType()))
            .findFirst().orElse(null);
        if (Objects.isNull(startNodeVO)) {
            return;
        }
        List<WorkflowFieldVO> globalVars = startNodeVO.getOutputs()
            .stream()
            .filter(p -> p.getSource() == WorkflowFieldVO.SourceEnum.USER)
            .toList();
        if (CollectionUtils.isEmpty(globalVars)) {
            log.info("user resource empty!");
            return;
        }
        List<WorkflowConfigVariable> workflowConfigVariables = new ArrayList<>();
        for (WorkflowFieldVO globalVariable : globalVars) {
            WorkflowConfigVariable workflowConfigVariable = WorkflowConfigVariable.builder()
                .name(globalVariable.getName())
                .type(globalVariable.getType())
                .description(globalVariable.getDescription())
                .defaultValue(globalVariable.getValue().getDefault())
                .scope(SCOPE_REQUEST)
                .build();
            workflowConfigVariables.add(workflowConfigVariable);
        }
        Map<String, Object> workflowConfigs = currentWorkflow.getConfigs();
        if (Objects.isNull(workflowConfigs)) {
            log.error("workflow configs empty!");
            return;
        }
        workflowConfigs.put(CommonConstant.Workflow.VARIABLES, workflowConfigVariables);
    }

    /**
     * 更新mapping表的模型信息
     *
     */
    public void buildGlobalModelReference(String projectId, String workspaceId, WorkflowVO workflow,
        List<MappingEntity> relateComponents, String appVersionId) {
        if (workflow == null) {
            return;
        }
        Map<String, Object> configs = workflow.getConfigs();
        Map<String, String> defaultModelConfig = this.fetchGlobalConfigModel(configs);
        if (Objects.isNull(defaultModelConfig)) {
            return;
        }
        Object modelType = defaultModelConfig.get(MODEL_TYPE);
        Object modelDeploymentId = defaultModelConfig.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
        if (Objects.isNull(modelDeploymentId)) {
            return;
        }
        String workflowId = workflow.getId();
        String workflowName = workflow.getName();

        if (Objects.nonNull(modelType) && Strings.CS.equals(modelType.toString(), "strategy")) {
            List<RouterStrategyEntity> strategyEntities = this.routerStrategyMapper.queryByIds(
                List.of(modelDeploymentId.toString()), projectId, workspaceId);
            List<MappingEntity> strategyMapping = strategyEntities.stream().map(strategyEntity -> {
                MappingEntity mappingEntity = new MappingEntity();
                mappingEntity.setMappingId(UUID.randomUUID().toString());
                mappingEntity.setAppId(workflowId);
                mappingEntity.setAppName(workflowName);
                mappingEntity.setAppType(WORKFLOW.toString());
                mappingEntity.setResourceId(strategyEntity.getId());
                mappingEntity.setResourceName(strategyEntity.getStrategyName());
                mappingEntity.setResourceDesc(strategyEntity.getStrategyDescription());
                mappingEntity.setResourceType(ResourceTypeEnum.STRATEGY.toString());
                mappingEntity.setAppVersion(appVersionId);
                return mappingEntity;
            }).toList();
            relateComponents.addAll(strategyMapping);
        } else {
            List<ModelServiceBase> modelServiceBases = this.modelServiceManager.queryAllModelByIds(projectId,
                workspaceId, Set.of(modelDeploymentId.toString()));
            List<MappingEntity> modelMapping = modelServiceBases.stream().map(modelServiceBase -> {
                MappingEntity mappingEntity = new MappingEntity();
                mappingEntity.setMappingId(UUID.randomUUID().toString());
                mappingEntity.setAppId(workflowId);
                mappingEntity.setAppName(workflowName);
                mappingEntity.setAppType(WORKFLOW.toString());
                mappingEntity.setResourceId(modelServiceBase.getId());
                mappingEntity.setResourceName(modelServiceBase.getModelName());
                mappingEntity.setResourceDesc(modelServiceBase.getModelDescription());
                mappingEntity.setResourceType(ResourceTypeEnum.MODEL.toString());
                mappingEntity.setAppVersion(appVersionId);
                return mappingEntity;
            }).toList();
            relateComponents.addAll(modelMapping);
        }
    }

    public void buildGlobalMemoryRepo(WorkflowVO workflow, List<MappingEntity> relateComponents, String appVersionId) {
        if (workflow == null) {
            return;
        }
        String workflowId = workflow.getId();
        String workflowName = workflow.getName();
        // 更新记忆库mapping信息
        String memoryRepoId = fetchMemoryRepoId(workflow);
        if (StringUtils.isNotBlank(memoryRepoId)) {
            MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectById(memoryRepoId);
            if (Objects.nonNull(memoryRepoEntity)){
                MappingEntity mappingEntity = buildMappingEntity(workflowId, workflowName, WORKFLOW.toString(), memoryRepoId, memoryRepoEntity.getName(), MEMORY.toString(), memoryRepoEntity.getDescription(), appVersionId);
                relateComponents.add(mappingEntity);
            }
        }
    }

    private MappingEntity buildMappingEntity(String appId, String appName, String appType, String resourceId, String resourceName, String resourceType, String resourceDesc, String appVersionId) {
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());
        mappingEntity.setAppId(appId);
        mappingEntity.setAppName(appName);
        mappingEntity.setAppType(appType);
        mappingEntity.setResourceId(resourceId);
        mappingEntity.setResourceName(resourceName);
        mappingEntity.setResourceDesc(resourceDesc);
        mappingEntity.setResourceType(resourceType);
        mappingEntity.setAppVersion(appVersionId);
        return mappingEntity;
    }

    private void addModelRef(WorkflowVO workflowVo, String versionId, Map<String, Object> nodeConfigs,
        List<MappingEntity> relateComponents) {
        Object objModel = nodeConfigs.get(MODEL);
        if (objModel == null) {
            Object objLlm = nodeConfigs.get("llm");
            if (objLlm != null) {
                Map<String, Object> mapLlm = JsonUtils.objectToClass(objLlm);
                if (!CollectionUtils.isEmpty(mapLlm)) {
                    objModel = mapLlm.get(MODEL);
                }
            }
        }
        if (objModel == null) {
            return;
        }
        Map<String, Object> modelInfo = JsonUtils.objectToClass(objModel);
        if (CollectionUtils.isEmpty(modelInfo)) {
            return;
        }
        relateComponents.add(buildModelReference(workflowVo, versionId, modelInfo));
    }

    private void checkKnowledge(WorkflowVO currentWorkflow) {
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            return;
        }
        HashMap<String, List<String>> knowledgeNodesMap = new HashMap<>();
        Set<String> allKnowledgeIds = new HashSet<>();
        Map<String, String> nodeNameMap = new HashMap<>();
        currentWorkflow.getNodes()
            .stream()
            .filter(item -> item.getType().equals(NodeType.KNOWLEDGE_REPO.getType()))
            .forEach(item -> {
                Map<String, Object> configs = item.getConfigs();
                List<Map<String, Object>> repos = JsonUtils.objectToClass(configs.get(CommonConstant.REPOS));
                List<String> singleNodeKnowledgeIds = new ArrayList<>();
                if (!CollectionUtils.isEmpty(repos)) {
                    repos.forEach(repo -> {
                        allKnowledgeIds.add(repo.get("id").toString());
                        singleNodeKnowledgeIds.add(repo.get("id").toString());
                    });
                    knowledgeNodesMap.put(item.getId(), singleNodeKnowledgeIds);
                    nodeNameMap.put(item.getId(), item.getName());
                }
            });
        if (CollectionUtils.isEmpty(allKnowledgeIds)) {
            return;
        }
        ListKnowledgeBasesQo knowledgeBaseQo = new ListKnowledgeBasesQo();
        knowledgeBaseQo.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
        knowledgeBaseQo.setKnowledgeBaseIds(allKnowledgeIds.stream().toList());
        knowledgeBaseQo.setLimit(allKnowledgeIds.size());
        List<KnowledgeBaseListItem> knowledgeBaseResponse = knowledgeBaseService.listKnowledgeBases(
            RequestContextUtils.getRequestProjectId(), knowledgeBaseQo).getItems();
        HashMap<String, KnowledgeBaseListItem> stringKnowledgeBaseListItemHashMap = new HashMap<>();
        // 多节点可以有不同类型的知识库；知识库多选时，允许以下几种情况 1.type都是internal 2.如果有type都是是external时且所有source的knowledge_base_connection_id一致
        knowledgeBaseResponse.forEach(item -> stringKnowledgeBaseListItemHashMap.put(item.getKnowledgeBaseId(), item));
        knowledgeNodesMap.forEach((k, singleNodeKnowledgeIds) -> {
            ArrayList<KnowledgeBaseListItem> singleNodeKnowledgeBaseList = new ArrayList<>();
            HashSet<KnowledgeBaseListItem.TypeEnum> types = new HashSet<>();
            HashSet<String> list = new HashSet<>();
            AtomicInteger shareNum = new AtomicInteger(0);
            singleNodeKnowledgeIds.forEach(itemId -> {
                KnowledgeBaseListItem item = stringKnowledgeBaseListItemHashMap.get(itemId);
                if (ObjectUtils.isEmpty(item)) {
                    log.error("The knowledge base [{}] does not exist in the knowledge retrieval node [{}].", itemId,
                        nodeNameMap.get(k));
                    throw new AgentStudioException(StudioError.KNOWLEDGE_BASE_NOT_EXIST_IN_NODE, nodeNameMap.get(k), itemId);
                }

                singleNodeKnowledgeBaseList.add(item);

                // 类型检查
                types.add(item.getType());

                // 外部知识库连接ID收集
                if (KnowledgeBaseListItem.TypeEnum.EXTERNAL.equals(item.getType())) {
                    ExternalKnowledgeBaseSource source = item.getSource();
                    list.add(source.getKnowledgeBaseConnectionId());
                }
                // 共享类型计数
                if (KnowledgeBaseListItem.RepoTypeEnum.SHARE.equals(item.getRepoType())) {
                    shareNum.getAndIncrement();
                }
            });
            // 校验共享知识库数量
            if (shareNum.get() > 1 && singleNodeKnowledgeBaseList.size() > 1) {
                log.error("Number of shared knowledge bases exceeds 1");
                throw new AgentStudioException(StudioError.FREE_KNOWLEDGE_BASE_LIMIT_EXCEEDED);
            }
            if (types.size() != 1 || list.size() > 1) {
                log.error("The knowledge base types are inconsistent");
                throw new AgentStudioException(StudioError.KNOWLEDGE_REPO_TYPE_INCONSISTENT);
            }
        });
    }


    /**
     * 从全局配置参数中，提取模型信息
     *
     */
    private Map<String, String> fetchGlobalConfigModel(Map<String, Object> globalConfig) {
        if (CollectionUtils.isEmpty(globalConfig)) {
            return null;
        }
        Object defaultModel = globalConfig.get(CommonConstant.ModelParam.DEFAULT_MODEL);
        if (defaultModel == null) {
            return null;
        }
        Map<String, String> modelConfigs = JsonUtils.objectToClass(defaultModel);
        if (CollectionUtils.isEmpty(modelConfigs)) {
            return null;
        }
        return modelConfigs;
    }

    private void validWorkflowWorkspace(WorkflowVO workflowVo, String projectId, String workspaceId) {
        for (WorkflowNodeVO node : workflowVo.getNodes()) {
            NodeType nodeType = NodeType.fromType(node.getType());
            if (nodeType == null) {
                continue;
            }

            if (nodeType == NodeType.INTENT_DETECTION_CONTAINER) {
                validIntentContainerRef(node, projectId, workspaceId);
            }
        }
    }

    private void validIntentContainerRef(WorkflowNodeVO node, String projectId, String workspaceId) {
        List<String> workflowIds = new ArrayList<>();
        List<WorkflowBranchVO> branches = node.getBranches();
        for (WorkflowBranchVO branch : branches) {
            Map<String, Object> configs = branch.getConfigs();

            // 过滤没有id或重复的
            if (configs.get(WORKFLOW_ID) == null || StringUtils.isEmpty(configs.get(WORKFLOW_ID).toString())
                || workflowIds.contains(configs.get(WORKFLOW_ID).toString())) {
                continue;
            }

            // 字段映射
            workflowIds.add(configs.get(WORKFLOW_ID).toString());
            configs.put(Constants.ID, configs.get(WORKFLOW_ID));
        }

        // 校验权限 workflowIds
        if (CollectionUtils.isEmpty(workflowIds)) {
            return;
        }

        List<WorkflowEntity> workflowEntityByIds =
            workflowMapper.getWorkflowEntityByIds(projectId, workspaceId, workflowIds);
        if (CollectionUtils.isEmpty(workflowEntityByIds)) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        List<String> usefulWorkflows =
            workflowEntityByIds.stream().map(WorkflowEntity::getId).collect(Collectors.toList());
        workflowIds.forEach(workflowId -> {
            if (!usefulWorkflows.contains(workflowId)) {
                throw new AgentStudioException(StudioError.WORKFLOW_NO_PERMISSION, workflowId);
            }
        });
    }

    public List<TriggerConfig> getTriggerConfigList(WorkflowVO workflow) {
        if (workflow == null) {
            return Collections.emptyList();
        }

        Map<String, Object> configs = workflow.getConfigs();
        if (configs == null) {
            return Collections.emptyList();
        }
        Object triggerConfigListObj = configs.get("trigger_list");
        if (triggerConfigListObj instanceof List<?>) {
            List<TriggerConfig> triggerConfigList = ((List<?>) triggerConfigListObj).stream()
                .map(obj -> mapper.convertValue(obj, TriggerConfig.class))
                .peek(triggerConfig -> {
                    if (triggerConfig.getTriggerId() == null || triggerConfig.getTriggerId().isEmpty()) {
                        triggerConfig.setTriggerId(UUID.randomUUID().toString());
                    }
                })
                .collect(Collectors.toList());
            return triggerConfigList;
        }
        return Collections.emptyList();
    }

    /**
     * 老版本工作流添加系统变量
     */
    private void addSysParam(WorkflowVO currentWorkflow) {
        if (!CollectionUtils.isEmpty(currentWorkflow.getNodes())) {
            List<WorkflowNodeVO> nodes = currentWorkflow.getNodes();

            // 调用公共方法获取start节点并处理outputs
            WorkflowNodeVO start = irAdapterService.getStartNodeWithOutputs(nodes, NodeType.START);

            // 根据语言选择系统参数模板
            boolean isChinese = LanguageUtils.isChinese();

            // 解析系统参数
            WorkflowFieldVO sysField = JSONObject.parseObject(
                isChinese ? workflowDefaultSystemParam : workflowDefaultSystemParamEnglish, WorkflowFieldVO.class);

            // 重建列表：替换已有系统参数 + 确保唯一系统参数
            List<WorkflowFieldVO> newOutputs = start.getOutputs()
                .stream()
                .filter(f -> !Strings.CS.equals(SYS, f.getName()))
                .collect(Collectors.toCollection(ArrayList::new));
            newOutputs.add(sysField);
            start.setOutputs(newOutputs);
        }
    }

    private boolean isWorkflowBasicSettingsRefresh(WorkflowEntity workflowEntity, WorkflowInfo body, String projectId,
        String workspaceId, long updateTime) {
        boolean isRefreshBasicSettings = false;
        if (StringUtils.isNotEmpty(body.getName()) && !Strings.CS.equals(body.getName(), workflowEntity.getName())) {
            workflowValidationService.validateName(body.getName());
            workflowEntity.setName(body.getName());
            isRefreshBasicSettings = true;
        }
        if (StringUtils.isNotEmpty(body.getCode()) && !Strings.CS.equals(body.getCode(), workflowEntity.getCode())) {
            workflowValidationService.validateCode(body.getCode());
            workflowEntity.setCode(body.getCode());
            isRefreshBasicSettings = true;
        }
        if (StringUtils.isNotEmpty(body.getAvatar())
            && !Strings.CS.equals(body.getAvatar(), workflowEntity.getAvatar())) {
            workflowValidationService.validateIcon(body.getAvatar());
            workflowEntity.setAvatar(body.getAvatar());
            isRefreshBasicSettings = true;
        }
        if (StringUtils.isNotEmpty(body.getDescription())
            && !Strings.CS.equals(body.getDescription(), workflowEntity.getDescription())) {
            workflowEntity.setDescription(body.getDescription());
            isRefreshBasicSettings = true;
        }
        if (StringUtils.isNotEmpty(body.getType())
            && !Strings.CS.equals(body.getType(), workflowEntity.getWorkflowType())) {
            workflowValidationService.validateWorkflowType(body.getType());
            workflowEntity.setWorkflowType(body.getType());
            isRefreshBasicSettings = true;
        }

        // 仅拖拽节点不更新工作流更新时间
        if (shouldRefreshIr(body, isRefreshBasicSettings)) {
            workflowEntity.setUpdatedAt(updateTime);
        }
        return isRefreshBasicSettings;
    }

    /**
     * 工作流dsl转ir
     *
     * @param workflowId 工作流Id
     * @param workflowEntity 工作流元数据
     * @param workflowVo 工作流dsl对象
     * @return 文件路径
     */
    public String workflowDslToIr(String workflowId, WorkflowEntity workflowEntity, WorkflowVO workflowVo) {
        return workflowCommonService.workflowDslToIr(workflowId, workflowEntity, workflowVo, null);
    }

    /**
     * 工作流dsl转ir
     *
     * @param workflowId 工作流Id
     * @param workflowEntity 工作流元数据
     * @param workflowVo 工作流dsl对象
     * @return 文件路径
     */
    public String workflowDslToIr(String workflowId, WorkflowEntity workflowEntity, WorkflowVO workflowVo,
        String versionId) {
        Map<String, Object> metadata = workflowCommonService.parseMetadata(workflowEntity);
        Map<String, Object> irInfo = irAdapterService.adaptWorkflow(workflowVo, metadata);
        String irObsKey = workflowId;
        if (!StringUtils.isEmpty(versionId)) {
            irObsKey = workflowId + Constants.UNDERLINE_STR + versionId;
        }
        return obsService.uploadObsFile(workflowId, irObsKey, CommonConstant.WORKFLOW,
            JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.IR);
    }

    @Override
    public WorkflowInfo parseThirdpartyWorkflowFile(String type, String workspaceId, String projectId, MultipartFile file) {
        try {

            // 检验file文件是否有安全问题
            // 无问题返回转换后的Map格式
            Map<String, Object> thirdpartyWorkflowInfo = validateFile(file);

            // 根据type类型选择适配器服务
            AdapterService adapterService = thirdpartyWorkflowAdapter.getService(type);

            // 校验文件格式
            adapterService.validateFormat(thirdpartyWorkflowInfo);

            // 解析并转换为WorkflowInfo
            WorkflowInfo workflowInfo = adapterService.convert(thirdpartyWorkflowInfo);

            // 返回
            return workflowInfo;

        } catch (AgentStudioException e) {
            // AgentStudioException类异常已第一时间打印日志，异常原样上抛即可，
            throw e;
        } catch (Exception e) {
            log.error("Failed to parse thirdparty workflow file", e);
            throw new AgentStudioException(StudioError.PARSE_THIRD_PARTY_WORKFLOW_FILE_FAILED);
        }
    }

    private Map<String, Object> validateFile(MultipartFile file) {
        try {
            // 校验文件格式和大小校验
            FileCommonUtils.validatedFile(file, fileMaxSize * 1024, DIFY_FILE_TYPE);
            Map<String, Object> fileData = yamlSerializer.load(file.getInputStream());

            return fileData;
        } catch (Exception e) {
            log.error("Failed to import the file, invalid content", e);
            throw new AgentStudioException(StudioError.WORKFLOW_IMPORT_FILE);
        }
    }

    private WorkflowSceneRsp parseWorkflowTable(String workflowId, String versionId, String dslPath) {
        // 转换标签名称
        App app = appMapper.selectByResourceId(workflowId);
        if (app == null) {
            log.error("workflow should published first!");
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_PUBLISHED);
        }
        List<Tag> tagList = tagMapper.select();
        List<String> tags =
            tagList.stream().filter(tag -> app.getTags().contains(tag.getTagId())).map(Tag::getName).toList();
        WorkflowSceneRsp workflowSceneRsp = new WorkflowSceneRsp().setWorkflowId(workflowId)
            .setName(app.getName())
            .setDesc(app.getDescription())
            .setType(app.getWorkflowType())
            .setIcon(app.getIcon())
            .setTags(tags)
            .setCreator(app.getCreator())
            .setPrologue(app.getPrologue())
            .setSuggestQueries(app.getSuggestQueries())
            .setPublishTime(app.getPublishedOn() != null ? app.getPublishedOn() : null);

        // 根据语言处理返回结果
        Locale locale = LanguageUtils.getLanguageLocale();

        // 如果creator是“官方预置”，进行替换
        if (CommonConstant.DEFAULT_USERNAME.equals(workflowSceneRsp.getCreator())) {
            workflowSceneRsp.setCreator(messageSource.getMessage("workflow.creator.official", null, locale));
        }

        // 兼容老版本，app表无数据，从工作流dsl中读取参数
        if (StringUtils.isEmpty(app.getInputParams()) && StringUtils.isEmpty(app.getOutputParams())) {
            String workflowJson = obsService.downloadObsFile(dslPath);
            WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);
            List<WorkflowNodeVO> workflowNodes = workflowVo.getNodes();
            WorkflowNodeVO startNode = WorkflowUtils.getWorkflowNodeID(INPUT_KEY, workflowNodes);
            List<WorkflowFieldVO> inputs = startNode == null ? null : startNode.getOutputs();
            if (inputs != null) {
                inputs = inputs.stream().filter(m -> !Strings.CS.equals(SYS, m.getName())).toList();
            }
            workflowSceneRsp.setInputs(parseFrontParamFromWorkflowField(inputs));

            WorkflowNodeVO endNode = WorkflowUtils.getWorkflowNodeID(OUTPUT_KEY, workflowNodes);
            List<WorkflowFieldVO> outputs = endNode == null ? null : endNode.getOutputs();
            workflowSceneRsp.setOutputs(parseFrontParamFromWorkflowField(outputs));
        } else {
            workflowSceneRsp.setInputs(parseWorkflowFrontParam(app.getInputParams()));
            workflowSceneRsp.setOutputs(parseWorkflowFrontParam(app.getOutputParams()));
        }
        workflowSceneRsp.setVersionId(versionId);

        int freeTrialUsageQuota = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(workflowId,
            RequestContextUtils.getRequestUserDomainId());
        FreeTrialQuota freeTrialQuota = new FreeTrialQuota();
        freeTrialQuota.setLimit(assetAppFreeTrialQuotaLimit);
        freeTrialQuota.setUsage(freeTrialUsageQuota);
        workflowSceneRsp.setFreeTrialQuota(freeTrialQuota);

        return workflowSceneRsp;
    }

    private List<WorkflowFrontParam> parseFrontParamFromWorkflowField(List<WorkflowFieldVO> workflowFields) {
        // 解析工作流参数供前端转换
        return CollectionUtils.isEmpty(workflowFields) ? Collections.emptyList()
            : workflowFields.stream()
                .map(field -> new WorkflowFrontParam().setName(field.getName())
                    .setFrontName(field.getName())
                    .setFrontContent(StringUtils.EMPTY)
                    .setType(field.getType())
                    .setDescription(field.getDescription())
                    .setRequired(field.isRequired())
                    .setSource(field.getSource().toString())
                    .setSchema(field.getSchema())
                    .setValue(field.getValue()))
                .toList();
    }

    private List<WorkflowFrontParam> parseWorkflowFrontParam(String params) {
        if (StringUtils.isEmpty(params)) {
            return Collections.emptyList();
        }
        List<Object> frontParams = JSON.parseObject(params, new TypeReference<>() {});
        return CollectionUtils.isEmpty(frontParams) ? Collections.emptyList()
            : frontParams.stream()
                .map(appParam -> JsonUtils.objectToClassType(appParam, WorkflowFrontParam.class))
                .toList();
    }

    private WorkflowEntity convertInfoToEntity(String workspaceId, WorkflowInfo workflowInfo) {
        WorkflowEntity workflowEntity = new WorkflowEntity();
        workflowEntity.setId(workflowInfo.getWorkflowId());
        workflowEntity.setName(workflowInfo.getName());
        workflowEntity.setDescription(workflowInfo.getDescription());
        workflowEntity.setCode(workflowInfo.getCode());
        workflowEntity.setAvatar(workflowInfo.getAvatar());
        workflowEntity.setStatus(
            workflowInfo.getStatus().equals(1) ? CommonConstant.WORKFLOW_PUBLISHED : CommonConstant.WORKFLOW_DEVELOP);
        workflowEntity.setVisibility(VisibilityEnum.PROJECT.getValue());
        workflowEntity.setCreatedBy(workflowInfo.getCreator());
        workflowEntity.setUpdatedBy(workflowInfo.getUpdater());
        if (workflowInfo.getCreateTime() != null) {
            workflowEntity.setCreatedAt(workflowInfo.getCreateTime());
        }
        if (workflowInfo.getUpdateTime() != null) {
            workflowEntity.setUpdatedAt(workflowInfo.getUpdateTime());
        }
        if (workflowInfo.getPublishTime() != null) {
            workflowEntity.setPublishedAt(workflowInfo.getPublishTime());
        }
        workflowEntity.setProjectId(workflowInfo.getProjectId());
        workflowEntity.setWorkspaceId(workflowInfo.getWorkspaceId());
        workflowEntity.setDomainId(workflowInfo.getDomainId());
        workflowEntity.setWorkspaceId(workspaceId);
        workflowEntity.setTraceId(workflowInfo.getWorkflowId());
        workflowEntity.setWorkflowType(workflowInfo.getType());
        return workflowEntity;
    }

    private String getUserName(String projectId) {
        if (Strings.CS.equals(opSvcProjectId, projectId)) {
            return CommonConstant.DEFAULT_USERNAME;
        } else {
            return RequestContextUtils.getRequestUserName();
        }
    }

    /**
     * 指定版本工作流DSL/IR路径
     *
     * @param workflowId 工作流Id
     * @param type 类型
     * @param versionId 版本号
     * @return 工作流DSL/IR路径
     */
    public String getWorkflowObsPath(String workflowId, String type, String versionId) {
        return String.format(WORKFLOW_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW, type, workflowId,
            workflowId + "_" + versionId);
    }

    /**
     * 是否需要更新IR，除只拖动节点情况均需要刷新IR
     *
     * @param body 工作流信息
     * @param isRefreshBasicSettings 是否刷新基础配置
     * @return ir是否需要刷新
     */
    private boolean shouldRefreshIr(WorkflowInfo body, boolean isRefreshBasicSettings) {
        return body.isIsDrag() == null || !body.isIsDrag() || isRefreshBasicSettings;
    }

    /**
     * 工作流返回需对特殊节点进行处理
     * 1、http节点返回的密文用空值覆盖
     *
     * @param workflowJson 原始json
     * @return 过滤后json
     */
    private String filterSpecialWorkflowNodes(String workflowJson) {
        String result = workflowJson;
        WorkflowVO currentWorkflow = JsonUtils.json2ObjQuietly(workflowJson, WorkflowVO.class);
        if (currentWorkflow != null) {
            for (WorkflowNodeVO node : currentWorkflow.getNodes()) {
                if (Strings.CS.equals(NodeType.HTTP.getType(), node.getType())
                    && node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO) != null) {
                    AuthInfo authInfo = JsonUtils
                        .objectToClassType(node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO), AuthInfo.class);
                    if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
                        authInfo.getAuthKeys().forEach(m -> m.setAuthKey(StringUtils.EMPTY));
                        node.getConfigs().put(CommonConstant.Workflow.AUTH_INFO, authInfo);
                    }
                } else if (Strings.CS.equals(NodeType.MCP.getType(), node.getType())) {
                    // 更新 mcp 服务是否有效
                    String mcpServerId = (String) node.getConfigs().get(Constants.ID);
                    MappingEntity entity =
                        mappingMapper.selectByAppIdAndResourceId(currentWorkflow.getId(), mcpServerId);
                    if (entity != null) {
                        node.getConfigs().put(CommonConstant.VALID, entity.isValid());
                    }
                } else if ((Strings.CS.equals(NodeType.KNOWLEDGE_REPO.getType(), node.getType())
                        || Strings.CS.equals(NodeType.INTENT_DETECTION.getType(), node.getType()))
                        && ObjectUtils.isEmpty(node.getConfigs().get("common_tags"))
                        && ObjectUtils.isEmpty(node.getConfigs().get("advanced_tags"))) {
                    // 特殊处理知识检索/意图识别节点，旧版本无统一配置的 common_tags/advanced_tags 字段
                    generateGeneralTags(node);
                }
            }
            result = JsonUtils.toJson(currentWorkflow);
        }
        return result;
    }

    /**
     * 特殊处理旧版本使用configs.repos[].tags字段，
     * 将旧版本的configs.repos[].tags字段内容转入到configs.common_tags字段
     *
     * @param node 工作流节点WorkflowNodeVO
     */
    private void generateGeneralTags(WorkflowNodeVO node) {
        Object reposObj = node.getConfigs().get("repos");
        if (!ObjectUtils.isEmpty(reposObj)) {
            String jsonStr = JSON.toJSONString(reposObj);
            List<JSONObject> repoList = JSON.parseArray(jsonStr, JSONObject.class);
            List<String> allTags = repoList.stream()
                    .map(repo -> repo.getJSONArray("tags"))
                    .filter(tags -> !ObjectUtils.isEmpty(tags)) // 防止 tags 为 null
                    .flatMap(tags -> tags.toJavaList(String.class).stream())
                    .distinct()
                    .toList();

            // 将allTags转换为BoolQueryNode OR结构
            if (!CollectionUtils.isEmpty(allTags)) {
                // 为每个tag创建一个RULE类型的节点
                List<BoolQueryNode> tagNodes = allTags.stream()
                        .map(tag -> BoolQueryNode.builder()
                                .type(BoolQueryNodeType.RULE)
                                .value(tag)
                                .build())
                        .toList();

                BoolQueryNode orGroupNode = BoolQueryNode.builder()
                        .type(BoolQueryNodeType.GROUP)
                        .operator(BoolQueryOperatorType.OR)
                        .children(tagNodes)
                        .build();
                node.getConfigs().put("common_tags", orGroupNode);
            } else {
                node.getConfigs().put("common_tags", null);
            }
        }
    }

    /**
     * 更新工作流中节点的模型配置，如果全局配置中开启默认模型的替换开关，则执行该更新动作
     *
     * @param currentWorkflow 需更新的工作流dsl
     * @param originWorkflow 原始工作流dsl
     */
    private void replaceDefaultModel(WorkflowVO currentWorkflow, WorkflowVO originWorkflow) {
        // 获取当前工作流的默认模型配置
        Map<String, Object> workflowConfigs = currentWorkflow.getConfigs();
        if (workflowConfigs == null) {
            // 工作流全局配置可能为空，默认不开启替换
            return;
        }
        Object defaultModel = workflowConfigs.get(CommonConstant.ModelParam.DEFAULT_MODEL);
        if (defaultModel == null) {
            // 默认模型配置为空时不替换
            return;
        }
        Map<String, String> modelConfigs = JsonUtils.objectToClass(defaultModel);

        // 如果模型为空或默认模型配置无变化，不替换
        if (originWorkflow.getConfigs() != null
            && originWorkflow.getConfigs().get(CommonConstant.ModelParam.DEFAULT_MODEL) != null
            && modelConfigs != null) {
            if (modelConfigs.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID) == null || originWorkflow.getConfigs()
                .get(CommonConstant.ModelParam.DEFAULT_MODEL)
                .toString()
                .contains(modelConfigs.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID))) {
                return;
            }
        }

        // default_model_switch不为空且值为true时，替换工作流节点模型配置
        Object defaultModelSwitch = workflowConfigs.get(CommonConstant.ModelParam.DEFAULT_MODEL_SWITCH);
        if (defaultModelSwitch == null || !Boolean.parseBoolean(defaultModelSwitch.toString())) {
            return;
        }
        for (WorkflowNodeVO node : currentWorkflow.getNodes()) {
            if (!CommonConstant.LLM_CONFIG_NODE.contains(node.getType())) {
                continue;
            }
            // 意图识别节点、高级意图识别节点model配置层级为configs llm model
            Map<String, Object> llm = JsonUtils.objectToClass(node.getConfigs().get(CommonConstant.Workflow.LLM));
            if (!Objects.isNull(llm)) {
                Map<String, String> modelConfigMap = JsonUtils.objectToClass(llm.get(CommonConstant.Workflow.MODEL));
                replaceModel(modelConfigMap, modelConfigs);
                llm.put(CommonConstant.Workflow.MODEL, modelConfigMap);
                node.getConfigs().put(CommonConstant.Workflow.LLM, llm);
                continue;
            }
            // 其他节点model配置层级为configs model
            Map<String, String> modelConfigMap =
                JsonUtils.objectToClass(node.getConfigs().get(CommonConstant.Workflow.MODEL));
            replaceModel(modelConfigMap, modelConfigs);
            node.getConfigs().put(CommonConstant.Workflow.MODEL, modelConfigMap);
        }
    }

    /**
     * 模型配置替换为默认模型配置
     *
     * @param modelConfigMap 节点模型配置
     * @param defaultModelConfigs 全局配置默认模型配置
     */
    private void replaceModel(Map<String, String> modelConfigMap, Map<String, String> defaultModelConfigs) {
        if (Objects.isNull(modelConfigMap)) {
            return;
        }
        for (String key : CommonConstant.MODEL_PARAMS) {
            if (!Objects.isNull(defaultModelConfigs.get(key))) {
                modelConfigMap.put(key, defaultModelConfigs.get(key));
            }
        }
    }

    /**
     * 更新工作流http节点，如前端不传鉴权信息，从原始工作流处获取信息替换
     *
     * @param currentWorkflow 需更新的工作流dsl
     * @param originWorkflow 原始工作流dsl
     */
    private void extendsAuthInfo(WorkflowVO currentWorkflow, WorkflowVO originWorkflow) {
        for (WorkflowNodeVO node : currentWorkflow.getNodes()) {
            if (!(Strings.CS.equals(NodeType.HTTP.getType(), node.getType())
                && node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO) != null)) {
                continue;
            }

            AuthInfo authInfo =
                JsonUtils.objectToClassType(node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO), AuthInfo.class);
            if (Objects.isNull(authInfo) || !AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
                continue;
            }

            // 前端服务级鉴权如未传key，说明复用原dsl中key值，否则需加密
            if (!CollectionUtils.isEmpty(authInfo.getAuthKeys())) {
                for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                    if (StringUtils.isBlank(authKeyInfo.getAuthKey())) {
                        authKeyInfo.setAuthKey(
                            parseAuthInfoFromWorkflow(node.getId(), authKeyInfo.getTargetName(), originWorkflow));
                    } else {
                        authKeyInfo.setAuthKey(CryptoUtils.encrypt(authKeyInfo.getAuthKey()));
                    }
                }
                node.getConfigs().put(CommonConstant.Workflow.AUTH_INFO, authInfo);
            }
        }
    }

    /**
     * 在原始dsl中获取指定加密鉴权信息，未找到则返回空
     *
     * @param nodeId 节点id
     * @param targetName key名
     * @param workflow 工作流信息
     * @return 是否包含加密鉴权信息
     */
    private String parseAuthInfoFromWorkflow(String nodeId, String targetName, WorkflowVO workflow) {
        for (WorkflowNodeVO node : workflow.getNodes()) {
            if (Strings.CS.equals(NodeType.HTTP.getType(), node.getType()) && Strings.CS.equals(nodeId, node.getId())
                && node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO) != null) {
                AuthInfo authInfo = JsonUtils
                    .objectToClassType(node.getConfigs().get(CommonConstant.Workflow.AUTH_INFO), AuthInfo.class);
                if (!Objects.isNull(authInfo) && AuthInfo.ScopeEnum.SERVICE.equals(authInfo.getScope())) {
                    for (AuthKeyInfo authKeyInfo : authInfo.getAuthKeys()) {
                        if (Strings.CS.equals(authKeyInfo.getTargetName(), targetName)) {
                            return authKeyInfo.getAuthKey();
                        }
                    }
                }
            }
        }
        return StringUtils.EMPTY;
    }

    private WorkflowEntity getWorkflowEntityById(String workflowId) {
        WorkflowEntity filter = new WorkflowEntity();
        filter.setId(workflowId);
        List<WorkflowEntity> workflowEntityList = workflowMapper.getWorkflowEntityByFilter(filter);
        if (workflowEntityList == null || workflowEntityList.isEmpty()) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        return workflowEntityList.get(0);
    }

    private WorkflowEntity getWorkflowEntityById(String projectId, String workspaceId, String workflowId) {
        WorkflowEntity workflowEntity =
            workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);
        if (ObjectUtils.isEmpty(workflowEntity)) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        return workflowEntity;
    }

    private String getDefaultWorkflowTemplate(String workflowType) {
        // 根据类型以及语言选择模板
        boolean isChinese = LanguageUtils.isChinese();
        boolean isTask = CommonConstant.Workflow.TASK.equals(workflowType);
        return isChinese ? (isTask ? workflowDefaultTaskFlow : workflowDefaultChatFlow)
            : (isTask ? workflowDefaultTaskFlowEnglish : workflowDefaultChatFlowEnglish);
    }

    private WorkflowEntity checkOpWorkflowPermission(String projectId, String workflowId) {
        if (!Strings.CS.equals(projectId, opSvcProjectId)) {
            log.error("projectId = {} tenant doesn't have publishing permissions", projectId);
            throw new AgentStudioException(StudioError.WORKFLOW_TENANT_NOT_PERMISSION);
        }
        WorkflowEntity workflow = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
            ThreadLocalUtils.getWorkspaceId(), workflowId);
        if (workflow == null) {
            log.error("workflow does not exist, projectId = {}, workflowId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        return workflow;
    }

    private WorkflowFrontParamInfo parseWorkflowParams(WorkflowEntity workflowEntity, String version) {
        // obs获取工作流dsl
        String workflowJson;
        if (StringUtils.isEmpty(version)) {
            workflowJson = obsService.downloadObsFile(workflowEntity.getDslPath());
        } else {
            ReleaseVersion releaseVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(workflowEntity.getId(), version);
            workflowJson = obsService.downloadObsFile(releaseVersion.getDslPath());
        }

        WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);

        // workflow参数回填
        WorkflowFrontParamInfo workflowFrontParamInfo = new WorkflowFrontParamInfo();
        workflowFrontParamInfo.setId(workflowEntity.getId());
        workflowFrontParamInfo.setIcon(workflowEntity.getAvatar());
        workflowFrontParamInfo.setName(workflowEntity.getName());
        workflowFrontParamInfo.setType(workflowEntity.getWorkflowType());
        workflowFrontParamInfo.setDescription(workflowVo.getDescription());

        // 设置开场白和推荐问
        if (workflowVo.getConfigs() != null) {
            workflowFrontParamInfo
                .setPrologue(workflowVo.getConfigs().getOrDefault(PROLOGUE, StringUtils.EMPTY).toString());
            Object suggestQueriesObj = workflowVo.getConfigs().getOrDefault(SUGGEST_QUERIES, StringUtils.EMPTY);
            if (suggestQueriesObj instanceof List<?>) {
                List<String> suggestList =
                    ((List<?>) suggestQueriesObj).stream().map(Object::toString).collect(Collectors.toList());
                workflowFrontParamInfo.setSuggestQueries(suggestList);
            }
        }
        List<WorkflowNodeVO> workflowNodes = workflowVo.getNodes();
        WorkflowNodeVO startNode = WorkflowUtils.getWorkflowNodeID(INPUT_KEY, workflowNodes);
        List<WorkflowFieldVO> inputs = startNode == null ? null : startNode.getOutputs();

        // 输入参数过滤系统参数回填
        if (inputs != null) {
            inputs = inputs.stream().filter(m -> !Strings.CS.equals(SYS, m.getName())).toList();
            workflowFrontParamInfo.setInputs(inputs.stream()
                .map(m -> new WorkflowFrontParam().setName(m.getName())
                    .setDescription(m.getDescription())
                    .setRequired(m.isRequired())
                    .setSchema(m.getSchema())
                    .setSource(m.getSource().toString())
                    .setType(m.getType())
                    .setValue(m.getValue()))
                .toList());
        }
        // 输出参数回填
        WorkflowNodeVO endNode = WorkflowUtils.getWorkflowNodeID(OUTPUT_KEY, workflowNodes);
        List<WorkflowFieldVO> outputs = endNode == null ? null : endNode.getOutputs();
        if (outputs != null) {
            workflowFrontParamInfo.setOutputs(outputs.stream()
                .map(m -> new WorkflowFrontParam().setName(m.getName())
                    .setDescription(m.getDescription())
                    .setRequired(m.isRequired())
                    .setSchema(m.getSchema())
                    .setSource(m.getSource().toString())
                    .setType(m.getType())
                    .setValue(m.getValue()))
                .toList());
        }
        return workflowFrontParamInfo;
    }

    @Override
    public WorkFlowEnvs getWorkflowEnvs(String projectId, String workflowId,
        @NotNull GetWorkflowEnvsQo getWorkflowEnvsQo) {
        WorkFlowEnvs workFlowEnvs = new WorkFlowEnvs();
        List<WorkFlowEnv> workFlowEnv = this.parseWorkflowEnvs(projectId, workflowId, getWorkflowEnvsQo.getVersionId(),
            getWorkflowEnvsQo.isNestedCheck() ? NESTED_DEEP : 0);
        List<WorkFlowEnv> distinctWorkFlowEnvs = workFlowEnv.stream()
            .collect(Collectors.toMap(env -> StringUtils.join(env.getName(), "|", env.getCnName(), "|", env.getType()),
                env -> env, (existing, replacement) -> existing))
            .values()
            .stream()
            .toList();
        workFlowEnvs.setVariables(distinctWorkFlowEnvs);
        return workFlowEnvs;
    }

    private @NotNull List<WorkFlowEnv> parseWorkflowEnvs(String projectId, String workflowId, String version,
        int recursionCount) {
        List<WorkFlowEnv> workFlowEnvs = new ArrayList<>();
        if (recursionCount < 0) {
            return workFlowEnvs;
        }

        // 获取工作流并校验权限
        WorkflowEntity workflowEntity = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
            ThreadLocalUtils.getWorkspaceId(), workflowId);
        if (workflowEntity == null) {
            log.error("workflow does not exist, projectId = {}, workflowId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        String obsDslPath = workflowEntity.getDslPath();
        if (StringUtils.isNotBlank(version)) {
            ReleaseVersion releaseVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(workflowEntity.getId(), version);
            obsDslPath = releaseVersion.getDslPath();
        }
        String workflowJson = obsService.downloadObsFile(obsDslPath);
        WorkflowVO workflowVo = JSON.parseObject(workflowJson, WorkflowVO.class);
        Map<String, Object> configs = workflowVo.getConfigs();
        if (CollectionUtils.isEmpty(configs) || configs.get("environment") == null
            || StringUtils.isBlank(String.valueOf(configs.get("environment")))) {
            return workFlowEnvs;
        }
        if (CollectionUtils.isEmpty(workflowVo.getNodes())) {
            return workFlowEnvs;
        }
        for (WorkflowNodeVO nodeVo : workflowVo.getNodes()) {
            if (nodeVo == null) {
                continue;
            }
            List<WorkflowFieldVO> outputs = nodeVo.getOutputs();
            if (!CollectionUtils.isEmpty(outputs)) {
                this.parseInputsOutputsEnv(workFlowEnvs, outputs);
            }
            List<WorkflowFieldVO> inputs = nodeVo.getInputs();
            if (CollectionUtils.isEmpty(inputs)) {
                continue;
            }
            this.parseInputsOutputsEnv(workFlowEnvs, inputs);
        }
        List<MappingEntity> mappingEntities =
            mappingMapper.selectByAppIdAndResourceType(workflowEntity.getId(), WORKFLOW.toString());
        for (MappingEntity mappingEntity : mappingEntities) {
            if (!Strings.CS.equals(mappingEntity.getResourceType(), WORKFLOW.toString())) {
                continue;
            }
            List<WorkFlowEnv> subWorkFlowEnvs = parseWorkflowEnvs(projectId, mappingEntity.getResourceId(),
                mappingEntity.getResourceVersion(), recursionCount - 1);
            workFlowEnvs.addAll(subWorkFlowEnvs);
        }
        return workFlowEnvs;
    }

    private void parseInputsOutputsEnv(List<WorkFlowEnv> workFlowEnvs, List<WorkflowFieldVO> inOrOutputs) {
        workFlowEnvs.addAll(inOrOutputs.stream()
            .filter(inOrOutput -> "environment".equalsIgnoreCase(String.valueOf(inOrOutput.getSource()))
                && inOrOutput.getValue() != null && inOrOutput.getValue().getContent() != null)
            .map(output -> JsonUtils.<Map<String, String>>objectToClass(output.getValue().getContent()))
            .filter(Objects::nonNull)
            .map(content -> content.get(REF_VAR_NAME))
            .filter(StringUtils::isNotBlank)
            .map(envVar -> {
                WorkFlowEnv variable = new WorkFlowEnv();
                variable.setName(envVar);
                return variable;
            })
            .toList());
    }

    public List<WorkflowEntity> queryWorkflowList(int limit, int offset) {
        return workflowMapper.queryWorkflowList(limit, offset);
    }

    /**
     * workflow导出
     *
     * @param projectId projectId
     * @param body body 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    @Override
    public org.springframework.core.io.Resource exportWorkflows(String projectId, String workspaceId,
        ExportParams body) {
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        return agentImportExportService.exportWorkflows(projectId, workspaceId, body);
    }

    /**
     * workflow导入
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importWorkflows 需要导入的工作流id列表
     * @param importTools 需要导入的插件id列表
     * @return ImportRsp 导入请求的响应，包括id、name、description、status和dependencies（工作流的依赖）
     */
    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Workflow",
        description = "导入工作流",
        resourceId = "-1"
    )
    public ImportRsp importWorkflows(String workspaceId, String projectId, MultipartFile file, String importWorkflows,
        String importTools, String mode) {
        agentManagementService.checkImportFile(file);
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        if (agentCommonService.isExportFileV2(file)) {
            return agentImportService.importFile(projectId, RequestContextUtils.getRequestWorkspaceId(), file, mode);
        }
        return agentImportExportService.importWorkflows(projectId, workspaceId, file, importWorkflows, importTools);
    }

    @Override
    public AutoAddResultJsonObject generateWorkflowPrologue(String projectId, String workflowId, String workspaceId) {
        // 获取工作流默认模型配置信息
        Map<String, String> modelConfigMap = getWorkflowModelConfigs(workflowId, projectId, workspaceId);
        WorkflowEntity workflowEntity = workflowMapper.selectByWorkflowId(projectId, workspaceId, workflowId);

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template =
            CommonUtil.getResourceContent(isChinese ? PromptPath.PROLOGUE_PROMPT : PromptPath.PROLOGUE_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, workflowEntity.getName()),
            KV.of(CommonConstant.DESCRIPTION, workflowEntity.getDescription()));
        String modelDeploymentId = modelConfigMap.get("model_deployment_id");
        String modelType = modelConfigMap.get("model_type");
        String model = modelConfigMap.get("model");
        return aiGenerateService.generatePrologue(modelDeploymentId, modelType, model, null, query, workspaceId);
    }

    @Override
    public AutoAddResultJsonObject recommendedWorkflowQuestions(String projectId, String workflowId,
        String workspaceId) {
        // 获取工作流默认模型配置信息
        Map<String, String> modelConfigMap = getWorkflowModelConfigs(workflowId, projectId, workspaceId);
        WorkflowEntity workflow = workflowMapper.getWorkflowEntityByWorkspaceId(projectId, workspaceId, workflowId);

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(
            isChinese ? PromptPath.RECOMMENDED_QUESTIONS_PROMPT : PromptPath.RECOMMENDED_QUESTIONS_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, workflow.getName()),
            KV.of(CommonConstant.DESCRIPTION, workflow.getDescription()));
        String modelDeploymentId = modelConfigMap.get("model_deployment_id");
        String modelType = modelConfigMap.get("model_type");
        String model = modelConfigMap.get("model");
        return aiGenerateService.recommendedQuestions(modelDeploymentId, modelType, model, null, query, workspaceId);
    }

    private Map<String, String> getWorkflowModelConfigs(String workflowId, String projectId, String workspaceId) {
        // 获取工作流默认模型配置信息
        WorkflowEntity workflow = workflowMapper.selectByWorkflowId(projectId, workspaceId, workflowId);
        if (workflow == null) {
            log.error("workflow does not exist, projectId = {}, workspaceId = {}, agentId = {}", projectId, workspaceId,
                workflowId);
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        String workflowInfo = obsService.downloadObsFile(workflow.getDslPath());
        Map<String, Object> workflowConfig = JSON.parseObject(workflowInfo, WorkflowVO.class).getConfigs();

        // 历史数据全局配置可能为空
        if (workflowConfig == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED);
        }
        Object defaultModel = workflowConfig.get("default_model");
        if (defaultModel == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        Map<String, String> modelConfigs;
        try {
            modelConfigs = new ObjectMapper().convertValue(defaultModel,
                new com.fasterxml.jackson.core.type.TypeReference<Map<String, String>>() {});
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        return modelConfigs;
    }


    /**
     * 转换特殊字符
     */
    private String escapeSqlSpecialChars(String content) {
        if (content == null || content.isEmpty()) {
            return content;
        }
        return content.replace("!", "!!")
            .replace("%", "!%")
            .replace("_", "!_");
    }
}
