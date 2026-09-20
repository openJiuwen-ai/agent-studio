/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 智能体列表查询请求体。
 */
@ApiModel(description = "智能体列表查询请求体。")

@Validated

public class ApplicationListReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("ids")
    @Schema(description = "智能体ID列表", example = "[\"app_001\"]")
    @Valid
    @Size(max = 100)
    private List<@Length() String> ids = null;

    @JsonProperty("name")
    @Schema(description = "智能体名称", example = "my_agent")
    @Length(min = 1, max = 64)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "智能体类型列表", example = "[\"chat\"]")
    @Valid
    @Size()
    private List<@Length() String> type = null;

    @JsonProperty("status")
    @Schema(description = "智能体状态", example = "published")
    private String status = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "分页偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "100")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 100;

    public List<String> getIds() {
        return ids;
    }

    public ApplicationListReq setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    public String getName() {
        return name;
    }

    public ApplicationListReq setName(String name) {
        this.name = name;
        return this;
    }

    public List<String> getType() {
        return type;
    }

    public ApplicationListReq setType(List<String> type) {
        this.type = type;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ApplicationListReq setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ApplicationListReq setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ApplicationListReq setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ApplicationListReq setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ApplicationListReq {\n");

        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
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
        ApplicationListReq applicationListReq = (ApplicationListReq) o;
        return Objects.equals(this.ids, applicationListReq.ids) && Objects.equals(this.name, applicationListReq.name)
            && Objects.equals(this.type, applicationListReq.type) && Objects.equals(this.status,
            applicationListReq.status) && Objects.equals(this.workspaceId, applicationListReq.workspaceId)
            && Objects.equals(this.offset, applicationListReq.offset) && Objects.equals(this.limit,
            applicationListReq.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(ids, name, type, status, workspaceId, offset, limit);
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
