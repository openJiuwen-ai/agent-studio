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
 * ListFaqFileChunksReq
 */

@Validated

public class ListFaqFileChunksReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "example-id-123")
    private String fileId = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "0")
    private Integer pageNum = null;

    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "0")
    private Integer pageSize = null;

    public String getFileId() {
        return fileId;
    }

    public ListFaqFileChunksReq setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListFaqFileChunksReq setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListFaqFileChunksReq setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListFaqFileChunksReq {\n");

        sb.append("    fileId: ").append(toIndentedString(fileId)).append("\n");
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
        ListFaqFileChunksReq listFaqFileChunksReq = (ListFaqFileChunksReq) o;
        return Objects.equals(this.fileId, listFaqFileChunksReq.fileId) && Objects.equals(this.pageNum,
            listFaqFileChunksReq.pageNum) && Objects.equals(this.pageSize, listFaqFileChunksReq.pageSize);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileId, pageNum, pageSize);
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
