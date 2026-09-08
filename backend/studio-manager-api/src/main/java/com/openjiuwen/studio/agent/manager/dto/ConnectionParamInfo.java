/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ConnectionParamInfo
 */

@Validated

public class ConnectionParamInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "状态码", example = "200")
    @Length(max = 100)
    private String code = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "示例字符串")
    @Length(max = 1000)
    private String value = null;

    public String getCode() {
        return code;
    }

    public ConnectionParamInfo setCode(String code) {
        this.code = code;
        return this;
    }

    public String getValue() {
        return value;
    }

    public ConnectionParamInfo setValue(String value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ConnectionParamInfo {\n");

        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
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
        ConnectionParamInfo connectionParamInfo = (ConnectionParamInfo) o;
        return Objects.equals(this.code, connectionParamInfo.code) && Objects.equals(this.value,
            connectionParamInfo.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, value);
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
