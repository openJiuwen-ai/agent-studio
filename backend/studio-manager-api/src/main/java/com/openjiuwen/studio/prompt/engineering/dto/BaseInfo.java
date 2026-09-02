/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * BaseInfo
 */

@Validated
public class BaseInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("code")
    @Schema(description = "编码", example = "1")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "示例文本")
    private String message = null;

    public String getId() {
        return id;
    }

    public BaseInfo setId(String id) {
        this.id = id;
        return this;
    }

    public Integer getCode() {
        return code;
    }

    public BaseInfo setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public BaseInfo setMessage(String message) {
        this.message = message;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BaseInfo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
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
        BaseInfo baseInfo = (BaseInfo) o;
        return Objects.equals(this.id, baseInfo.id) && Objects.equals(this.code, baseInfo.code) && Objects.equals(
            this.message, baseInfo.message);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, code, message);
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
