/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * UpdateFileMetaInfoRsp
 */

@Validated

public class UpdateFileMetaInfoRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "example-id-123")
    private String fileId = null;

    public String getFileId() {
        return fileId;
    }

    public UpdateFileMetaInfoRsp setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateFileMetaInfoRsp {\n");

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
        UpdateFileMetaInfoRsp updateFileMetaInfoRsp = (UpdateFileMetaInfoRsp) o;
        return Objects.equals(this.fileId, updateFileMetaInfoRsp.fileId);
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
