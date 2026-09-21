/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
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
 * SearchCriteria
 */

@Validated

public class SearchCriteria implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-12345678")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("id")
    @Schema(description = "唯一标识ID", example = "abc-123-def")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("ids")
    @Schema(description = "ID列表，最多100个", example = "[]")
    @Valid
    @Size(max = 100)
    private List<@Length() String> ids = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "search-name")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("call_mode")
    @Schema(description = "调用模式", example = "sync")
    @Length(max = 64)
    private String callMode = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "搜索工具")
    @Length(max = 64)
    private String toolChineseName = null;

    @JsonProperty("tool_desc")
    @Schema(description = "工具描述", example = "用于搜索的工具")
    @Length(max = 64)
    private String toolDesc = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user001")
    @Length(max = 256)
    private String creator = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "agent")
    @Length(max = 64)
    private String type = null;

    @JsonProperty("sub_type")
    @Schema(description = "子类型", example = "chat")
    @Length(max = 64)
    private String subType = null;

    @JsonProperty("intf_type")
    @Schema(description = "接口类型", example = "rest")
    @Length(max = 64)
    private String intfType = null;

    @JsonProperty("tag_id")
    @Schema(description = "标签ID", example = "tag-001")
    @Length(max = 256)
    private String tagId = null;

    @JsonProperty("user_id")
    @Schema(description = "用户ID", example = "user123")
    @Length(max = 256)
    private String userId = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "platform")
    @Length(max = 64)
    private String source = null;

    @JsonProperty("exclude_ids")
    @Schema(description = "排除的ID列表，最多100个", example = "[]")
    @Valid
    @Size(max = 100)
    private List<@Length() String> excludeIds = null;

    @JsonProperty("workflow_type")
    @Schema(description = "工作流类型", example = "standard")
    @Length(max = 16)
    private String workflowType = null;

    @JsonProperty("published")
    @Schema(description = "是否已发布", example = "true")
    private Boolean published = null;

    @JsonProperty("customize_node")
    @Schema(description = "是否自定义节点", example = "false")
    private Boolean customizeNode = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    @Length(max = 64)
    private String status = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "搜索条件描述")
    @Length(max = 1000)
    private String description = null;

    @JsonProperty("label")
    @Schema(description = "标签", example = "label-001")
    @Length(max = 32)
    private String label = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "default")
    private String category = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public SearchCriteria setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getId() {
        return id;
    }

    public SearchCriteria setId(String id) {
        this.id = id;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public SearchCriteria setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getName() {
        return name;
    }

    public SearchCriteria setName(String name) {
        this.name = name;
        return this;
    }

    public String getCallMode() {
        return callMode;
    }

    public SearchCriteria setCallMode(String callMode) {
        this.callMode = callMode;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public SearchCriteria setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolDesc() {
        return toolDesc;
    }

    public SearchCriteria setToolDesc(String toolDesc) {
        this.toolDesc = toolDesc;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public SearchCriteria setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getType() {
        return type;
    }

    public SearchCriteria setType(String type) {
        this.type = type;
        return this;
    }

    public String getSubType() {
        return subType;
    }

    public SearchCriteria setSubType(String subType) {
        this.subType = subType;
        return this;
    }

    public String getIntfType() {
        return intfType;
    }

    public SearchCriteria setIntfType(String intfType) {
        this.intfType = intfType;
        return this;
    }

    public String getTagId() {
        return tagId;
    }

    public SearchCriteria setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    public String getUserId() {
        return userId;
    }

    public SearchCriteria setUserId(String userId) {
        this.userId = userId;
        return this;
    }

    public String getSource() {
        return source;
    }

    public SearchCriteria setSource(String source) {
        this.source = source;
        return this;
    }

    public List<String> getExcludeIds() {
        return excludeIds;
    }

    public SearchCriteria setExcludeIds(List<String> excludeIds) {
        this.excludeIds = excludeIds;
        return this;
    }

    public String getWorkflowType() {
        return workflowType;
    }

    public SearchCriteria setWorkflowType(String workflowType) {
        this.workflowType = workflowType;
        return this;
    }

    public SearchCriteria setPublished(Boolean published) {
        this.published = published;
        return this;
    }

    public Boolean isPublished() {
        return published;
    }

    public SearchCriteria setCustomizeNode(Boolean customizeNode) {
        this.customizeNode = customizeNode;
        return this;
    }

    public Boolean isCustomizeNode() {
        return customizeNode;
    }

    public String getStatus() {
        return status;
    }

    public SearchCriteria setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public SearchCriteria setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getLabel() {
        return label;
    }

    public SearchCriteria setLabel(String label) {
        this.label = label;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public SearchCriteria setCategory(String category) {
        this.category = category;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SearchCriteria {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    callMode: ").append(toIndentedString(callMode)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolDesc: ").append(toIndentedString(toolDesc)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    subType: ").append(toIndentedString(subType)).append("\n");
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
        sb.append("    label: ").append(toIndentedString(label)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
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
        SearchCriteria searchCriteria = (SearchCriteria) o;
        return Objects.equals(this.workspaceId, searchCriteria.workspaceId) && Objects.equals(this.id,
            searchCriteria.id) && Objects.equals(this.ids, searchCriteria.ids) && Objects.equals(this.name,
            searchCriteria.name) && Objects.equals(this.callMode, searchCriteria.callMode) && Objects.equals(
            this.toolChineseName, searchCriteria.toolChineseName) && Objects.equals(this.toolDesc,
            searchCriteria.toolDesc) && Objects.equals(this.creator, searchCriteria.creator) && Objects.equals(
            this.type, searchCriteria.type) && Objects.equals(this.subType, searchCriteria.subType) && Objects.equals(
            this.intfType, searchCriteria.intfType) && Objects.equals(this.tagId, searchCriteria.tagId)
            && Objects.equals(this.userId, searchCriteria.userId) && Objects.equals(this.source, searchCriteria.source)
            && Objects.equals(this.excludeIds, searchCriteria.excludeIds) && Objects.equals(this.workflowType,
            searchCriteria.workflowType) && Objects.equals(this.published, searchCriteria.published) && Objects.equals(
            this.customizeNode, searchCriteria.customizeNode) && Objects.equals(this.status, searchCriteria.status)
            && Objects.equals(this.description, searchCriteria.description) && Objects.equals(this.label,
            searchCriteria.label) && Objects.equals(this.category, searchCriteria.category);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, id, ids, name, callMode, toolChineseName, toolDesc, creator, type, subType,
            intfType, tagId, userId, source, excludeIds, workflowType, published, customizeNode, status, description,
            label, category);
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
