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
 * ListWorkflowLastVersionsQo: converted from multi query params
 */
@ApiModel(description = "ListWorkflowLastVersionsQo: converted from multi query params")

@Validated

public class ListWorkflowLastVersionsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 65535L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "返回数量限制", example = "5")
    @Range(min = 1L, max = 10000L)
    private Integer limit = 5;

    @JsonProperty("id")
    @Schema(description = "工作流ID列表", example = "[\"wf_001\"]")
    @Valid
    @Size(max = 1000)
    private List<@Length(max = 128) String> id = null;

    @JsonProperty("name")
    @Schema(description = "工作流名称", example = "my_workflow")
    @Pattern(regexp = "^.{0,64}$")
    @Length(max = 192)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "工作流描述", example = "天气查询流程")
    @Length(max = 512)
    private String description = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user_001")
    @Length(max = 128)
    private String creator = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "workflow")
    @Length(max = 128)
    private String type = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListWorkflowLastVersionsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public ListWorkflowLastVersionsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListWorkflowLastVersionsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public List<String> getId() {
        return id;
    }

    public ListWorkflowLastVersionsQo setId(List<String> id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListWorkflowLastVersionsQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ListWorkflowLastVersionsQo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ListWorkflowLastVersionsQo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListWorkflowLastVersionsQo setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListWorkflowLastVersionsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        ListWorkflowLastVersionsQo listWorkflowLastVersionsQo = (ListWorkflowLastVersionsQo) o;
        return Objects.equals(this.workspaceId, listWorkflowLastVersionsQo.workspaceId) && Objects.equals(this.offset,
            listWorkflowLastVersionsQo.offset) && Objects.equals(this.limit, listWorkflowLastVersionsQo.limit)
            && Objects.equals(this.id, listWorkflowLastVersionsQo.id) && Objects.equals(this.name,
            listWorkflowLastVersionsQo.name) && Objects.equals(this.description, listWorkflowLastVersionsQo.description)
            && Objects.equals(this.creator, listWorkflowLastVersionsQo.creator) && Objects.equals(this.type,
            listWorkflowLastVersionsQo.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, offset, limit, id, name, description, creator, type);
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
