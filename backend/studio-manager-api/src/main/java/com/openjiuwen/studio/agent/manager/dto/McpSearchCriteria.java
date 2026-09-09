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
import java.util.List;
import java.util.Objects;

/**
 * 搜索条件
 */
@ApiModel(description = "搜索条件")

@Validated

public class McpSearchCriteria implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("ids")
    @Schema(description = "ID列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> ids = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "天气查询服务")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "天气查询")
    @Length(max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "查询天气信息")
    @Length(max = 64)
    private String toolDesc = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user-001")
    private String creator = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "MCP")
    @Length(max = 64)
    private String type = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "REST")
    @Length(max = 64)
    private String intfType = null;

    @JsonProperty("tag_id")
    @Schema(description = "标签ID", example = "tag-001")
    private String tagId = null;

    @JsonProperty("user_id")
    @Schema(description = "用户ID", example = "user-001")
    private String userId = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "MARKET")
    @Length(max = 64)
    private String source = null;

    @JsonProperty("exclude_ids")
    @Schema(description = "排除ID列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> excludeIds = null;

    @JsonProperty("workflow_type")
    @Schema(description = "工作流类型", example = "AGENT")
    @Length(max = 16)
    private String workflowType = null;

    @JsonProperty("published")
    @Schema(description = "是否已发布", example = "true")
    private Boolean published = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "PUBLISHED")
    private String status = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "MCP搜索条件描述")
    private String description = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public McpSearchCriteria setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getId() {
        return id;
    }

    public McpSearchCriteria setId(String id) {
        this.id = id;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public McpSearchCriteria setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpSearchCriteria setName(String name) {
        this.name = name;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public McpSearchCriteria setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public McpSearchCriteria setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public McpSearchCriteria setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpSearchCriteria setType(String type) {
        this.type = type;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public McpSearchCriteria setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public String getTagId() {
        return tagId;
    }

    public McpSearchCriteria setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    public String getUserId() {
        return userId;
    }

    public McpSearchCriteria setUserId(String userId) {
        this.userId = userId;
        return this;
    }

    public String getSource() {
        return source;
    }

    public McpSearchCriteria setSource(String source) {
        this.source = source;
        return this;
    }

    public List<String> getExcludeIds() {
        return excludeIds;
    }

    public McpSearchCriteria setExcludeIds(List<String> excludeIds) {
        this.excludeIds = excludeIds;
        return this;
    }

    public String getWorkflowType() {
        return workflowType;
    }

    public McpSearchCriteria setWorkflowType(String workflowType) {
        this.workflowType = workflowType;
        return this;
    }

    public McpSearchCriteria setPublished(Boolean published) {
        this.published = published;
        return this;
    }

    public Boolean isPublished() {
        return published;
    }

    public McpSearchCriteria setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public String getStatus() {
        return status;
    }

    public McpSearchCriteria setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpSearchCriteria setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpSearchCriteria {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    intfType: ").append(toIndentedString(intfType)).append("\n");
        sb.append("    tagId: ").append(toIndentedString(tagId)).append("\n");
        sb.append("    userId: ").append(toIndentedString(userId)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    excludeIds: ").append(toIndentedString(excludeIds)).append("\n");
        sb.append("    workflowType: ").append(toIndentedString(workflowType)).append("\n");
        sb.append("    published: ").append(toIndentedString(published)).append("\n");
        sb.append("    customizeNode: ").append(toIndentedString(customizeNode)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        McpSearchCriteria mcpSearchCriteria = (McpSearchCriteria) o;
        return Objects.equals(this.workspaceId, mcpSearchCriteria.workspaceId) && Objects.equals(this.id,
            mcpSearchCriteria.id) && Objects.equals(this.ids, mcpSearchCriteria.ids) && Objects.equals(this.name,
            mcpSearchCriteria.name) && Objects.equals(this.toolChineseName, mcpSearchCriteria.toolChineseName)
            && Objects.equals(this.toolDesc, mcpSearchCriteria.toolDesc) && Objects.equals(this.creator,
            mcpSearchCriteria.creator) && Objects.equals(this.type, mcpSearchCriteria.type) && Objects.equals(
            this.intfType, mcpSearchCriteria.intfType) && Objects.equals(this.tagId, mcpSearchCriteria.tagId)
            && Objects.equals(this.userId, mcpSearchCriteria.userId) && Objects.equals(this.source,
            mcpSearchCriteria.source) && Objects.equals(this.excludeIds, mcpSearchCriteria.excludeIds)
            && Objects.equals(this.workflowType, mcpSearchCriteria.workflowType) && Objects.equals(this.published,
            mcpSearchCriteria.published) && Objects.equals(this.customizeNode, mcpSearchCriteria.customizeNode)
            && Objects.equals(this.status, mcpSearchCriteria.status) && Objects.equals(this.description,
            mcpSearchCriteria.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, id, ids, name, toolChineseName, toolDesc, creator, type, intfType, tagId,
            userId, source, excludeIds, workflowType, published, customizeNode, status, description);
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
