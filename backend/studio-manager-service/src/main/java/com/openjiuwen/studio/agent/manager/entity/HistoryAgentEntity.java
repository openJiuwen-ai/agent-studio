/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.manager.dto.AdditionalQuestionsConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.AgentVariable;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.VoiceInteraction;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;
import java.util.List;

/**
 * 已删除的Agent资源表
 *
 */
@NoArgsConstructor
@AllArgsConstructor
@Data
@Builder
public class HistoryAgentEntity {

    /**
     * 已删除Agent资源表唯一标识
     */
    @JsonProperty("history_id")
    private String historyId;

    /**
     * agent唯一标识
     */
    @JsonProperty("agent_id")
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
     * agent名称
     */
    @JsonProperty("name")
    private String name;

    /**
     * agent描述
     */
    @JsonProperty("description")
    private String description;

    /**
     * agent图标
     */
    @JsonProperty("icon")
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
    private ModelConfig modelConfig;

    /**
     * agent关联的模型类型
     */
    @JsonProperty("model_type")
    private String modelType;

    /**
     * agent关联的模型资产名称
     */
    @JsonProperty("model")
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
    @JsonProperty("instructions")
    private String instructions;

    /**
     * agent使用触发器
     */
    @JsonProperty("trigger_list")
    private List<TriggerConfig> triggerList;

    /**
     * agent使用的记忆变量
     */
    @JsonProperty("memory_variables")
    private List<MemoryVariable> memoryVariables;

    /**
     * agent开场白
     */
    @JsonProperty("prologue")
    private String prologue;

    /**
     * agent推荐问
     */
    @JsonProperty("suggest_queries")
    private List<String> suggestQueries;

    /**
     * 追问配置
     */
    @JsonProperty("additional_questions_config")
    private AdditionalQuestionsConfig additionalQuestionsConfig;

    /**
     * 语音配置
     */
    @JsonProperty("voice_interaction")
    private VoiceInteraction voiceInteraction;

    /**
     * 知识检索策略
     */
    @JsonProperty("knowledge_retrieve_policy")
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

    @JsonProperty("type")
    private String type;

    /**
     * agent子类型（如：deepresearch）
     */
    @JsonProperty("sub_type")
    private String subType;

    /**
     * agent状态
     */
    @JsonProperty("status")
    private String status;

    /**
     * 应用创建者
     */
    @JsonProperty("creator")
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
    private List<AgentVariable> agentVariables;

    /**
     * 记忆相关的配置
     */
    @JsonProperty("memory_config")
    private AgentMemoryConfig memoryConfig;

    /**
     * 是否已共享,(0=否，1=是)
     */
    @JsonProperty("is_share")
    private Integer isShare;
}
