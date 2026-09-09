/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListStudioSkillsQo: converted from multi query params
 */
@ApiModel(description = "ListStudioSkillsQo: converted from multi query params")

@Validated

public class ListStudioSkillsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "100")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 100;

    @JsonProperty("offset")
    @Schema(description = "查询偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("status")
    @Schema(description = "技能状态", example = "PUBLISHED")
    private String status = null;

    @JsonProperty("name")
    @Schema(description = "技能名称", example = "我的技能")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "技能描述", example = "这是一个示例技能")
    private String description = null;

    @JsonProperty("source")
    @Schema(description = "技能来源", example = "STUDIO")
    private String source = null;

    @JsonProperty("priority_status")
    @Schema(description = "优先级状态", example = "HIGH")
    private String priorityStatus = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("tag_id")
    @Schema(description = "标签ID", example = "tag_001")
    private String tagId = null;

    @JsonProperty("published_asset")
    @Schema(description = "已发布资产数量", example = "1")
    private Integer publishedAsset = null;

    public Integer getLimit() {
        return limit;
    }

    public ListStudioSkillsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListStudioSkillsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListStudioSkillsQo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListStudioSkillsQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ListStudioSkillsQo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getSource() {
        return source;
    }

    public ListStudioSkillsQo setSource(String source) {
        this.source = source;
        return this;
    }

    public String getPriorityStatus() {
        return priorityStatus;
    }

    public ListStudioSkillsQo setPriorityStatus(String priorityStatus) {
        this.priorityStatus = priorityStatus;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListStudioSkillsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getTagId() {
        return tagId;
    }

    public ListStudioSkillsQo setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    public Integer getPublishedAsset() {
        return publishedAsset;
    }

    public ListStudioSkillsQo setPublishedAsset(Integer publishedAsset) {
        this.publishedAsset = publishedAsset;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListStudioSkillsQo {\n");

        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    priorityStatus: ").append(toIndentedString(priorityStatus)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    tagId: ").append(toIndentedString(tagId)).append("\n");
        sb.append("    publishedAsset: ").append(toIndentedString(publishedAsset)).append("\n");
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
        ListStudioSkillsQo listStudioSkillsQo = (ListStudioSkillsQo) o;
        return Objects.equals(this.limit, listStudioSkillsQo.limit) && Objects.equals(this.offset,
            listStudioSkillsQo.offset) && Objects.equals(this.status, listStudioSkillsQo.status) && Objects.equals(
            this.name, listStudioSkillsQo.name) && Objects.equals(this.description, listStudioSkillsQo.description)
            && Objects.equals(this.source, listStudioSkillsQo.source) && Objects.equals(this.priorityStatus,
            listStudioSkillsQo.priorityStatus) && Objects.equals(this.workspaceId, listStudioSkillsQo.workspaceId)
            && Objects.equals(this.tagId, listStudioSkillsQo.tagId) && Objects.equals(this.publishedAsset,
            listStudioSkillsQo.publishedAsset);
    }

    @Override
    public int hashCode() {
        return Objects.hash(limit, offset, status, name, description, source, priorityStatus, workspaceId, tagId,
            publishedAsset);
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
