/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 导入意图响应体
 */
@ApiModel(description = "导入意图响应体")

@Validated

public class ComplexIntentImportRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("succeed_len")
    @Schema(description = "导入成功数量", example = "10")
    private Integer succeedLen = 0;

    @JsonProperty("failed_len")
    @Schema(description = "导入失败数量", example = "2")
    private Integer failedLen = 0;

    @JsonProperty("success")
    @Schema(description = "是否成功", example = "true")
    private Boolean success = false;

    @JsonProperty("intent_ids")
    @Schema(description = "意图ID列表", example = "[\"intent_001\"]")
    @Valid
    @Size()
    private List<@Length() String> intentIds = null;

    public Integer getSucceedLen() {
        return succeedLen;
    }

    public ComplexIntentImportRsp setSucceedLen(Integer succeedLen) {
        this.succeedLen = succeedLen;
        return this;
    }

    public Integer getFailedLen() {
        return failedLen;
    }

    public ComplexIntentImportRsp setFailedLen(Integer failedLen) {
        this.failedLen = failedLen;
        return this;
    }

    public ComplexIntentImportRsp setSuccess(Boolean success) {
        this.success = success;
        return this;
    }

    public Boolean isSuccess() {
        return success;
    }

    public List<String> getIntentIds() {
        return intentIds;
    }

    public ComplexIntentImportRsp setIntentIds(List<String> intentIds) {
        this.intentIds = intentIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ComplexIntentImportRsp {\n");

        sb.append("    succeedLen: ").append(toIndentedString(succeedLen)).append("\n");
        sb.append("    failedLen: ").append(toIndentedString(failedLen)).append("\n");
        sb.append("    success: ").append(toIndentedString(success)).append("\n");
        sb.append("    intentIds: ").append(toIndentedString(intentIds)).append("\n");
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
        ComplexIntentImportRsp complexIntentImportRsp = (ComplexIntentImportRsp) o;
        return Objects.equals(this.succeedLen, complexIntentImportRsp.succeedLen) && Objects.equals(this.failedLen,
            complexIntentImportRsp.failedLen) && Objects.equals(this.success, complexIntentImportRsp.success)
            && Objects.equals(this.intentIds, complexIntentImportRsp.intentIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(succeedLen, failedLen, success, intentIds);
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
