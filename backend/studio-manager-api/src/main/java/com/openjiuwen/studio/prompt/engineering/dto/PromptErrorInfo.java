/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 错误信息
 */
@ApiModel(description = "错误信息")

@Validated
public class PromptErrorInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("code")
    @Schema(description = "编码", example = "1")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "示例文本")
    private String message = null;

    @JsonProperty("details")
    @Schema(description = "详情", example = "示例文本")
    private String details = null;

    public Integer getCode() {
        return code;
    }

    public PromptErrorInfo setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public PromptErrorInfo setMessage(String message) {
        this.message = message;
        return this;
    }

    public String getDetails() {
        return details;
    }

    public PromptErrorInfo setDetails(String details) {
        this.details = details;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptErrorInfo {\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
        sb.append("    details: ").append(toIndentedString(details)).append("\n");
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
        PromptErrorInfo promptErrorInfo = (PromptErrorInfo) o;
        return Objects.equals(this.code, promptErrorInfo.code) && Objects.equals(this.message, promptErrorInfo.message)
            && Objects.equals(this.details, promptErrorInfo.details);
    }

    @Override
    public int hashCode() {
        return Objects.hash(code, message, details);
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
