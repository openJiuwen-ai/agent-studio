/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryWorkspaceQo: converted from multi query params
 */
@ApiModel(description = "QueryWorkspaceQo: converted from multi query params")

@Validated

public class QueryWorkspaceQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("scope")
    @Schema(description = "scope", example = "示例字符串")
    private String scope = "user";

    @JsonProperty("type")
    @Schema(description = "类型", example = "example-type")
    private String type = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "示例字符串")
    private String source = null;

    public String getScope() {
        return scope;
    }

    public QueryWorkspaceQo setScope(String scope) {
        this.scope = scope;
        return this;
    }

    public String getType() {
        return type;
    }

    public QueryWorkspaceQo setType(String type) {
        this.type = type;
        return this;
    }

    public String getSource() {
        return source;
    }

    public QueryWorkspaceQo setSource(String source) {
        this.source = source;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryWorkspaceQo {\n");

        sb.append("    scope: ").append(toIndentedString(scope)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
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
        QueryWorkspaceQo queryWorkspaceQo = (QueryWorkspaceQo) o;
        return Objects.equals(this.scope, queryWorkspaceQo.scope) && Objects.equals(this.type, queryWorkspaceQo.type)
            && Objects.equals(this.source, queryWorkspaceQo.source);
    }

    @Override
    public int hashCode() {
        return Objects.hash(scope, type, source);
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
