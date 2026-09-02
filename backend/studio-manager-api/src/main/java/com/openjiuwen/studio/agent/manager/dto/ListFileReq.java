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
 * ListFileReq
 */

@Validated

public class ListFileReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_name")
    @Schema(description = "文件名称", example = "document.pdf")
    private String fileName = null;

    @JsonProperty("file_type")
    @Schema(description = "文件类型", example = "pdf")
    private String fileType = null;

    @JsonProperty("file_status")
    @Schema(description = "文件状态", example = "uploaded")
    private String fileStatus = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    private Integer pageNum = null;

    @JsonProperty("page_size")
    @Schema(description = "每页大小", example = "10")
    private Integer pageSize = null;

    public String getFileName() {
        return fileName;
    }

    public ListFileReq setFileName(String fileName) {
        this.fileName = fileName;
        return this;
    }

    public String getFileType() {
        return fileType;
    }

    public ListFileReq setFileType(String fileType) {
        this.fileType = fileType;
        return this;
    }

    public String getFileStatus() {
        return fileStatus;
    }

    public ListFileReq setFileStatus(String fileStatus) {
        this.fileStatus = fileStatus;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListFileReq setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListFileReq setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListFileReq {\n");

        sb.append("    fileName: ").append(toIndentedString(fileName)).append("\n");
        sb.append("    fileType: ").append(toIndentedString(fileType)).append("\n");
        sb.append("    fileStatus: ").append(toIndentedString(fileStatus)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
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
        ListFileReq listFileReq = (ListFileReq) o;
        return Objects.equals(this.fileName, listFileReq.fileName) && Objects.equals(this.fileType,
            listFileReq.fileType) && Objects.equals(this.fileStatus, listFileReq.fileStatus) && Objects.equals(
            this.pageNum, listFileReq.pageNum) && Objects.equals(this.pageSize, listFileReq.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileName, fileType, fileStatus, pageNum, pageSize);
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
