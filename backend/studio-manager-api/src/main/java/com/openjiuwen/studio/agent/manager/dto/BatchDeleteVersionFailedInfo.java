/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 批量删除版本失败详情
 */
@ApiModel(description = "批量删除版本失败详情")

@Validated

public class BatchDeleteVersionFailedInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "1787901244768", required = true)
    @NotNull
    private String versionId = null;

    @JsonProperty("error_code")
    @Schema(description = "错误码", example = "SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY")
    private String errorCode = null;

    @JsonProperty("error_msg")
    @Schema(description = "错误信息", example = "共享资源版本不允许直接删除")
    private String errorMsg = null;

    public String getVersionId() {
        return versionId;
    }

    public BatchDeleteVersionFailedInfo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public BatchDeleteVersionFailedInfo setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public BatchDeleteVersionFailedInfo setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteVersionFailedInfo {\n");

        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    errorCode: ").append(toIndentedString(errorCode)).append("\n");
        sb.append("    errorMsg: ").append(toIndentedString(errorMsg)).append("\n");
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
        BatchDeleteVersionFailedInfo batchDeleteVersionFailedInfo = (BatchDeleteVersionFailedInfo) o;
        return Objects.equals(this.versionId, batchDeleteVersionFailedInfo.versionId)
            && Objects.equals(this.errorCode, batchDeleteVersionFailedInfo.errorCode)
            && Objects.equals(this.errorMsg, batchDeleteVersionFailedInfo.errorMsg);
    }

    @Override
    public int hashCode() {
        return Objects.hash(versionId, errorCode, errorMsg);
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
