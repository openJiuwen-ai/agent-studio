/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.util.List;
import java.util.Objects;

/**
 * 完整错误信息
 */
@ApiModel(description = "完整错误信息")
@Validated
public class ErrorRsp {
    @JsonProperty("error_code")
    @Schema(description = "错误码", example = "400")
    private String errorCode = null;

    @JsonProperty("error_msg")
    @Schema(description = "错误消息", example = "参数校验失败")
    private String errorMsg = null;

    @JsonProperty("error_reason")
    @Schema(description = "错误原因", example = "name不能为空")
    private String errorReason = null;

    @JsonProperty("error_suggestion")
    @Schema(description = "修复建议", example = "请提供name参数")
    private String errorSuggestion = null;

    @JsonProperty("details")
    @Schema(description = "错误详情列表", example = "[]")
    @Valid
    @Size()
    private List<ErrorDetail> details = null;

    public String getErrorCode() {
        return errorCode;
    }

    public ErrorRsp setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public ErrorRsp setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
        return this;
    }

    public String getErrorReason() {
        return errorReason;
    }

    public ErrorRsp setErrorReason(String errorReason) {
        this.errorReason = errorReason;
        return this;
    }

    public String getErrorSuggestion() {
        return errorSuggestion;
    }

    public ErrorRsp setErrorSuggestion(String errorSuggestion) {
        this.errorSuggestion = errorSuggestion;
        return this;
    }

    public List<ErrorDetail> getDetails() {
        return details;
    }

    public ErrorRsp setDetails(List<ErrorDetail> details) {
        this.details = details;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ErrorRsp {\n");

        sb.append("    errorCode: ").append(toIndentedString(errorCode)).append("\n");
        sb.append("    errorMsg: ").append(toIndentedString(errorMsg)).append("\n");
        sb.append("    errorReason: ").append(toIndentedString(errorReason)).append("\n");
        sb.append("    errorSuggestion: ").append(toIndentedString(errorSuggestion)).append("\n");
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
        ErrorRsp errorRsp = (ErrorRsp) o;
        return Objects.equals(this.errorCode, errorRsp.errorCode) && Objects.equals(this.errorMsg, errorRsp.errorMsg)
            && Objects.equals(this.errorReason, errorRsp.errorReason) && Objects.equals(this.errorSuggestion,
            errorRsp.errorSuggestion) && Objects.equals(this.details, errorRsp.details);
    }

    @Override
    public int hashCode() {
        return Objects.hash(errorCode, errorMsg, errorReason, errorSuggestion, details);
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
