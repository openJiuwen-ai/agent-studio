/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 智能体对象，包含智能体的相关信息。
 */
@ApiModel(description = "智能体对象，包含智能体的相关信息。")

@Validated

public class AgentInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("agent_id")
    @Schema(description = "智能体唯一标识", example = "agent-001", required = true)
    @NotBlank
    private String agentId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目 ID", example = "proj-001")
    private String projectId = null;

    @JsonProperty("name")
    @Schema(description = "智能体名称", example = "智能助手")
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "智能体类型：agent-单智能体，controller-多智能体", example = "agent")
    private String type = null;

    @JsonProperty("sub_type")
    @Schema(description = "智能体子类型", example = "chat")
    private String subType = null;

    @JsonProperty("description")
    @Schema(description = "智能体描述", example = "这是一个智能助手")
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "智能体图标", example = "icon.png")
    private String icon = null;

    @JsonProperty("details")
    @Schema(description = "多智能体控制器配置", example = "{}")
    @Valid
    private ControllerVO details = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "[\"标签1\", \"标签2\"]")
    @Valid
    @Size()
    private List<@Length() String> tags = null;

    @JsonProperty("instructions")
    @Schema(description = "提示词指令内容", example = "你是一个智能助手")
    private String instructions = null;

    @JsonProperty("model_deployment_id")
    @Schema(description = "模型部署 ID", example = "deploy-001")
    private String modelDeploymentId = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "qwen-72b")
    private String modelName = null;

    @JsonProperty("service_name")
    @Schema(description = "服务名称", example = "model-service")
    private String serviceName = null;

    @JsonProperty("model_endpoint")
    @Schema(description = "模型推理端点 URL", example = "https://api.example.com/v1")
    private String modelEndpoint = null;

    @JsonProperty("model_version")
    @Schema(description = "模型版本号", example = "1.0.0")
    private String modelVersion = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型标识", example = "llm")
    private String modelType = null;

    @JsonProperty("model")
    @Schema(description = "模型标识符", example = "qwen-72b")
    private String model = null;

    @JsonProperty("model_config")
    @Schema(description = "模型参数配置", example = "{}")
    @Valid
    private ModelConfig modelConfig = null;

    @JsonProperty("tools")
    @Schema(description = "工具引用列表", example = "[]")
    @Valid
    @Size()
    private List<ToolReference> tools = null;

    @JsonProperty("workflows")
    @Schema(description = "工作流引用列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowReference> workflows = null;

    @JsonProperty("mcp_servers")
    @Schema(description = "MCP 服务器引用列表", example = "[]")
    @Valid
    @Size()
    private List<McpServerReference> mcpServers = null;

    @JsonProperty("skills")
    @Schema(description = "技能引用列表", example = "[]")
    @Valid
    @Size()
    private List<SkillReference> skills = null;

    @JsonProperty("knowledge_repos")
    @Schema(description = "知识库引用列表", example = "[]")
    @Valid
    @Size()
    private List<KnowledgeRepoReference> knowledgeRepos = null;

    @JsonProperty("knowledge_retrieve_policy")
    @Schema(description = "知识检索策略", example = "{}")
    @Valid
    private KnowledgeRetrievePolicy knowledgeRetrievePolicy = null;

    @JsonProperty("trigger_list")
    @Schema(description = "触发器配置列表", example = "[]")
    @Valid
    @Size()
    private List<TriggerConfig> triggerList = null;

    @JsonProperty("memory_variables")
    @Schema(description = "记忆变量列表", example = "[]")
    @Valid
    @Size()
    private List<MemoryVariable> memoryVariables = null;

    @JsonProperty("prologue")
    @Schema(description = "开场白", example = "你好，我是智能助手")
    private String prologue = null;

    @JsonProperty("suggest_queries")
    @Schema(description = "推荐问题列表", example = "[\"今天天气怎么样？\"]")
    @Valid
    @Size()
    private List<@Length() String> suggestQueries = null;

    @JsonProperty("additional_questions_config")
    @Schema(description = "追加问题配置", example = "{}")
    @Valid
    private AdditionalQuestionsConfig additionalQuestionsConfig = null;

    @JsonProperty("voice_interaction")
    @Schema(description = "语音交互配置", example = "{}")
    @Valid
    private VoiceInteraction voiceInteraction = null;

    @JsonProperty("reference")
    @Schema(description = "引用配置", example = "{}")
    @Valid
    private Reference reference = null;

    @JsonProperty("content_review")
    @Schema(description = "内容审核配置", example = "{}")
    @Valid
    private Object contentReview = null;

    @JsonProperty("safety_barrier")
    @Schema(description = "是否启用安全护栏", example = "false")
    private Boolean safetyBarrier = null;

    @JsonProperty("agent_variables")
    @Schema(description = "智能体变量列表，最多 30 个", example = "[]")
    @Valid
    @Size(max = 30)
    private List<AgentVariable> agentVariables = null;

    @JsonProperty("input_variables")
    @Schema(description = "输入变量列表，最多 30 个", example = "[]")
    @Valid
    @Size(max = 30)
    private List<InputVariable> inputVariables = null;

    @JsonProperty("memory_config")
    @Schema(description = "记忆配置", example = "{}")
    @Valid
    private AgentMemoryConfig memoryConfig = null;

    @JsonProperty("status")
    @Schema(description = "智能体状态", example = "draft")
    private String status = null;

    @JsonProperty("url")
    @Schema(description = "智能体访问 URL", example = "https://agent.example.com")
    private String url = null;

    @JsonProperty("creator")
    @Schema(description = "创建者名称", example = "admin")
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者 ID", example = "user-001")
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2026-01-01T00:00:00Z")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2026-01-01T00:00:00Z")
    private Date updateTime = null;

    @JsonProperty("publish_time")
    @Schema(description = "发布时间", example = "2026-01-01T00:00:00Z")
    private Date publishTime = null;

    @JsonProperty("workflow_switch_enabled")
    @Schema(description = "是否启用工作流开关", example = "false")
    private Boolean workflowSwitchEnabled = null;

    @JsonProperty("scheduling_mode")
    @Schema(description = "调度模式", example = "manual")
    private String schedulingMode = null;

    @JsonProperty("plan_qa_independent")
    @Schema(description = "计划 QA 是否独立执行", example = "false")
    private Boolean planQaIndependent = null;

    @JsonProperty("plan_model_deployment_id")
    @Schema(description = "规划模型部署 ID", example = "deploy-002")
    private String planModelDeploymentId = null;

    @JsonProperty("plan_model_name")
    @Schema(description = "规划模型名称", example = "qwen-72b")
    private String planModelName = null;

    @JsonProperty("plan_model_type")
    @Schema(description = "规划模型类型标识", example = "llm")
    private String planModelType = null;

    @JsonProperty("plan_model")
    @Schema(description = "规划模型标识符", example = "qwen-72b")
    private String planModel = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间 ID", example = "ws-001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("search_engine")
    @Schema(description = "搜索引擎配置", example = "{}")
    @Valid
    private ToolReference searchEngine = null;

    @JsonProperty("is_template")
    @Schema(description = "是否为模板", example = "false")
    private Boolean isTemplate = null;

    @JsonProperty("plan_model_config")
    @Schema(description = "规划模型参数配置", example = "{}")
    @Valid
    private ModelConfig planModelConfig = null;

    @JsonProperty("is_share")
    @Schema(description = "是否已分享", example = "0")
    private Integer isShare = null;

    @JsonProperty("fromShare")
    @Schema(description = "是否来自分享", example = "false")
    private Boolean fromShare = null;

    @JsonProperty("channel_type")
    @Schema(description = "渠道类型列表", example = "[\"web\", \"api\"]")
    @Valid
    @Size()
    private List<@Length() String> channelType = null;

    @JsonProperty("free_trial_quota")
    @Schema(description = "免费试用配额", example = "{}")
    @Valid
    private FreeTrialQuota freeTrialQuota = null;

    @JsonProperty("scenes")
    @Schema(description = "场景列表", example = "[]")
    @Valid
    @Size()
    private List<Scene> scenes = null;

    @JsonProperty("planning")
    @Schema(description = "规划配置", example = "{}")
    @Valid
    private Planning planning = null;

    @JsonProperty("character_dr")
    @Schema(description = "角色设定标识", example = "0")
    private Integer characterDr = null;

    @JsonProperty("writing_template")
    @Schema(description = "写作模板", example = "default")
    private String writingTemplate = null;

    public String getAgentId() {
        return agentId;
    }

    public AgentInfo setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public AgentInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getName() {
        return name;
    }

    public AgentInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public AgentInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getSubType() {
        return subType;
    }

    public AgentInfo setSubType(String subType) {
        this.subType = subType;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AgentInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public AgentInfo setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public ControllerVO getDetails() {
        return details;
    }

    public AgentInfo setDetails(ControllerVO details) {
        this.details = details;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public AgentInfo setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    public String getInstructions() {
        return instructions;
    }

    public AgentInfo setInstructions(String instructions) {
        this.instructions = instructions;
        return this;
    }

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public AgentInfo setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public AgentInfo setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getServiceName() {
        return serviceName;
    }

    public AgentInfo setServiceName(String serviceName) {
        this.serviceName = serviceName;
        return this;
    }

    public String getModelEndpoint() {
        return modelEndpoint;
    }

    public AgentInfo setModelEndpoint(String modelEndpoint) {
        this.modelEndpoint = modelEndpoint;
        return this;
    }

    public String getModelVersion() {
        return modelVersion;
    }

    public AgentInfo setModelVersion(String modelVersion) {
        this.modelVersion = modelVersion;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public AgentInfo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getModel() {
        return model;
    }

    public AgentInfo setModel(String model) {
        this.model = model;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public AgentInfo setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public List<ToolReference> getTools() {
        return tools;
    }

    public AgentInfo setTools(List<ToolReference> tools) {
        this.tools = tools;
        return this;
    }

    public List<WorkflowReference> getWorkflows() {
        return workflows;
    }

    public AgentInfo setWorkflows(List<WorkflowReference> workflows) {
        this.workflows = workflows;
        return this;
    }

    public List<McpServerReference> getMcpServers() {
        return mcpServers;
    }

    public AgentInfo setMcpServers(List<McpServerReference> mcpServers) {
        this.mcpServers = mcpServers;
        return this;
    }

    public List<SkillReference> getSkills() {
        return skills;
    }

    public AgentInfo setSkills(List<SkillReference> skills) {
        this.skills = skills;
        return this;
    }

    public List<KnowledgeRepoReference> getKnowledgeRepos() {
        return knowledgeRepos;
    }

    public AgentInfo setKnowledgeRepos(List<KnowledgeRepoReference> knowledgeRepos) {
        this.knowledgeRepos = knowledgeRepos;
        return this;
    }

    public KnowledgeRetrievePolicy getKnowledgeRetrievePolicy() {
        return knowledgeRetrievePolicy;
    }

    public AgentInfo setKnowledgeRetrievePolicy(KnowledgeRetrievePolicy knowledgeRetrievePolicy) {
        this.knowledgeRetrievePolicy = knowledgeRetrievePolicy;
        return this;
    }

    public List<TriggerConfig> getTriggerList() {
        return triggerList;
    }

    public AgentInfo setTriggerList(List<TriggerConfig> triggerList) {
        this.triggerList = triggerList;
        return this;
    }

    public List<MemoryVariable> getMemoryVariables() {
        return memoryVariables;
    }

    public AgentInfo setMemoryVariables(List<MemoryVariable> memoryVariables) {
        this.memoryVariables = memoryVariables;
        return this;
    }

    public String getPrologue() {
        return prologue;
    }

    public AgentInfo setPrologue(String prologue) {
        this.prologue = prologue;
        return this;
    }

    public List<String> getSuggestQueries() {
        return suggestQueries;
    }

    public AgentInfo setSuggestQueries(List<String> suggestQueries) {
        this.suggestQueries = suggestQueries;
        return this;
    }

    public AdditionalQuestionsConfig getAdditionalQuestionsConfig() {
        return additionalQuestionsConfig;
    }

    public AgentInfo setAdditionalQuestionsConfig(AdditionalQuestionsConfig additionalQuestionsConfig) {
        this.additionalQuestionsConfig = additionalQuestionsConfig;
        return this;
    }

    public VoiceInteraction getVoiceInteraction() {
        return voiceInteraction;
    }

    public AgentInfo setVoiceInteraction(VoiceInteraction voiceInteraction) {
        this.voiceInteraction = voiceInteraction;
        return this;
    }

    public Reference getReference() {
        return reference;
    }

    public AgentInfo setReference(Reference reference) {
        this.reference = reference;
        return this;
    }

    public Object getContentReview() {
        return contentReview;
    }

    public AgentInfo setContentReview(Object contentReview) {
        this.contentReview = contentReview;
        return this;
    }

    public AgentInfo setSafetyBarrier(Boolean safetyBarrier) {
        this.safetyBarrier = safetyBarrier;
        return this;
    }

    public Boolean isSafetyBarrier() {
        return safetyBarrier;
    }

    public List<AgentVariable> getAgentVariables() {
        return agentVariables;
    }

    public AgentInfo setAgentVariables(List<AgentVariable> agentVariables) {
        this.agentVariables = agentVariables;
        return this;
    }

    public List<InputVariable> getInputVariables() {
        return inputVariables;
    }

    public AgentInfo setInputVariables(List<InputVariable> inputVariables) {
        this.inputVariables = inputVariables;
        return this;
    }

    public AgentMemoryConfig getMemoryConfig() {
        return memoryConfig;
    }

    public AgentInfo setMemoryConfig(AgentMemoryConfig memoryConfig) {
        this.memoryConfig = memoryConfig;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public AgentInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public AgentInfo setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public AgentInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public AgentInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public AgentInfo setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public AgentInfo setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public Date getPublishTime() {
        return publishTime;
    }

    public AgentInfo setPublishTime(Date publishTime) {
        this.publishTime = publishTime;
        return this;
    }

    public AgentInfo setWorkflowSwitchEnabled(Boolean workflowSwitchEnabled) {
        this.workflowSwitchEnabled = workflowSwitchEnabled;
        return this;
    }

    public Boolean isWorkflowSwitchEnabled() {
        return workflowSwitchEnabled;
    }

    public String getSchedulingMode() {
        return schedulingMode;
    }

    public AgentInfo setSchedulingMode(String schedulingMode) {
        this.schedulingMode = schedulingMode;
        return this;
    }

    public AgentInfo setPlanQaIndependent(Boolean planQaIndependent) {
        this.planQaIndependent = planQaIndependent;
        return this;
    }

    public Boolean isPlanQaIndependent() {
        return planQaIndependent;
    }

    public String getPlanModelDeploymentId() {
        return planModelDeploymentId;
    }

    public AgentInfo setPlanModelDeploymentId(String planModelDeploymentId) {
        this.planModelDeploymentId = planModelDeploymentId;
        return this;
    }

    public String getPlanModelName() {
        return planModelName;
    }

    public AgentInfo setPlanModelName(String planModelName) {
        this.planModelName = planModelName;
        return this;
    }

    public String getPlanModelType() {
        return planModelType;
    }

    public AgentInfo setPlanModelType(String planModelType) {
        this.planModelType = planModelType;
        return this;
    }

    public String getPlanModel() {
        return planModel;
    }

    public AgentInfo setPlanModel(String planModel) {
        this.planModel = planModel;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public AgentInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public ToolReference getSearchEngine() {
        return searchEngine;
    }

    public AgentInfo setSearchEngine(ToolReference searchEngine) {
        this.searchEngine = searchEngine;
        return this;
    }

    public AgentInfo setIsTemplate(Boolean isTemplate) {
        this.isTemplate = isTemplate;
        return this;
    }

    public Boolean isIsTemplate() {
        return isTemplate;
    }

    public ModelConfig getPlanModelConfig() {
        return planModelConfig;
    }

    public AgentInfo setPlanModelConfig(ModelConfig planModelConfig) {
        this.planModelConfig = planModelConfig;
        return this;
    }

    public Integer getIsShare() {
        return isShare;
    }

    public AgentInfo setIsShare(Integer isShare) {
        this.isShare = isShare;
        return this;
    }

    public Boolean getFromShare() {
        return fromShare;
    }

    public AgentInfo setFromShare(Boolean fromShare) {
        this.fromShare = fromShare;
        return this;
    }

    public List<String> getChannelType() {
        return channelType;
    }

    public AgentInfo setChannelType(List<String> channelType) {
        this.channelType = channelType;
        return this;
    }

    public FreeTrialQuota getFreeTrialQuota() {
        return freeTrialQuota;
    }

    public AgentInfo setFreeTrialQuota(FreeTrialQuota freeTrialQuota) {
        this.freeTrialQuota = freeTrialQuota;
        return this;
    }

    public List<Scene> getScenes() {
        return scenes;
    }

    public AgentInfo setScenes(List<Scene> scenes) {
        this.scenes = scenes;
        return this;
    }

    public Planning getPlanning() {
        return planning;
    }

    public AgentInfo setPlanning(Planning planning) {
        this.planning = planning;
        return this;
    }

    public AgentInfo setCharacterDr(Integer characterDr) {
        this.characterDr = characterDr;
        return this;
    }
    public Integer getCharacterDr() {
        return characterDr;
    }

    public AgentInfo setWritingTemplate(String writingTemplate) {
        this.writingTemplate = writingTemplate;
        return this;
    }
    public String getWritingTemplate() {
        return writingTemplate;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentInfo {\n");

        sb.append("    agentId: ").append(toIndentedString(agentId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    subType: ").append(toIndentedString(subType)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    details: ").append(toIndentedString(details)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    instructions: ").append(toIndentedString(instructions)).append("\n");
        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    serviceName: ").append(toIndentedString(serviceName)).append("\n");
        sb.append("    modelEndpoint: ").append(toIndentedString(modelEndpoint)).append("\n");
        sb.append("    modelVersion: ").append(toIndentedString(modelVersion)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
        sb.append("    workflows: ").append(toIndentedString(workflows)).append("\n");
        sb.append("    mcpServers: ").append(toIndentedString(mcpServers)).append("\n");
        sb.append("    skills: ").append(toIndentedString(skills)).append("\n");
        sb.append("    knowledgeRepos: ").append(toIndentedString(knowledgeRepos)).append("\n");
        sb.append("    knowledgeRetrievePolicy: ").append(toIndentedString(knowledgeRetrievePolicy)).append("\n");
        sb.append("    triggerList: ").append(toIndentedString(triggerList)).append("\n");
        sb.append("    memoryVariables: ").append(toIndentedString(memoryVariables)).append("\n");
        sb.append("    prologue: ").append(toIndentedString(prologue)).append("\n");
        sb.append("    suggestQueries: ").append(toIndentedString(suggestQueries)).append("\n");
        sb.append("    additionalQuestionsConfig: ").append(toIndentedString(additionalQuestionsConfig)).append("\n");
        sb.append("    voiceInteraction: ").append(toIndentedString(voiceInteraction)).append("\n");
        sb.append("    reference: ").append(toIndentedString(reference)).append("\n");
        sb.append("    contentReview: ").append(toIndentedString(contentReview)).append("\n");
        sb.append("    safetyBarrier: ").append(toIndentedString(safetyBarrier)).append("\n");
        sb.append("    agentVariables: ").append(toIndentedString(agentVariables)).append("\n");
        sb.append("    inputVariables: ").append(toIndentedString(inputVariables)).append("\n");
        sb.append("    memoryConfig: ").append(toIndentedString(memoryConfig)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    publishTime: ").append(toIndentedString(publishTime)).append("\n");
        sb.append("    workflowSwitchEnabled: ").append(toIndentedString(workflowSwitchEnabled)).append("\n");
        sb.append("    schedulingMode: ").append(toIndentedString(schedulingMode)).append("\n");
        sb.append("    planQaIndependent: ").append(toIndentedString(planQaIndependent)).append("\n");
        sb.append("    planModelDeploymentId: ").append(toIndentedString(planModelDeploymentId)).append("\n");
        sb.append("    planModelName: ").append(toIndentedString(planModelName)).append("\n");
        sb.append("    planModelType: ").append(toIndentedString(planModelType)).append("\n");
        sb.append("    planModel: ").append(toIndentedString(planModel)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    searchEngine: ").append(toIndentedString(searchEngine)).append("\n");
        sb.append("    isTemplate: ").append(toIndentedString(isTemplate)).append("\n");
        sb.append("    planModelConfig: ").append(toIndentedString(planModelConfig)).append("\n");
        sb.append("    isShare: ").append(toIndentedString(isShare)).append("\n");
        sb.append("    channelType: ").append(toIndentedString(channelType)).append("\n");
        sb.append("    freeTrialQuota: ").append(toIndentedString(freeTrialQuota)).append("\n");
        sb.append("    scenes: ").append(toIndentedString(scenes)).append("\n");
        sb.append("    planning: ").append(toIndentedString(planning)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        AgentInfo agentInfo = (AgentInfo) o;
        return Objects.equals(this.agentId, agentInfo.agentId) && Objects.equals(this.projectId, agentInfo.projectId)
            && Objects.equals(this.name, agentInfo.name) && Objects.equals(this.type, agentInfo.type) && Objects.equals(
            this.subType, agentInfo.subType) && Objects.equals(this.description, agentInfo.description)
            && Objects.equals(this.icon, agentInfo.icon) && Objects.equals(this.details, agentInfo.details)
            && Objects.equals(this.tags, agentInfo.tags) && Objects.equals(this.instructions, agentInfo.instructions)
            && Objects.equals(this.modelDeploymentId, agentInfo.modelDeploymentId) && Objects.equals(this.modelName,
            agentInfo.modelName) && Objects.equals(this.serviceName, agentInfo.serviceName) && Objects.equals(
            this.modelEndpoint, agentInfo.modelEndpoint) && Objects.equals(this.modelVersion, agentInfo.modelVersion)
            && Objects.equals(this.modelType, agentInfo.modelType) && Objects.equals(this.model, agentInfo.model)
            && Objects.equals(this.modelConfig, agentInfo.modelConfig) && Objects.equals(this.tools, agentInfo.tools)
            && Objects.equals(this.workflows, agentInfo.workflows) && Objects.equals(this.mcpServers,
            agentInfo.mcpServers) && Objects.equals(this.skills, agentInfo.skills) && Objects.equals(
            this.knowledgeRepos, agentInfo.knowledgeRepos) && Objects.equals(this.knowledgeRetrievePolicy,
            agentInfo.knowledgeRetrievePolicy) && Objects.equals(this.triggerList, agentInfo.triggerList)
            && Objects.equals(this.memoryVariables, agentInfo.memoryVariables) && Objects.equals(this.prologue,
            agentInfo.prologue) && Objects.equals(this.suggestQueries, agentInfo.suggestQueries) && Objects.equals(
            this.additionalQuestionsConfig, agentInfo.additionalQuestionsConfig) && Objects.equals(
            this.voiceInteraction, agentInfo.voiceInteraction) && Objects.equals(this.reference, agentInfo.reference)
            && Objects.equals(this.contentReview, agentInfo.contentReview) && Objects.equals(this.safetyBarrier,
            agentInfo.safetyBarrier) && Objects.equals(this.agentVariables, agentInfo.agentVariables) && Objects.equals(
            this.inputVariables, agentInfo.inputVariables) && Objects.equals(this.memoryConfig, agentInfo.memoryConfig)
            && Objects.equals(this.status, agentInfo.status) && Objects.equals(this.url, agentInfo.url)
            && Objects.equals(this.creator, agentInfo.creator) && Objects.equals(this.creatorId, agentInfo.creatorId)
            && Objects.equals(this.createTime, agentInfo.createTime) && Objects.equals(this.updateTime,
            agentInfo.updateTime) && Objects.equals(this.publishTime, agentInfo.publishTime) && Objects.equals(
            this.workflowSwitchEnabled, agentInfo.workflowSwitchEnabled) && Objects.equals(this.schedulingMode,
            agentInfo.schedulingMode) && Objects.equals(this.planQaIndependent, agentInfo.planQaIndependent)
            && Objects.equals(this.planModelDeploymentId, agentInfo.planModelDeploymentId) && Objects.equals(
            this.planModelName, agentInfo.planModelName) && Objects.equals(this.planModelType, agentInfo.planModelType)
            && Objects.equals(this.planModel, agentInfo.planModel) && Objects.equals(this.workspaceId,
            agentInfo.workspaceId) && Objects.equals(this.searchEngine, agentInfo.searchEngine) && Objects.equals(
            this.isTemplate, agentInfo.isTemplate) && Objects.equals(this.planModelConfig, agentInfo.planModelConfig)
            && Objects.equals(this.isShare, agentInfo.isShare) && Objects.equals(this.channelType,
            agentInfo.channelType) && Objects.equals(this.freeTrialQuota, agentInfo.freeTrialQuota) && Objects.equals(
            this.scenes, agentInfo.scenes) && Objects.equals(this.planning, agentInfo.planning);
    }

    @Override
    public int hashCode() {
        return Objects.hash(agentId, projectId, name, type, subType, description, icon, details, tags, instructions,
            modelDeploymentId, modelName, serviceName, modelEndpoint, modelVersion, modelType, model, modelConfig,
            tools, workflows, mcpServers, skills, knowledgeRepos, knowledgeRetrievePolicy, triggerList, memoryVariables,
            prologue, suggestQueries, additionalQuestionsConfig, voiceInteraction, reference, contentReview,
            safetyBarrier, agentVariables, inputVariables, memoryConfig, status, url, creator, creatorId, createTime,
            updateTime, publishTime, workflowSwitchEnabled, schedulingMode, planQaIndependent, planModelDeploymentId,
            planModelName, planModelType, planModel, workspaceId, searchEngine, isTemplate, planModelConfig, isShare,
            channelType, freeTrialQuota, scenes, planning);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
