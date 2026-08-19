/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.AdditionalQuestionsConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentVariable;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.InputVariable;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.Reference;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.VoiceInteraction;
import com.openjiuwen.studio.agent.manager.mapper.handler.AdditionalQuestionsConfigHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.AgentInputVariableArrayHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.AgentMemoryConfigHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.AgentVariableArrayHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.JsonHandlerKnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.mapper.handler.ListHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.MemoryVariableArrayHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.ModelConfigHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.ReferenceHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.TriggerConfigArrayHandler;
import com.openjiuwen.studio.agent.manager.mapper.handler.VoiceInteractionHandler;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;
import java.util.List;
import java.util.Map;

/**
 * 功能描述 Agent数据库实体
 *
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "t_agent")
public class Agent {
    /**
     * agent唯一标识
     */
    @JsonProperty("agent_id")
    @Id
    private String agentId;

    /**
     * 租户唯一标识
     */
    @JsonProperty("project_id")
    private String projectId;

    /**
     * 溯源ID
     */
    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("deleted")
    private Boolean deleted = false;

    /**
     * 项目空间ID
     */
    @JsonProperty("workspace_id")
    private String workspaceId;

    /**
     * 项目空间ID
     */
    @JsonProperty("domain_id")
    private String domainId;

    /**
     * 关联的assistant标识
     */
    @JsonProperty("assistant_id")
    private String assistantId;

    /**
     * agent名称
     */
    private String name;

    /**
     * agent描述
     */
    private String description;

    /**
     * agent图标
     */
    private String icon;

    /**
     * agent关联的模型deployment_id
     */
    @JsonProperty("model_deployment_id")
    private String modelDeploymentId;

    /**
     * agent关联的模型名称
     */
    @JsonProperty("model_name")
    private String modelName;

    /**
     * agent关联的模型参数
     */
    @JsonProperty("model_config")
    @Convert(converter = ModelConfigHandler.class)
    @Column(name = "model_config")
    private ModelConfig modelConfig;

    /**
     * agent关联的模型类型
     */
    @JsonProperty("model_type")
    private String modelType;

    /**
     * agent关联的模型资产名称
     */
    private String model;

    /**
     * 规划模型是否独立配置
     */
    @JsonProperty("plan_qa_independent")
    private Boolean planQaIndependent;

    /**
     * 规划模型资产名称
     */
    @JsonProperty("plan_model")
    private String planModel;

    /**
     * 规划模型deployment_id
     */
    @JsonProperty("plan_model_deployment_id")
    private String planModelDeploymentId;

    /**
     * 规划模型名称
     */
    @JsonProperty("plan_model_name")
    private String planModelName;

    /**
     * 规划模型参数
     */
    @JsonProperty("plan_model_config")
    private ModelConfig planModelConfig;

    /**
     * 规划模型类型
     */
    @JsonProperty("plan_model_type")
    private String planModelType;

    /**
     * agent使用的系统指令
     */
    @Column(name = "instructions", columnDefinition = "TEXT")
    private String instructions;

    /**
     * agent使用触发器
     */
    @JsonProperty("trigger_list")
    @Convert(converter = TriggerConfigArrayHandler.class)
    @Column(name = "trigger_list", columnDefinition = "TEXT")
    private List<TriggerConfig> triggerList;

    /**
     * agent使用的记忆变量
     */
    @JsonProperty("memory_variables")
    @Convert(converter = MemoryVariableArrayHandler.class)
    @Column(name = "memory_variables")
    private List<MemoryVariable> memoryVariables;

    /**
     * agent开场白
     */
    private String prologue;

    /**
     * agent推荐问
     */
    @JsonProperty("suggest_queries")
    @Convert(converter = ListHandler.class)
    @Column(name = "suggest_queries")
    private List<String> suggestQueries;

    /**
     * 追问配置
     */
    @JsonProperty("additional_questions_config")
    @Convert(converter = AdditionalQuestionsConfigHandler.class)
    @Column(name = "additional_questions_config")
    private AdditionalQuestionsConfig additionalQuestionsConfig;

    /**
     * 语音配置
     */
    @JsonProperty("voice_interaction")
    @Convert(converter = VoiceInteractionHandler.class)
    @Column(name = "voice_interaction")
    private VoiceInteraction voiceInteraction;

    /**
     * 是否开启引用和归属
     */
    @JsonProperty("reference")
    @Convert(converter = ReferenceHandler.class)
    @Column(name = "reference")
    private Reference reference;


    /**
     * 知识检索策略
     */
    @JsonProperty("knowledge_retrieve_policy")
    @Convert(converter = JsonHandlerKnowledgeRetrievePolicy.class)
    @Column(name = "knowledge_retrieve_policy")
    private KnowledgeRetrievePolicy knowledgeRetrievePolicy;

    /**
     * 内容审核
     */
    @JsonProperty("content_review")
    private String contentReview;

    /**
     * 安全护栏
     */
    @JsonProperty("safety_barrier")
    private Boolean safetyBarrier;

    @JsonProperty("dsl_path")
    private String dslPath;

    @JsonProperty("ir_path")
    private String irPath;

    private String type;

    /**
     * agent子类型（如：deepresearch）
     */
    @JsonProperty("sub_type")
    private String subType;

    /**
     * agent状态
     */
    private String status;

    /**
     * 应用创建者
     */
    private String creator;

    /**
     * 应用创建者ID
     */
    @JsonProperty("creator_id")
    private String creatorId;

    /**
     * 工作流跳转
     */
    @JsonProperty("workflow_switch_enabled")
    private Boolean workflowSwitchEnabled;

    /**
     * agent调度模式，ReAct、RAG
     */
    @JsonProperty("scheduling_mode")
    private String schedulingMode;

    /**
     * agent创建时间
     */
    @JsonProperty("created_on")
    private Date createdOn;

    /**
     * agent更新时间
     */
    @JsonProperty("updated_on")
    private Date updatedOn;

    /**
     * agent发布时间
     */
    @JsonProperty("published_on")
    private Date publishedOn;

    /**
     * agent图标名称
     */
    @JsonProperty("icon_name")
    private String iconName;

    /**
     * Agent定义的变量列表
     */
    @JsonProperty("agent_variables")
    @Convert(converter = AgentVariableArrayHandler.class)
    private List<AgentVariable> agentVariables;


    /**
     * Agent定义的用户输入变量列表
     */
    @JsonProperty("input_variables")
    @Convert(converter = AgentInputVariableArrayHandler.class)
    private List<InputVariable> inputVariables;

    /**
     * 记忆相关的配置
     */
    @JsonProperty("memory_config")
    @Convert(converter = AgentMemoryConfigHandler.class)
    private AgentMemoryConfig memoryConfig;

    /**
     * 是否已共享,(0=否，1=是)
     */
    @JsonProperty("is_share")
    private Integer isShare;

    /**
     * 配置MCP后选择的要使用的工具
     */
    @JsonProperty("mcp_choose_tools")
    @Convert(converter = ListHandler.class)
    private Map<String, List<String>> mcpChooseTools;

    /**
     * 转换Dto
     *
     * @return AgentInfo
     */
    public AgentInfo convertToDto(ControllerVO controllerVO) {
        AgentInfo agentInfo = new AgentInfo();
        agentInfo.setAgentId(this.getAgentId());
        agentInfo.setProjectId(this.getProjectId());
        agentInfo.setName(this.getName());
        agentInfo.setDescription(this.getDescription());
        agentInfo.setIcon(this.getIcon());
        agentInfo.setModelDeploymentId(this.getModelDeploymentId());
        agentInfo.setModelName(this.getModelName());
        agentInfo.setModelType(this.getModelType());
        agentInfo.setModel(this.getModel());
        agentInfo.setModelConfig(this.getModelConfig());
        agentInfo.setInstructions(this.getInstructions());
        agentInfo.setTriggerList(this.getTriggerList());
        agentInfo.setMemoryVariables(this.getMemoryVariables());
        agentInfo.setPrologue(this.getPrologue());
        agentInfo.setSuggestQueries(this.getSuggestQueries());
        agentInfo.setAdditionalQuestionsConfig(this.getAdditionalQuestionsConfig());
        agentInfo.setVoiceInteraction(this.getVoiceInteraction());
        agentInfo.setReference(this.getReference());
        agentInfo.setStatus(this.getStatus());
        agentInfo.setCreator(this.getCreator());
        agentInfo.setCreatorId(this.getCreatorId());
        agentInfo.setCreateTime(this.getCreatedOn());
        agentInfo.setUpdateTime(this.getUpdatedOn());
        agentInfo.setPublishTime(this.getPublishedOn());
        agentInfo.setKnowledgeRetrievePolicy(this.getKnowledgeRetrievePolicy());
        agentInfo.setWorkflowSwitchEnabled(this.getWorkflowSwitchEnabled());
        agentInfo.setSchedulingMode(this.getSchedulingMode());
        agentInfo.setType(this.getType());
        agentInfo.setSubType(this.getSubType());
        agentInfo.setSafetyBarrier(this.getSafetyBarrier());
        agentInfo.setAgentVariables(this.getAgentVariables());
        agentInfo.setInputVariables(this.getInputVariables());
        agentInfo.setMemoryConfig(this.getMemoryConfig());
        agentInfo.setPlanQaIndependent(this.getPlanQaIndependent());
        agentInfo.setPlanModel(this.getPlanModel());
        agentInfo.setPlanModelType(this.getPlanModelType());
        agentInfo.setPlanModelName(this.getPlanModelName());
        agentInfo.setPlanModelDeploymentId(this.getPlanModelDeploymentId());
        agentInfo.setPlanModelConfig(this.getPlanModelConfig());
        agentInfo.setIsShare(this.getIsShare());

        if (this.getContentReview() != null) {
            agentInfo.setContentReview(JsonUtils.json2Obj(this.getContentReview(), Constants.MAP_TYPE_REFERENCE));
        }
        if (controllerVO != null) {
            agentInfo.setDetails(controllerVO);
        }
        return agentInfo;
    }

    /**
     * 转换Dto
     *
     * @return AgentInfo
     */
    public AgentInfo convertToDto() {
        return convertToDto(null);
    }
}
