/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

/**
 * 查询记忆服务实例详情响应体
 */
@ApiModel(description = "查询记忆服务实例详情响应体")
public class ShowMemoryServiceInstanceResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("instance_id")
    @Schema(description = "实例ID")
    private String instanceId = null;

    @JsonProperty("name")
    @Schema(description = "实例名称")
    private String name = null;

    @JsonProperty("base_url")
    @Schema(description = "agent-memory服务地址")
    private String baseUrl = null;

    @JsonProperty("health_status")
    @Schema(description = "健康检查状态")
    private String healthStatus = null;

    @JsonProperty("last_check_at")
    @Schema(description = "最近健康检查时间")
    private Date lastCheckAt = null;

    @JsonProperty("deploy_meta")
    @Schema(description = "展示用JSON")
    private String deployMeta = null;

    @JsonProperty("created_user_id")
    @Schema(description = "创建人ID")
    private String createdUserId = null;

    @JsonProperty("created_user_name")
    @Schema(description = "创建人名")
    private String createdUserName = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间")
    private Date updateTime = null;

    public String getInstanceId() {
        return instanceId;
    }

    public ShowMemoryServiceInstanceResponseBody setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ShowMemoryServiceInstanceResponseBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public ShowMemoryServiceInstanceResponseBody setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
        return this;
    }

    public String getHealthStatus() {
        return healthStatus;
    }

    public ShowMemoryServiceInstanceResponseBody setHealthStatus(String healthStatus) {
        this.healthStatus = healthStatus;
        return this;
    }

    public Date getLastCheckAt() {
        return lastCheckAt;
    }

    public ShowMemoryServiceInstanceResponseBody setLastCheckAt(Date lastCheckAt) {
        this.lastCheckAt = lastCheckAt;
        return this;
    }

    public String getDeployMeta() {
        return deployMeta;
    }

    public ShowMemoryServiceInstanceResponseBody setDeployMeta(String deployMeta) {
        this.deployMeta = deployMeta;
        return this;
    }

    public String getCreatedUserId() {
        return createdUserId;
    }

    public ShowMemoryServiceInstanceResponseBody setCreatedUserId(String createdUserId) {
        this.createdUserId = createdUserId;
        return this;
    }

    public String getCreatedUserName() {
        return createdUserName;
    }

    public ShowMemoryServiceInstanceResponseBody setCreatedUserName(String createdUserName) {
        this.createdUserName = createdUserName;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public ShowMemoryServiceInstanceResponseBody setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public ShowMemoryServiceInstanceResponseBody setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        ShowMemoryServiceInstanceResponseBody that = (ShowMemoryServiceInstanceResponseBody) o;
        return Objects.equals(this.instanceId, that.instanceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(instanceId);
    }
}
