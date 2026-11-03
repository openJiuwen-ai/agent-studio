/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.openjiuwen.studio.agent.manager.dto.LongTermMemoryStrategy;
import lombok.Builder;
import lombok.Data;

import java.util.Date;
import java.util.List;

/**
 * 记忆库实体类
 */
@Data
@Builder
public class MemoryRepoEntity {
    /**
     * 主键id
     */
    private String id;

    /**
     * 记忆库名称
     */
    private String name;

    /**
     * 描述
     */
    private String description;

    /**
     * 图标
     */
    private String icon;

    // =====================================触发条件=====================================

    /**
     * 间隔时间，单位分钟
     */
    private Integer timeSpan;

    /**
     * 最大对话轮数
     */
    private Integer conversationRound;


    // =====================================记忆提取策略=====================================

    /**
     * 记忆提取策略，使用json string格式存储
     */
    private List<LongTermMemoryStrategy> longTermMemoryStrategies;

    /**
     * 记忆后端类型：BUILTIN（内置）/EXTERNAL（外部agent-memory）
     */
    private String memoryBackendType;

    /**
     * 外部记忆服务实例ID（EXTERNAL时必填）
     */
    private String memoryServiceInstanceId;

    /**
     * scope级模型配置JSON（LLM/Embedding + enable_*），由manager推送到实例，不进IR
     */
    private String scopeModelConfig;


    /**
     * 租户唯一标识
     */
    private String projectId;

    /**
     * 项目空间ID
     */
    private String workspaceId;

    /**
     * 项目空间ID
     */
    private String domainId;

    /**
     * 创建人（用户ID）
     */
    private String createdUserId;

    /**
     * 创建人（用户名）
     */
    private String createdUserName;

    /**
     * 更新人（用户id）
     */
    private String lastUpdateUserId;

    /**
     * 更新人（用户名）
     */
    private String lastUpdateUserName;

    /**
     * 创建时间
     */
    private Date createTime;

    /**
     * 更新时间
     */
    private Date updateTime;
}
