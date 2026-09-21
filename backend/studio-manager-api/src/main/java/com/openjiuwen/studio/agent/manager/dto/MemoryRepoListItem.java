/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 记忆库列表中的信息
 */
@ApiModel(description = "记忆库列表中的信息")

@Validated

public class MemoryRepoListItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("memory_repo_id")
    @Schema(description = "记忆库ID", example = "mem_001")
    @Length(max = 64)
    private String memoryRepoId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("name")
    @Schema(description = "记忆库名称", example = "我的记忆库")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "用于存储用户记忆")
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("long_term_memory_strategies")
    @Schema(description = "长期记忆策略列表", example = "[]")
    @Valid
    @Size(max = 200)
    private List<LongTermMemoryStrategy> longTermMemoryStrategies = null;

    @JsonProperty("created_user_id")
    @Schema(description = "创建者用户ID", example = "user_001")
    @Length(max = 100)
    private String createdUserId = null;

    @JsonProperty("created_user_name")
    @Schema(description = "创建者用户名", example = "张三")
    @Length(max = 100)
    private String createdUserName = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00Z")
    private Date createTime = null;

    @JsonProperty("last_update_user_id")
    @Schema(description = "最后更新者用户ID", example = "user_002")
    @Length(max = 100)
    private String lastUpdateUserId = null;

    @JsonProperty("last_update_user_name")
    @Schema(description = "最后更新者用户名", example = "李四")
    @Length(max = 100)
    private String lastUpdateUserName = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2024-01-02T00:00:00Z")
    private Date updateTime = null;

    public String getMemoryRepoId() {
        return memoryRepoId;
    }

    public MemoryRepoListItem setMemoryRepoId(String memoryRepoId) {
        this.memoryRepoId = memoryRepoId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public MemoryRepoListItem setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public MemoryRepoListItem setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public MemoryRepoListItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public MemoryRepoListItem setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<LongTermMemoryStrategy> getLongTermMemoryStrategies() {
        return longTermMemoryStrategies;
    }

    public MemoryRepoListItem setLongTermMemoryStrategies(List<LongTermMemoryStrategy> longTermMemoryStrategies) {
        this.longTermMemoryStrategies = longTermMemoryStrategies;
        return this;
    }

    public String getCreatedUserId() {
        return createdUserId;
    }

    public MemoryRepoListItem setCreatedUserId(String createdUserId) {
        this.createdUserId = createdUserId;
        return this;
    }

    public String getCreatedUserName() {
        return createdUserName;
    }

    public MemoryRepoListItem setCreatedUserName(String createdUserName) {
        this.createdUserName = createdUserName;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public MemoryRepoListItem setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getLastUpdateUserId() {
        return lastUpdateUserId;
    }

    public MemoryRepoListItem setLastUpdateUserId(String lastUpdateUserId) {
        this.lastUpdateUserId = lastUpdateUserId;
        return this;
    }

    public String getLastUpdateUserName() {
        return lastUpdateUserName;
    }

    public MemoryRepoListItem setLastUpdateUserName(String lastUpdateUserName) {
        this.lastUpdateUserName = lastUpdateUserName;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public MemoryRepoListItem setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryRepoListItem {\n");

        sb.append("    memoryRepoId: ").append(toIndentedString(memoryRepoId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    longTermMemoryStrategies: ").append(toIndentedString(longTermMemoryStrategies)).append("\n");
        sb.append("    createdUserId: ").append(toIndentedString(createdUserId)).append("\n");
        sb.append("    createdUserName: ").append(toIndentedString(createdUserName)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    lastUpdateUserId: ").append(toIndentedString(lastUpdateUserId)).append("\n");
        sb.append("    lastUpdateUserName: ").append(toIndentedString(lastUpdateUserName)).append("\n");
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
        MemoryRepoListItem memoryRepoListItem = (MemoryRepoListItem) o;
        return Objects.equals(this.memoryRepoId, memoryRepoListItem.memoryRepoId) && Objects.equals(this.workspaceId,
            memoryRepoListItem.workspaceId) && Objects.equals(this.name, memoryRepoListItem.name) && Objects.equals(
            this.description, memoryRepoListItem.description) && Objects.equals(this.icon, memoryRepoListItem.icon)
            && Objects.equals(this.longTermMemoryStrategies, memoryRepoListItem.longTermMemoryStrategies)
            && Objects.equals(this.createdUserId, memoryRepoListItem.createdUserId) && Objects.equals(
            this.createdUserName, memoryRepoListItem.createdUserName) && Objects.equals(this.createTime,
            memoryRepoListItem.createTime) && Objects.equals(this.lastUpdateUserId, memoryRepoListItem.lastUpdateUserId)
            && Objects.equals(this.lastUpdateUserName, memoryRepoListItem.lastUpdateUserName) && Objects.equals(
            this.updateTime, memoryRepoListItem.updateTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memoryRepoId, workspaceId, name, description, icon, longTermMemoryStrategies, createdUserId,
            createdUserName, createTime, lastUpdateUserId, lastUpdateUserName, updateTime);
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
