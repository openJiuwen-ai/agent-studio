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
 * 文件列表
 */
@ApiModel(description = "文件列表")

@Validated

public class FaqFileInfoListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("file_info_list")
    @Schema(description = "文件", example = "[]")
    @Valid
    @Size()
    private List<FileInfo> fileInfoList = null;

    public Integer getCount() {
        return count;
    }

    public FaqFileInfoListRsp setCount(Integer count) {
        this.count = count;
        return this;
    }

    public List<FileInfo> getFileInfoList() {
        return fileInfoList;
    }

    public FaqFileInfoListRsp setFileInfoList(List<FileInfo> fileInfoList) {
        this.fileInfoList = fileInfoList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FaqFileInfoListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    fileInfoList: ").append(toIndentedString(fileInfoList)).append("\n");
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
        FaqFileInfoListRsp faqFileInfoListRsp = (FaqFileInfoListRsp) o;
        return Objects.equals(this.count, faqFileInfoListRsp.count) && Objects.equals(this.fileInfoList,
            faqFileInfoListRsp.fileInfoList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, fileInfoList);
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
