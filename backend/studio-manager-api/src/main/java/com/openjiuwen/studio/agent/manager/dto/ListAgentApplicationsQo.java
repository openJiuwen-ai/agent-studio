/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListAgentApplicationsQo: converted from multi query params
 */
@ApiModel(description = "ListAgentApplicationsQo: converted from multi query params")

@Validated

public class ListAgentApplicationsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "100")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 100;

    @JsonProperty("name")
    @Schema(description = "应用名称", example = "my-agent")
    @Pattern(regexp = "^.{0,64}$")
    @Length(max = 192)
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "应用ID", example = "app-001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("status")
    @Schema(description = "应用状态", example = "running")
    private String status = null;

    @JsonProperty("type")
    @Schema(description = "应用类型", example = "chat")
    @Pattern(regexp = "^[a-zA-Z,]+$")
    @Length(min = 1, max = 64)
    private String type = null;

    public Integer getOffset() {
        return offset;
    }

    public ListAgentApplicationsQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListAgentApplicationsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public String getName() {
        return name;
    }

    public ListAgentApplicationsQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public ListAgentApplicationsQo setId(String id) {
        this.id = id;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ListAgentApplicationsQo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListAgentApplicationsQo setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListAgentApplicationsQo {\n");

        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        ListAgentApplicationsQo listAgentApplicationsQo = (ListAgentApplicationsQo) o;
        return Objects.equals(this.offset, listAgentApplicationsQo.offset) && Objects.equals(this.limit,
            listAgentApplicationsQo.limit) && Objects.equals(this.name, listAgentApplicationsQo.name) && Objects.equals(
            this.id, listAgentApplicationsQo.id) && Objects.equals(this.status, listAgentApplicationsQo.status)
            && Objects.equals(this.type, listAgentApplicationsQo.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(offset, limit, name, id, status, type);
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
