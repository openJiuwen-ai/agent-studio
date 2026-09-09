/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListPromptTasksQo: converted from multi query params
 */
@ApiModel(description = "ListPromptTasksQo: converted from multi query params")

@Validated
public class ListPromptTasksQo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "running")
    @Pattern(regexp = "^(DRAFT|WAITING|RUNNING|SUCCESS|FAILED|PAUSE|PAUSING)$")
    private String status = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "text")
    private String type = null;

    @JsonProperty("pageNum")
    @Schema(description = "页数量", example = "1")
    @Range(min = 1L)
    private Integer pageNum = 1;

    @JsonProperty("pageSize")
    @Schema(description = "页大小", example = "1")
    @Range(min = 10L, max = 100L)
    private Integer pageSize = 10;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListPromptTasksQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListPromptTasksQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListPromptTasksQo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListPromptTasksQo setType(String type) {
        this.type = type;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListPromptTasksQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListPromptTasksQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListPromptTasksQo {\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
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
        ListPromptTasksQo listPromptTasksQo = (ListPromptTasksQo) o;
        return Objects.equals(this.workspaceId, listPromptTasksQo.workspaceId) && Objects.equals(this.name,
            listPromptTasksQo.name) && Objects.equals(this.status, listPromptTasksQo.status) && Objects.equals(
            this.type, listPromptTasksQo.type) && Objects.equals(this.pageNum, listPromptTasksQo.pageNum)
            && Objects.equals(this.pageSize, listPromptTasksQo.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, name, status, type, pageNum, pageSize);
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
