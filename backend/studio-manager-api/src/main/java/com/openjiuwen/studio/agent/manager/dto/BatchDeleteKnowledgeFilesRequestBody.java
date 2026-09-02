/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 批量删除知识文件请求体
 */
@ApiModel(description = "批量删除知识文件请求体")

@Validated

public class BatchDeleteKnowledgeFilesRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_ids")
    @Schema(description = "文件", example = "[]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 1000)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(min = 1, max = 64) String> fileIds
        = new ArrayList<String>();

    public List<@Size(min = 1, max = 1000) String> getFileIds() {
        return fileIds;
    }

    public BatchDeleteKnowledgeFilesRequestBody setFileIds(List<@Size(min = 1, max = 1000) String> fileIds) {
        this.fileIds = fileIds;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class BatchDeleteKnowledgeFilesRequestBody {\n");

        sb.append("    fileIds: ").append(toIndentedString(fileIds)).append("\n");
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
        BatchDeleteKnowledgeFilesRequestBody batchDeleteKnowledgeFilesRequestBody
            = (BatchDeleteKnowledgeFilesRequestBody) o;
        return Objects.equals(this.fileIds, batchDeleteKnowledgeFilesRequestBody.fileIds);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileIds);
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
