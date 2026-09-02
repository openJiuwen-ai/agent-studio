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
 * 工作流中的渠道变量。
 */
@ApiModel(description = "工作流中的渠道变量。")

@Validated

public class WorkFlowEnv implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "变量名称", example = "api_key")
    private String name = null;

    @JsonProperty("cn_name")
    @Schema(description = "变量中文名称", example = "API密钥")
    private String cnName = null;

    @JsonProperty("type")
    @Schema(description = "变量类型", example = "string")
    private String type = null;

    @JsonProperty("description")
    @Schema(description = "变量描述", example = "API认证密钥")
    private String description = null;

    @JsonProperty("required")
    @Schema(description = "是否必填", example = "true")
    private Boolean required = null;

    public String getName() {
        return name;
    }

    public WorkFlowEnv setName(String name) {
        this.name = name;
        return this;
    }

    public String getCnName() {
        return cnName;
    }

    public WorkFlowEnv setCnName(String cnName) {
        this.cnName = cnName;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkFlowEnv setType(String type) {
        this.type = type;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkFlowEnv setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkFlowEnv setRequired(Boolean required) {
        this.required = required;
        return this;
    }

    public Boolean isRequired() {
        return required;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkFlowEnv {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    cnName: ").append(toIndentedString(cnName)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    required: ").append(toIndentedString(required)).append("\n");
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
        WorkFlowEnv workFlowEnv = (WorkFlowEnv) o;
        return Objects.equals(this.name, workFlowEnv.name) && Objects.equals(this.cnName, workFlowEnv.cnName)
            && Objects.equals(this.type, workFlowEnv.type) && Objects.equals(this.description, workFlowEnv.description)
            && Objects.equals(this.required, workFlowEnv.required);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, cnName, type, description, required);
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
