/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * mcp 服务配置信息
 */
@ApiModel(description = "mcp 服务配置信息")

@Validated

public class McpServerConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "config_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("server_id")
    @Schema(description = "服务ID", example = "server_001")
    @Length(max = 64)
    private String serverId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project_001")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("auth_keys")
    @Schema(description = "认证密钥列表", example = "[{\"keyId\":\"key1\",\" keyValue\":\"secret\"}]")
    @Valid
    @Size()
    private List<AuthKeyInfo> authKeys = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user_001")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1714521600000")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1714608000000")
    private Date updateTime = null;

    public String getId() {
        return id;
    }

    public McpServerConfig setId(String id) {
        this.id = id;
        return this;
    }

    public String getServerId() {
        return serverId;
    }

    public McpServerConfig setServerId(String serverId) {
        this.serverId = serverId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public McpServerConfig setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public List<AuthKeyInfo> getAuthKeys() {
        return authKeys;
    }

    public McpServerConfig setAuthKeys(List<AuthKeyInfo> authKeys) {
        this.authKeys = authKeys;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public McpServerConfig setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public McpServerConfig setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public McpServerConfig setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerConfig {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    serverId: ").append(toIndentedString(serverId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    authKeys: ").append(toIndentedString(authKeys)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
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
        McpServerConfig mcpServerConfig = (McpServerConfig) o;
        return Objects.equals(this.id, mcpServerConfig.id) && Objects.equals(this.serverId, mcpServerConfig.serverId)
            && Objects.equals(this.projectId, mcpServerConfig.projectId) && Objects.equals(this.authKeys,
            mcpServerConfig.authKeys) && Objects.equals(this.creatorId, mcpServerConfig.creatorId) && Objects.equals(
            this.createTime, mcpServerConfig.createTime) && Objects.equals(this.updateTime, mcpServerConfig.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, serverId, projectId, authKeys, creatorId, createTime, updateTime);
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
