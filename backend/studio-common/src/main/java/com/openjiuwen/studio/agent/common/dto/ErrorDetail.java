/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.util.Objects;

/**
 * 错误信息
 */
@ApiModel(description = "错误信息")
@Validated
public class ErrorDetail {
    @JsonProperty("error_code")
    @Schema(description = "错误码", example = "400")
    private String errorCode = null;

    @JsonProperty("error_msg")
    @Schema(description = "错误消息", example = "参数校验失败")
    private String errorMsg = null;

    public String getErrorCode() {
        return errorCode;
    }

    public ErrorDetail setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public ErrorDetail setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ErrorDetail {\n");

        sb.append("    errorCode: ").append(toIndentedString(errorCode)).append("\n");
        sb.append("    errorMsg: ").append(toIndentedString(errorMsg)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        ErrorDetail errorDetail = (ErrorDetail) obj;
        return Objects.equals(this.errorCode, errorDetail.errorCode) && Objects.equals(this.errorMsg,
            errorDetail.errorMsg);
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, errorMsg);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}
