/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 文件切片列表响应
 */
@ApiModel(description = "文件切片列表响应")

@Validated

public class FileChunkListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    private Long count = null;

    @JsonProperty("file_chunk_list")
    @Schema(description = "文件分块列表", example = "[]")
    @Valid
    @Size()
    private List<FileChunkInfo> fileChunkList = null;

    public Long getCount() {
        return count;
    }

    public FileChunkListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<FileChunkInfo> getFileChunkList() {
        return fileChunkList;
    }

    public FileChunkListRsp setFileChunkList(List<FileChunkInfo> fileChunkList) {
        this.fileChunkList = fileChunkList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FileChunkListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    fileChunkList: ").append(toIndentedString(fileChunkList)).append("\n");
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
        FileChunkListRsp fileChunkListRsp = (FileChunkListRsp) o;
        return Objects.equals(this.count, fileChunkListRsp.count) && Objects.equals(this.fileChunkList,
            fileChunkListRsp.fileChunkList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, fileChunkList);
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
