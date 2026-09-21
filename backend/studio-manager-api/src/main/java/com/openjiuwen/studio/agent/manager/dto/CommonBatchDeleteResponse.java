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
 * 批量删除响应体
 */
@ApiModel(description = "批量删除响应体")

@Validated

public class CommonBatchDeleteResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("success_ids")
    @Schema(description = "是否成功", example = "[]")
    @Valid
    @Size()
    private List<@Length(min = 1, max = 10) String> successIds = null;

    @JsonProperty("failed_ids")
    @Schema(description = "是否失败", example = "[]")
    @Valid
    @Size()
    private List<@Length(min = 1, max = 10) String> failedIds = null;

    public List<String> getSuccessIds() {
        return successIds;
    }

    public CommonBatchDeleteResponse setSuccessIds(List<String> successIds) {
        this.successIds = successIds;
        return this;
    }

    public List<String> getFailedIds() {
        return failedIds;
    }

    public CommonBatchDeleteResponse setFailedIds(List<String> failedIds) {
        this.failedIds = failedIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CommonBatchDeleteResponse {\n");

        sb.append("    successIds: ").append(toIndentedString(successIds)).append("\n");
        sb.append("    failedIds: ").append(toIndentedString(failedIds)).append("\n");
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
        CommonBatchDeleteResponse commonBatchDeleteResponse = (CommonBatchDeleteResponse) o;
        return Objects.equals(this.successIds, commonBatchDeleteResponse.successIds) && Objects.equals(this.failedIds,
            commonBatchDeleteResponse.failedIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(successIds, failedIds);
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
