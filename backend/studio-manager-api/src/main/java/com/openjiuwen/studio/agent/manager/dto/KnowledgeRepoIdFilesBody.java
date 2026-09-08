/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;

import org.springframework.core.io.Resource;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * KnowledgeRepoIdFilesBody
 */

@Validated

public class KnowledgeRepoIdFilesBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file")
    @Schema(description = "文件", example = "file-content", required = true)
    @NotBlank
    private Resource file = null;

    public Resource getFile() {
        return file;
    }

    public KnowledgeRepoIdFilesBody setFile(Resource file) {
        this.file = file;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeRepoIdFilesBody {\n");

        sb.append("    file: ").append(toIndentedString(file)).append("\n");
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
        KnowledgeRepoIdFilesBody knowledgeRepoIdFilesBody = (KnowledgeRepoIdFilesBody) o;
        return Objects.equals(this.file, knowledgeRepoIdFilesBody.file);
    }

    @Override
    public int hashCode() {
        return Objects.hash(file);
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
