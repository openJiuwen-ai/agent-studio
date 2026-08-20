/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.LogUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.bo.FileCheckWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.manager.dto.TagInfo;
import com.openjiuwen.studio.agent.manager.entity.App;
import com.openjiuwen.studio.agent.manager.entity.Tag;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.TagMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

/**
 * 功能描述 公共管理service
 *
 */
@Service
@Slf4j
public class CommonManagementService implements ICommonManagementService {
    private static final String FRONT_CONFIGS_KEY = "front-page.configs";

    private static final String FRONT_DEFAULT_CONFIGS_KEY = "front-page.default-configs";

    private static final String AVATAR_FOLDER = "icon";

    private static final int KB = 1024;

    private final TagMapper tagMapper;

    private final MgObsService mgObsService;

    private final I18nUtil i18nUtil;

    private final AppMapper appMapper;

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    @Value("${agent.max-upload-image-size}")
    private long imageMaxSize;

    @Value("${icon.max-size}")
    private long iconMaxSize;

    @Value("${file.default-type}")
    private String allowedDefaultTypeStr;

    @Value("${file.icon-type}")
    private String allowedIconTypeStr;

    @Value("${file.img-type}")
    private String allowedImgTypeStr;

    @Value("${agent.mcp-bound-limit}")
    private int agentMcpBoundLimit;

    @Value("${workflow.bound.limit}")
    private int agentWorkflowBoundLimit;

    @Value("${op.svc.project-id}")
    private String opProjectId;

    @Value("${knowledge.bound.limit}")
    private int agentKnowledgeBoundLimit;

    @Value("${tool.bound.limit}")
    private int agentToolBoundLimit;

    @Value("${model.public.enable:false}")
    private boolean publicModelEnable;

    @Value("${knowledge.kooSearch.embedding-model}")
    private String kosEmbeddingModel;

    @Value("${knowledge.kooSearch.reRank-model}")
    private String kosReRankModel;

    @Value("${knowledge.lakeSearch.embedding-model}")
    private String mrsEmbeddingModel;

    @Value("${knowledge.lakeSearch.reRank-model}")
    private String mrsReRankModel;

    @Value("${knowledge.share.enabled}")
    private boolean knowledgeShareEnabled;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${knowledge.internal.enabled}")
    private boolean knowledgeInternalEnabled;

    @Value("${knowledge.ocr-enable}")
    private boolean isOcrEnable;

    @Value("${knowledge.recall-threshold.min}")
    private double knowledgeRecallThresholdMin;

    @Value("${knowledge.recall-threshold.max}")
    private double knowledgeRecallThresholdMax;

    @Value("${front-page.block-nodes}")
    private String frontPageBlockNodes;

    @Value("${knowledge.file-type}")
    private String knowledgeFileType;

    @Value("${audio.support-interaction}")
    private Boolean isAudioSupportInteraction;

    @Value("${audio.chinese-timbre}")
    private String audioChineseTimbre;

    @Value("${audio.english-timbre}")
    private String audioEnglishTimbre;

    @Value("${env.type}")
    private String envType;

    @Value("${display.agentops.operations:true}")
    private boolean opsMenuDisplay;

    @Value("${display.safety.barrier:true}")
    private boolean safetyBarrierDisplay;

    @Value("${display.agentops.deploy-whitelist:-}")
    private String deployWhiteLists;

    @Value("${display.agentops.switch-new-ops:false}")
    private boolean agentOpsNewSwitch;

    @Value("${display.agentops.label-all:true}")
    private boolean opsLabelAllDisplay;

    @Value("${display.agentops.evaluation:false}")
    private boolean opsEvaluationDisplay;

    @Value("${agent.long-term-memory-enable}")
    private boolean longTermMemoryEnable;

    @Value("${agent.tooluse.enable:true}")
    private boolean agentToolPriorityEnable;

    @Value("${publish.agent-builder.enable}")
    private boolean publishAgentBuilderEnable;

    @Value("${front-page.code_env_options}")
    private String codeEnvOptions;

    @Value("${front-page.code_def_env}")
    private String codeDefEnv;

    @Value("${model.interface.protocol.his_openai_enable:false}")
    private boolean hisModelProtocolEnable;

    @Value("${space-service-display:false}")
    private boolean spaceServiceDisplay;

    @Value("${apikey.enable:false}")
    private boolean apiKeyEnable;

    @Value("${display.mutilagent.max_iteration:30}")
    private int maxIteration;

    @Value("${display.chat-workflow.async-enable:false}")
    private boolean chatWorkflowAsyncEnable;

    @Value("${display.workflow.async-enable:false}")
    private boolean workflowAsyncEnable;

    @Value("${env.sandbox.enable}")
    private boolean sandboxEnable;

    @Value("${tool.plugin-publish:false}")
    private boolean pluginChoice;

    @Value("${memory.user-profile-enable:false}")
    private boolean userProfileEnable;

    @Value("${memory.repo-enable:false}")
    private boolean memoryRepoEnable;

    @Value("${prompt.contentlenth}")
    private int promptContentLength;

    @Value("${publish.app-store.enable:false}")
    private boolean publishAppEnable;

    @Value("${asset.app.free.trial-quota-limit:10}")
    private int assetAppFreeTrialQuotaLimit;

    @Value("${model.sync-model.maas.region:}")
    private String maasRegion;

    @Value("${model.sync-model.maas.square-page}")
    private String maasSquarePage;

    @Value("${model.platform.nl2agent_recognition_model_id:184}")
    private String nl2agentDefaultModelId;

    @Value("${agent.demo-agent-id:}")
    private String demoAgentId;

    @Value("${workflow.demo-workflow-id:}")
    private String demoWorkflowId;

    @Value("${display.agent.multimodel.enable:false}")
    private boolean agentMultiModelEnable;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Value("${display.show.model.status:false}")
    private boolean displayShowModelStatus;

    @Value("${license-default-display-time:180}")
    private int licenseDefaultDisplayTime;

    @Value("${model.interface.authType.hmac_auth_enabled}")
    private boolean HMACAuthEnabled;

    @Value("${front-page.runtime-host}")
    private String runtimeHost;

    @Value("${front-page.studio-btn-show:true}")
    private boolean studioBtnShow;

    @Value("${common_region_id:}")
    private String regionId;

    @Value("${memory.prompt.user_profile}")
    private String userProfilePrompt;

    @Value("${memory.prompt.semantic_memory}")
    private String semanticMemoryPrompt;

    private Set<String> frontPageBlockNodeList = new HashSet<>();

    private Set<String> allowedIconType = new HashSet<>();

    private Set<String> allowedImgType = new HashSet<>();

    private Set<String> allowedDefaultType = new HashSet<>();

    private List<String> codeEnvOptionsList;

    private Set<String> supportedKnowledgeType = new HashSet<>();

    @PostConstruct
    public void init() {
        if (StringUtils.isNotEmpty(frontPageBlockNodes)) {
            frontPageBlockNodeList = Arrays.stream(frontPageBlockNodes.split(CommonConstant.SEPARATOR))
                .collect(Collectors.toSet());
        }
        if (StringUtils.isNotEmpty(knowledgeFileType)) {
            supportedKnowledgeType = Arrays.stream(knowledgeFileType.split(CommonConstant.SEPARATOR))
                .map(String::toLowerCase)
                .collect(Collectors.toSet());
        }
        allowedIconType = Arrays.stream(allowedIconTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
        allowedImgType = Arrays.stream(allowedImgTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
        allowedDefaultType = Arrays.stream(allowedDefaultTypeStr.split(CommonConstant.SEPARATOR))
            .collect(Collectors.toSet());
        if (StringUtils.isNotEmpty(codeEnvOptions)) {
            codeEnvOptionsList = JSON.parseArray(codeEnvOptions, String.class);
        }
    }

    /**
     * 构造器
     */
    public CommonManagementService(TagMapper tagMapper, MgObsService mgObsService, I18nUtil i18nUtil,
        AppMapper appMapper) {
        this.tagMapper = tagMapper;
        this.mgObsService = mgObsService;
        this.i18nUtil = i18nUtil;
        this.appMapper = appMapper;
    }

    @Override
    public Object systemSettings(String projectId, String service) {
        String configs = SpringBeanUtils.getProperty(FRONT_CONFIGS_KEY, "{}");
        String defConfigs = SpringBeanUtils.getProperty(FRONT_DEFAULT_CONFIGS_KEY, "{}");
        JSONObject configJson = JSONObject.parseObject(configs);
        JSONObject defConfigJsonObject = JSONObject.parseObject(defConfigs);

        // config合并到默认配置，重复则覆盖默认值
        if (configJson != null && !configJson.isEmpty()) {
            for (String key : configJson.keySet()) {
                defConfigJsonObject.put(key, configJson.get(key));
            }
        }

        defConfigJsonObject.put("ocr_enable", isOcrEnable);
        defConfigJsonObject.put("embedding_model_name", getPreSetEmbeddingModel());
        defConfigJsonObject.put("rerank_model_name", getPreSetReRankModel());
        defConfigJsonObject.put("knowledge_source", knowledgeSource);
        defConfigJsonObject.put("share_knowledge_enabled", knowledgeShareEnabled);
        defConfigJsonObject.put("agent_tool_bound_limit", agentToolBoundLimit);
        defConfigJsonObject.put("agent_workflow_bound_limit", agentWorkflowBoundLimit);
        defConfigJsonObject.put("agent_knowledge_bound_limit", agentKnowledgeBoundLimit);
        defConfigJsonObject.put("agent_mcp_bound_limit", agentMcpBoundLimit);
        defConfigJsonObject.put("knowledge_recall_threshold_min", knowledgeRecallThresholdMin);
        defConfigJsonObject.put("knowledge_recall_threshold_max", knowledgeRecallThresholdMax);
        defConfigJsonObject.put("block_nodes", frontPageBlockNodeList);
        defConfigJsonObject.put("audio_support_interaction", isAudioSupportInteraction);
        defConfigJsonObject.put("audio_chinese_timbre", JSON.parseArray(audioChineseTimbre));
        defConfigJsonObject.put("audio_english_timbre", JSON.parseArray(audioEnglishTimbre));
        defConfigJsonObject.put("knowledge_internal_enabled", knowledgeInternalEnabled);
        defConfigJsonObject.put("agentops_menu_display", opsMenuDisplay);
        defConfigJsonObject.put("safety_barrier_display", safetyBarrierDisplay);
        defConfigJsonObject.put("agentops_label_all_display", opsLabelAllDisplay);
        defConfigJsonObject.put("agentops_evaluation_display", opsEvaluationDisplay);
        defConfigJsonObject.put("agentops_deploy_display", isOpsDeployDisplay());
        defConfigJsonObject.put("agent_ops_new", agentOpsNewSwitch);
        defConfigJsonObject.put("public_model_enabled", publicModelEnable); // 是否允许配置公开模型
        defConfigJsonObject.put("long_term_memory_enabled", longTermMemoryEnable); // 是否启用长期记忆
        defConfigJsonObject.put("agent_tool_priority_enable", agentToolPriorityEnable); // 是否开启工具优先
        defConfigJsonObject.put("his_openai_enable", hisModelProtocolEnable); // 是否开启HIS 定制的模型接入能力 鉴权
        defConfigJsonObject.put("apikey_enable", apiKeyEnable); // 是否开启apieky功能
        defConfigJsonObject.put("knowledge_file_types", supportedKnowledgeType);
        defConfigJsonObject.put("prompt_max_length", promptContentLength);
        defConfigJsonObject.put("hmac_auth_enabled", HMACAuthEnabled); // 是否开启HMAC鉴权
        defConfigJsonObject.put("user_profile_prompt", userProfilePrompt); // 用户偏好提示词
        defConfigJsonObject.put("semantic_memory_prompt", semanticMemoryPrompt); // 语义记忆提示词

        // 用于快速入门体验智能体的agentId
        if (StringUtils.isNotBlank(demoAgentId)) {
            defConfigJsonObject.put("demo_agent_id", demoAgentId);
        } else {
            defConfigJsonObject.put("demo_agent_id", getRandomAppId("agent"));
        }

        // 用于快速入门体验工作流的workflowId
        if (StringUtils.isNotBlank(demoWorkflowId)) {
            defConfigJsonObject.put("demo_workflow_id", demoWorkflowId);
        } else {
            defConfigJsonObject.put("demo_workflow_id", getRandomAppId("workflow"));
        }

        // 是否支持发布到agent-builder空间
        defConfigJsonObject.put("publish_agent-builder_enable", publishAgentBuilderEnable);

        // 设置代码节点执行环境选项
        defConfigJsonObject.put("code_env_options", codeEnvOptionsList);
        defConfigJsonObject.put("code_def_env", codeDefEnv);

        defConfigJsonObject.put("mutilagent_max_iteration", maxIteration);
        defConfigJsonObject.put("chat_workflow_async_enable", chatWorkflowAsyncEnable);
        defConfigJsonObject.put("workflow_async_enable", workflowAsyncEnable);

        // 是否支持sandbox执行方式，仅对HC生效
        defConfigJsonObject.put("env_sandbox_enable", sandboxEnable);

        // 是否支持发布到应用百宝箱
        defConfigJsonObject.put("env_publish_app_store_enable", publishAppEnable);
        defConfigJsonObject.put("asset_app_free_trial_quota_limit", assetAppFreeTrialQuotaLimit);

        defConfigJsonObject.put("space_service_display", spaceServiceDisplay);
        defConfigJsonObject.put("plugin_publish_choice", pluginChoice);
        defConfigJsonObject.put("memory_user_profile_enable", userProfileEnable);
        defConfigJsonObject.put("memory_repo_enable", memoryRepoEnable);
        defConfigJsonObject.put("maas_service_region", maasRegion);
        defConfigJsonObject.put("maas_square_page", maasSquarePage);
        defConfigJsonObject.put("nl2agent_recognition_model", nl2agentDefaultModelId);
        defConfigJsonObject.put("agent_multimodel_enable", agentMultiModelEnable);
        defConfigJsonObject.put("platform_provider_id", platformProviderId);
        defConfigJsonObject.put("display_show_model_status", displayShowModelStatus);

        defConfigJsonObject.put("license-default-display-time", licenseDefaultDisplayTime);

        // 非图片文件上传大小上限（单位 KB），供前端聊天附件上传入口统一校验
        defConfigJsonObject.put("file_max_size_kb", fileMaxSize);

        defConfigJsonObject.put("studio_btn_show", studioBtnShow);

        if (StringUtils.isNotEmpty(runtimeHost)) {
            String runtimeApiEndpointPrefix = String.format(runtimeHost,
                RequestContextUtils.getRequestUserDomainId(), regionId);
            // 去除协议前缀，前端拼接时会自行添加https://
            runtimeApiEndpointPrefix = runtimeApiEndpointPrefix.replaceFirst("^https?://", "");
            defConfigJsonObject.put("runtime_api_endpoint_prefix", runtimeApiEndpointPrefix);
        }

        return defConfigJsonObject;
    }

    private boolean isOpsDeployDisplay() {
        boolean opsDeployDisplay;
        if (Strings.CS.equals(deployWhiteLists, "*")) {
            opsDeployDisplay = Boolean.TRUE;
        } else {
            List<String> domainIds = Arrays.stream(deployWhiteLists.split(",")).toList();
            opsDeployDisplay = domainIds.contains(RequestContextUtils.getRequestUserDomainId())
                ? Boolean.TRUE
                : Boolean.FALSE;
        }
        return opsDeployDisplay;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "Avatar",
        description = "上传头像",
        resourceId = "-1",
        resourceName = ""
    )
    public FileUploadRsp uploadAvatar(String projectId, MultipartFile file) {
        // 1、校验头像
        String safeFileName = checkUploadFile(file, CommonConstant.ICON);

        // 2、上传OBS
        try {
            String objectKey = String.format("%s/%s", AVATAR_FOLDER, safeFileName);
            mgObsService.uploadObsFile(objectKey, file.getInputStream(), 0);
        } catch (IOException e) {
            log.error("Upload file to obs failed.", e);
            throw new AgentStudioException(StudioError.UPLOAD_FILE_TO_OBS_FAILED);
        }

        // 3、返回safeName
        return new FileUploadRsp().setFileName(safeFileName);
    }

    /**
     * 查询标签列表
     *
     * @param projectId projectId
     * @return List
     */
    @Override
    public List<TagInfo> listTags(String projectId, String workspaceId) {
        List<Tag> tagList = tagMapper.select();
        return tagList.stream().map(Tag::convertToDto).toList();
    }

    /**
     * 上传文件校验
     *
     * @param file 文件
     * @param type 文件类型
     * @return 新生成的文件名
     */
    private String checkUploadFile(MultipartFile file, String type) {
        // 文件为空
        if (file == null || file.isEmpty()) {
            log.error("The uploaded file cannot be empty.");
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        FileCheckWrapper fileCheckWrapper = buildFileCheckWrapper(type);
        // 校验文件大小
        if (file.getSize() > fileCheckWrapper.getSize() * KB) {
            log.error("The avatar file size exceeds the limit: {}KB", iconMaxSize);
            throw new AgentStudioException(StudioError.PICTURE_FILE_SIZE_EXCEED_LIMIT);
        }

        // 校验文件名
        String fileName = file.getOriginalFilename();
        if (StringUtils.isBlank(fileName) || fileName.contains("..") || fileName.contains("\\") || fileName.contains(
            "/")) {
            log.error("The file name is illegal: {}", LogUtils.encodeForLog(fileName));
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        // 校验文件类型
        String fileType = fileName.substring(fileName.lastIndexOf('.'));
        if (StringUtils.isBlank(fileType) || !fileCheckWrapper.getType().contains(fileType.toLowerCase(Locale.ROOT))) {
            log.error("The file type is not supported: {}", LogUtils.encodeForLog(fileType));
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_TYPE);
        }

        // 生成随机名
        return UUID.randomUUID() + fileType;
    }

    /**
     * 根据校验类型获取文件校验包装类
     *
     * @param type 校验类型
     * @return FileCheckWrapper 文件校验包装类
     */
    private FileCheckWrapper buildFileCheckWrapper(String type) {
        FileCheckWrapper.FileCheckWrapperBuilder builder = FileCheckWrapper.builder();
        return switch (type) {
            case CommonConstant.ICON -> builder.size(iconMaxSize).type(allowedIconType).build();
            case CommonConstant.IMAGE -> builder.size(imageMaxSize).type(allowedImgType).build();
            default -> builder.size(fileMaxSize).type(allowedDefaultType).build();
        };
    }

    private String getPreSetEmbeddingModel() {
        // HCS环境不需要预置模型
        if (CommonConstant.EnvType.HCS.equalsIgnoreCase(envType)) {
            return "";
        }
        return KnowledgeSourceEnum.KOOSEARCH.toString().equalsIgnoreCase(knowledgeSource)
            ? kosEmbeddingModel
            : mrsEmbeddingModel;
    }

    private String getPreSetReRankModel() {
        // HCS环境不需要预置模型
        if (CommonConstant.EnvType.HCS.equalsIgnoreCase(envType)) {
            return "";
        }
        return KnowledgeSourceEnum.KOOSEARCH.toString().equalsIgnoreCase(knowledgeSource)
            ? kosReRankModel
            : mrsReRankModel;
    }

    /**
     * 随机获取一个预置的 app id (根据 resource type）
     */
    private String getRandomAppId(String resourceType) {
        App randomAppInfo = appMapper.selectRandomAppByResourceType(resourceType);
        return randomAppInfo == null ? "" : randomAppInfo.getAppId();
    }
}

