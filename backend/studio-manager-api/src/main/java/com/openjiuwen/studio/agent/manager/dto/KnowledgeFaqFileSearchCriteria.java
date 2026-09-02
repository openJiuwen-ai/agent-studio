/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 知识库Faq文件列表查询条件。
 */
@ApiModel(description = "知识库Faq文件列表查询条件。")

@Validated

public class KnowledgeFaqFileSearchCriteria implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_name")
    @Schema(description = "文件名称", example = "示例名称")
    @Length(max = 1024)
    private String fileName = null;

    @JsonProperty("file_status")
    @Schema(description = "文件", example = "active")
    @Length(max = 128)
    private String fileStatus = null;

    @JsonProperty("ids")
    @Schema(description = "ids", example = "[]")
    @Valid
    @Size(min = 1, max = 1000)
    private List<@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Length(min = 1, max = 64) String> ids = null;

    public String getFileName() {
        return fileName;
    }

    public KnowledgeFaqFileSearchCriteria setFileName(String fileName) {
        this.fileName = fileName;
        return this;
    }

    public String getFileStatus() {
        return fileStatus;
    }

    public KnowledgeFaqFileSearchCriteria setFileStatus(String fileStatus) {
        this.fileStatus = fileStatus;
        return this;
    }

    public List<String> getIds() {
        return ids;
    }

    public KnowledgeFaqFileSearchCriteria setIds(List<String> ids) {
        this.ids = ids;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeFaqFileSearchCriteria {\n");

        sb.append("    fileName: ").append(toIndentedString(fileName)).append("\n");
        sb.append("    fileStatus: ").append(toIndentedString(fileStatus)).append("\n");
        sb.append("    ids: ").append(toIndentedString(ids)).append("\n");
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
        KnowledgeFaqFileSearchCriteria knowledgeFaqFileSearchCriteria = (KnowledgeFaqFileSearchCriteria) o;
        return Objects.equals(this.fileName, knowledgeFaqFileSearchCriteria.fileName) && Objects.equals(this.fileStatus,
            knowledgeFaqFileSearchCriteria.fileStatus) && Objects.equals(this.ids, knowledgeFaqFileSearchCriteria.ids);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileName, fileStatus, ids);
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
