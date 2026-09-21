/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建知识文档切片响应体
 */
@ApiModel(description = "创建知识文档切片响应体")

@Validated

public class CreateFileChunkRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("title")
    @Schema(description = "标题", example = "标题示例", required = true)
    @NotBlank
    @Length(min = 1, max = 10000)
    private String title = null;

    public String getTitle() {
        return title;
    }

    public CreateFileChunkRsp setTitle(String title) {
        this.title = title;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateFileChunkRsp {\n");

        sb.append("    title: ").append(toIndentedString(title)).append("\n");
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
        CreateFileChunkRsp createFileChunkRsp = (CreateFileChunkRsp) o;
        return Objects.equals(this.title, createFileChunkRsp.title);
    }

    @Override
    public int hashCode() {
        return Objects.hash(title);
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
