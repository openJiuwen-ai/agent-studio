/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ObsResp
 */

@Validated
public class ObsResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("file_name")
    @Schema(description = "文件名称", example = "示例文本")
    private String fileName = null;

    @JsonProperty("file_type")
    @Schema(description = "文件类型", example = "示例文本")
    private String fileType = null;

    @JsonProperty("content_length")
    @Schema(description = "内容长度", example = "1700000000000")
    private Long contentLength = null;

    @JsonProperty("last_modified")
    @Schema(description = "最后修改时间", example = "1700000000000")
    private Long lastModified = null;

    public String getFileName() {
        return fileName;
    }

    public ObsResp setFileName(String fileName) {
        this.fileName = fileName;
        return this;
    }

    public String getFileType() {
        return fileType;
    }

    public ObsResp setFileType(String fileType) {
        this.fileType = fileType;
        return this;
    }

    public Long getContentLength() {
        return contentLength;
    }

    public ObsResp setContentLength(Long contentLength) {
        this.contentLength = contentLength;
        return this;
    }

    public Long getLastModified() {
        return lastModified;
    }

    public ObsResp setLastModified(Long lastModified) {
        this.lastModified = lastModified;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ObsResp {\n");
        sb.append("    fileName: ").append(toIndentedString(fileName)).append("\n");
        sb.append("    fileType: ").append(toIndentedString(fileType)).append("\n");
        sb.append("    contentLength: ").append(toIndentedString(contentLength)).append("\n");
        sb.append("    lastModified: ").append(toIndentedString(lastModified)).append("\n");
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
        ObsResp obsResp = (ObsResp) o;
        return Objects.equals(this.fileName, obsResp.fileName) && Objects.equals(this.fileType, obsResp.fileType)
            && Objects.equals(this.contentLength, obsResp.contentLength) && Objects.equals(this.lastModified,
            obsResp.lastModified);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileName, fileType, contentLength, lastModified);
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
