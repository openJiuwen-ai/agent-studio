/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import lombok.Builder;
import lombok.Data;

import java.util.Date;

/**
 * 外部记忆服务实例实体类
 */
@Data
@Builder
public class MemoryServiceInstanceEntity {

    /**
     * 主键id
     */
    private String id;

    /**
     * 实例名称
     */
    private String name;

    /**
     * agent-memory服务地址（如 http://mem-svc-a:8000）
     * 非敏感，会进IR
     */
    private String baseUrl;

    /**
     * MEMORY_API_KEY，加密存储；不入IR，由manager同步到OBS auth文件供runtime惰性取
     */
    private String apiKey;

    /**
     * 项目空间ID
     */
    private String workspaceId;

    /**
     * 租户唯一标识
     */
    private String projectId;

    /**
     * IAM账号ID，租户ID
     */
    private String domainId;

    /**
     * 健康检查状态：HEALTHY/UNHEALTHY/UNKNOWN
     */
    private String healthStatus;

    /**
     * 最近健康检查时间
     */
    private Date lastCheckAt;

    /**
     * 展示用JSON：vector_store_type / db_type等
     */
    private String deployMeta;

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
