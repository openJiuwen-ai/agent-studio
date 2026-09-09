/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库文件列表查询条件。
 */
@ApiModel(description = "知识库文件列表查询条件。")

@Validated

public class KnowledgeFileSearchCriteria implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_name")
    @Schema(description = "文件名称", example = "示例名称")
    @Length(max = 1024)
    private String fileName = null;

    @JsonProperty("file_type")
    @Schema(description = "文件类型", example = "example-type")
    @Pattern(regexp = "^[a-zA-Z,]*$")
    @Length(max = 128)
    private String fileType = null;

    @JsonProperty("file_status")
    @Schema(description = "文件", example = "active")
    @Length(max = 128)
    private String fileStatus = null;

    public String getFileName() {
        return fileName;
    }

    public KnowledgeFileSearchCriteria setFileName(String fileName) {
        this.fileName = fileName;
        return this;
    }

    public String getFileType() {
        return fileType;
    }

    public KnowledgeFileSearchCriteria setFileType(String fileType) {
        this.fileType = fileType;
        return this;
    }

    public String getFileStatus() {
        return fileStatus;
    }

    public KnowledgeFileSearchCriteria setFileStatus(String fileStatus) {
        this.fileStatus = fileStatus;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeFileSearchCriteria {\n");

        sb.append("    fileName: ").append(toIndentedString(fileName)).append("\n");
        sb.append("    fileType: ").append(toIndentedString(fileType)).append("\n");
        sb.append("    fileStatus: ").append(toIndentedString(fileStatus)).append("\n");
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
        KnowledgeFileSearchCriteria knowledgeFileSearchCriteria = (KnowledgeFileSearchCriteria) o;
        return Objects.equals(this.fileName, knowledgeFileSearchCriteria.fileName) && Objects.equals(this.fileType,
            knowledgeFileSearchCriteria.fileType) && Objects.equals(this.fileStatus,
            knowledgeFileSearchCriteria.fileStatus);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileName, fileType, fileStatus);
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
