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
 * 引用和归属。
 */
@ApiModel(description = "引用和归属。")

@Validated

public class Reference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("switch")
    @Schema(description = "是否启用引用和归属", example = "false")
    private Boolean _switch = false;

    @JsonProperty("json_format")
    @Schema(description = "是否以JSON格式输出引用", example = "false")
    private Boolean jsonFormat = false;

    public Reference setSwitch(Boolean _switch) {
        this._switch = _switch;
        return this;
    }

    public Boolean isSwitch() {
        return _switch;
    }

    public Reference setJsonFormat(Boolean jsonFormat) {
        this.jsonFormat = jsonFormat;
        return this;
    }

    public Boolean isJsonFormat() {
        return jsonFormat;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Reference {\n");

        sb.append("    _switch: ").append(toIndentedString(_switch)).append("\n");
        sb.append("    jsonFormat: ").append(toIndentedString(jsonFormat)).append("\n");
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
        Reference reference = (Reference) o;
        return Objects.equals(this._switch, reference._switch) && Objects.equals(this.jsonFormat, reference.jsonFormat);
    }

    @Override
    public int hashCode() {
        return Objects.hash(_switch, jsonFormat);
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
