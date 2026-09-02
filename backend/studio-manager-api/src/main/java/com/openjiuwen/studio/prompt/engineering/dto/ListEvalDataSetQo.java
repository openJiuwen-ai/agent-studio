/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListEvalDataSetQo: converted from multi query params
 */
@ApiModel(description = "ListEvalDataSetQo: converted from multi query params")

@Validated
public class ListEvalDataSetQo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("pageNum")
    @Schema(description = "页数量", example = "1")
    @Range(min = 1L)
    private Integer pageNum = 1;

    @JsonProperty("pageSize")
    @Schema(description = "页大小", example = "1")
    @Range(min = 10L, max = 100L)
    private Integer pageSize = 20;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListEvalDataSetQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListEvalDataSetQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListEvalDataSetQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListEvalDataSetQo {\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ListEvalDataSetQo listEvalDataSetQo = (ListEvalDataSetQo) o;
        return Objects.equals(this.workspaceId, listEvalDataSetQo.workspaceId) && Objects.equals(this.pageNum,
            listEvalDataSetQo.pageNum) && Objects.equals(this.pageSize, listEvalDataSetQo.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, pageNum, pageSize);
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
