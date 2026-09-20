/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 知识文件分片信息
 */
@ApiModel(description = "知识文件分片信息")

@Validated

public class FileChunkInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "分片ID", example = "chunk_001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String id = null;

    @JsonProperty("content")
    @Schema(description = "分片内容", example = "这是分片文本内容", required = true)
    @NotBlank
    @Length(min = 1, max = 65535)
    private String content = null;

    @JsonProperty("title")
    @Schema(description = "分片标题", example = "第一章 概述", required = true)
    @NotBlank
    @Length(max = 65535)
    private String title = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    private Long pageNum = null;

    @JsonProperty("component_num")
    @Schema(description = "组件编号", example = "1")
    private Long componentNum = null;

    @JsonProperty("timestamp")
    @Schema(description = "时间戳", example = "1717200000000")
    @Length(max = 13)
    private String timestamp = null;

    @JsonProperty("knowledge_repo_id")
    @Schema(description = "知识库ID", example = "repo_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String knowledgeRepoId = null;

    @JsonProperty("image_ids")
    @Schema(description = "图片ID列表", example = "[\"img_001\"]")
    @Valid
    @Size(max = 100)
    private List<@Length(min = 1, max = 100) String> imageIds = null;

    @JsonProperty("image_paths")
    @Schema(description = "图片路径列表", example = "[\"/images/img_001.png\"]")
    @Valid
    @Size(max = 100)
    private List<@Length(min = 1, max = 2000) String> imagePaths = null;

    public String getId() {
        return id;
    }

    public FileChunkInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getContent() {
        return content;
    }

    public FileChunkInfo setContent(String content) {
        this.content = content;
        return this;
    }

    public String getTitle() {
        return title;
    }

    public FileChunkInfo setTitle(String title) {
        this.title = title;
        return this;
    }

    public Long getPageNum() {
        return pageNum;
    }

    public FileChunkInfo setPageNum(Long pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Long getComponentNum() {
        return componentNum;
    }

    public FileChunkInfo setComponentNum(Long componentNum) {
        this.componentNum = componentNum;
        return this;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public FileChunkInfo setTimestamp(String timestamp) {
        this.timestamp = timestamp;
        return this;
    }

    public String getKnowledgeRepoId() {
        return knowledgeRepoId;
    }

    public FileChunkInfo setKnowledgeRepoId(String knowledgeRepoId) {
        this.knowledgeRepoId = knowledgeRepoId;
        return this;
    }

    public List<String> getImageIds() {
        return imageIds;
    }

    public FileChunkInfo setImageIds(List<String> imageIds) {
        this.imageIds = imageIds;
        return this;
    }

    public List<String> getImagePaths() {
        return imagePaths;
    }

    public FileChunkInfo setImagePaths(List<String> imagePaths) {
        this.imagePaths = imagePaths;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class FileChunkInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    title: ").append(toIndentedString(title)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    componentNum: ").append(toIndentedString(componentNum)).append("\n");
        sb.append("    timestamp: ").append(toIndentedString(timestamp)).append("\n");
        sb.append("    knowledgeRepoId: ").append(toIndentedString(knowledgeRepoId)).append("\n");
        sb.append("    imageIds: ").append(toIndentedString(imageIds)).append("\n");
        sb.append("    imagePaths: ").append(toIndentedString(imagePaths)).append("\n");
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
        FileChunkInfo fileChunkInfo = (FileChunkInfo) o;
        return Objects.equals(this.id, fileChunkInfo.id) && Objects.equals(this.content, fileChunkInfo.content)
            && Objects.equals(this.title, fileChunkInfo.title) && Objects.equals(this.pageNum, fileChunkInfo.pageNum)
            && Objects.equals(this.componentNum, fileChunkInfo.componentNum) && Objects.equals(this.timestamp,
            fileChunkInfo.timestamp) && Objects.equals(this.knowledgeRepoId, fileChunkInfo.knowledgeRepoId)
            && Objects.equals(this.imageIds, fileChunkInfo.imageIds) && Objects.equals(this.imagePaths,
            fileChunkInfo.imagePaths);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, content, title, pageNum, componentNum, timestamp, knowledgeRepoId, imageIds,
            imagePaths);
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
