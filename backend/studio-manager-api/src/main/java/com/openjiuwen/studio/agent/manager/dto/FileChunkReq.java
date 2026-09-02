/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识文件分片请求
 */
@ApiModel(description = "知识文件分片请求")

@Validated

public class FileChunkReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("title")
    @Schema(description = "标题", example = "文档标题")
    @Length(max = 10000)
    private String title = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "文档内容", required = true)
    @NotBlank
    @Length(min = 1, max = 10000)
    private String content = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    @Range(min = 1L, max = 65535L)
    private Long pageNum = null;

    @JsonProperty("component_num")
    @Schema(description = "组件编号", example = "1")
    @Range(min = 1L, max = 65535L)
    private Long componentNum = null;

    public String getTitle() {
        return title;
    }

    public FileChunkReq setTitle(String title) {
        this.title = title;
        return this;
    }

    public String getContent() {
        return content;
    }

    public FileChunkReq setContent(String content) {
        this.content = content;
        return this;
    }

    public Long getPageNum() {
        return pageNum;
    }

    public FileChunkReq setPageNum(Long pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Long getComponentNum() {
        return componentNum;
    }

    public FileChunkReq setComponentNum(Long componentNum) {
        this.componentNum = componentNum;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FileChunkReq {\n");

        sb.append("    title: ").append(toIndentedString(title)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    componentNum: ").append(toIndentedString(componentNum)).append("\n");
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
        FileChunkReq fileChunkReq = (FileChunkReq) o;
        return Objects.equals(this.title, fileChunkReq.title) && Objects.equals(this.content, fileChunkReq.content)
            && Objects.equals(this.pageNum, fileChunkReq.pageNum) && Objects.equals(this.componentNum,
            fileChunkReq.componentNum);
    }

    @Override
    public int hashCode() {
        return Objects.hash(title, content, pageNum, componentNum);
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
