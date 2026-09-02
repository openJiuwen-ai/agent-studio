/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 结构化消息导入结果
 */
@ApiModel(description = "结构化消息导入结果")

@Validated

public class StructuredMessagesUploadResult implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total_count")
    @Schema(description = "总数", example = "100", required = true)
    @NotNull
    private Long totalCount = null;

    @JsonProperty("success_count")
    @Schema(description = "成功数量", example = "90", required = true)
    @NotNull
    private Long successCount = null;

    @JsonProperty("failed_count")
    @Schema(description = "失败数量", example = "10", required = true)
    @NotNull
    private Long failedCount = null;

    @JsonProperty("success_list")
    @Schema(description = "成功列表", example = "[]")
    @Valid
    @Size()
    private List<StructMessage> successList = null;

    @JsonProperty("failed_list")
    @Schema(description = "失败列表", example = "[]")
    @Valid
    @Size()
    private List<FailedStructuredMessage> failedList = null;

    public Long getTotalCount() {
        return totalCount;
    }

    public StructuredMessagesUploadResult setTotalCount(Long totalCount) {
        this.totalCount = totalCount;
        return this;
    }

    public Long getSuccessCount() {
        return successCount;
    }

    public StructuredMessagesUploadResult setSuccessCount(Long successCount) {
        this.successCount = successCount;
        return this;
    }

    public Long getFailedCount() {
        return failedCount;
    }

    public StructuredMessagesUploadResult setFailedCount(Long failedCount) {
        this.failedCount = failedCount;
        return this;
    }

    public List<StructMessage> getSuccessList() {
        return successList;
    }

    public StructuredMessagesUploadResult setSuccessList(List<StructMessage> successList) {
        this.successList = successList;
        return this;
    }

    public List<FailedStructuredMessage> getFailedList() {
        return failedList;
    }

    public StructuredMessagesUploadResult setFailedList(List<FailedStructuredMessage> failedList) {
        this.failedList = failedList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class StructuredMessagesUploadResult {\n");

        sb.append("    totalCount: ").append(toIndentedString(totalCount)).append("\n");
        sb.append("    successCount: ").append(toIndentedString(successCount)).append("\n");
        sb.append("    failedCount: ").append(toIndentedString(failedCount)).append("\n");
        sb.append("    successList: ").append(toIndentedString(successList)).append("\n");
        sb.append("    failedList: ").append(toIndentedString(failedList)).append("\n");
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
        StructuredMessagesUploadResult structuredMessagesUploadResult = (StructuredMessagesUploadResult) o;
        return Objects.equals(this.totalCount, structuredMessagesUploadResult.totalCount) && Objects.equals(
            this.successCount, structuredMessagesUploadResult.successCount) && Objects.equals(this.failedCount,
            structuredMessagesUploadResult.failedCount) && Objects.equals(this.successList,
            structuredMessagesUploadResult.successList) && Objects.equals(this.failedList,
            structuredMessagesUploadResult.failedList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalCount, successCount, failedCount, successList, failedList);
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
