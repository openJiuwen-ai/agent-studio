/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ControllerConfigIRGlobalVariables
 */

@Validated

public class ControllerConfigIRGlobalVariables implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "全局变量名称", example = "var_name")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "全局变量描述", example = "变量描述信息")
    private String description = null;

    @JsonProperty("default")
    @Schema(description = "默认值", example = "default_value")
    @Valid
    private Object _default = null;

    @JsonProperty("type")
    @Schema(description = "变量类型", example = "string")
    private String type = null;

    public String getName() {
        return name;
    }

    public ControllerConfigIRGlobalVariables setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerConfigIRGlobalVariables setDescription(String description) {
        this.description = description;
        return this;
    }

    public Object getDefault() {
        return _default;
    }

    public ControllerConfigIRGlobalVariables setDefault(Object _default) {
        this._default = _default;
        return this;
    }

    public String getType() {
        return type;
    }

    public ControllerConfigIRGlobalVariables setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerConfigIRGlobalVariables {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    _default: ").append(toIndentedString(_default)).append("\n");
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
        ControllerConfigIRGlobalVariables controllerConfigIRGlobalVariables = (ControllerConfigIRGlobalVariables) o;
        return Objects.equals(this.name, controllerConfigIRGlobalVariables.name) && Objects.equals(this.description,
            controllerConfigIRGlobalVariables.description) && Objects.equals(this._default,
            controllerConfigIRGlobalVariables._default) && Objects.equals(this.type,
            controllerConfigIRGlobalVariables.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, _default, type);
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
