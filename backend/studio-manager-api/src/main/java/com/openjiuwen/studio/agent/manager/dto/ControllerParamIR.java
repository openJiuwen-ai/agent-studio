/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 参数ir对象。
 */
@ApiModel(description = "参数ir对象。")

@Validated

public class ControllerParamIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "参数名称", example = "param-1")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "参数描述", example = "参数描述")
    private String description = null;

    @JsonProperty("default")
    @Schema(description = "默认值", example = "default-value")
    @Valid
    private Object _default = null;

    @JsonProperty("type")
    @Schema(description = "参数类型", example = "string")
    private String type = null;

    @JsonProperty("required")
    @Schema(description = "是否必填", example = "true")
    private Boolean required = null;

    public String getName() {
        return name;
    }

    public ControllerParamIR setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerParamIR setDescription(String description) {
        this.description = description;
        return this;
    }

    public Object getDefault() {
        return _default;
    }

    public ControllerParamIR setDefault(Object _default) {
        this._default = _default;
        return this;
    }

    public String getType() {
        return type;
    }

    public ControllerParamIR setType(String type) {
        this.type = type;
        return this;
    }

    public ControllerParamIR setRequired(Boolean required) {
        this.required = required;
        return this;
    }

    public Boolean isRequired() {
        return required;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerParamIR {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    _default: ").append(toIndentedString(_default)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        ControllerParamIR controllerParamIR = (ControllerParamIR) o;
        return Objects.equals(this.name, controllerParamIR.name) && Objects.equals(this.description,
            controllerParamIR.description) && Objects.equals(this._default, controllerParamIR._default)
            && Objects.equals(this.type, controllerParamIR.type) && Objects.equals(this.required,
            controllerParamIR.required);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, _default, type, required);
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
