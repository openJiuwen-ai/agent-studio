/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.common.constant.Constants.AppType.CONTROLLER;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.annotation.DistributedLock;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.FileCommonUtils;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.PromptPath;
import com.openjiuwen.studio.agent.manager.dto.AdditionalQuestionsConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentApplicationInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentApplicationListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentMcpDetail;
import com.openjiuwen.studio.agent.manager.dto.AgentSkillDetail;
import com.openjiuwen.studio.agent.manager.dto.AgentToolDetail;
import com.openjiuwen.studio.agent.manager.dto.AgentVariable;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListItem;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentWorkflowDetail;
import com.openjiuwen.studio.agent.manager.dto.ApplicationListReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.AutoAddStudioResourceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.dto.ExternalKnowledgeBaseSource;
import com.openjiuwen.studio.agent.manager.dto.FreeTrialQuota;
import com.openjiuwen.studio.agent.manager.dto.GetAgentVersionQo;
import com.openjiuwen.studio.agent.manager.dto.Guideline;
import com.openjiuwen.studio.agent.manager.dto.Icon;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.InputVariable;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.dto.ListAgentApplicationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.manager.dto.Scene;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.dto.SkillReference;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberInfo;
import com.openjiuwen.studio.agent.manager.dto.maas.ImageGenerationRequest;
import com.openjiuwen.studio.agent.manager.dto.maas.ImageGenerationResponse;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.AgentBaseInfo;
import com.openjiuwen.studio.agent.manager.entity.AgentExportEntity;
import com.openjiuwen.studio.agent.manager.entity.AgentVersion;
import com.openjiuwen.studio.agent.manager.entity.App;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.entity.SkillVersionEntity;
import com.openjiuwen.studio.agent.manager.entity.Tag;
import com.openjiuwen.studio.agent.manager.entity.ToolExportEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginExportEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.AgentType;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.TriggerType;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AgentVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.TagMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.MaasModelClient;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.adapter.AgentPluginAdapter;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMemberService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.IconNameCheckUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.BooleanUtils;
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
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

/**
 * 功能描述 Agent管理Service
 *
 */
@Slf4j
@Service
public class AgentManagementService implements IAgentManagementService {

    private static final Pattern AGENT_NAME_PT = Pattern.compile(
        "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$");

    private static final String AGENT_OBS_PATH_TEMPLATE = "%s/%s/%s/%s.json";

    private static final int THREAD_POOL_SIZE = 100;

    /**
     * 支持的DeepResearch写作模板文件类型
     */
    private static final Set<String> DEEP_RESEARCH_TEMPLATE_TYPES = Collections.unmodifiableSet(
        new HashSet<>(Arrays.asList("doc", "docx", "pdf", "md", "html")));

    /**
     * 复制名称模板
     */
    private static final String NAME_FORMAT = "%s_%s";

    private static final String IMPORT_FILE_TYPE = ".jsonl";

    private static final String ACTIVE = "active";

    private static final int KB = 1024;

    // 保留：中文、英文字母、数字、空格、下划线、中划线
    private static final String ALLOWED_PATTERN = "[^\\u4e00-\\u9fa5a-zA-Z0-9 _-]";

    // 智能体图标自动生成
    public static final String QWEN_IMAGE = "qwen-image";

    public static final String SIZE = "512x512";

    public static final String PNG = ".png";

    private static final String AVATAR_FOLDER = "icon";

    // 自主动态规划模式
    private static final String PLAN_EXECUTE = "PlanExecute";

    // 最大指南数量
    private static final int MAX_GUIDELINE_NUM = 100;

    // ReAct模式
    private static final String REACT = "ReAct";

    private static final int MAX_SKILL_NUM = 50;

    private final ExecutorService fixedThreadPool = Executors.newFixedThreadPool(THREAD_POOL_SIZE);

    private final ObjectMapper jacksonObjectMapper;

    private final Scheduler scheduler;

    private final AgentMapper agentMapper;

    private final AgentVersionMapper agentVersionMapper;

    private final ReleaseVersionMapper releaseVersionMapper;

    private final ReleaseChannelMapper releaseChannelMapper;

    private final AppMapper appMapper;

    private final WorkflowMapper workflowMapper;

    private final WorkspaceMapper workspaceMapper;

    private final PermissionService permissionService;

    private final MappingMapper mappingMapper;

    private final TagMapper tagMapper;

    private final MgObsService mgObsService;

    private final RelationManagementService relationManagementService;

    private final IrAdapterService irAdapterService;

    private final AgentImportExportService agentImportExportService;

    private final AgentCommonService agentCommonService;

    private final ControllerManagementService controllerManagementService;

    private final PublishUtils publishUtils;

    private final MessageSource messageSource;

    private final JiuWenService jiuWenService;

    private final AgentMemoryConfigService agentMemoryConfigService;

    private final AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    @Autowired
    private WorkspaceMemberService workSpaceMemberService;

    @Autowired
    private AgentRuntimeClient agentRuntimeClient;

    @Autowired
    private AgentSpaceService agentSpaceService;

    @Autowired
    private WorkflowValidationService workflowValidationService;

    @Autowired
    private SkuManageService skuManageService;


    @Autowired
    private AiGenService aiGenService;

    @Autowired
    private AgentExportService agentExportService;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private AgentImportService agentImportService;

    @Autowired
    private EnvironmentServiceManagerService environmentServiceManagerService;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${inner.agent-runtime.endpoint}")
    private String agentRuntimeEndpoint;

    @Value("${inner.agent-runtime.run-agent.stream-url}")
    private String runAgentStreamUrl;

    @Value("${agent.endpoint-template:}")
    private String endpointTemplate;

    @Value("${front-page.runtime-host:}")
    private String runtimeHost;

    @Value("${server.ssl.enabled:}")
    private String serverSslEnabled;

    private String controllerEndPointTemplate;

    @Value("${agent.max-release-version-size}")
    private int releaseMaxSize;

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    @Value("${release.channel.webpage-endpoint}")
    private Integer webpageEndpoint;

    @Value("${knowledge.recall-threshold.min}")
    private double knowledgeRecallThresholdMin;

    @Value("${knowledge.recall-threshold.max}")
    private double knowledgeRecallThresholdMax;

    @Value("${agent.long-term-memory-enable}")
    private boolean longTermMemoryEnable;

    @Value("${prr.is-soft-delete: true}")
    private Boolean isSoftDelete;

    @Value("${maas.authorization}")
    private String authorization;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${publish.agent-builder.enable}")
    private boolean publishAgentBuilderEnable;

    @Value("${export.max-length}")
    private int importMaxLen;

    @Value("${publish.app-store.enable:false}")
    private boolean publishAppEnable;

    @Value("${content-review.configs}")
    private String contentReviewConfigs;

    @Value("${asset.app.free.trial-quota-limit:10}")
    private int assetAppFreeTrialQuotaLimit;

    @Autowired
    private MaasModelClient maasModelClient;

    @Autowired
    private AgentPluginAdapter agentPluginAdapter;

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private SkillVersionMapper skillVersionMapper;

    @Autowired
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    /**
     * 构造方法
     *
     * @param agentMapper agentMapper
     */
    public AgentManagementService(AgentMapper agentMapper, AgentVersionMapper agentVersionMapper,
        ReleaseVersionMapper releaseVersionMapper, ReleaseChannelMapper releaseChannelMapper, AppMapper appMapper,
        WorkflowMapper workflowMapper, TagMapper tagMapper, MgObsService service, ObjectMapper jacksonObjectMapper,
        MappingMapper mappingMapper, RelationManagementService relationManagementService,
        IrAdapterService irAdapterService, Scheduler scheduler, AgentImportExportService agentImportExportService,
        AgentCommonService agentCommonService, ControllerManagementService controllerManagementService,
        PublishUtils publishUtils, MessageSource messageSource, JiuWenService jiuWenService,
        WorkspaceMapper workspaceMapper, PermissionService permissionService,
        AgentMemoryConfigService agentMemoryConfigService, AssetFreeTrialMgmtService assetFreeTrialMgmtService) {
        this.agentMapper = agentMapper;
        this.agentVersionMapper = agentVersionMapper;
        this.releaseVersionMapper = releaseVersionMapper;
        this.releaseChannelMapper = releaseChannelMapper;
        this.appMapper = appMapper;
        this.workflowMapper = workflowMapper;
        this.mappingMapper = mappingMapper;
        this.tagMapper = tagMapper;
        this.mgObsService = service;
        this.jacksonObjectMapper = jacksonObjectMapper;
        this.relationManagementService = relationManagementService;
        this.scheduler = scheduler;
        this.irAdapterService = irAdapterService;
        this.agentImportExportService = agentImportExportService;
        this.agentCommonService = agentCommonService;
        this.controllerManagementService = controllerManagementService;
        this.publishUtils = publishUtils;
        this.messageSource = messageSource;
        this.jiuWenService = jiuWenService;
        this.workspaceMapper = workspaceMapper;
        this.permissionService = permissionService;
        this.agentMemoryConfigService = agentMemoryConfigService;
        this.assetFreeTrialMgmtService = assetFreeTrialMgmtService;
    }

    @PostConstruct
    private void init() {
        controllerEndPointTemplate = endpointTemplate + "?type=controller";
    }

    protected String authGeneratorName(String projectId, String workspaceId, String description) {
        if (description.length() < 60 && AGENT_NAME_PT.matcher(description).matches()) {
            return description;
        }
        List<ModelServiceData> models = modelServiceManager.queryAvailableServices(projectId, workspaceId, "LLM", true);
        if (models.isEmpty()) {
            log.warn("Not found available model service.");
            return CommonConstant.AGENT_NAME_DEFAULT;
        }

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(isChinese ? PromptPath.NAME_PROMPT : PromptPath.NAME_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, description));
        String modelDeploymentId = models.get(0).getId();
        String modelType = models.get(0).getModelType();
        ModelConfig config = new ModelConfig();
        try {
            AutoAddResultJsonObject result = generateName(modelDeploymentId, modelType, modelDeploymentId, config,
                query, workspaceId);
            if (StringUtils.isEmpty(result.getName())) {
                log.warn("Not found model generate name.");
                return CommonConstant.AGENT_NAME_DEFAULT;
            }
            return result.getName();
        } catch (Exception e) {
            log.warn("Fail generator name by model.", e);
            return CommonConstant.AGENT_NAME_DEFAULT;
        }
    }

    @Override
    @DistributedLock(prefix = "agent:create:")
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "创建智能体",
        resourceId = "-1",
        resourceName = "body.name"
    )
    public AgentInfo createAgent(String projectId, String workspaceId, CreateAgentReq body) {
        AgentType agentType = AgentType.naValueOf(body.getType() == null ? null : body.getType().toString());
        if (StringUtils.isEmpty(body.getName())) {
            body.setName(authGeneratorName(projectId, workspaceId, body.getDescription()));
            body.setName(validateName(projectId, body.getName(), agentType.name(), true));
        } else {
            body.setName(body.getName());
        }

        skuManageService.validateInsertAppCountExceededLimitOrNot();

        if (agentType == AgentType.CONTROLLER) {
            return controllerManagementService.createController(projectId, workspaceId, body);
        }
        return createAndGetAgent(projectId, workspaceId, body);
    }

    private AgentInfo createAndGetAgent(String projectId, String workspaceId, CreateAgentReq body) {
        Agent agent = agentCommonService.initAgent(projectId, workspaceId, body);
        // 追问默认配置
        AdditionalQuestionsConfig additionalQuestionsConfig = new AdditionalQuestionsConfig();
        additionalQuestionsConfig.setEnable(true);
        additionalQuestionsConfig.setRounds(CommonConstant.ROUNDS_DEFAULT);
        // 根据语言选择prompt模板
        boolean isChinese = LanguageUtils.isChinese();
        additionalQuestionsConfig.setPrompt(isChinese
            ? CommonConstant.ADDITIONAL_QUESTIONS_PROMPT_CUSTOM
            : CommonConstant.ADDITIONAL_QUESTIONS_PROMPT_CUSTOM_EN);
        agent.setAdditionalQuestionsConfig(additionalQuestionsConfig);
        agent.setSubType(CommonConstant.COMMON_AGENT_TYPE);
        agent.setModelConfig(new ModelConfig());
        // 内容审核
        agent.setContentReview(contentReviewConfigs);
        // 检查agent icon
        agentCommonService.checkAgentIcon(agent.getIcon());
        // 上传dsl文件
        AgentInfo agentInfo = agentCommonService.buildComplexAgentInfo(agent);
        String dslVersionPath;
        String jsonContent = JsonUtils.serializeWithFallback(agentInfo, log,
            "AgentInfo for obs upload, agentId: " + agent.getAgentId());
        dslVersionPath = mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId(), CommonConstant.AGENT,
            jsonContent, CommonConstant.DSL_STR);
        agent.setDslPath(dslVersionPath);
        // 上传agent IR文件
        String irPath = uploadAgentIr(agent);
        agent.setIrPath(irPath);
        agentMapper.insert(agent);

        return getAgent(projectId, workspaceId, agent.getAgentId()).convertToDto();
    }

    /**
     * @param agent agent
     * @param oldName oldName
     * @param projectId projectId
     */
    public void generateValidName(Agent agent, String oldName, String projectId) {
        // name长度限制64，如果原有名称接近限制长度，需要先做截断
        if (oldName.length() > 61) {
            oldName = oldName.substring(0, 61);
        }

        // 生成拷贝后名称后缀，不与已有重复
        int suffixNum = 1;
        String newName = String.format(NAME_FORMAT, oldName, suffixNum);
        agent.setName(newName);

        // 获取所有中文名称
        Set<String> currentNames = getCurrentNames(projectId, oldName, agent.getType());
        while (currentNames.contains(agent.getName())) {
            ++suffixNum;
            agent.setName(String.format(NAME_FORMAT, oldName, suffixNum));
        }
        validateName(projectId, agent.getName(), agent.getType(), false);
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "复制智能体",
        resourceId = "agentId",
        resourceName = ""
    )
    public AgentInfo copyAgent(String projectId, String agentId, String workspaceId, String targetWorkspaceId) {
        Agent oldAgent = getAgent(projectId, workspaceId, agentId);

        // 构建复制的agent对象入库
        Agent newAgent = new Agent();
        String newAgentId = UUID.randomUUID().toString();
        newAgent.setAgentId(newAgentId);
        newAgent.setProjectId(projectId);
        newAgent.setWorkspaceId(workspaceId);
        generateValidName(newAgent, oldAgent.getName(), projectId);
        newAgent.setDescription(oldAgent.getDescription());
        newAgent.setIcon(oldAgent.getIcon());
        newAgent.setModelDeploymentId(oldAgent.getModelDeploymentId());
        newAgent.setModelName(oldAgent.getModelName());
        newAgent.setModelConfig(oldAgent.getModelConfig());
        newAgent.setInstructions(oldAgent.getInstructions());
        newAgent.setTriggerList(oldAgent.getTriggerList());
        newAgent.setMemoryVariables(oldAgent.getMemoryVariables());
        newAgent.setPrologue(oldAgent.getPrologue());
        newAgent.setSuggestQueries(oldAgent.getSuggestQueries());
        newAgent.setAdditionalQuestionsConfig(oldAgent.getAdditionalQuestionsConfig());
        newAgent.setStatus(AgentStatus.DRAFT.toString());
        newAgent.setCreator(RequestContextUtils.getRequestUserName());
        newAgent.setCreatorId(RequestContextUtils.getRequestUserId());
        newAgent.setModelType(oldAgent.getModelType());
        newAgent.setKnowledgeRetrievePolicy(oldAgent.getKnowledgeRetrievePolicy());
        newAgent.setType(StringUtils.isEmpty(oldAgent.getType()) ? AgentType.AGENT.getValue() : oldAgent.getType());
        newAgent.setContentReview(oldAgent.getContentReview());
        newAgent.setWorkspaceId(targetWorkspaceId);
        newAgent.setDomainId(RequestContextUtils.getRequestUserDomainId());
        newAgent.setSubType(oldAgent.getSubType());
        newAgent.setSchedulingMode(oldAgent.getSchedulingMode());
        newAgent.setDslPath(oldAgent.getDslPath());
        newAgent.setMemoryConfig(oldAgent.getMemoryConfig());
        newAgent.setDeleted(0);
        AgentType agentType = AgentType.naValueOf(oldAgent.getType());

        if (workspaceId.equals(targetWorkspaceId)) {
            skuManageService.validateInsertAppCountExceededLimitOrNot();
            if (agentType.equals(AgentType.CONTROLLER)) {
                return controllerManagementService.copy(oldAgent, newAgent);
            }
            return copyAgentInSameWorkspace(agentId, newAgent);
        }

        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.CROSS_SPACE_COPY);

        Set<String> currentUserJoinedWorkspaceIdSet = workSpaceMemberService.queryAllWorkSpaceInfoByIamUserId(
                RequestContextUtils.getRequestUserId())
            .stream()
            .map(WorkSpaceMemberEntity::getWorkspaceId)
            .collect(Collectors.toSet());

        if (CollectionUtils.isEmpty(currentUserJoinedWorkspaceIdSet) || !currentUserJoinedWorkspaceIdSet.contains(
            targetWorkspaceId)) {
            log.error("the user {} not in workspace {} when copy agent", RequestContextUtils.getRequestUserId(),
                targetWorkspaceId);
            throw new AgentStudioException(StudioError.USER_NOT_IN_TARGET_WORKSPACE);
        }

        String exportAgentStr = agentImportExportService.exportAgentStr(projectId, workspaceId, agentId);

        List<ImportListInfo> importListInfoList = listImportInfoFromJson(projectId, exportAgentStr);

        agentImportExportService.importAgentWithStr(projectId, targetWorkspaceId, exportAgentStr, importListInfoList);

        // 这里直接返回复制的对象信息，不能查询，避免读未提交
        return newAgent.convertToDto();
    }

    private AgentInfo copyAgentInSameWorkspace(String oldAgentId, Agent newAgent) {
        String projectId = newAgent.getProjectId();
        String workspaceId = newAgent.getWorkspaceId();
        String newAgentId = newAgent.getAgentId();
        newAgent.setTraceId(newAgentId);

        // 上传agent IR文件
        String irPath = uploadAgentIr(newAgent);
        newAgent.setIrPath(irPath);
        agentMapper.insert(newAgent);

        List<MappingEntity> boundKnowledgeMappings = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            CommonConstant.REPO_TYPE);
        if (!boundKnowledgeMappings.isEmpty()) {
            // 处理复制agent和knowledgeRepo的关联信息入库
            relationManagementService.handleAgentKnowledgeRepo(projectId, workspaceId, newAgentId,
                boundKnowledgeMappings);
        }

        List<MappingEntity> hasBoundToolList = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            CommonConstant.TOOL_TYPE);
        if (!hasBoundToolList.isEmpty()) {
            // 处理复制agent和tool的关联信息入库
            relationManagementService.handleAgentTool(projectId, workspaceId, newAgentId, hasBoundToolList);
        }

        List<MappingEntity> boundWorkflowMappings = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            CommonConstant.WORKFLOW_TYPE);
        if (!boundWorkflowMappings.isEmpty()) {
            // 处理复制agent和workflow的关联信息入库
            relationManagementService.handleAgentWorkflow(projectId, workspaceId, newAgentId, boundWorkflowMappings);
        }

        List<MappingEntity> boundMcpMappings = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            CommonConstant.MCP_TYPE);
        if (!boundMcpMappings.isEmpty()) {
            // 处理复制agent和mcp server的关联信息入库
            relationManagementService.handleAgentMcp(projectId, workspaceId, newAgentId, boundMcpMappings);
        }
        List<MappingEntity> boundModelMappings = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            ResourceTypeEnum.MODEL.toString());
        if (!boundModelMappings.isEmpty()) {
            // 处理复制agent和模型的关联信息入库
            List<MappingEntity> boundModelMappingsAndNewMappingId = boundModelMappings.stream()
                .peek(entity -> entity.setMappingId(UUID.randomUUID().toString()))
                .toList();
            relationManagementService.handleAgentModel(projectId, workspaceId, newAgentId,
                boundModelMappingsAndNewMappingId);
        }
        List<MappingEntity> boundSkillMappings = mappingMapper.selectByAppIdAndResourceType(oldAgentId,
            CommonConstant.SKILL_TYPE);
        if (!boundSkillMappings.isEmpty()) {
            // 处理复制agent和SKill的关联信息入库
            relationManagementService.handleAgentSkill(projectId, workspaceId, newAgentId, boundSkillMappings);
        }
        return getAgent(projectId, newAgent.getAgentId()).convertToDto();
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "添加智能体触发器",
        resourceId = "agentId",
        resourceName = ""
    )
    public TriggerConfig addTrigger(String projectId, String agentId, String workspaceId, TriggerConfig body) {
        if (!TriggerType.TIMER.name().equals(body.getType()) && !TriggerType.EVENT.name().equals(body.getType())) {
            log.error("Trigger type is wrong. The wrong type is {}. projectId = {}, agentId = {}", body.getType(),
                projectId, agentId);
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_TYPE_INCORRECT, body.getType());
        }
        Agent agent = getAgent(projectId, workspaceId, agentId);
        List<TriggerConfig> triggerList = agent.getTriggerList();
        if (!CollectionUtils.isEmpty(triggerList) && triggerList.size() >= CommonConstant.MAX_TRIGGER_NUMS) {
            log.error("The number of triggers has reached the upper limit. projectId = {}, agentId = {}", projectId,
                agentId);
            throw new AgentStudioException(StudioError.AGENT_TRIGGER_SIZE_LIMIT);
        }
        if (TriggerType.TIMER.name().equals(body.getType())) {
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
                        .usingJobData(CommonConstant.AGENT_ID, agentId)
                        .usingJobData(CommonConstant.TRIGGER_ID, body.getTriggerId())
                        .usingJobData(CommonConstant.PROMPT, body.getPrompt())
                        .usingJobData(CommonConstant.WORKSPACE_ID, workspaceId)
                        .usingJobData(CommonConstant.AGENT_RUNTIME_ENDPOINT, agentRuntimeEndpoint)
                        .usingJobData(CommonConstant.RUN_AGENT_STREAM_URL, runAgentStreamUrl)
                        .build();
                    scheduler.scheduleJob(jobDetail, trigger);
                    if (!scheduler.isShutdown()) {
                        scheduler.start();
                    }
                }
            } catch (SchedulerException e) {
                log.error("Scheduler add job failed.", e);
                throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
            }
        }
        ModifyAgentReq modifyAgentReq = new ModifyAgentReq();
        if (triggerList == null) {
            modifyAgentReq.setTriggerList(new ArrayList<>());
        } else {
            modifyAgentReq.setTriggerList(triggerList);
        }
        body.setCreatedOn(new Date());
        modifyAgentReq.getTriggerList().add(body);

        // 更新agent
        Agent newAgent = buildModifyAgent(projectId, workspaceId, agentId, modifyAgentReq);
        agentMapper.updateByPrimaryKeySelective(newAgent);
        newAgent = getAgent(projectId, agentId);
        uploadAgentIr(newAgent);
        return body;
    }

    @Override
    public AutoAddResultJsonObject autoAddStudioResource(String projectId, String workspaceId, String agentId,
        AutoAddStudioResourceRequestBody body) {
        // 1.校验部分
        if (StringUtils.isBlank(body.getInstructions())) {
            throw new AgentStudioException(StudioError.MISSING_REQUIRED_INSTRUCTIONS);
        }
        Agent agent = agentMapper.selectById(agentId);
        if (agent == null) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        ResourceTypeEnum resourceType = ResourceTypeEnum.fromValue(body.getType());
        if (resourceType == null || StringUtils.isBlank(body.getType())) {
            throw new AgentStudioException(StudioError.UNSUPPORTED_RESOURCE_TYPE);
        }

        // 2.提示词替换
        String template;
        String query;
        List<SkillDetails> skillDetails = new ArrayList<>();
        switch (resourceType) {
            case SKILL -> {
                // 2.1. 广场
                skillDetails.addAll(
                    skillMapper.search(new SkillEntity().setStatus("developed"), 0, Integer.MAX_VALUE, null, null, 1));
                // 2.2. 组件库
                skillDetails.addAll(skillMapper.search(
                    new SkillEntity().setProjectId(projectId).setWorkspaceId(workspaceId).setStatus("developed"), 0,
                    Integer.MAX_VALUE, null,null,0));
                // 2.3. 剔除已经关联的skill和同名skill
                List<MappingEntity> hasBoundSkills = mappingMapper.selectByAppIdAndResourceType(agentId,
                    CommonConstant.SKILL_TYPE);
                List<String> hasBoundSkillIds = hasBoundSkills.stream().map(MappingEntity::getResourceId).toList();
                List<String> hasBoundSkillNames = hasBoundSkills.stream().map(MappingEntity::getResourceName).toList();
                skillDetails.removeIf(skill -> hasBoundSkillIds.contains(skill.getSkillId()));
                skillDetails.removeIf(skill -> hasBoundSkillNames.contains(skill.getName()));
                // 2.4. 余下skill列表剔除重名
                List<SkillDetails> uniqueSkills = skillDetails.stream()
                    .collect(Collectors.collectingAndThen(Collectors.toMap(SkillDetails::getName, skill -> skill,
                        (existing, replacement) -> existing
                    ), map -> new ArrayList<>(map.values())));
                // 2.5. 提取name、description
                List<SkillDetails> skillsCatalog = uniqueSkills.stream()
                    .map(skill -> new SkillDetails().setName(skill.getName()).setDescription(skill.getDescription()))
                    .toList();
                // 2.6. 模板替换
                String skillsCatalogJson = JSON.toJSONString(skillsCatalog);
                template = CommonUtil.getResourceContent(LanguageUtils.isChinese()
                    ? PromptPath.AUTO_ADD_SKILLS_PROMPT
                    : PromptPath.AUTO_ADD_SKILLS_PROMPT_EN);
                PromptTemplate promptTemplate = new PromptTemplate(template);
                query = promptTemplate.format(KV.of(CommonConstant.INSTRUCTIONS, body.getInstructions()),
                    KV.of(CommonConstant.SKILLS_CATALOG, skillsCatalogJson));
            }
            default -> throw new AgentStudioException(StudioError.UNSUPPORTED_RESOURCE_TYPE);
        }

        // 3.调用大模型
        String modelRsp;
        try {
            modelRsp = jiuWenService.callModel(
                agentCommonService.buildAskModelReq(agent.getModelDeploymentId(), agent.getModelType(),
                    agent.getModel(), agent.getModelConfig(), query), workspaceId);
        } catch (Exception e) {
            log.error("Call model failed.", e);
            throw new AgentStudioException(StudioError.CALL_MODEL_ERROR);
        }

        // 4.解析大模型返回结果
        return parseModelResponse(modelRsp, resourceType, body.getLimit(), body.getConfidence(), skillDetails);
    }

    /**
     * 解析大模型返回结果
     *
     * @param modelRsp 大模型返回的JSON字符串
     * @return AutoAddResultJsonObject 包含过滤后的skill列表
     */
    private AutoAddResultJsonObject parseModelResponse(String modelRsp, ResourceTypeEnum resourceType, int limit, double confidenceThreshold,
        List<SkillDetails> skillDetails) {
        log.info("model response: {}", modelRsp);
        if (StringUtils.isBlank(modelRsp)) {
            return new AutoAddResultJsonObject();
        }
        try {
            return switch (resourceType) {
                case SKILL -> parseModelResponseAutoAddSkill(modelRsp, limit, confidenceThreshold, skillDetails);
                default -> throw new AgentStudioException(StudioError.UNSUPPORTED_RESOURCE_TYPE);
            };
        } catch (Exception e) {
            log.error("Failed to parse the result returned by the foundation model: {}", modelRsp, e);
            // 解析失败时返回空结果
            return new AutoAddResultJsonObject();
        }
    }

    /**
     * 解析智能添加skill的大模型响应
     * @param modelRsp modelRsp
     * @param limit limit
     * @param confidenceThreshold confidenceThreshold
     * @return AutoAddResultJsonObject
     */
    private AutoAddResultJsonObject parseModelResponseAutoAddSkill(String modelRsp, int limit, double confidenceThreshold,
        List<SkillDetails> skillDetails) {
        JSONObject jsonResponse = JSON.parseObject(modelRsp);
        JSONArray selectedSkills = jsonResponse.getJSONArray("selected_skills");
        // 1.按confidence降序排序
        JsonUtils.sortJsonArrayByConfidence(selectedSkills, false);
        if (selectedSkills == null || selectedSkills.isEmpty()) {
            return new AutoAddResultJsonObject();
        }
        // 2.选择对应skill
        List<SkillReference> filteredSkills = new ArrayList<>();
        for (Object jsonObject : selectedSkills) {
            JSONObject skillObj = (JSONObject) jsonObject;
            Double confidence = skillObj.getDouble("confidence");
            // 置信度大于阈值
            if (confidence != null && confidence >= confidenceThreshold) {
                String skillName = skillObj.getString("name");
                if (StringUtils.isNotBlank(skillName)) {
                    SkillReference skillReference = new SkillReference();
                    skillReference.setSkillName(skillName);
                    skillDetails.stream().filter(skillEntity -> skillEntity.getName().equals(skillName)).findFirst().ifPresent(skillEntity -> {
                        skillReference.setSkillId(skillEntity.getSkillId());
                        skillReference.setLastVersionId(skillEntity.getUsedVersion());
                    });
                    filteredSkills.add(skillReference);
                }
            }
            if (filteredSkills.size() >= limit) {
                break;
            }
        }
        AutoAddResultJsonObject result = new AutoAddResultJsonObject();
        return result.setSkills(filteredSkills);
    }


    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Agent",
        description = "删除智能体",
        resourceId = "agentId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteAgent(String projectId, String agentId, String workspaceId) {
        // 校验Agent是否能够删除
        checkAgentShouldBeDeletedOrNot(projectId, workspaceId, agentId);

        // agent-builder空间取消发布
        if (publishAgentBuilderEnable) {
            agentSpaceService.delete(workspaceId, agentId);
        }
        // 删除数据库数据，包括资源关联信息、版本信息、应用信息
        if (isSoftDelete) {
            // 处理mapping表，将数据迁移到mapping历史表，删除mapping原有数据
            agentCommonService.softDeleteMapping(agentId);

            // 处理Agent版本表，迁移到新的表，旧数据删除
            agentCommonService.softDeleteReleaseVersionByAppId(agentId);

            // 处理Agent资源表，迁移到新的表，旧数据删除
            agentCommonService.softDeleteAgent(projectId, agentId);

        } else {
            mappingMapper.deleteBatchByAppId(agentId, null, true);
            releaseVersionMapper.deleteByAppId(agentId);
            agentMapper.deleteByPrimaryKey(agentId, projectId);
        }
        mappingMapper.updateValidByResourceIdAndVersionId(agentId, null);
        appMapper.deleteByResourceId(agentId, projectId, workspaceId);
        releaseChannelMapper.deleteByAppId(agentId);
        agentVersionMapper.deleteByAgentId(agentId);

        String requestIamToken = RequestContextUtils.getRequestAuthToken();
        String language = LanguageUtils.getLanguage();

        // 删除obs桶中的IR文件和DSL文件
        fixedThreadPool.execute(() -> {
            String irPath = CommonConstant.AGENT_TYPE + CommonConstant.FOLDER_SEPARATOR + CommonConstant.Workflow.IR
                + CommonConstant.FOLDER_SEPARATOR + agentId;
            String dslPath = CommonConstant.AGENT_TYPE + CommonConstant.FOLDER_SEPARATOR + CommonConstant.DSL_STR
                + CommonConstant.FOLDER_SEPARATOR + agentId;
            if (isSoftDelete) {
                // 软删除时ir,dsl文件增加“.deleted”后缀,其他全部删除
                mgObsService.appendSuffixByPrefix(irPath, CommonConstant.DELETED_SUFFIX);
                mgObsService.appendSuffixByPrefix(dslPath, CommonConstant.DELETED_SUFFIX);
            } else {
                mgObsService.deleteObsObjects(irPath);
                mgObsService.deleteObsObjects(dslPath);
            }
            // 删除用户的所有长期记忆
            agentMemoryConfigService.clearUserMemoriesInApplication(requestIamToken, language, projectId, agentId);
        });
        try {
            agentRuntimeClient.clearResourceCache(requestIamToken, projectId, agentId, Constants.AppType.AGENT);
        } catch (Exception e) {
            log.warn("Failed to clear runtime agent resource:", e);
        }

        return new CommonDeleteRsp().setId(agentId);
    }

    private void checkAgentShouldBeDeletedOrNot(String projectId, String workspaceId, String agentId) {
        Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);

        if (agent == null) {
            log.error("agent does not exist, projectId = {}, workspaceId = {}, agentId = {}", projectId, workspaceId,
                agentId);
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        if (shareResourceMapper.countResourceByResourceId(projectId, agentId) > 0) {
            log.error("the agent has been shared,you can't delete it");
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY);
        }

        if (CollectionUtils.isEmpty(agent.getTriggerList())) {
            return;
        }

        for (TriggerConfig triggerConfig : agent.getTriggerList()) {
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

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Agent",
        description = "删除触发器",
        resourceId = "triggerId",
        resourceName = ""
    )
    public Void deleteTrigger(String projectId, String agentId, String triggerId, String workspaceId) {
        Agent agent = getAgent(projectId, workspaceId, agentId);
        List<TriggerConfig> triggerList = agent.getTriggerList();
        if (CollectionUtils.isEmpty(triggerList)) {
            log.error("Trigger does not exist! projectId = {}, agentId = {}, triggerId = {}", projectId, agentId,
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
                ModifyAgentReq modifyAgentReq = new ModifyAgentReq();
                modifyAgentReq.setTriggerList(triggerList);

                // 更新agent
                Agent newAgent = buildModifyAgent(projectId, workspaceId, agentId, modifyAgentReq);
                agentMapper.updateByPrimaryKeySelective(newAgent);
                newAgent = getAgent(projectId, agentId);
                uploadAgentIr(newAgent);
                return null;
            }
        }
        log.error("Trigger does not exist! projectId = {}, agentId = {}, triggerId = {}", projectId, agentId,
            triggerId);
        throw new AgentStudioException(StudioError.AGENT_TRIGGER_EXIST, triggerId);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Agent",
        description = "编辑触发器",
        resourceId = "agentId",
        resourceName = ""
    )
    public TriggerConfig editTrigger(String projectId, String agentId, String workspaceId, TriggerConfig body) {
        // delete 原任务
        deleteTrigger(projectId, agentId, body.getTriggerId(), workspaceId);
        addTrigger(projectId, agentId, workspaceId, body);
        return body;
    }

    @Override
    public AgentInfo retrieveAgent(String projectId, String agentId, String workspaceId) {
        Agent agent = getAgent(projectId, workspaceId, agentId);
        return agentCommonService.buildComplexAgentInfo(agent);
    }

    /**
     * 根据agentId查询指定agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return Agent
     */
    @NotNull
    public Agent getAgent(String projectId, String agentId) {
        return agentCommonService.getAgent(projectId, agentId);
    }

    /**
     * 获取Agent并校验存在性
     *
     * @param projectId 项目ID
     * @param workspaceId 空间ID
     * @param agentId agent资源ID
     * @return Agent详情
     */
    @NotNull
    public Agent getAgent(String projectId, String workspaceId, String agentId) {
        return agentCommonService.getAgent(projectId, workspaceId, agentId);
    }

    @Override
    public AgentListRsp listAgents(String projectId, ListAgentsQo listAgentsQo) {
        String workspaceId = listAgentsQo.getWorkspaceId();
        SearchCriteria searchCriteria = new SearchCriteria();
        searchCriteria.setId(listAgentsQo.getId());
        searchCriteria.setName(StrUtils.filterSpecialWords(listAgentsQo.getName()));
        searchCriteria.setType(listAgentsQo.getType());
        searchCriteria.setWorkspaceId(workspaceId);
        searchCriteria.setDescription(StrUtils.filterSpecialWords(listAgentsQo.getDescription()));
        searchCriteria.setCreator(StrUtils.filterSpecialWords(listAgentsQo.getCreator()));
        searchCriteria.setStatus(listAgentsQo.getStatus());
        PageHelper.offsetPage(listAgentsQo.getOffset(), listAgentsQo.getLimit());
        List<Agent> agentList = agentMapper.selectByProjectIdAndSearchCriteria(projectId, searchCriteria);
        PageInfo<Agent> agentPageInfo = new PageInfo<>(agentList);

        PageInfo<AgentInfo> agentInfoPageInfo = new PageInfo<>();
        List<AgentInfo> agentInfoList = agentList.stream().map(Agent::convertToDto).toList();
        agentInfoList.forEach(item -> {
            AgentType type = AgentType.naValueOf(item.getType());
            String agentTemplate = type == AgentType.CONTROLLER ? controllerEndPointTemplate : endpointTemplate;
            String agentUrl = String.format(agentTemplate, projectId, item.getAgentId());
            if (StringUtils.isNotEmpty(runtimeHost)) {
                String protocol = Constants.TRUE.equalsIgnoreCase(serverSslEnabled) ? "https://" : "http://";
                agentUrl = protocol + runtimeHost.replaceFirst("^https?://", "") + agentUrl;
            }
            item.setUrl(agentUrl);
        });
        // 更新发布渠道信息
        agentInfoList.forEach(item -> {
            List<String> channelTypes = new ArrayList<>();
            if (CommonConstant.AGENT_PUBLISHED.equals(item.getStatus())) {
                List<ReleaseChannel> releaseChannels = releaseChannelMapper.selectByAppIdAndWorkspaceId(item.getAgentId(), projectId, workspaceId);
                channelTypes.addAll(releaseChannels.stream().map(ReleaseChannel::getChannelType).toList());
            }
            item.setChannelType(channelTypes);
        });
        agentInfoPageInfo.setList(agentInfoList);
        AgentListRsp agentListRsp = new AgentListRsp();
        agentListRsp.setAgentList(agentInfoList);
        agentListRsp.setCount(agentPageInfo.getTotal());
        return agentListRsp;
    }

    @Override
    public AgentApplicationListRsp listAgentApplications(String projectId, ListAgentApplicationsQo request) {
        List<String> agentType = request.getType() == null ? null : Arrays.asList(request.getType().split(","));
        // 数据库查询
        PageHelper.offsetPage(request.getOffset(), request.getLimit());
        List<String> ids = StringUtils.isEmpty(request.getId()) ? null : Collections.singletonList(request.getId());
        List<AgentApplicationInfo> agentInfoList = agentMapper.selectByProjectIdAndSearchKey(projectId, ids,
            request.getName(), request.getStatus(), agentType, null);

        // 所属空间名称
        if (CollectionUtils.isNotEmpty(agentInfoList)) {
            List<String> workspaceIds = agentInfoList.stream().map(AgentApplicationInfo::getWorkspaceId).toList();
            List<WorkspaceEntity> workspaces = workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(projectId,
                workspaceIds, null);
            Map<String, String> workSpaceIdName = workspaces.stream()
                .collect(Collectors.toMap(WorkspaceEntity::getId, WorkspaceEntity::getName));
            agentInfoList.forEach(agentApplicationInfo -> {
                agentApplicationInfo.setWorkspaceName(
                    workSpaceIdName.getOrDefault(agentApplicationInfo.getWorkspaceId(), StringUtils.EMPTY));
            });
        }

        // 分页数据
        PageInfo<AgentApplicationInfo> agentPageInfo = new PageInfo<>(agentInfoList);
        PageInfo<AgentApplicationInfo> agentInfoPageInfo = new PageInfo<>();
        agentInfoPageInfo.setList(agentInfoList);

        // 构造返回结果
        AgentApplicationListRsp resp = new AgentApplicationListRsp();
        resp.setAgentList(agentInfoList);
        resp.setCount(agentPageInfo.getTotal());
        return resp;
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Agent",
        description = "修改智能体",
        resourceId = "agentId",
        resourceName = "body.name"
    )
    public AgentInfo modifyAgent(String projectId, String agentId, String workspaceId, ModifyAgentReq body) {
        updateLatestValid(agentId, body);
        if (!KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            checkKnowledgeType(body);
        }

        Agent agent = agentMapper.selectById(agentId);
        if (agent == null) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        AgentType agentType = AgentType.naValueOf(body.getType() == null ? agent.getType() : body.getType().toString());


        switch (agentType) {
            case CONTROLLER -> {
                Agent newAgent = buildModifyAgent(projectId, workspaceId, agentId, body);
                return controllerManagementService.modify(newAgent, projectId, workspaceId, body);
            }
            default -> {
                return modifySingleAgent(projectId, workspaceId, agentId, body);
            }
        }
    }

    private void updateLatestValid(String agentId, ModifyAgentReq body) {
        log.debug("Entering updateLatestValid with agentId={}, body={}", agentId, body);

        if (body.getUpdateTime() != null) {
            Agent agent = agentMapper.selectById(agentId);
            log.debug("Retrieved agent information: {}", agent);

            if (Objects.isNull(agent)) {
                throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
            }
            if (!agent.getUpdatedOn().equals(body.getUpdateTime())) {
                log.error("agent has updated by others, latest UpdateTime = {}, request updateTime = {}",
                    agent.getUpdatedOn(), body.getUpdateTime());
                throw new AgentStudioException(StudioError.AGENT_HAS_BEEN_UPDATED);
            }
        }
    }

    private AgentInfo modifySingleAgent(String projectId, String workspaceId, String agentId, ModifyAgentReq body) {
        workflowValidationService.validateContentReview(body.getContentReview());
        // 更新agent接口不支持直接更新触发器信息
        body.setTriggerList(null);
        // 处理数据库中通用字段
        Agent newAgent = buildModifyAgent(projectId, workspaceId, agentId, body);
        // 处理通用字段
        if (body.getKnowledgeRepos() != null) {
            List<MappingEntity> knowledgeReferences = new ArrayList<>();
            for (String id : body.getKnowledgeRepos()) {
                MappingEntity mappingEntity = new MappingEntity();
                mappingEntity.setAppId(agentId);
                mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
                mappingEntity.setResourceId(id);
                mappingEntity.setResourceType(CommonConstant.REPO_TYPE);
                knowledgeReferences.add(mappingEntity);
            }

            // 处理agent和knowledgeRepo的关联信息入库
            relationManagementService.handleAgentKnowledgeRepo(projectId, workspaceId, agentId, knowledgeReferences);
        }
        if (body.getTools() != null) {
            List<String> toolIds = body.getTools();
            agentCommonService.validTools(projectId, workspaceId, toolIds);
            List<MappingEntity> toolReferences = generateMappingToolsEntities(agentId, toolIds);
            // 处理agent和tool的关联信息入库
            relationManagementService.handleAgentTool(projectId, workspaceId, agentId, toolReferences);
        }
        if (body.getToolDetails() != null) {
            List<AgentToolDetail> toolDetails = body.getToolDetails();
            List<String> toolIds = toolDetails.stream().map(AgentToolDetail::getToolId).toList();
            List<MappingEntity> toolReferences = generateToolReferences(agentId, toolDetails, toolIds);
            agentCommonService.validTools(projectId, workspaceId, toolIds);
            relationManagementService.handleAgentTool(projectId, workspaceId, agentId, toolReferences);
        }
        if (body.getWorkflows() != null) {
            ListWorkflowsQo listWorkflowsQo = new ListWorkflowsQo();
            listWorkflowsQo.setStatus(CommonConstant.WORKFLOW_PUBLISHED);
            listWorkflowsQo.setWorkspaceId(workspaceId);
            List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowSearchCriteria(projectId,
                listWorkflowsQo);
            List<String> selectWorkflowIds = workflowEntities.stream().map(WorkflowEntity::getId).toList();

            List<MappingEntity> workflowReferences = new ArrayList<>();
            for (String id : body.getWorkflows()) {
                // 校验id是否可用
                if (CollectionUtils.isEmpty(selectWorkflowIds) || !selectWorkflowIds.contains(id)) {
                    throw new AgentStudioException(StudioError.SUB_WORKFLOW_CANNOT_USE, id);
                }
                MappingEntity workflowMapping = new MappingEntity();
                workflowMapping.setAppId(agentId);
                workflowMapping.setAppType(CommonConstant.AGENT_TYPE);
                workflowMapping.setResourceId(id);
                workflowMapping.setResourceType(CommonConstant.WORKFLOW_TYPE);
                workflowReferences.add(workflowMapping);
            }

            // 处理agent和workflow的关联信息入库
            relationManagementService.handleAgentWorkflow(projectId, workspaceId, agentId, workflowReferences);

            // 清空agent关联的所有工作流时，需要将工作流跳转设置为false
            if (body.getWorkflows().isEmpty()) {
                newAgent.setWorkflowSwitchEnabled(false);
            }
        }
        if (body.getWorkflowDetails() != null) {
            List<AgentWorkflowDetail> agentWorkflowDetails = body.getWorkflowDetails();
            List<MappingEntity> workflowReferences = generateAgentWorkflowReferences(agentWorkflowDetails, workspaceId,
                projectId, agentId);
            relationManagementService.handleAgentWorkflow(projectId, workspaceId, agentId, workflowReferences);
            // 清空agent关联的所有工作流时，需要将工作流跳转设置为false
            if (body.getWorkflowDetails().isEmpty()) {
                newAgent.setWorkflowSwitchEnabled(false);
            }
        }
        if (body.getMcpServers() != null) {
            Map<String, List<String>> mcpChooseTools = body.getMcpChooseTools();
            newAgent.setMcpChooseTools(mcpChooseTools);
            List<MappingEntity> mcpReferences = new ArrayList<>();
            for (String id : body.getMcpServers()) {
                MappingEntity mcpMapping = new MappingEntity();
                mcpMapping.setAppId(agentId);
                mcpMapping.setAppType(CommonConstant.AGENT_TYPE);
                mcpMapping.setResourceId(id);
                mcpMapping.setResourceType(CommonConstant.MCP_TYPE);
                mcpMapping.setResourceChooseTools(
                    mcpChooseTools == null ? null : JsonUtils.toJson(mcpChooseTools.get(id)));
                mcpReferences.add(mcpMapping);
            }

            // 处理agent和mcp server的关联信息入库
            relationManagementService.handleAgentMcp(projectId, workspaceId, agentId, mcpReferences);
        }
        // 新版入参结构，适配agent中支持mcp传递动态参数。
        if (body.getMcpDetails() != null) {
            List<AgentMcpDetail> mcpDetails = body.getMcpDetails();
            List<MappingEntity> mcpReferences = generateAgentMcpReferences(agentId, mcpDetails);

            // 处理agent和mcp server的关联信息入库
            relationManagementService.handleAgentMcp(projectId, workspaceId, agentId, mcpReferences);
        }
        if (StringUtils.isNotBlank(body.getModelDeploymentId())) {
            MappingEntity entity = new MappingEntity();
            String agentName = newAgent.getName();
            Agent agent = this.getAgent(projectId, workspaceId, agentId);
            if (StringUtils.isBlank(agentName)) {
                agentName = agent.getName();
            }
            entity.setAppId(agentId);
            entity.setAppName(agentName);
            entity.setAppType(CommonConstant.AGENT_TYPE);
            entity.setResourceId(newAgent.getModelDeploymentId());
            entity.setResourceName(newAgent.getModelName());
            entity.setResourceType(ResourceTypeEnum.MODEL.toString());
            if (BooleanUtils.isTrue(body.isStrategyFlag())) {
                entity.setResourceType(ResourceTypeEnum.STRATEGY.toString());
            }
            List<MappingEntity> mappingEntities = mappingMapper.selectAllByAppId(agentId);
            List<MappingEntity> oldMappings = mappingEntities.stream()
                .filter(p -> Strings.CS.equals(p.getResourceId(), agent.getModelDeploymentId()))
                .toList();
            if (CollectionUtils.isNotEmpty(oldMappings)) {
                if (CollectionUtils.size(oldMappings) == 1) {
                    entity.setMappingId(oldMappings.get(0).getMappingId());
                    mappingMapper.updateById(entity);
                }
            } else {
                entity.setMappingId(UUID.randomUUID().toString());
                mappingMapper.insert(entity);
            }
        }
        if (body.getSkills() != null) {
            // 0. 还原版本场景，根据传入的skills，构造List<AgentSkillDetail>
            List<String> skillIds = body.getSkills().stream().map(SkillReference::getSkillId).toList();
            List<SkillDetails> skillDetails = skillMapper.searchBySkillIds(skillIds);
            List<AgentSkillDetail> agentSkillDetails = new ArrayList<>();
            skillDetails.forEach(skill -> {
                AgentSkillDetail agentSkillDetail = new AgentSkillDetail().setSkillId(skill.getSkillId())
                    .setSkillVersion(skill.getUsedVersion());
                agentSkillDetails.add(agentSkillDetail);
            });
            // 1. 校验
            Map<String, SkillDetails> validSkillsMap = validateSkills(agentSkillDetails);
            // 2. 生成技能引用实体
            List<MappingEntity> skillReferences = generateSkillReferences(agentId, agentSkillDetails, validSkillsMap);
            // 3. 处理agent和skill的关联信息入库
            relationManagementService.handleAgentSkill(projectId, workspaceId, agentId, skillReferences);
        }
        if (body.getSkillDetails() != null) {
            List<AgentSkillDetail> skillDetails = body.getSkillDetails();
            // 1. 校验
            Map<String, SkillDetails> validSkillsMap = validateSkills(skillDetails);
            // 2. 生成技能引用实体（仅包含有效skill）
            List<MappingEntity> skillReferences = generateSkillReferences(agentId, skillDetails, validSkillsMap);
            // 3. 处理agent和skill的关联信息入库
            relationManagementService.handleAgentSkill(projectId, workspaceId, agentId, skillReferences);
        }

        AgentInfo agentInfo = agentCommonService.buildComplexAgentInfo(newAgent);

        // 这里 可能存在兼容问题 比如当一个 getAgent必须加一个额外的配置 agentInfo.setWritingTemplate 因为这个是独立于buildComplexAgentInfo方法的
        // WritingTemplate 没有数据库存在的
        // 处理深度研究模式字段
        if (body.getSearchEngine() != null) {
            String toolId = body.getSearchEngine().getId();
            if (StringUtils.isNotBlank(toolId)) {
                agentCommonService.validTools(projectId, workspaceId, Collections.singletonList(toolId));
                List<MappingEntity> toolReferences = new ArrayList<>();
                MappingEntity mappingEntity = new MappingEntity();
                mappingEntity.setAppId(agentId);
                mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
                mappingEntity.setResourceId(toolId);
                mappingEntity.setResourceType(CommonConstant.TOOL_TYPE);
                mappingEntity.setSubType(CommonConstant.DEEPRESEARCH_TYPE);
                toolReferences.add(mappingEntity);
                // 处理agent和tool的关联信息入库
                relationManagementService.handleAgentTool(projectId, workspaceId, agentId, toolReferences);
                List<ToolReference> tools = relationManagementService.listAgentTools(projectId, workspaceId, agentId, 0,
                    20);
                ToolReference tool = tools.stream().filter(t -> t.getToolId().equals(toolId)).findFirst().orElse(null);
                agentInfo.setSearchEngine(tool);
            } else {
                agentInfo.setSearchEngine(createEmptyToolReference());
            }
        }
        if (body.getWritingTemplate() != null) {
            agentInfo.setWritingTemplate(body.getWritingTemplate());
        }
        if (body.isIsTemplate() != null) {
            agentInfo.setIsTemplate(body.isIsTemplate());
        }

        // 处理可控自主规划模式字段
        if (body.getScenes() != null) {
            validateScenes(body.getScenes());
            // 检查是否存在id，如果不存在则置一个uuid，存在则跳过
            body.getScenes().stream()
                .filter(scene -> StringUtils.isBlank(scene.getId()))
                .forEach(scene -> scene.setId(UUID.randomUUID().toString()));
            agentInfo.setScenes(body.getScenes());
        }

        // 模式
        String agentType = body.getType() != null ? body.getType().toString() : null;
        // 需要查表去更新，不然前端在更改页面其他逻辑，如修改提示词，模型，引入插件、工作流未加type都会退回到通用模式
        Agent existingAgent = getAgent(projectId, workspaceId, agentId);
        if (agentType == null) {
            boolean isCommonSubType = Strings.CS.equals(existingAgent.getSubType(), CommonConstant.COMMON_AGENT_TYPE);
            // 兼容老数据，未有subtype
            agentType = isCommonSubType || existingAgent.getSubType() == null
                ? CommonConstant.AGENT_TYPE
                : existingAgent.getSubType();
        }

        // 如果body存在subtype，直接以subtype为准，即还原版本场景
        if (body.getSubType() != null) {
            agentType = body.getSubType();
        }

        if (body.getMemoryConfig() != null) {
            if (!CommonConstant.PLANEXECUTE_TYPE.equals(agentType)) {
                throw new AgentStudioException(StudioError.AGENT_TYPE_MEMORY_REPO_NOT_SUPPORT, newAgent.getName());
            }
            String memoryRepoId = body.getMemoryConfig().getMemoryRepoId();
            // 处理agent和memory的关联信息入库
            relationManagementService.handleAgentMemoryRepo(projectId, workspaceId, agentId, memoryRepoId, CommonConstant.AGENT_TYPE);
        }
        switch (agentType) {
            case (CommonConstant.AGENT_TYPE), (CommonConstant.COMMON_AGENT_TYPE) -> {
                newAgent.setType(CommonConstant.AGENT_TYPE);
                newAgent.setSubType(CommonConstant.COMMON_AGENT_TYPE);
                newAgent.setWorkspaceId(workspaceId);
                newAgent.setSchedulingMode(REACT);
                agentInfo.setType(CommonConstant.AGENT_TYPE);
                agentInfo.setSubType(CommonConstant.COMMON_AGENT_TYPE);
                agentInfo.setWorkspaceId(workspaceId);
                agentInfo.setSchedulingMode(REACT);
            }
            case (CommonConstant.DEEPRESEARCH_TYPE) -> {
                newAgent.setType(CommonConstant.AGENT_TYPE);
                newAgent.setSubType(CommonConstant.DEEPRESEARCH_TYPE);
                newAgent.setWorkspaceId(workspaceId);
                newAgent.setSchedulingMode(REACT);
                agentInfo.setType(CommonConstant.AGENT_TYPE);
                agentInfo.setSubType(CommonConstant.DEEPRESEARCH_TYPE);
                agentInfo.setWorkspaceId(workspaceId);
                agentInfo.setSchedulingMode(REACT);
            }
            case (CommonConstant.PLANEXECUTE_TYPE) -> {
                newAgent.setType(CommonConstant.AGENT_TYPE);
                newAgent.setSubType(CommonConstant.PLANEXECUTE_TYPE);
                newAgent.setWorkspaceId(workspaceId);
                newAgent.setSchedulingMode(PLAN_EXECUTE);
                agentInfo.setType(CommonConstant.AGENT_TYPE);
                agentInfo.setSubType(CommonConstant.PLANEXECUTE_TYPE);
                agentInfo.setWorkspaceId(workspaceId);
                agentInfo.setSchedulingMode(PLAN_EXECUTE);
            }
            default -> {
                throw new AgentStudioException(StudioError.UNSUPPORTED_AGENT_TYPE);
            }
        }

        String dslVersionPath;
        String existingAgentJson = JsonUtils.serializeWithFallback(existingAgent.convertToDto(), log,
            "AgentInfo for obs upload, agentId: " + agentId);
        String agentInfoJson = JsonUtils.serializeWithFallback(agentInfo, log,
            "AgentInfo for obs upload, agentId: " + agentId);
        String updatedAgentJson = JsonUtils.serializeWithFallback(newAgent, log,
            "AgentInfo for obs upload, agentId: " + agentId);

        if (StringUtils.isNotBlank(existingAgent.getDslPath())) {
            String downloadedJson = mgObsService.downloadObsFile(existingAgent.getDslPath());
            String mergedJson = JsonUtils.mergeDslData(existingAgentJson, downloadedJson, log,
                "DSL merge for agentId: " + agentId);
            String intermediateJson = JsonUtils.mergeDslData(agentInfoJson, mergedJson, log,
                "DSL merge for agentId: " + agentId);
            String finalMergedJson = JsonUtils.mergeDslData(updatedAgentJson, intermediateJson, log,
                "DSL merge for agentId: " + agentId);
            // 确保 DSL 文件中的 content_review 字段是 JSONObject，避免被转义为字符串
            finalMergedJson = JsonUtils.ensureJsonObjectField(finalMergedJson, "content_review");
            dslVersionPath = mgObsService.uploadObsFile(agentId, agentId, CommonConstant.AGENT, finalMergedJson,
                CommonConstant.DSL_STR);
        } else {
            String intermediateJson = JsonUtils.mergeDslData(agentInfoJson, existingAgentJson, log,
                "DSL merge for agentId: " + agentId);
            String finalMergedJson = JsonUtils.mergeDslData(updatedAgentJson, intermediateJson, log,
                "DSL merge for agentId: " + agentId);
            // 确保 DSL 文件中的 content_review 字段是 JSONObject，避免被转义为字符串
            finalMergedJson = JsonUtils.ensureJsonObjectField(finalMergedJson, "content_review");
            dslVersionPath = mgObsService.uploadObsFile(agentId, agentId, CommonConstant.AGENT, finalMergedJson,
                CommonConstant.DSL_STR);
        }

        newAgent.setDslPath(dslVersionPath);
        agentMapper.updateByPrimaryKeySelective(newAgent);
        mappingMapper.updateAppNameByAppId(agentId, newAgent.getName());
        newAgent = getAgent(projectId, workspaceId, agentId);
        newAgent.setMcpChooseTools(body.getMcpChooseTools());
        updateSystemPrompt(newAgent);
        uploadAgentIr(newAgent);

        if (CommonConstant.DEEPRESEARCH_TYPE.equals(agentType) ||
            CommonConstant.PLANEXECUTE_TYPE.equals(agentType)) {
            return retrieveAgent(projectId, agentId, workspaceId);
        }

        return newAgent.convertToDto();
    }

    /**
     * 校验skill
     * @param skillDetails 前端传入body
     * @return 有效的Map<String, SkillEntity>
     */
    private Map<String, SkillDetails> validateSkills(List<AgentSkillDetail> skillDetails) {
        // 1. 空值校验
        if (CollectionUtils.isEmpty(skillDetails)) {
            return new HashMap<>();
        }
        // 2. 最大数量校验
        if (skillDetails.size() > MAX_SKILL_NUM) {
            throw new AgentStudioException(StudioError.SKILL_NUM_EXCEED_LIMIT);
        }
        // 3. 传入的skill_id和skill_version有效性校验
        List<String> invalidSkillIds = new ArrayList<>();
        List<String> skillIds = skillDetails.stream()
            .map(AgentSkillDetail::getSkillId)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
        List<SkillDetails> skillDetailsList = skillMapper.searchBySkillIds(skillIds);
        if (CollectionUtils.isEmpty(skillDetailsList)) {
            return new HashMap<>();
        }
        Map<String, SkillDetails> skillDetailsMap = skillDetailsList.stream()
            .filter(Objects::nonNull)
            .collect(Collectors.toMap(SkillDetails::getSkillId, skill -> skill,
                (existing, replacement) -> existing, HashMap::new));
        for (AgentSkillDetail skillDetail : skillDetails) {
            String skillId = skillDetail.getSkillId();
            String skillVersion = skillDetail.getSkillVersion();
            SkillDetails skill = skillDetailsMap.get(skillId);
            if (skill == null) {
                continue;
            }
            if (!StringUtils.isBlank(skillVersion) && !Objects.equals(skillVersion, skill.getUsedVersion())) {
                invalidSkillIds.add(skillId);
            }
        }
        if (!invalidSkillIds.isEmpty()) {
            throw new AgentStudioException(StudioError.SKILL_ID_OR_VERSION_NOT_MATCH);
        }
        return skillDetailsMap;
    }

    /**
     * 生成技能引用实体
     * @param agentId agent ID
     * @param skillDetails 技能详情列表
     * @return 映射实体列表
     */
    private List<MappingEntity> generateSkillReferences(String agentId, List<AgentSkillDetail> skillDetails, Map<String, SkillDetails> validSkillsMap) {
        if (CollectionUtils.isEmpty(skillDetails)) {
            return Collections.emptyList();
        }
        List<MappingEntity> skillReferences = new ArrayList<>();
        for (AgentSkillDetail skillDetail : skillDetails) {
            SkillDetails validSkill = validSkillsMap.get(skillDetail.getSkillId());
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setAppId(agentId);
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            mappingEntity.setResourceId(skillDetail.getSkillId());
            mappingEntity.setResourceType(CommonConstant.SKILL_TYPE);
            mappingEntity.setResourceVersion(skillDetail.getSkillVersion());
            mappingEntity.setReferenceType(ReferenceTypeEnum.DIRECT.getValue());
            if (validSkill == null) {
                mappingEntity.setValid(false);
            } else {
                mappingEntity.setResourceName(validSkill.getName());
                mappingEntity.setResourceDesc(validSkill.getDescription());
                SkillVersionEntity skillVersionEntity = skillVersionMapper.searchByVersionId(skillDetail.getSkillVersion());
                mappingEntity.setExtendInfo(skillVersionEntity != null ? skillVersionEntity.getVersionName() : null);
            }
            skillReferences.add(mappingEntity);
        }
        return skillReferences;
    }

    /**
     * 校验场景信息，不超过100个
     * @param scenes 场景
     */
    private void validateScenes(List<Scene> scenes) {
        // 单个智能体指南数量不超过100个
        int countGuideline = 0;
        // 提前计算剩余允许的指南数量，避免在循环内重复计算
        for (Scene scene : scenes) {
            List<Guideline> guidelines = scene.getGuidelines();
            if (guidelines == null || guidelines.isEmpty()) {
                continue;
            }
            int currentGuidelineCount = guidelines.size();
            // 检查是否会超出限制
            if (currentGuidelineCount > MAX_GUIDELINE_NUM ||
                countGuideline > MAX_GUIDELINE_NUM - currentGuidelineCount) {
                throw new AgentStudioException(StudioError.GUIDELINE_NUM_EXCEED_LIMIT);
            }
            countGuideline += currentGuidelineCount;
            if (countGuideline == MAX_GUIDELINE_NUM) {
                break;
            }
        }
    }

    /**
     * 原始生成插件的方法
     *
     * @param agentId agentId
     * @param toolIds toolIds
     * @return 引用关系
     */
    private List<MappingEntity> generateMappingToolsEntities(String agentId, List<String> toolIds) {
        if (CollectionUtils.isEmpty(toolIds)) {
            return Collections.emptyList();
        }

        List<String> pluginsIds = handlePluginId(toolIds);

        List<ShareResourceEntity> shareWorkflowList = shareResourceMapper.selectShareResourceByResourceIds(pluginsIds);

        Map<String, ShareResourceEntity> shareWorkflowMap = shareWorkflowList.stream()
            .collect(Collectors.toMap(ShareResourceEntity::getResourceId, Function.identity()));
        List<MappingEntity> toolReferences = new ArrayList<>();
        for (String id : toolIds) {
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setAppId(agentId);
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            mappingEntity.setResourceId(id);
            mappingEntity.setResourceType(CommonConstant.TOOL_TYPE);
            if (shareWorkflowMap.containsKey(getPluginId(id))) {
                mappingEntity.setReferenceType(ReferenceTypeEnum.SHARE.getValue());
            } else {
                mappingEntity.setReferenceType(ReferenceTypeEnum.DIRECT.getValue());
            }
            toolReferences.add(mappingEntity);
        }
        return toolReferences;
    }

    private @NotNull List<MappingEntity> generateToolReferences(String agentId, List<AgentToolDetail> toolDetails,
        List<String> toolIds) {
        if (CollectionUtils.isEmpty(toolDetails)) {
            return Collections.emptyList();
        }

        List<String> pluginsIds = handlePluginId(toolIds);

        List<ShareResourceEntity> shareWorkflowList = shareResourceMapper.selectShareResourceByResourceIds(pluginsIds);

        Map<String, ShareResourceEntity> shareWorkflowMap = shareWorkflowList.stream()
            .collect(Collectors.toMap(ShareResourceEntity::getResourceId, Function.identity()));

        List<MappingEntity> toolReferences = new ArrayList<>();
        for (AgentToolDetail toolDetail : toolDetails) {
            String toolId = toolDetail.getToolId();
            String toolVersion = agentPluginAdapter.getToolVersion(getPluginId(toolId), toolDetail.getToolVersion());
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setAppId(agentId);
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            mappingEntity.setResourceId(toolId);
            mappingEntity.setResourceVersion(toolVersion);
            mappingEntity.setReferenceType(CommonConstant.TOOL_TYPE);
            mappingEntity.setExtendInfo(toolDetail.getToolParam());
            if (shareWorkflowMap.containsKey(getPluginId(toolId))) {
                mappingEntity.setReferenceType(ReferenceTypeEnum.SHARE.getValue());
            } else {
                mappingEntity.setReferenceType(ReferenceTypeEnum.DIRECT.getValue());
            }
            toolReferences.add(mappingEntity);
        }
        return toolReferences;
    }

    /**
     * 生成单智能体和工作流的引入关系
     */
    public List<MappingEntity> generateAgentWorkflowReferences(List<AgentWorkflowDetail> agentWorkflowDetails,
        String workspaceId, String projectId, String agentId) {
        if (CollectionUtils.isEmpty(agentWorkflowDetails)) {
            return Collections.emptyList();
        }

        List<String> workflowIdList = agentWorkflowDetails.stream().map(AgentWorkflowDetail::getWorkflowId).toList();
        List<ShareResourceEntity> shareWorkflowList = shareResourceMapper.selectShareResourceByResourceIds(
            workflowIdList);

        Map<String, ShareResourceEntity> shareWorkflowMap = shareWorkflowList.stream()
            .filter(entity -> !workspaceId.equals(entity.getWorkspaceId()))
            .collect(Collectors.toMap(ShareResourceEntity::getResourceId, Function.identity(),
                (existingValue, newValue) -> existingValue));

        ListWorkflowsQo listWorkflowsQo = new ListWorkflowsQo();
        listWorkflowsQo.setStatus(CommonConstant.WORKFLOW_PUBLISHED);
        listWorkflowsQo.setWorkspaceId(workspaceId);
        List<String> selectWorkflowIds = workflowMapper.selectByWorkflowSearchCriteria(projectId, listWorkflowsQo)
            .stream()
            .map(WorkflowEntity::getId)
            .toList();

        return agentWorkflowDetails.stream().map(agentWorkflowDetail -> {
            String id = agentWorkflowDetail.getWorkflowId();
            MappingEntity workflowMapping = new MappingEntity();
            workflowMapping.setAppId(agentId);
            workflowMapping.setAppType(CommonConstant.AGENT_TYPE);
            workflowMapping.setResourceId(id);
            workflowMapping.setResourceVersion(agentWorkflowDetail.getWorkflowVersion());
            workflowMapping.setResourceType(CommonConstant.WORKFLOW_TYPE);
            workflowMapping.setExtendInfo(agentWorkflowDetail.getWorkflowParam());

            if (!selectWorkflowIds.contains(id) && !shareWorkflowMap.containsKey(id)) {
                log.error("the sub-workflow {} is not existed", id);
                throw new AgentStudioException(StudioError.SUB_WORKFLOW_CANNOT_USE, id);
            }

            if (shareWorkflowMap.containsKey(id)) {
                workflowMapping.setReferenceType(ReferenceTypeEnum.SHARE.getValue());
            }
            return workflowMapping;
        }).collect(Collectors.toList());
    }

    /**
     *
     * @param agentId agent id
     * @param mcpDetails agent mcp关联信息
     * @return mcpReferences mcp 映射关系
     */
    public List<MappingEntity> generateAgentMcpReferences(String agentId, List<AgentMcpDetail> mcpDetails) {
        if (CollectionUtils.isEmpty(mcpDetails)) {
            return Collections.emptyList();
        }

        List<MappingEntity> mcpReferences = new ArrayList<>();
        for (AgentMcpDetail mcpDetail : mcpDetails) {
            MappingEntity mcpMapping = new MappingEntity();
            mcpMapping.setAppId(agentId);
            mcpMapping.setAppType(CommonConstant.AGENT_TYPE);
            mcpMapping.setResourceId(mcpDetail.getMcpId());
            mcpMapping.setResourceType(CommonConstant.MCP_TYPE);
            mcpMapping.setExtendInfo(mcpDetail.getMcpParam());
            mcpReferences.add(mcpMapping);
        }

        return mcpReferences;
    }

    private void updateSystemPrompt(Agent newAgent) {
        String template = CommonUtil.getResourceContent(PromptPath.AUTO_GENERATION_REFERENCES);
        if (!ObjectUtils.isEmpty(newAgent.getKnowledgeRetrievePolicy()) && Boolean.TRUE.equals(
            newAgent.getKnowledgeRetrievePolicy().isShowSource())) {
            newAgent.setInstructions(Optional.ofNullable(newAgent.getInstructions()).orElse("") + template);
        }
        if (!ObjectUtils.isEmpty(newAgent.getKnowledgeRetrievePolicy()) && Boolean.TRUE.equals(
            newAgent.getKnowledgeRetrievePolicy().isRetrieveImage())) {
            // 更新提示词，保留检索结果中的图片信息，防止智能体自动过滤
            String preserveRetrieveImgPrompt = CommonUtil.getResourceContent(
                LanguageUtils.isChinese() ? PromptPath.PRESERVE_RETRIEVE_IMG : PromptPath.PRESERVE_RETRIEVE_IMG_EN);
            newAgent.setInstructions(
                Optional.ofNullable(newAgent.getInstructions()).orElse("") + preserveRetrieveImgPrompt);
        }
    }

    /**
     * 创建空的ToolReference对象
     *
     * @return 空的ToolReference对象，所有字符串属性为空字符串，AuthInfo包含默认值
     */
    private ToolReference createEmptyToolReference() {
        ToolReference toolReference = new ToolReference();
        toolReference.setToolId("");
        toolReference.setPluginChineseName("");
        toolReference.setToolDisplayName("");
        toolReference.setToolChineseName("");
        toolReference.setToolParameter("");
        toolReference.setToolIcon("");
        toolReference.setDesc("");
        toolReference.setCredentialStatus("");
        toolReference.setPluginDisplayName("");
        toolReference.setMetadata("");
        // 创建包含默认值的空AuthInfo对象
        AuthInfo emptyAuthInfo = new AuthInfo();
        emptyAuthInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        emptyAuthInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        // 创建空的AuthKeyInfo对象
        AuthKeyInfo emptyAuthKeyInfo = new AuthKeyInfo();
        emptyAuthKeyInfo.setTargetName("");
        emptyAuthKeyInfo.setAuthKey("");
        emptyAuthKeyInfo.setSourceName("");
        emptyAuthKeyInfo.setDesc("");
        // 将空的AuthKeyInfo添加到auth_keys列表中
        List<AuthKeyInfo> emptyAuthKeys = new ArrayList<>();
        emptyAuthKeys.add(emptyAuthKeyInfo);
        emptyAuthInfo.setAuthKeys(emptyAuthKeys);
        toolReference.setAuthInfo(emptyAuthInfo);
        return toolReference;
    }

    private Agent buildModifyAgent(String projectId, String workspaceId, String agentId, ModifyAgentReq body) {
        // 修改权限校验
        Agent oldAgent = validAgent(projectId, workspaceId, agentId, body);

        Agent newAgent = new Agent();
        newAgent.setAgentId(agentId);
        newAgent.setProjectId(projectId);
        newAgent.setWorkspaceId(workspaceId);
        newAgent.setName(body.getName());
        newAgent.setDescription(body.getDescription());
        if (body.getIcon() == null) {
            newAgent.setIcon(oldAgent.getIcon());
        } else {
            // 检查agent iconName
            IconNameCheckUtils.validaIconName(body.getIcon());
            String icon = ImageBase64Utils.getImageBase64(body.getIcon(), mgObsService);
            newAgent.setIconName(body.getIcon());
            newAgent.setIcon(icon);
        }
        newAgent.setModelDeploymentId(body.getModelDeploymentId());
        newAgent.setModelName(body.getModelName());
        newAgent.setModelConfig(body.getModelConfig());
        newAgent.setInstructions(body.getInstructions());
        newAgent.setTriggerList(body.getTriggerList());
        newAgent.setMemoryVariables(body.getMemoryVariables());
        newAgent.setPrologue(body.getPrologue());
        newAgent.setSuggestQueries(body.getSuggestQueries());
        newAgent.setAdditionalQuestionsConfig(body.getAdditionalQuestionsConfig());
        newAgent.setVoiceInteraction(body.getVoiceInteraction());
        newAgent.setReference(body.getReference());
        newAgent.setStatus(oldAgent.getStatus());
        newAgent.setUpdatedOn(new Date(System.currentTimeMillis()));
        newAgent.setModelType(body.getModelType());

        // 规划模型参数配置
        newAgent.setPlanQaIndependent(body.isPlanQaIndependent());
        newAgent.setPlanModelType(body.getPlanModelType());
        newAgent.setPlanModelDeploymentId(body.getPlanModelDeploymentId());
        newAgent.setPlanModelName(body.getPlanModelName());
        newAgent.setPlanModelConfig(body.getPlanModelConfig());
        newAgent.setPlanModel(body.getPlanModel());

        // 规划模型无需配置重复语句惩罚
        if (ObjectUtils.isNotEmpty(newAgent.getPlanModelConfig())) {
            newAgent.getPlanModelConfig().setFrequencyPenalty(null);
        }
        newAgent.setSafetyBarrier(
            body.isSafetyBarrier() != null ? body.isSafetyBarrier() : oldAgent.getSafetyBarrier());

        if (body.getContentReview() != null) {
            newAgent.setContentReview(JsonUtils.toJson(body.getContentReview()));
        }
        // 检查agent icon
        agentCommonService.checkAgentIcon(newAgent.getIcon());

        // 有模型配置传参时才更新model字段，适配model传参为null的场景
        if (body.getModelDeploymentId() != null) {
            newAgent.setModel(body.getModel());
        } else {
            newAgent.setModel(oldAgent.getModel());
        }
        checkKnowledgeRetrievePolicy(body.getKnowledgeRetrievePolicy());
        newAgent.setKnowledgeRetrievePolicy(body.getKnowledgeRetrievePolicy());
        // 检查Agent定义的变量是否合法
        checkAgentVariables(body.getAgentVariables());
        newAgent.setAgentVariables(body.getAgentVariables());

        // 检查Agent定义的入参变量是否合法
        checkAgentInputVariables(body.getInputVariables());
        newAgent.setInputVariables(body.getInputVariables());

        // 记忆配置
        newAgent.setMemoryConfig(body.getMemoryConfig());
        newAgent.setWorkflowSwitchEnabled(body.isWorkflowSwitchEnabled());
        newAgent.setSchedulingMode(
            Optional.ofNullable(body.getSchedulingMode())
                .map(Objects::toString)
                .orElse(oldAgent.getSchedulingMode()));
        return newAgent;
    }

    private Agent validAgent(String projectId, String workspaceId, String agentId, ModifyAgentReq body) {
        Agent oldAgent = getAgent(projectId, workspaceId, agentId);
        if (body.getName() != null && !body.getName().equals(oldAgent.getName())) {
            validateName(projectId, body.getName(), oldAgent.getType(), false);
        }
        return oldAgent;
    }

    /**
     * 上传智能体 IR（中间表示）文件到 OBS
     *
     * <p>IR 文件包含智能体的运行时配置，包括内容审核配置。
     * 在上传前需要确保 content_review 字段是 JSONObject 而非转义字符串，
     * 否则运行时无法正确解析敏感词配置（参见 {@link JsonUtils#ensureJsonObjectField}）。
     *
     * @param agent 智能体实体
     * @return OBS 上的 IR 文件路径
     */
    private String uploadAgentIr(Agent agent) {
        Map<String, Object> metadata = agentImportExportService.parseMetadata(agent);
        Map<String, Object> irInfo = processIrBySubType(agent, metadata, agent.getSubType());
        String irJson = JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue);
        // 确保 content_review 字段是 JSONObject，避免运行时解析失败
        irJson = JsonUtils.ensureJsonObjectField(irJson, Constants.Workflow.CONTENT_REVIEW);
        return mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId(), CommonConstant.AGENT,
            irJson, CommonConstant.Workflow.IR);
    }

    /**
     * 根据subType子类型，分别处理ir
     * @param agent agent
     * @param metadata metadata
     * @param subType subType
     * @return irInfo
     */
    private Map<String, Object> processIrBySubType(Agent agent, Map<String, Object> metadata, String subType) {

        Map<String, Object> irInfo = new HashMap<>();

        // DeepResearch模式
        if (CommonConstant.DEEPRESEARCH_TYPE.equals(subType) && StringUtils.isNotBlank(agent.getDslPath())) {
            AgentInfo agentInfo = getAgentInfo(agent);
            irInfo = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        }

        // PlanExecute模式
        if (CommonConstant.PLANEXECUTE_TYPE.equals(subType) && StringUtils.isNotBlank(agent.getDslPath())) {
            getAgentInfo(agent);
            irInfo = irAdapterService.adaptAgent(agent, metadata);
        }

        // Common模式
        if (CommonConstant.COMMON_AGENT_TYPE.equals(subType) || subType == null) {
            irInfo = irAdapterService.adaptAgent(agent, metadata);
        }

        return irInfo;
    }

    /**
     * DeepResearch模式与PlanExecute模式元数据存储在dsl中，需要获取dsl信息
     * @param agent agent
     * @return AgentInfo
     */
    private @NotNull AgentInfo getAgentInfo(Agent agent) {
        String agentDslJson = mgObsService.downloadObsFile(agent.getDslPath());
        AgentInfo agentInfo = JSON.parseObject(agentDslJson, AgentInfo.class);
        // 检查所下载的dsl中id与传入agent的id是否相等
        // 不等，即为复制情况，复制时dsl为老agent信息，需要更新
        if (!agentInfo.getAgentId().equals(agent.getAgentId())) {
            agentInfo.setAgentId(agent.getAgentId());
            agentInfo.setName(agent.getName());
            agentInfo.setWorkspaceId(agent.getWorkspaceId());
            // dslPath更新
            String agentInfoJson = JsonUtils.serializeWithFallback(agentInfo, log,
                "AgentInfo for obs upload, agentId: " + agent.getAgentId());
            String mergedJson = JsonUtils.mergeDslData(agentInfoJson, agentDslJson, log,
                "DSL merge for agentId: " + agent.getAgentId());
            String dslVersionPath = mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId(),
                CommonConstant.AGENT, mergedJson, CommonConstant.DSL_STR);
            agent.setDslPath(dslVersionPath);
        }

        return agentInfo;
    }

    @Override
    public AgentInfo retrieveAgentApp(String projectId, String agentId, String workspaceId) {
        AgentVersion onlineAgent = agentVersionMapper.selectOnlineVersion(agentId);
        if (onlineAgent == null) {
            log.error("online agent does not exist, projectId = {}, agentId = {}", projectId, agentId);
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        String agentDslJson = mgObsService.downloadObsFile(onlineAgent.getDslPath());
        AgentInfo agentInfo = JSON.parseObject(agentDslJson, AgentInfo.class);

        // 转换标签名称
        App app = appMapper.selectByResourceId(agentId);
        List<Tag> tagList = tagMapper.select();
        List<String> tags = tagList.stream()
            .filter(tag -> app.getTags().contains(tag.getTagId()))
            .map(Tag::getNameEn)
            .toList();
        List<String> tagsInfo = new ArrayList<>();
        Locale locale = LanguageUtils.getLanguageLocale();
        for (String tag : tags) {
            String key = "app.tag." + tag;
            tagsInfo.add(messageSource.getMessage(key, null, locale));
        }
        agentInfo.setTags(tags);
        agentInfo.setCreator(messageSource.getMessage("agent-app.creator.official", null, locale));

        int freeTrialUsageQuota = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(agentId,
            RequestContextUtils.getRequestUserDomainId());
        FreeTrialQuota freeTrialQuota = new FreeTrialQuota();
        freeTrialQuota.setLimit(assetAppFreeTrialQuotaLimit);
        freeTrialQuota.setUsage(freeTrialUsageQuota);
        agentInfo.setFreeTrialQuota(freeTrialQuota);
        return agentInfo;
    }

    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "发布智能体",
        resourceId = "agentId",
        resourceName = ""
    )
    public AgentInfo publishAgent(String projectId, String agentId, String workspaceId, List<String> tags) {
        Agent agent = getAgent(projectId, workspaceId, agentId);

        // 查询agent是否有历史在线版本，如果有将历史版本下线
        AgentVersion onlineVersion = agentVersionMapper.selectOnlineVersion(agentId);
        if (!Objects.isNull(onlineVersion)) {
            agentVersionMapper.updateAgentVersionStatus(false, onlineVersion.getVersionId());
        }

        // 创建一个新的AgentVersion对象，用于记录当前发布agent的版本信息，同时上传一个新的发布态IR文件
        AgentVersion agentVersion = new AgentVersion(agent);
        agentVersion.setTags(tags);
        Map<String, Object> metadata = agentImportExportService.parseMetadata(agent);
        Map<String, Object> irInfo = irAdapterService.adaptAgent(agent, metadata);
        String irPath = mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId() + "_published",
            CommonConstant.AGENT, JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue),
            CommonConstant.Workflow.IR);
        agentVersion.setIrPath(irPath);

        // 创建一个新的发布态DSL文件，保存应用元数据快照
        AgentInfo agentInfo = retrieveAgent(projectId, agentId, workspaceId);
        String dslVersionPath;
        if (StringUtils.isNotBlank(agent.getDslPath()) && CommonConstant.DEEPRESEARCH_TYPE.equals(agent.getSubType())) {
            // 如果有dsl 直接从dsl返回
            String agentJson = mgObsService.downloadObsFile(agent.getDslPath());
            dslVersionPath = mgObsService.uploadObsFile(agentId, agentId + "_published", CommonConstant.AGENT,
                agentJson, CommonConstant.DSL_STR);
        } else {
            String jsonContent = JsonUtils.serializeWithFallback(agentInfo, log,
                "AgentInfo for obs upload, agentId: " + agentId);
            dslVersionPath = mgObsService.uploadObsFile(agentId, agentId + "_published", CommonConstant.AGENT,
                jsonContent, CommonConstant.DSL_STR);
        }
        agentVersion.setDslPath(dslVersionPath);
        agentVersionMapper.insert(agentVersion);

        // 删除老的App，创建一个新的App对象，记录agent发布的应用信息
        appMapper.deleteByResourceId(agentId, projectId, workspaceId);
        App app = new App(agent);
        app.setTags(tags);
        if (Objects.equals(projectId, opSvcProjectId)) {
            app.setCreator(CommonConstant.DEFAULT_USERNAME);
        }
        appMapper.insert(app);
        return agent.convertToDto();
    }

    /**
     * 上传Agent DeepResearch写作模板
     *
     * @param projectId 项目ID
     * @param workspaceId 工作空间ID
     * @param file 上传的文件
     * @param agentId Agent ID
     * @return 文件上传响应
     */
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "上传写作模板",
        resourceId = "agentId",
        resourceName = ""
    )
    public FileUploadRsp uploadDeepResearchTemplate(String projectId, String agentId, String workspaceId,
        MultipartFile file) {

        // 参数校验
        if (StringUtils.isEmpty(projectId)) {
            throw new AgentStudioException(StudioError.PROJECT_ID_INVALID);
        }
        if (StringUtils.isEmpty(workspaceId)) {
            throw new AgentStudioException(StudioError.WORKSPACE_ID_INVALID);
        }
        if (file == null || file.isEmpty()) {
            throw new AgentStudioException(StudioError.FILE_CANNOT_BE_EMPTY);
        }
        if (StringUtils.isEmpty(agentId)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION);
        }

        // 校验文件类型是否为支持的DeepResearch写作模板类型
        validateDeepResearchTemplateFile(file);

        String originalFileName = file.getOriginalFilename();

        try {
            // 构建上传路径
            String uploadPath = String.format("%s/%s/%s/%s", CommonConstant.AGENT, CommonConstant.WRITING_TEMPLATE,
                agentId, originalFileName);
            InputStream inputStream = file.getInputStream();
            String objectName = mgObsService.uploadObsFile(uploadPath, inputStream, -1);
            // 设置返回响应体Url和Headers参数
            FileUploadRsp uploadRsp = new FileUploadRsp();
            uploadRsp.setFileName(originalFileName);
            uploadRsp.setUrl(objectName);
            return uploadRsp;
        } catch (IOException e) {
            log.error("Upload DeepResearch template to obs failed. AgentId: {}, FileName: {}", agentId,
                file.getOriginalFilename(), e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }
    }

    /**
     * 校验DeepResearch写作模板文件
     *
     * @param file 上传的文件
     */
    private void validateDeepResearchTemplateFile(MultipartFile file) {
        String originalFilename = file.getOriginalFilename();
        if (StringUtils.isEmpty(originalFilename)) {
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        // 检查文件扩展名
        String fileExtension = getFileExtension(originalFilename);
        if (!DEEP_RESEARCH_TEMPLATE_TYPES.contains(fileExtension.toLowerCase(Locale.ROOT))) {
            log.error("Unsupported DeepResearch template file type: {}. Supported types: {}", fileExtension,
                DEEP_RESEARCH_TEMPLATE_TYPES);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_TYPE);
        }

        // 检查文件大小（限制为10MB）
        long maxSize = 10L * 1024 * 1024; // 10MB
        if (file.getSize() > maxSize) {
            log.error("DeepResearch template file size exceeds limit. Size: {}, Limit: {}", file.getSize(), maxSize);
            throw new AgentStudioException(StudioError.FILE_SIZE_EXCEED_LIMIT);
        }

        // 检查文件内容是否为空
        try {
            if (file.getBytes().length == 0) {
                throw new AgentStudioException(StudioError.ILLEGAL_FILE);
            }
        } catch (IOException e) {
            log.error("Failed to read file bytes for validation", e);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }
    }

    /**
     * 获取文件扩展名
     *
     * @param filename 文件名
     * @return 扩展名（不含点）
     */
    private String getFileExtension(String filename) {
        if (StringUtils.isEmpty(filename)) {
            return "";
        }

        int lastDotIndex = filename.lastIndexOf('.');
        if (lastDotIndex > 0 && lastDotIndex < filename.length() - 1) {
            return filename.substring(lastDotIndex + 1).toLowerCase(Locale.ROOT);
        }
        return "";
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "创建智能体版本",
        resourceId = "agentId",
        resourceName = ""
    )
    public Void createAgentVersion(String projectId, String agentId, String workspaceId,
        CreateVersionReq createVersionReq) {
        // 校验发布版本数量
        List<ReleaseVersion> releaseVersionList = releaseVersionMapper.selectByAppId(agentId);
        if (releaseVersionList.size() > releaseMaxSize) {
            throw new AgentStudioException(StudioError.RELEASE_VERSION_SIZE_EXCEED_LIMIT);
        }

        Set<String> existedVersionNameSet = releaseVersionList.stream()
            .map(ReleaseVersion::getVersionName)
            .collect(Collectors.toSet());

        if (existedVersionNameSet.contains(createVersionReq.getVersionName())) {
            log.error("the version name of agent {} already existed.", agentId);
            throw new AgentStudioException(StudioError.VERSION_NAME_ALREADY_EXISTED);
        }

        AgentInfo agentInfo = retrieveAgent(projectId, agentId, workspaceId);
        Agent agent = getAgent(projectId, workspaceId, agentId);
        ReleaseVersion releaseVersion = new ReleaseVersion();
        String versionId = String.valueOf(System.currentTimeMillis());

        AgentType agentType = AgentType.naValueOf(agent.getType());

        // 创建DSL文件的版本快照
        if (Objects.requireNonNull(agentType) == AgentType.CONTROLLER) {
            String dslVersionPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.AGENT,
                CommonConstant.Workflow.FLOW, agentId, agentId + Constants.UNDERLINE_STR + versionId);
            releaseVersion.setDslPath(dslVersionPath);
            mgObsService.copyObsObject(agent.getDslPath(), dslVersionPath);

            String controllerJson = mgObsService.downloadObsFile(agent.getDslPath());
            ControllerVO controllerVO = JSONObject.parseObject(controllerJson, ControllerVO.class);

            if (controllerVO != null && StringUtils.isNotBlank(controllerVO.getEnvironment())) {
                String environmentId = controllerVO.getEnvironment();
                try {
                    this.environmentServiceManagerService.uploadEnvironmentVarToObsFileForController(projectId, agentId,
                        environmentId, workspaceId, versionId);
                } catch (Exception e) {
                    log.error(
                        "Controller version release, environment variable copy writing to obs failed; environment id is {}",
                        environmentId, e);
                }
            }
        } else {
            String dslVersionPath;
            if (StringUtils.isNotBlank(agent.getDslPath()) && CommonConstant.DEEPRESEARCH_TYPE.equals(
                agent.getSubType())) {
                // 如果有dsl 直接从dsl返回
                String agentJson = mgObsService.downloadObsFile(agent.getDslPath());
                dslVersionPath = mgObsService.uploadObsFile(agentId, agentId + "_published", CommonConstant.AGENT,
                    agentJson, CommonConstant.DSL_STR);
            } else {
                String jsonContent = JsonUtils.serializeWithFallback(agentInfo, log,
                    "AgentInfo for obs upload, agentId: " + agentId);
                dslVersionPath = mgObsService.uploadObsFile(agentId, agentId + Constants.UNDERLINE_STR + versionId,
                    CommonConstant.AGENT, jsonContent, CommonConstant.DSL_STR);
            }
            releaseVersion.setDslPath(dslVersionPath);
        }

        // 创建ir文件快照
        String irVersionPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.AGENT, CommonConstant.Workflow.IR,
            agentId, agentId + Constants.UNDERLINE_STR + versionId);
        releaseVersion.setIrPath(irVersionPath);
        updateIrPrompt(agent);
        mgObsService.copyObsObject(agent.getIrPath(), irVersionPath);

        // 创建一个新的releaseVersion对象，用于记录当前发布agent的版本信息
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setVersionId(versionId);
        releaseVersion.setVersionName(createVersionReq.getVersionName());
        releaseVersion.setVersionNote(createVersionReq.getVersionNote());
        releaseVersion.setAppId(agentId);
        releaseVersion.setAppType(CommonConstant.AGENT_TYPE);
        releaseVersion.setStatus("normal");
        releaseVersion.setSubType(agent.getSubType());
        releaseVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersion.setCreatorId(RequestContextUtils.getRequestUserId());
        Date now = new Date(System.currentTimeMillis());
        releaseVersion.setReleasedOn(now);
        releaseVersion.setUpdatedOn(now);
        releaseVersionMapper.insert(releaseVersion);

        boolean isReviewEnabled = false;
        if (agentInfo.getContentReview() != null) {
            Map<String, Object> contentReviewConfigs = JsonUtils.json2Obj(JsonUtils.toJson(agentInfo.getContentReview()), new TypeReference<>() { });
            if (contentReviewConfigs != null && contentReviewConfigs.get(Constants.Workflow.ENABLED) != null) {
                isReviewEnabled = (boolean) contentReviewConfigs.get(Constants.Workflow.ENABLED);
            }
        }

        // 记录最新发布的版本元数据至OBS和Redis
        publishUtils.savePublish(AgentMetadata.builder()
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .projectId(projectId)
            .workspaceId(workspaceId)
            .agentId(releaseVersion.getAppId())
            .versionId(releaseVersion.getVersionId())
            .updatedAt(System.currentTimeMillis())
            .isContentReviewEnable(isReviewEnabled)
            .build(), Constants.LATEST_PUBLISH_VERSION, mgObsService);

        // t_mapping表中增加发布版本和资源的关联信息
        List<MappingEntity> boundKnowledgeMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.REPO_TYPE);
        if (!boundKnowledgeMappings.isEmpty()) {
            // 处理复制agent和knowledgeRepo的关联信息入库
            relationManagementService.createAgentKnowledge(projectId, workspaceId, agentId, versionId,
                boundKnowledgeMappings);
        }

        List<MappingEntity> hasBoundToolList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.TOOL_TYPE);
        if (!hasBoundToolList.isEmpty()) {
            // 处理复制agent和tool的关联信息入库
            relationManagementService.createAgentTool(projectId, workspaceId, agentId, versionId, hasBoundToolList);
        }

        List<MappingEntity> boundWorkflowMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.WORKFLOW_TYPE);
        if (!boundWorkflowMappings.isEmpty()) {
            // 处理复制agent和workflow的关联信息入库
            relationManagementService.createAgentWorkflow(projectId, workspaceId, agentId, versionId,
                boundWorkflowMappings);
        }

        List<MappingEntity> boundMcpMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.MCP_TYPE);
        if (!boundMcpMappings.isEmpty()) {
            // 处理复制agent和mcp server的关联信息入库
            relationManagementService.createAgentMcp(projectId, workspaceId, agentId, versionId, boundMcpMappings);
        }

        List<MappingEntity> boundSkillMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.SKILL_TYPE);
        if (!boundSkillMappings.isEmpty()) {
            // 处理复制agent和skill的关联信息入库
            relationManagementService.createAgentSkill(projectId, workspaceId, agentId, versionId, boundSkillMappings);
        }

        List<MappingEntity> boundModelMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            ResourceTypeEnum.MODEL.toString());
        List<MappingEntity> modelMappings = boundModelMappings.stream()
            .peek(mapping -> mapping.setMappingId(""))
            .toList();
        if (!boundModelMappings.isEmpty()) {
            // 处理复制agent和模型的关联信息入库
            relationManagementService.createAgentModel(projectId, workspaceId, agentId, versionId, modelMappings);
        }

        List<MappingEntity> boundSubControllerMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.CONTROLLER);
        if (!boundSubControllerMappings.isEmpty()) {
            // 处理复制agent和子agent的关联信息入库
            relationManagementService.createAgentSubController(projectId, workspaceId, agentId, versionId,
                boundSubControllerMappings);
        }

        // 发布版本时，将 controller 引用的单智能体（resource_type=agent）草稿 mapping 复制为版本 mapping，
        // 否则版本导出（依赖 t_mapping）查不到单智能体，导致导出包丢失、导入后单智能体缺失
        List<MappingEntity> boundSubAgentMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.AGENT_TYPE);
        if (!boundSubAgentMappings.isEmpty()) {
            relationManagementService.createAgentSubAgent(projectId, workspaceId, agentId, versionId,
                boundSubAgentMappings);
        }

        // 设置agent的状态为已发布
        agent.setStatus(AgentStatus.PUBLISHED.toString());
        agent.setPublishedOn(new Date(System.currentTimeMillis()));
        agentMapper.updateByPrimaryKeySelective(agent);
        return null;
    }

    /**
     * 创建Agent版本
     */
    @Transactional
    @Override
    public Void createAgentVersionV1(String projectId, String agentId, String workspaceId, CreateVersionReq body) {
        return createAgentVersion(projectId, agentId, workspaceId, body);
    }

    /**
     * 更新ir中的提示词，删除不需要的提示词，并保留系统预置提示词
     *
     * @param agent
     */
    private void updateIrPrompt(Agent agent) {
        if (!AgentType.AGENT.getValue().equals(agent.getType()) || CommonConstant.DEEPRESEARCH_TYPE.equals(
            agent.getSubType())) {
            return;
        }
        String instructions = agent.getInstructions();
        String json = mgObsService.downloadObsFile(agent.getIrPath());
        if (!StringUtils.isBlank(json)) {
            JSONObject jsonObject = JSONObject.parseObject(json);
            JSONObject configs = jsonObject.getJSONObject("configs");
            // 获取原始值
            String oldValue = configs.getString("sysPromptTemplate");
            // 要删除的特殊内容
            String updated = removeSection(oldValue, "CitationRules");
            // 更新值
            agent.setInstructions(updated);
        }
        uploadAgentIr(agent);
        // 更新完ir中的instructions后，需要恢复
        agent.setInstructions(instructions);
    }

    private String removeSection(String prompt, String sectionName) {
        String regex = "(?s)===BEGIN " + sectionName + "===.*?===END " + sectionName + "===";
        return prompt.replaceAll(regex, "");
    }

    @Override
    public AgentInfo getAgentVersion(String projectId, String agentId, String versionId,
        GetAgentVersionQo getAgentVersionQo) {
        return getAgentVersionInfo(projectId, agentId, versionId, getAgentVersionQo);
    }

    public AgentInfo getAgentVersionInfo(String projectId, String agentId, String versionId,
        GetAgentVersionQo getAgentVersionQo) {
        Agent agent = getAgent(projectId, getAgentVersionQo.getWorkspaceId(), agentId);
        AgentType agentType = AgentType.naValueOf(agent.getType());
        if (StringUtils.isBlank(versionId)) {
            return agentCommonService.buildComplexAgentInfo(agent);
        }
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), versionId);
        if (releaseVersion == null) {
            throw new AgentStudioException(StudioError.AGENT_VERSION_NOT_EXIST);
        }
        if (Objects.requireNonNull(agentType) == AgentType.CONTROLLER) {
            String controllerJson = mgObsService.downloadObsFile(releaseVersion.getDslPath());
            return agent.convertToDto(JSONObject.parseObject(controllerJson, ControllerVO.class));
        }
        String agentDslJson = mgObsService.downloadObsFile(releaseVersion.getDslPath());
        return JSON.parseObject(agentDslJson, AgentInfo.class)
            .setTriggerList(agent.getTriggerList())
            .setUpdateTime(agent.getUpdatedOn());
    }

    @Override
    public VersionListRsp listAgentVersions(String projectId, String agentId, ListAgentVersionsQo listAgentVersionsQo) {
        Agent agent = getAgent(projectId, listAgentVersionsQo.getWorkspaceId(), agentId);
        List<ReleaseVersion> versionList = releaseVersionMapper.selectByAppId(agentId);
        List<VersionInfo> versionInfoList = versionList.stream().map(ReleaseVersion::convertToInfo).toList();
        VersionListRsp versionListRsp = new VersionListRsp();
        versionListRsp.setCount(versionInfoList.size());
        int size = versionInfoList.size() > releaseMaxSize ? releaseMaxSize : versionInfoList.size();
        versionListRsp.setVersionList(versionInfoList.subList(0, size));
        return versionListRsp;
    }

    /**
     * 获取Agent版本列表
     */
    @Override
    public VersionListRsp listAgentVersionsV1(String projectId, String agentId,
        ListAgentVersionsV1Qo listAgentVersionsV1Qo) {
        ListAgentVersionsQo qo = JSON.parseObject(JSON.toJSONString(listAgentVersionsV1Qo), ListAgentVersionsQo.class);
        return listAgentVersions(projectId, agentId, qo);
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Agent",
        description = "删除智能体版本",
        resourceId = "versionId",
        resourceName = ""
    )
    public CommonDeleteRsp deleteAgentVersion(String projectId, String agentId, String versionId, String workspaceId) {
        Agent agent = getAgent(projectId, workspaceId, agentId);
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), versionId);
        ShareResourceEntity shareResource = shareResourceMapper.selectShareResourceEntityByResourceId(agentId);
        if (ObjectUtils.isNotEmpty(shareResource) && StringUtils.isNotEmpty(shareResource.getVersionList())
            && shareResource.getVersionList().contains(versionId)) {
            log.error("the resource version has been shared,you can't delete it");
            throw new AgentStudioException(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY);
        }
        if (isSoftDelete) {
            mgObsService.softDeleteObsFile(releaseVersion.getDslPath());
            mgObsService.softDeleteObsFile(releaseVersion.getIrPath());

            // 处理Agent版本表，迁移到新的表，旧数据删除
            agentCommonService.softDeleteReleaseVersionById(releaseVersion);
        } else {
            mgObsService.deleteObsFile(releaseVersion.getDslPath());
            mgObsService.deleteObsFile(releaseVersion.getIrPath());
            releaseVersionMapper.deleteByPrimaryKey(releaseVersion.getId());
        }
        // 删除最新发布版本
        publishUtils.deletePublish(releaseVersion.getAppId(), Constants.LATEST_PUBLISH_VERSION, mgObsService);

        // 删除agent版本关联的发布渠道
        List<ReleaseChannel> channelList = releaseChannelMapper.selectByAppIdAndVersionId(agentId, versionId);
        for (ReleaseChannel channel : channelList) {
            deleteAgentChannelUnchecked(projectId, agentId, channel.getId(), workspaceId);
        }

        // 删除agent版本和资源的关联信息
        mappingMapper.deleteBatchByAppId(agentId, versionId, false);

        // 如果版本被全部删除
        List<ReleaseVersion> versionList = releaseVersionMapper.selectByAppId(agentId);
        if (versionList.isEmpty()) {
            // 将应用状态更新为草稿状态
            agent.setStatus(AgentStatus.DRAFT.toString());
            agentMapper.updateByPrimaryKeySelective(agent);
        } else {
            // 取现存最新的版本，作为最新发布版本保存
            ReleaseVersion latestReleaseVersion = versionList.stream()
                .max(Comparator.comparing(ReleaseVersion::getVersionId))
                .get();
            String agentIr = mgObsService.getObject(latestReleaseVersion.getIrPath());
            // 从IR获取内容审核开关
            Optional<JSONObject> jsonObject = Optional.ofNullable(JSON.parseObject(agentIr));
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
                .build(), Constants.LATEST_PUBLISH_VERSION, mgObsService);
        }

        return new CommonDeleteRsp().setId(versionId);
    }

    /**
     * 删除版本时，同步删除发布渠道，不校验发布渠道类型,防止Obs软删除后，数据库未删
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param channelId channelId
     * @param workspaceId workspaceId
     * @return null
     */
    public void deleteAgentChannelUnchecked(String projectId, String agentId, String channelId, String workspaceId) {

        ReleaseChannel channel =
            releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, agentId, projectId, workspaceId);

        if (channel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            appMapper.deleteByResourceId(agentId, projectId, workspaceId);
        }
        releaseChannelMapper.deleteByPrimaryKeyAndWorkspaceId(channelId, projectId, workspaceId);

        // 同步删除agent-runtime应用发布信息
        deleteAgentChannelInRuntime(projectId, channel);
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Agent",
        description = "创建发布渠道",
        resourceId = "agentId",
        resourceName = ""
    )
    public VersionChannelInfo createAgentChannel(String projectId, String agentId, String workspaceId,
        CreateChannelReq createChannelReq) {
        log.debug("Entering createAgentChannel with projectId={}, agentId={}, workspaceId={}, body={}", projectId,
            agentId, workspaceId, createChannelReq);

        // 校验Agent是否存在
        Agent agent = getAgent(projectId, workspaceId, agentId);

        ReleaseChannel newReleaseChannel = new ReleaseChannel();
        newReleaseChannel.setCreator(RequestContextUtils.getRequestUserName());
        newReleaseChannel.setCreatorId(RequestContextUtils.getRequestUserId());
        log.debug("Initialized releaseChannel with creator={}, creatorId={}", newReleaseChannel.getCreator(),
            newReleaseChannel.getCreatorId());

        String channelType = createChannelReq.getChannelType();
        switch (channelType) {
            case CommonConstant.WEB_PAGE_CHANNEL, CommonConstant.CLOUD_STORE_CHANNEL -> {
                String shortCode = StrUtils.generateShortUuid();
                newReleaseChannel.setShortCode(shortCode);
                newReleaseChannel.setEntryPoint(webpageEndpoint + shortCode);
                newReleaseChannel.setVisibilityScope(String.valueOf(createChannelReq.getVisibilityScope()));
                newReleaseChannel.setCallCount(createChannelReq.getCallCount());
                // 设置sub_type
                if (agent.getSubType() != null) {
                    newReleaseChannel.setSubType(agent.getSubType());
                }
            }
            case CommonConstant.APP_STORE_CHANNEL -> {
                if (!publishAppEnable) {
                    // 百宝箱发布通道类型不支持
                    log.error("the Appstore channel not supported, agentId: {}.", agentId);
                    throw new AgentStudioException(StudioError.AGENT_CHANNEL_TYPE_INCORRECT);
                }
                String domainProjectId = RequestContextUtils.getRequestProjectId();
                if (domainProjectId != null && domainProjectId.equals(opSvcProjectId)) {
                    List<Object> tagList = createChannelReq.getMetadata() == null
                        ? new ArrayList<>()
                        : JSON.parseArray(
                            JSON.toJSONString(createChannelReq.getMetadata(), JSONWriter.Feature.WriteMapNullValue));
                    newReleaseChannel.setMetadata(tagList.toString());

                    // 设置sub_type
                    if (agent.getSubType() != null) {
                        newReleaseChannel.setSubType(agent.getSubType());
                    }

                    // 兼容老的百宝箱发布逻辑
                    publishAgent(projectId, agentId, workspaceId, tagList.stream().map(Object::toString).toList());
                } else {
                    throw new AgentStudioException(StudioError.OP_ACCOUNT_ONLY_ALLOWED_TO_PUBLISH);
                }
            }
            case CommonConstant.AGENT_BUILDER -> {
                Agent agentInfo = getAgent(projectId, workspaceId, agentId);
                newReleaseChannel.setId(agentId);
                newReleaseChannel.setProjectId(projectId);
                newReleaseChannel.setWorkspaceId(workspaceId);
                newReleaseChannel.setAppType(agentInfo.getType());
                newReleaseChannel.setSubType(agentInfo.getSubType());
                newReleaseChannel.setReleasedOn(new Date(System.currentTimeMillis()));
                newReleaseChannel.setAppId(agentId);
                newReleaseChannel.setStatus("released");
                newReleaseChannel.setChannelType(channelType);
                agentSpaceService.publish(newReleaseChannel);
                return newReleaseChannel.convertToInfo();
            }
            default -> {
                // 发布通道类型不存在
                log.error("the channel type {} is incorrect.", channelType);
                throw new AgentStudioException(StudioError.AGENT_CHANNEL_TYPE_INCORRECT);
            }
        }
        String channelId = UUID.randomUUID().toString();
        ReleaseChannel oldChannel = releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(agentId, channelType,
            projectId, workspaceId);
        log.debug("Checked for existing release channel: {}", oldChannel != null ? "Found" : "Not found");

        if (oldChannel != null) {
            // 检查发布通道是否已存在，已存在则表示重新生成，更新通道记录
            channelId = oldChannel.getId();
            newReleaseChannel.setId(channelId);
            if (oldChannel.getReleasedOn() == null) {
                newReleaseChannel.setReleasedOn(new Date(System.currentTimeMillis()));
            }
            newReleaseChannel.setVersionId(createChannelReq.getVersionId());
            newReleaseChannel.setVisibilityScope(createChannelReq.getVisibilityScope().toString());
            newReleaseChannel.setCallCount(createChannelReq.getCallCount());
            newReleaseChannel.setWorkspaceId(workspaceId);
            releaseChannelMapper.updateByPrimaryKeySelective(newReleaseChannel);

            // 如果发布渠道为网页或云商店，更新通道记录需要先同步删除agent-runtime的发布信息（以老的shortCode为key）
            String releaseId = oldChannel.getShortCode();
            if (oldChannel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL) || oldChannel.getChannelType()
                .equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
                agentRuntimeClient.deleteReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseId,
                    oldChannel.getChannelType(), oldChannel.getVersionId());
            }
        } else {
            // 通道不存在则新建
            newReleaseChannel.setId(channelId);
            newReleaseChannel.setProjectId(projectId);
            newReleaseChannel.setWorkspaceId(workspaceId);
            newReleaseChannel.setAppId(agentId);
            newReleaseChannel.setAppType(CommonConstant.AGENT_TYPE);
            newReleaseChannel.setVersionId(createChannelReq.getVersionId());
            newReleaseChannel.setChannelType(channelType);
            newReleaseChannel.setStatus("released");
            ReleaseVersion version = releaseVersionMapper.selectByAppIdAndVersionId(agentId,
                createChannelReq.getVersionId());
            newReleaseChannel.setVersionName(version.getVersionName());
            newReleaseChannel.setReleasedOn(new Date(System.currentTimeMillis()));
            releaseChannelMapper.insert(newReleaseChannel);
        }

        // 将应用发布信息同步agent-runtime
        newReleaseChannel = releaseChannelMapper.selectByPrimaryKey(channelId);
        ReleaseInfo release = new ReleaseInfo();
        release.setAppId(newReleaseChannel.getAppId());
        release.setProjectId(projectId);
        release.setWorkspaceId(workspaceId);
        release.setAppType(newReleaseChannel.getAppType());
        release.setVersionId(newReleaseChannel.getVersionId());
        release.setChannelType(newReleaseChannel.getChannelType());
        release.setShortCode(newReleaseChannel.getShortCode());
        release.setVisibilityScope(newReleaseChannel.getVisibilityScope());
        release.setCallCount(newReleaseChannel.getCallCount());
        log.debug("Prepared releaseInfo for agent-runtime: {}", release);

        agentRuntimeClient.createReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, release);

        return newReleaseChannel.convertToInfo();
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "Agent",
        description = "删除发布渠道",
        resourceId = "channelId",
        resourceName = ""
    )
    public Void deleteAgentChannel(String projectId, String agentId, String channelId, String workspaceId) {
        // 发布到agent-builder空间，agentId和channelId相同
        if (publishAgentBuilderEnable && agentId.equals(channelId)) {
            agentSpaceService.unpublish(workspaceId, agentId);
            return null;
        }

        ReleaseChannel channel = releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, agentId, projectId,
            workspaceId);

        // 校验存在性
        if (ObjectUtils.isEmpty(channel)) {
            throw new AgentStudioException(StudioError.AGENT_PUBLISH_CHANNEL_NOT_EXIST);
        }
        // 校验渠道类型
        // 当前页面仅应用百宝箱渠道和AgentBuilder渠道支持删除
        if (!channel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL) && !channel.getChannelType()
            .equals(CommonConstant.AGENT_BUILDER)) {
            throw new AgentStudioException(StudioError.AGENT_CHANNEL_NOT_SUPPORT_DELETE);
        }

        if (channel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            appMapper.deleteByResourceId(agentId, projectId, workspaceId);
        }
        releaseChannelMapper.deleteByPrimaryKeyAndWorkspaceId(channelId, projectId, workspaceId);

        // 同步删除agent-runtime应用发布信息
        deleteAgentChannelInRuntime(projectId, channel);
        return null;
    }

    private void deleteAgentChannelInRuntime(String projectId, ReleaseChannel channel) {

        String releaseId = null;
        if (channel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL) || channel.getChannelType()
            .equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
            releaseId = channel.getShortCode();
        } else if (channel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            releaseId = channel.getAppId();
        }

        agentRuntimeClient.deleteReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseId,
            channel.getChannelType(), channel.getVersionId());
    }

    @Override
    public VersionChannelListRsp listAgentChannels(String projectId, String agentId,
        ListAgentChannelsQo listAgentChannelsQo) {
        VersionChannelListRsp channelListRsp = new VersionChannelListRsp();
        List<ReleaseChannel> releaseChannelList = releaseChannelMapper.selectByAppIdAndWorkspaceId(agentId, projectId,
            listAgentChannelsQo.getWorkspaceId());
        // 查询agent-builder空间发布
        if (publishAgentBuilderEnable) {
            getAgent(projectId, listAgentChannelsQo.getWorkspaceId(), agentId);
            ReleaseChannel agentBuilderChannel = agentSpaceService.publishQuery(listAgentChannelsQo.getWorkspaceId(),
                agentId);
            if (agentBuilderChannel != null) {
                agentBuilderChannel.setAppType(CommonConstant.AGENT_TYPE);
                releaseChannelList.add(agentBuilderChannel);
            }
        }
        List<VersionChannelInfo> channelInfoList = releaseChannelList.stream()
            .map(ReleaseChannel::convertToInfo)
            .toList();
        channelListRsp.setCount(channelInfoList.size());
        channelListRsp.setChannelList(channelInfoList);

        // 获取应用的最新发布版本
        VersionListRsp versionListRsp = listAgentVersions(projectId, agentId,
            new ListAgentVersionsQo().setWorkspaceId(listAgentChannelsQo.getWorkspaceId()));
        if (!versionListRsp.getVersionList().isEmpty()) {
            channelListRsp.setLatestVersionId(versionListRsp.getVersionList().get(0).getVersionId());
        }
        return channelListRsp;
    }

    @Override
    public AgentVersionListRsp listAgentLastVersions(String projectId,
        ListAgentLastVersionsQo listAgentLastVersionsQo) {
        listAgentLastVersionsQo.setName(StrUtils.filterSpecialWords(listAgentLastVersionsQo.getName()));
        PageHelper.offsetPage(listAgentLastVersionsQo.getOffset(), listAgentLastVersionsQo.getLimit());
        SearchCriteria filter = new SearchCriteria().setId(listAgentLastVersionsQo.getId())
            .setName(listAgentLastVersionsQo.getName())
            .setType(listAgentLastVersionsQo.getType())
            .setSubType(listAgentLastVersionsQo.getSubType())
            .setWorkspaceId(listAgentLastVersionsQo.getWorkspaceId());
        List<AgentVersionListItem> agentLastVersionList = agentMapper.getAgentLastVersionBySearchCriteria(projectId,
            filter);
        PageInfo<AgentVersionListItem> agentVersionPageInfo = new PageInfo<>(agentLastVersionList);
        AgentVersionListRsp resp = new AgentVersionListRsp();
        resp.setCount(agentVersionPageInfo.getTotal());
        resp.setAgentVersionList(agentLastVersionList);
        return resp;
    }

    @Transactional
    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "Agent",
        description = "修改发布渠道",
        resourceId = "channelId",
        resourceName = ""
    )
    public VersionChannelInfo modifyAgentChannel(String projectId, String agentId, String channelId, String workspaceId,
        ModifyChannelReq body) {
        ReleaseChannel oldChannel = releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, agentId, projectId,
            workspaceId);
        if (ObjectUtils.isEmpty(oldChannel)) {
            throw new AgentStudioException(StudioError.AGENT_PUBLISH_CHANNEL_NOT_EXIST);
        }
        ReleaseChannel newChannel = new ReleaseChannel();
        newChannel.setId(oldChannel.getId());
        newChannel.setVersionId(body.getVersionId());
        newChannel.setVisibilityScope(body.getVisibilityScope().toString());
        newChannel.setCallCount(body.getCallCount());
        ReleaseVersion version = releaseVersionMapper.selectByAppIdAndVersionId(agentId, body.getVersionId());
        newChannel.setVersionName(version.getVersionName());
        // 更新subType
        if (version.getSubType() != null) {
            newChannel.setSubType(version.getSubType());
        }
        newChannel.setCreatorId(RequestContextUtils.getRequestUserId());
        newChannel.setWorkspaceId(workspaceId);
        releaseChannelMapper.updateByPrimaryKeySelective(newChannel);
        ReleaseChannel channel = releaseChannelMapper.selectByPrimaryKey(channelId);

        // 同步更新agent-runtime应用发布信息
        String releaseId = null;
        if (oldChannel.getChannelType().equals(CommonConstant.WEB_PAGE_CHANNEL) || oldChannel.getChannelType()
            .equals(CommonConstant.CLOUD_STORE_CHANNEL)) {
            releaseId = oldChannel.getShortCode();
        } else if (oldChannel.getChannelType().equals(CommonConstant.APP_STORE_CHANNEL)) {
            // 兼容老的百宝箱发布逻辑，修改百宝箱应用版本
            String[] strArray = JsonUtils.json2ObjQuietly(oldChannel.getMetadata(), String[].class);
            publishAgent(projectId, agentId, workspaceId, Arrays.stream(Objects.requireNonNull(strArray)).toList());
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
        releaseInfo.setCallCount(body.getCallCount());
        releaseInfo.setVisibilityScope(body.getVisibilityScope().toString());
        log.debug("Prepared Updated releaseInfo for agent-runtime: {}", releaseInfo);

        agentRuntimeClient.createReleaseInfo(RequestContextUtils.getRequestAuthToken(), projectId, releaseInfo);
        return channel.convertToInfo();
    }

    @Override
    public AutoAddResultJsonObject generateAgentPrologue(String projectId, String agentId, String workspaceId) {
        Agent agentInfo = getAgent(projectId, workspaceId, agentId);

        // 若用户未设置应用名称，则设置默认应用名称
        if (StringUtils.isBlank(agentInfo.getName())) {
            agentInfo.setName(CommonConstant.AGENT_NAME_DEFAULT);
        }

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(
            isChinese ? PromptPath.PROLOGUE_PROMPT : PromptPath.PROLOGUE_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, agentInfo.getName()),
            KV.of(CommonConstant.DESCRIPTION, agentInfo.getDescription()));
        String modelDeploymentId = agentInfo.getModelDeploymentId();
        String modelType = agentInfo.getModelType();
        ModelConfig config = agentInfo.getModelConfig();
        return aiGenService.generatePrologue(modelDeploymentId, modelType, agentInfo.getModel(), config, query,
            workspaceId);
    }

    @Override
    public AgentApplicationListRsp getAgentApplications(String projectId, ApplicationListReq body) {
        // 数据库查询
        PageHelper.offsetPage(body.getOffset(), body.getLimit());
        List<AgentApplicationInfo> agentInfoList = agentMapper.selectByProjectIdAndSearchKey(projectId, body.getIds(),
            body.getName(), body.getStatus(), body.getType(), body.getWorkspaceId());

        // 所属空间名称
        if (CollectionUtils.isNotEmpty(agentInfoList)) {
            List<String> workspaceIds = agentInfoList.stream().map(AgentApplicationInfo::getWorkspaceId).toList();
            List<WorkspaceEntity> workspaces = workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(projectId,
                workspaceIds, null);
            Map<String, String> workSpaceIdName = workspaces.stream()
                .collect(Collectors.toMap(WorkspaceEntity::getId, WorkspaceEntity::getName));
            agentInfoList.forEach(agentApplicationInfo -> {
                agentApplicationInfo.setWorkspaceName(
                    workSpaceIdName.getOrDefault(agentApplicationInfo.getWorkspaceId(), StringUtils.EMPTY));
            });
        }

        // 分页数据
        PageInfo<AgentApplicationInfo> agentPageInfo = new PageInfo<>(agentInfoList);
        PageInfo<AgentApplicationInfo> agentInfoPageInfo = new PageInfo<>();
        agentInfoPageInfo.setList(agentInfoList);

        // 构造返回结果
        AgentApplicationListRsp resp = new AgentApplicationListRsp();
        resp.setAgentList(agentInfoList);
        resp.setCount(agentPageInfo.getTotal());
        return resp;
    }

    @Override
    public AutoAddResultJsonObject generateAgentDescription(String projectId, String agentId, String workspaceId) {
        Agent agentInfo = getAgent(projectId, workspaceId, agentId);
        // 若用户未设置应用名称，则设置默认应用名称
        if (StringUtils.isBlank(agentInfo.getName())) {
            agentInfo.setName(CommonConstant.AGENT_NAME_DEFAULT);
        }

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(
            isChinese ? PromptPath.DESCRIPTION_PROMPT : PromptPath.DESCRIPTION_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, agentInfo.getName()));
        String modelDeploymentId = agentInfo.getModelDeploymentId();
        String modelType = agentInfo.getModelType();
        ModelConfig config = agentInfo.getModelConfig();
        return generateDescription(modelDeploymentId, modelType, agentInfo.getModel(), config, query, workspaceId);
    }

    @Override
    public AutoAddResultJsonObject generateAgentIcons(String projectId, String workspaceId, CreateAgentReq body) {
        // 校验name和description是否为空
        if (StringUtils.isBlank(body.getName()) || StringUtils.isBlank(body.getDescription())) {
            throw new AgentStudioException(StudioError.MISSING_REQUIRED_PARAMETERS);
        }

        // 构造提示词
        boolean isChinese = LanguageUtils.isChinese();
        String template =
            CommonUtil.getResourceContent(isChinese ? PromptPath.ICON_PROMPT : PromptPath.ICON_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, body.getName()),
            KV.of(CommonConstant.DESCRIPTION, body.getDescription()));

        // 构造请求
        ImageGenerationRequest imageGenerationRequest = new ImageGenerationRequest();
        imageGenerationRequest.setPrompt(query);
        imageGenerationRequest.setModel(QWEN_IMAGE);
        imageGenerationRequest.setSize(SIZE);

        ResponseEntity<String> response;
        String key = Constants.Header.AUTHORIZATION_PREFIX + authorization;
        try {
            response = maasModelClient.generateImage(key, imageGenerationRequest);
        } catch (Exception e) {
            log.error("Failed to generate icon using the model.", e);
            throw new AgentStudioException(StudioError.GENERATE_ICON_FAILED);
        }

        // 处理响应
        if (response.getStatusCode() != HttpStatus.OK || StringUtils.isBlank(response.getBody())) {
            log.error("Failed to generate icon using the model. StatusCode: {}, ResponseBody: {}", response.getStatusCode(),
                response.getBody());
            throw new AgentStudioException(StudioError.GENERATE_ICON_FAILED);
        }

        try {
            JSONObject imageGenerationResponse = JSON.parseObject(response.getBody());
            JSONArray data = imageGenerationResponse.getJSONArray("data");
            if (data == null || data.isEmpty()) {
                log.error("Failed to generate icon, the data in response is null!");
                throw new AgentStudioException(StudioError.GENERATE_ICON_FAILED);
            }
            // 原始响应图片
            String b64Json = data.getObject(0, ImageGenerationResponse.ImageData.class).getB64Json();
            // 1. 将512*512像素压缩到128*128
            String b64JsonCompressed = ImageBase64Utils.resizeBase64Image(b64Json, 128, 128);
            // 2、上传OBS
            String iconName = UUID.randomUUID() + PNG;
            byte[] imageBytes = Base64.getDecoder().decode(b64JsonCompressed.substring(b64JsonCompressed.indexOf(',') + 1));
            String objectKey = String.format("%s/%s", AVATAR_FOLDER, iconName);
            mgObsService.uploadObsFile(objectKey, new ByteArrayInputStream(imageBytes), 0);
            return new AutoAddResultJsonObject().setIcons(new Icon().setIcon(iconName).setIconDetail(b64JsonCompressed));
        } catch (Exception e) {
            log.error("Error parsing response body: {}", response.getBody(), e);
            throw new AgentStudioException(StudioError.GENERATE_ICON_FAILED);
        }
    }

    @Override
    public AutoAddResultJsonObject generateAgentName(String projectId, String agentId, String workspaceId) {
        Agent agentInfo = getAgent(projectId, workspaceId, agentId);
        // 若用户未设置应用名称，则设置默认应用名称
        if (StringUtils.isBlank(agentInfo.getName())) {
            agentInfo.setName(CommonConstant.AGENT_NAME_DEFAULT);
        }

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(isChinese ? PromptPath.NAME_PROMPT : PromptPath.NAME_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, agentInfo.getName()));
        String modelDeploymentId = agentInfo.getModelDeploymentId();
        String modelType = agentInfo.getModelType();
        ModelConfig config = agentInfo.getModelConfig();
        return generateName(modelDeploymentId, modelType, agentInfo.getModel(), config, query, workspaceId);
    }

    private Map<String, String> getWorkflowModelConfigs(String workflowId) {
        // 获取工作流默认模型配置信息
        WorkflowEntity workflow = workflowMapper.getWorkflowById(workflowId);
        String workflowInfo = mgObsService.downloadObsFile(workflow.getDslPath());
        Map<String, Object> workflowConfigs = JSON.parseObject(workflowInfo, WorkflowVO.class).getConfigs();

        // 历史数据全局配置可能为空
        if (workflowConfigs == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED);
        }
        Object defaultModel = workflowConfigs.get("default_model");
        if (defaultModel == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        Map<String, String> modelConfigs;
        try {
            modelConfigs = new ObjectMapper().convertValue(defaultModel, new TypeReference<Map<String, String>>() { });
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        return modelConfigs;
    }

    public AutoAddResultJsonObject generateDescription(String modelDeploymentId, String modelType, String model,
        ModelConfig config, String query, String workspaceId) {
        // 调用模型并解析返回结果
        String description = null;
        try {
            for (int callCounts = 0; callCounts < CommonConstant.MODEL_CALLS; callCounts++) {
                description = jiuWenService.callModel(
                    agentCommonService.buildAskModelReq(modelDeploymentId, modelType, model, config, query),
                    workspaceId);
                if (!StringUtils.isBlank(description)) {
                    break;
                }
            }
        } catch (Exception e) {
            log.error("Call model failed.", e);
            throw new AgentStudioException(StudioError.CALL_MODEL_ERROR);
        }

        if (StringUtils.isBlank(description)) {

            boolean isChinese = LanguageUtils.isChinese();

            return new AutoAddResultJsonObject().setDescription(
                isChinese ? CommonConstant.DESCRIPTIOPN : CommonConstant.DESCRIPTIOPN_EN);
        }

        // 截取前256个字符
        if (description.length() > 256) {
            description = description.substring(0, 256);
        }
        description = description.trim();
        return new AutoAddResultJsonObject().setDescription(description);
    }

    private AutoAddResultJsonObject generateName(String modelDeploymentId, String modelType, String model,
        ModelConfig config, String query, String workspaceId) {
        // 调用模型并解析返回结果
        String name = null;
        try {
            for (int callCounts = 0; callCounts < CommonConstant.MODEL_CALLS; callCounts++) {
                name = jiuWenService.callModel(
                    agentCommonService.buildAskModelReq(modelDeploymentId, modelType, model, config, query),
                    workspaceId);
                if (!StringUtils.isBlank(name)) {
                    break;
                }
            }
        } catch (Exception e) {
            log.error("Call model failed.", e);
            throw new AgentStudioException(StudioError.CALL_MODEL_ERROR);
        }

        // 去除所有非法字符
        String clean = name.replaceAll(ALLOWED_PATTERN, "");

        // 去除首尾空格
        clean = clean.trim();

        // 应用名称 支持中英文、数字、下划线、中划线和空格，长度 2-64 字符，但不允许以空格开头或结尾
        if (StringUtils.isBlank(clean) || clean.length() < 2) {

            boolean isChinese = LanguageUtils.isChinese();

            return new AutoAddResultJsonObject().setName(
                isChinese ? CommonConstant.AGENT_NAME_DEFAULT : CommonConstant.AGENT_NAME_DEFAULT_EN);
        }

        // 截取前64个字符
        if (clean.length() > 64) {
            clean = clean.substring(0, 64);
        }

        return new AutoAddResultJsonObject().setName(clean);
    }

    @Override
    public Map<String, List<String>> getPermissionsByRole(String projectId, String workspaceId) {
        WorkspaceMemberInfo workspaceMemberInfo = workSpaceMemberService.queryWorkspaceMemberDetail(projectId,
            RequestContextUtils.getRequestUserId(), workspaceId);
        String role = workspaceMemberInfo.getRole();
        List<String> permissions = permissionService.getMergedPermissions().get(role);
        Map<String, List<String>> result = new HashMap<>();
        result.put(role, permissions);
        return result;
    }

    @Override
    public AutoAddResultJsonObject recommendedAgentQuestions(String projectId, String agentId, String workspaceId) {
        Agent agentInfo = getAgent(projectId, workspaceId, agentId);

        // 若用户未设置应用名称，则设置默认应用名称
        if (StringUtils.isBlank(agentInfo.getName())) {
            agentInfo.setName(CommonConstant.AGENT_NAME_DEFAULT);
        }

        // 构造query
        // 根据语言选择prompt模板
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtil.getResourceContent(
            isChinese ? PromptPath.RECOMMENDED_QUESTIONS_PROMPT : PromptPath.RECOMMENDED_QUESTIONS_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(CommonConstant.NAME, agentInfo.getName()),
            KV.of(CommonConstant.DESCRIPTION, agentInfo.getDescription()));
        String modelDeploymentId = agentInfo.getModelDeploymentId();
        String modelType = agentInfo.getModelType();
        ModelConfig config = agentInfo.getModelConfig();
        return aiGenService.recommendedQuestions(modelDeploymentId, modelType, agentInfo.getModel(), config, query,
            workspaceId);
    }

    /**
     * 模型调用异常
     *
     * @param projectId String
     * @param agentId String
     */
    private void modelCallingException(String projectId, String agentId) {
        log.error("Failed to call model. projectId = {}, agentId = {}", projectId, agentId);
        throw new AgentStudioException(StudioError.CALL_MODEL_ERROR);
    }

    /**
     * 解析导入文件
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @return listImportFile 根据文件内容解析出来的配置
     */
    @Override
    public List<ImportListInfo> listImportFile(String workspaceId, String projectId, MultipartFile file, Integer offset,
        Integer limit) {
        if (agentCommonService.isExportFileV2(file)) {
            return agentImportService.checkBeforeImportFile(RequestContextUtils.getRequestWorkspaceId(), projectId,
                file);
        }
        checkImportFile(file);
        List<ImportListInfo> importList = new ArrayList<>();
        int currentOffset = 0;
        try (BufferedReader bufferedReader = new BufferedReader(
            new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;

            // 逐行读取文件中的jsonl配置
            while ((line = bufferedReader.readLine()) != null) {

                // offset行之前不执行解析逻辑
                if (currentOffset < offset) {
                    currentOffset++;
                    continue;
                }
                Map<String, Object> jsonMap = jacksonObjectMapper.readValue(line, new TypeReference<>() { });
                if (!jsonMap.containsKey(CommonConstant.IMPORT_TYPE)) {
                    log.error("Incorrect file format.");
                    throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                }

                // 根据导入类型分类处理导入逻辑
                switch (jsonMap.get(CommonConstant.IMPORT_TYPE).toString()) {
                    case CommonConstant.AGENT:

                        // 校验AgentJson格式
                        AgentExportEntity agentExportEntity = jacksonObjectMapper.convertValue(jsonMap,
                            new TypeReference<>() { });
                        if (agentExportEntity == null) {
                            log.error("Incorrect file format.");
                            throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                        }

                        // 解析文件内容
                        agentImportExportService.resolveAgents(projectId, importList, agentExportEntity);
                        break;
                    case CommonConstant.WORKFLOW:

                        // 校验工作流json格式
                        WorkflowExportEntity workflowExportEntity = jacksonObjectMapper.convertValue(jsonMap,
                            new TypeReference<>() { });
                        if (workflowExportEntity == null) {
                            log.error("Incorrect file format.");
                            throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                        }

                        // 解析文件内容
                        agentImportExportService.resolveWorkflows(projectId, importList, workflowExportEntity);
                        break;
                    case CommonConstant.PLUGIN:

                        // 判断是tool还是plugin
                        String requestInfo = jsonMap.get("metadata").toString();
                        if (requestInfo.contains("basic_info")) {
                            PluginExportEntity plugin = jacksonObjectMapper.convertValue(jsonMap,
                                new TypeReference<>() { });
                            if (plugin == null) {
                                throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                            }
                            agentImportExportService.resolvePlugins(projectId, importList, plugin.getMetadata());
                            break;
                        } else {
                            // 校验插件json格式
                            ToolExportEntity tool = jacksonObjectMapper.convertValue(jsonMap,
                                new TypeReference<>() { });
                            if (tool == null) {
                                throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                            }
                            // 解析文件内容
                            agentImportExportService.resolveTools(projectId, importList, tool.getMetadata());
                            break;
                        }
                    default:
                        // 导入类型有误
                        throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                }
                if (importList.size() >= importMaxLen) {
                    break;
                }
            }
        } catch (Exception e) {
            log.error("listImportFile file:{}, error: {}", i18nUtil.getMessage(StudioError.FILE_RESOLVE_FILE),
                e.getMessage());
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return importList;
    }

    private void checkKnowledgeType(ModifyAgentReq body) {
        // 知识库多选时，允许以下几种情况 1.type都是internal 2.如果有type都是是external时且所有source的knowledge_base_connection_id一致
        if (CollectionUtils.isNotEmpty(body.getKnowledgeRepos())) {
            ListKnowledgeBasesQo knowledgeBasesQo = new ListKnowledgeBasesQo();
            knowledgeBasesQo.setKnowledgeBaseIds(body.getKnowledgeRepos());
            knowledgeBasesQo.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
            List<KnowledgeBaseListItem> knowledgeBaseResponse = knowledgeBaseService.listKnowledgeBaseByShareScope(
                RequestContextUtils.getRequestProjectId(), knowledgeBasesQo).getItems();
            AtomicInteger shareNum = new AtomicInteger();
            knowledgeBaseResponse.forEach(item -> {
                if (KnowledgeBaseListItem.RepoTypeEnum.SHARE.equals(item.getRepoType())) {
                    shareNum.getAndIncrement();
                }
            });
            if (shareNum.get() > 1 && knowledgeBaseResponse.size() > 1) {
                log.error("Number of shared knowledge bases exceeds 1");
                throw new AgentStudioException(StudioError.FREE_KNOWLEDGE_BASE_LIMIT_EXCEEDED);
            }
            HashSet<KnowledgeBaseListItem.TypeEnum> types = new HashSet<>();
            HashSet<String> list = new HashSet<>();
            knowledgeBaseResponse.forEach(item -> {
                types.add(item.getType());
                if (KnowledgeBaseListItem.TypeEnum.EXTERNAL.equals(item.getType())) {
                    ExternalKnowledgeBaseSource source = item.getSource();
                    list.add(source.getKnowledgeBaseConnectionId());
                }
            });
            if (types.size() != 1 || list.size() > 1) {
                log.error("The knowledge base types are inconsistent");
                throw new AgentStudioException(StudioError.KNOWLEDGE_REPO_TYPE_INCONSISTENT);
            }
        }
    }

    /**
     * 插件导出
     *
     * @param projectId projectId
     * @param body 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    @Override
    public Resource exportTools(String projectId, String workspaceId, ExportParams body) {
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        return agentImportExportService.exportTools(projectId, workspaceId, body);
    }

    /**
     * 插件导入
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importIds 需要导入的插件id列表
     * @return ImportRsp 导入请求的响应，包括id、name、description、status
     */
    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Agent",
        description = "导入工具",
        resourceId = "-1",
        resourceName = ""
    )
    public ImportRsp importTools(String workspaceId, String projectId, MultipartFile file, String importIds) {
        checkImportFile(file);
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        return agentImportExportService.importTools(projectId, workspaceId, file, importIds);
    }

    /**
     * 导出Agent
     *
     * @param projectId projectId
     * @param body body 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    @Override
    public Resource exportAgents(String projectId, String workspaceId, ExportParams body) {
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        return agentImportExportService.exportAgents(projectId, workspaceId, body);
    }

    @Override
    public ExportResourceRsp exportResource(String projectId, String workspaceId, ExportResourceParams body) {
        return agentExportService.exportResource(projectId, workspaceId, body);
    }

    /**
     * 导入Agent
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importAgents 需要导入的Agent id
     * @param importTools 需要导入的插件id
     * @param importWorkflows 需要导入的Workflow id
     * @return ImportRsp 导入请求的响应，包括id、name、description、status和dependencies（Agent的依赖）
     */
    @Override
    @OperationLog(
        operationType = OperationType.IMPORT,
        resourceType = "Agent",
        description = "导入智能体",
        resourceId = "-1",
        resourceName = ""
    )
    public ImportRsp importAgents(String workspaceId, String projectId, MultipartFile file, String importAgents,
        String importTools, String importWorkflows, String mode) {
        checkImportFile(file);
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        if (agentCommonService.isExportFileV2(file)) {
            return agentImportService.importFile(projectId, RequestContextUtils.getRequestWorkspaceId(), file, mode);
        }
        return agentImportExportService.importAgents(projectId, file, importAgents, importTools, importWorkflows);
    }

    public List<ImportListInfo> listImportInfoFromJson(String projectId, String resourceStr) {
        List<ImportListInfo> importList = new ArrayList<>();
        try {
            Map<String, Object> jsonMap = jacksonObjectMapper.readValue(resourceStr, new TypeReference<>() { });
            switch (jsonMap.get(CommonConstant.IMPORT_TYPE).toString()) {
                case CommonConstant.AGENT -> {
                    AgentExportEntity agentExportEntity = jacksonObjectMapper.convertValue(jsonMap,
                        new TypeReference<>() { });
                    if (agentExportEntity == null) {
                        throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                    }
                    agentImportExportService.resolveAgents(projectId, importList, agentExportEntity);
                }
                case CommonConstant.WORKFLOW -> {
                    WorkflowExportEntity workflowExportEntity = jacksonObjectMapper.convertValue(jsonMap,
                        new TypeReference<>() { });
                    if (workflowExportEntity == null) {
                        throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                    }
                    agentImportExportService.resolveWorkflows(projectId, importList, workflowExportEntity);
                }
                case CommonConstant.PLUGIN -> {
                    ToolExportEntity tool = jacksonObjectMapper.convertValue(jsonMap, new TypeReference<>() { });
                    if (tool == null) {
                        throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                    }
                    agentImportExportService.resolveTools(projectId, importList, tool.getMetadata());
                }
                default -> {
                    throw new AgentStudioException(StudioError.FILE_FORMAT_INCORRECT);
                }
            }
        } catch (Exception e) {
            log.error("listImportFile file:{}, error: {}", i18nUtil.getMessage(StudioError.FILE_RESOLVE_FILE),
                e.getMessage());
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return importList;
    }

    /**
     * 根据类型获取当前租户所有可见应用中文名称set集合
     *
     * @param projectId projectId
     * @param name 名字
     * @param agentType agent类型
     * @return 中文名合集
     */
    public Set<String> getCurrentNames(String projectId, String name, String agentType) {
        // 获取当前user id下所有应用名称
        SearchCriteria searchCriteria = new SearchCriteria();
        searchCriteria.setName(name);
        searchCriteria.setWorkspaceId(ThreadLocalUtils.getWorkspaceId());
        searchCriteria.setType(agentType);
        return agentMapper.selectByProjectIdAndSearchCriteria(projectId, searchCriteria)
            .stream()
            .map(Agent::getName)
            .collect(Collectors.toSet());
    }

    /**
     * 验证agent名称是否合法
     *
     * @param projectId projectId
     * @param name 中文名
     * @param agentType agent类型
     */
    public String validateName(String projectId, String name, String agentType, boolean generatorName) {
        if (StringUtils.isEmpty(name)) {
            throw createException(agentType);
        }

        Set<String> currentNames = getCurrentNames(projectId, name, agentType);
        if (!currentNames.contains(name)) {
            return name;
        }
        if (!generatorName) {
            throw createException(agentType);
        }
        int times = 0;
        String baseName = name.length() < 60 ? name : name.substring(0, 60);
        while (times < 500) {
            ++times;
            String value = baseName + UUID.randomUUID().toString().substring(0, 4);
            if (!currentNames.contains(value)) {
                return value;
            }
        }
        throw createException(agentType);
    }

    private AgentStudioException createException(String agentType) {
        if (agentType != null && agentType.equalsIgnoreCase(CONTROLLER)) {
            return new AgentStudioException(StudioError.MULTI_AGENT_NAME_CONFLICT);
        }
        return new AgentStudioException(StudioError.AGENT_NAME_INVALID);
    }

    private void checkKnowledgeRetrievePolicy(KnowledgeRetrievePolicy policy) {
        if (Objects.isNull(policy)) {
            return;
        }
        float topK = policy.getTopK();
        if (policy.getRecallThreshold() > knowledgeRecallThresholdMax
            || policy.getRecallThreshold() < knowledgeRecallThresholdMin) {
            throw new AgentStudioException(StudioError.KNOW_RECALL_THRESHOLD_ILLEGAL);
        }
        if (policy.getFaqThreshold() > knowledgeRecallThresholdMax
            || policy.getFaqThreshold() < knowledgeRecallThresholdMin) {
            throw new AgentStudioException(StudioError.FAQ_THRESHOLD_ILLEGAL);
        }
    }

    /**
     * 校验Agent中定义的用户输入参数变量，包括：
     * 列表中变量的key+type不能重复出现
     *
     * @param variables
     */
    private void checkAgentInputVariables(List<InputVariable> variables) {
        if (CollectionUtils.isEmpty(variables)) {
            return;
        }
        Map<String, List<InputVariable>> variableMap = variables.stream()
            .collect(Collectors.groupingBy(
                inputVariable -> String.join(",", inputVariable.getVariableKey(), inputVariable.getInputType())));
        Set<String> duplicateKeys = variableMap.entrySet()
            .stream()
            .filter(item -> item.getValue().size() > 1)
            .map(Map.Entry::getKey)
            .collect(Collectors.toSet());
        if (duplicateKeys.isEmpty()) {
            return;
        }
        log.warn("Agent input variables duplicate:{}", duplicateKeys);
        throw new AgentStudioException(StudioError.AGENT_VARIABLE_DUPLICATE, duplicateKeys);
    }

    /**
     * 校验Agent中定义的变量，包括：
     * 列表中变量的key不能重复出现
     *
     * @param variables
     */
    private void checkAgentVariables(List<AgentVariable> variables) {
        if (CollectionUtils.isEmpty(variables)) {
            return;
        }
        Map<String, List<AgentVariable>> variableMap = variables.stream()
            .collect(Collectors.groupingBy(AgentVariable::getVariableKey));
        Set<String> duplicateKeys = variableMap.entrySet()
            .stream()
            .filter(item -> item.getValue().size() > 1)
            .map(Map.Entry::getKey)
            .collect(Collectors.toSet());
        if (duplicateKeys.isEmpty()) {
            return;
        }
        log.warn("Agent variables duplicate:{}", duplicateKeys);
        throw new AgentStudioException(StudioError.AGENT_VARIABLE_DUPLICATE, duplicateKeys);
    }

    public void checkImportFile(MultipartFile file) {
        FileCommonUtils.validatedFile(file, fileMaxSize * KB, IMPORT_FILE_TYPE);
    }

    public List<AgentBaseInfo> queryAgentList(String agentType, int limit, int offset) {
        return agentMapper.queryAgentList(agentType, limit, offset);
    }

    private List<String> handlePluginId(List<String> toolIds) {
        List<String> result = new ArrayList<>();
        for (String item : toolIds) {
            String[] parts = item.split("#");
            result.add(parts[0]);
        }
        return result;
    }

    private String getPluginId(String toolId) {
        String[] parts = toolId.split("#");
        return parts[0];
    }
}
