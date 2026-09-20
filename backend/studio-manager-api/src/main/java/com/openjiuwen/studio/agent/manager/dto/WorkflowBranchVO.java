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
import java.util.Map;
import java.util.Objects;

/**
 * 工作流节点分支对象，任何会出现分叉的节点使用该象承载分支信息。
 */
@ApiModel(description = "工作流节点分支对象，任何会出现分叉的节点使用该象承载分支信息。")

@Validated

public class WorkflowBranchVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    @JsonProperty("configs")
    @Schema(description = "configs", example = "示例字符串")
    @Valid
    @Size()
    private Map<String, Object> configs = null;

    public String getId() {
        return id;
    }

    public WorkflowBranchVO setId(String id) {
        this.id = id;
        return this;
    }

    public Map<String, Object> getConfigs() {
        return configs;
    }

    public WorkflowBranchVO setConfigs(Map<String, Object> configs) {
        this.configs = configs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowBranchVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
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
        WorkflowBranchVO workflowBranchVO = (WorkflowBranchVO) o;
        return Objects.equals(this.id, workflowBranchVO.id) && Objects.equals(this.configs, workflowBranchVO.configs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, configs);
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
