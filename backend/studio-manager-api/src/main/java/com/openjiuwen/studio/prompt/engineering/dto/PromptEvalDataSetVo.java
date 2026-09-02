/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 数据集详情
 */
@ApiModel(description = "数据集详情")

@Validated
public class PromptEvalDataSetVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("workspaceId")
    @Schema(description = "工作空间ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String workspaceId = null;

    @JsonProperty("projectId")
    @Schema(description = "项目ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String projectId = null;

    @JsonProperty("boundTaskIds")
    @Schema(description = "bound任务Ids", example = "")
    @Valid
    private List<@Length() String> boundTaskIds = null;

    @JsonProperty("items")
    @Schema(description = "项列表", example = "")
    @Valid
    private List<PromptEvalDataItem> items = null;

    @JsonProperty("itemTotal")
    @Schema(description = "项总数", example = "1")
    private Integer itemTotal = null;

    @JsonProperty("itemIndex")
    @Schema(description = "项Index", example = "1")
    private Integer itemIndex = null;

    @JsonProperty("pageSize")
    @Schema(description = "页大小", example = "1")
    private Integer pageSize = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "示例文本")
    private String message = null;

    public String getId() {
        return id;
    }

    public PromptEvalDataSetVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public PromptEvalDataSetVo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public PromptEvalDataSetVo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public List<String> getBoundTaskIds() {
        return boundTaskIds;
    }

    public PromptEvalDataSetVo setBoundTaskIds(List<String> boundTaskIds) {
        this.boundTaskIds = boundTaskIds;
        return this;
    }

    public List<PromptEvalDataItem> getItems() {
        return items;
    }

    public PromptEvalDataSetVo setItems(List<PromptEvalDataItem> items) {
        this.items = items;
        return this;
    }

    public Integer getItemTotal() {
        return itemTotal;
    }

    public PromptEvalDataSetVo setItemTotal(Integer itemTotal) {
        this.itemTotal = itemTotal;
        return this;
    }

    public Integer getItemIndex() {
        return itemIndex;
    }

    public PromptEvalDataSetVo setItemIndex(Integer itemIndex) {
        this.itemIndex = itemIndex;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public PromptEvalDataSetVo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public PromptEvalDataSetVo setMessage(String message) {
        this.message = message;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptEvalDataSetVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    boundTaskIds: ").append(toIndentedString(boundTaskIds)).append("\n");
        sb.append("    items: ").append(toIndentedString(items)).append("\n");
        sb.append("    itemTotal: ").append(toIndentedString(itemTotal)).append("\n");
        sb.append("    itemIndex: ").append(toIndentedString(itemIndex)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
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
        PromptEvalDataSetVo promptEvalDataSetVo = (PromptEvalDataSetVo) o;
        return Objects.equals(this.id, promptEvalDataSetVo.id) && Objects.equals(this.workspaceId,
            promptEvalDataSetVo.workspaceId) && Objects.equals(this.projectId, promptEvalDataSetVo.projectId)
            && Objects.equals(this.boundTaskIds, promptEvalDataSetVo.boundTaskIds) && Objects.equals(this.items,
            promptEvalDataSetVo.items) && Objects.equals(this.itemTotal, promptEvalDataSetVo.itemTotal)
            && Objects.equals(this.itemIndex, promptEvalDataSetVo.itemIndex) && Objects.equals(this.pageSize,
            promptEvalDataSetVo.pageSize) && Objects.equals(this.message, promptEvalDataSetVo.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, workspaceId, projectId, boundTaskIds, items, itemTotal, itemIndex, pageSize, message);
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
