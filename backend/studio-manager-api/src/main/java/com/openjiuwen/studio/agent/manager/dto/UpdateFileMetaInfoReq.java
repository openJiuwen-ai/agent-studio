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
 * 更新文档元信息请求体
 */
@ApiModel(description = "更新文档元信息请求体")

@Validated

public class UpdateFileMetaInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "示例标签")
    @Valid
    @Size(max = 20)
    private List<@Pattern(
        regexp = "^[a-zA-Z0-9\\u4e00-\\u9fa5][a-zA-Z0-9\\u4e00-\\u9fa5:\\-\\_/\\.?&=@#%+~!\\$'\\(\\),;\\*\\[\\]]{0,254}$") @Length(
        min = 1, max = 100) String> tags = null;

    public List<String> getTags() {
        return tags;
    }

    public UpdateFileMetaInfoReq setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateFileMetaInfoReq {\n");

        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
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
        UpdateFileMetaInfoReq updateFileMetaInfoReq = (UpdateFileMetaInfoReq) o;
        return Objects.equals(this.tags, updateFileMetaInfoReq.tags);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tags);
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
