/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceToolsTestResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("isError")
    @Schema(description = "is错误", example = "true")
    private Boolean isError = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "[]")
    @Valid
    @Size()
    private List<Object> content = null;

    public McpServiceToolsTestResp setIsError(Boolean isError) {
        this.isError = isError;
        return this;
    }

    public Boolean isIsError() {
        return isError;
    }

    public List<Object> getContent() {
        return content;
    }

    public McpServiceToolsTestResp setContent(List<Object> content) {
        this.content = content;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceToolsTestResp {\n");

        sb.append("    isError: ").append(toIndentedString(isError)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
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
        McpServiceToolsTestResp mcpServiceToolsTestResp = (McpServiceToolsTestResp) o;
        return Objects.equals(this.isError, mcpServiceToolsTestResp.isError) && Objects.equals(this.content,
            mcpServiceToolsTestResp.content);
    }

    @Override
    public int hashCode() {
        return Objects.hash(isError, content);
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
