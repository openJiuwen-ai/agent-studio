/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * InlineResponse404
 */

@Validated

public class InlineResponse404 implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("error")
    @Schema(description = "错误信息", example = "错误信息示例")
    private String error = null;

    public String getError() {
        return error;
    }

    public InlineResponse404 setError(String error) {
        this.error = error;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class InlineResponse404 {\n");

        sb.append("    error: ").append(toIndentedString(error)).append("\n");
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
        InlineResponse404 inlineResponse404 = (InlineResponse404) o;
        return Objects.equals(this.error, inlineResponse404.error);
    }

    @Override
    public int hashCode() {
        return Objects.hash(error);
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
