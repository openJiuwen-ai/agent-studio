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
 * SuccessInfo
 */

@Validated

public class SuccessInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("message")
    @Schema(description = "消息", example = "操作成功")
    private String message = null;

    public String getMessage() {
        return message;
    }

    public SuccessInfo setMessage(String message) {
        this.message = message;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SuccessInfo {\n");

        sb.append("    message: ").append(toIndentedString(message)).append("\n");
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
        SuccessInfo successInfo = (SuccessInfo) o;
        return Objects.equals(this.message, successInfo.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(message);
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
