/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import io.swagger.annotations.ApiModel;
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
    @NotBlank
    private String agentId = null;

    @JsonProperty("project_id")
    private String projectId = null;

    @JsonProperty("name")
    private String name = null;

    @JsonProperty("type")
    private String type = null;

    @JsonProperty("sub_type")
    private String subType = null;

    @JsonProperty("description")
    private String description = null;

    @JsonProperty("icon")
    private String icon = null;

    @JsonProperty("details")
    @Valid
    private ControllerVO details = null;

    @JsonProperty("tags")
    @Valid
    @Size()
    private List<@Length() String> tags = null;

    @JsonProperty("instructions")
    private String instructions = null;

    @JsonProperty("model_deployment_id")
    private String modelDeploymentId = null;

    @JsonProperty("model_name")
    private String modelName = null;

    @JsonProperty("service_name")
    private String serviceName = null;

    @JsonProperty("model_endpoint")
    private String modelEndpoint = null;

    @JsonProperty("model_version")
    private String modelVersion = null;

    @JsonProperty("model_type")
    private String modelType = null;

    @JsonProperty("model")
    private String model = null;

    @JsonProperty("model_config")
    @Valid
    private ModelConfig modelConfig = null;

    @JsonProperty("tools")
    @Valid
    @Size()
    private List<ToolReference> tools = null;

    @JsonProperty("workflows")
    @Valid
    @Size()
    private List<WorkflowReference> workflows = null;

    @JsonProperty("mcp_servers")
    @Valid
    @Size()
    private List<McpServerReference> mcpServers = null;

    @JsonProperty("skills")
    @Valid
    @Size()
    private List<SkillReference> skills = null;

    @JsonProperty("knowledge_repos")
    @Valid
    @Size()
    private List<KnowledgeRepoReference> knowledgeRepos = null;

    @JsonProperty("knowledge_retrieve_policy")
    @Valid
    private KnowledgeRetrievePolicy knowledgeRetrievePolicy = null;

    @JsonProperty("trigger_list")
    @Valid
    @Size()
    private List<TriggerConfig> triggerList = null;

    @JsonProperty("memory_variables")
    @Valid
    @Size()
    private List<MemoryVariable> memoryVariables = null;

    @JsonProperty("prologue")
    private String prologue = null;

    @JsonProperty("suggest_queries")
    @Valid
    @Size()
    private List<@Length() String> suggestQueries = null;

    @JsonProperty("additional_questions_config")
    @Valid
    private AdditionalQuestionsConfig additionalQuestionsConfig = null;

    @JsonProperty("voice_interaction")
    @Valid
    private VoiceInteraction voiceInteraction = null;

    @JsonProperty("reference")
    @Valid
    private Reference reference = null;

    @JsonProperty("content_review")
    @Valid
    private Object contentReview = null;

    @JsonProperty("safety_barrier")
    private Boolean safetyBarrier = null;

    @JsonProperty("agent_variables")
    @Valid
    @Size(max = 30)
    private List<AgentVariable> agentVariables = null;

    @JsonProperty("input_variables")
    @Valid
    @Size(max = 30)
    private List<InputVariable> inputVariables = null;

    @JsonProperty("memory_config")
    @Valid
    private AgentMemoryConfig memoryConfig = null;

    @JsonProperty("status")
    private String status = null;

    @JsonProperty("url")
    private String url = null;

    @JsonProperty("creator")
    private String creator = null;

    @JsonProperty("creator_id")
    private String creatorId = null;

    @JsonProperty("create_time")
    private Date createTime = null;

    @JsonProperty("update_time")
    private Date updateTime = null;

    @JsonProperty("publish_time")
    private Date publishTime = null;

    @JsonProperty("workflow_switch_enabled")
    private Boolean workflowSwitchEnabled = null;

    @JsonProperty("scheduling_mode")
    private String schedulingMode = null;

    @JsonProperty("plan_qa_independent")
    private Boolean planQaIndependent = null;

    @JsonProperty("plan_model_deployment_id")
    private String planModelDeploymentId = null;

    @JsonProperty("plan_model_name")
    private String planModelName = null;

    @JsonProperty("plan_model_type")
    private String planModelType = null;

    @JsonProperty("plan_model")
    private String planModel = null;

    @JsonProperty("workspace_id")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("search_engine")
    @Valid
    private ToolReference searchEngine = null;

    @JsonProperty("is_template")
    private Boolean isTemplate = null;

    @JsonProperty("plan_model_config")
    @Valid
    private ModelConfig planModelConfig = null;

    @JsonProperty("is_share")
    private Integer isShare = null;

    @JsonProperty("fromShare")
    private Boolean fromShare = null;

    @JsonProperty("channel_type")
    @Valid
    @Size()
    private List<@Length() String> channelType = null;

    @JsonProperty("free_trial_quota")
    @Valid
    private FreeTrialQuota freeTrialQuota = null;

    @JsonProperty("scenes")
    @Valid
    @Size()
    private List<Scene> scenes = null;

    @JsonProperty("planning")
    @Valid
    private Planning planning = null;

    @JsonProperty("character_dr")
    private Integer characterDr = null;

    @JsonProperty("writing_template")
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
