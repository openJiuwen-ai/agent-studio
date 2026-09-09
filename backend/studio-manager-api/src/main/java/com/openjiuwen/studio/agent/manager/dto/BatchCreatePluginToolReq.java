/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量创建工具请求体
 */
@ApiModel(description = "批量创建工具请求体")

@Validated

public class BatchCreatePluginToolReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 100)
    private List<CreatePluginToolReq> tools = new ArrayList<CreatePluginToolReq>();

    public List<CreatePluginToolReq> getTools() {
        return tools;
    }

    public BatchCreatePluginToolReq setTools(List<CreatePluginToolReq> tools) {
        this.tools = tools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchCreatePluginToolReq {\n");

        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
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
        BatchCreatePluginToolReq batchCreatePluginToolReq = (BatchCreatePluginToolReq) o;
        return Objects.equals(this.tools, batchCreatePluginToolReq.tools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tools);
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
