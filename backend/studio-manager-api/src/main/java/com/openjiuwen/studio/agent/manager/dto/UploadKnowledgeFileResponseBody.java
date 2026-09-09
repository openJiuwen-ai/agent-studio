/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 上传文件响应体
 */
@ApiModel(description = "上传文件响应体")

@Validated

public class UploadKnowledgeFileResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "example-id-123", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String fileId = null;

    public String getFileId() {
        return fileId;
    }

    public UploadKnowledgeFileResponseBody setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UploadKnowledgeFileResponseBody {\n");

        sb.append("    fileId: ").append(toIndentedString(fileId)).append("\n");
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
        UploadKnowledgeFileResponseBody uploadKnowledgeFileResponseBody = (UploadKnowledgeFileResponseBody) o;
        return Objects.equals(this.fileId, uploadKnowledgeFileResponseBody.fileId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileId);
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
