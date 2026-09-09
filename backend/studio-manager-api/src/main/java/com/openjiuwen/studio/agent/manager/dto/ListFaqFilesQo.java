/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * ListFaqFilesQo: converted from multi query params
 */
@ApiModel(description = "ListFaqFilesQo: converted from multi query params")

@Validated

public class ListFaqFilesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    @JsonProperty("ids")
    @Schema(description = "文件ID列表", example = "[\"file-001\"]")
    @Valid
    @Size(min = 1, max = 1000)
    private List<@Length(min = 1, max = 64) String> ids = null;

    @JsonProperty("name")
    @Schema(description = "文件名称", example = "faq.xlsx")
    @Length(max = 1024)
    private String name = null;

    @JsonProperty("status")
    @Schema(description = "文件状态", example = "ready")
    @Length(max = 128)
    private String status = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListFaqFilesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListFaqFilesQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListFaqFilesQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public ListFaqFilesQo setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListFaqFilesQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListFaqFilesQo setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListFaqFilesQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        ListFaqFilesQo listFaqFilesQo = (ListFaqFilesQo) o;
        return Objects.equals(this.workspaceId, listFaqFilesQo.workspaceId) && Objects.equals(this.offset,
            listFaqFilesQo.offset) && Objects.equals(this.limit, listFaqFilesQo.limit) && Objects.equals(this.ids,
            listFaqFilesQo.ids) && Objects.equals(this.name, listFaqFilesQo.name) && Objects.equals(this.status,
            listFaqFilesQo.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, ids, name, status);
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
