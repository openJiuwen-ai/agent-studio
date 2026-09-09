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
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 文档信息
 */
@ApiModel(description = "文档信息")

@Validated

public class ChatReferenceInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "file_001")
    @Length(min = 1, max = 64)
    private String fileId = null;

    @JsonProperty("chunk_id")
    @Schema(description = "分块ID", example = "chunk_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String chunkId = null;

    @JsonProperty("title")
    @Schema(description = "标题", example = "用户手册")
    @Length(min = 1, max = 65535)
    private String title = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "这是一个文档内容")
    @Length(min = 1, max = 65535)
    private String content = null;

    @JsonProperty("update_date_time")
    @Schema(description = "更新日期时间", example = "2026-01-01T00:00:00Z")
    @Length(min = 1, max = 64)
    private String updateDateTime = null;

    @JsonProperty("doc_type")
    @Schema(description = "文档类型", example = "pdf")
    @Length(min = 1, max = 64)
    private String docType = null;

    @JsonProperty("file_path")
    @Schema(description = "文件路径", example = "/docs/manual.pdf")
    @Length(min = 1, max = 64)
    private String filePath = null;

    @JsonProperty("category")
    @Schema(description = "分类", example = "技术文档")
    @Length(min = 4, max = 255)
    private String category = null;

    @JsonProperty("tags")
    @Schema(description = "标签列表", example = "[]")
    @Valid
    @Size(max = 250)
    private List<@Length(min = 4, max = 255) String> tags = null;

    @JsonProperty("score")
    @Schema(description = "评分", example = "95.5")
    @Range(min = 0L, max = 10000L)
    private Float score = null;

    @JsonProperty("subtitle")
    @Schema(description = "副标题", example = "第一章")
    @Length(min = 1, max = 65535)
    private String subtitle = null;

    @JsonProperty("repo_id")
    @Schema(description = "仓库ID", example = "repo_001")
    @Length(min = 1, max = 64)
    private String repoId = null;

    @JsonProperty("image_ids")
    @Schema(description = "图片ID列表", example = "[]")
    @Valid
    @Size(max = 100)
    private List<@Length(min = 1, max = 100) String> imageIds = null;

    @JsonProperty("image_paths")
    @Schema(description = "图片路径列表", example = "[]")
    @Valid
    @Size(max = 100)
    private List<@Length(min = 1, max = 2000) String> imagePaths = null;

    public String getFileId() {
        return fileId;
    }

    public ChatReferenceInfo setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    public String getChunkId() {
        return chunkId;
    }

    public ChatReferenceInfo setChunkId(String chunkId) {
        this.chunkId = chunkId;
        return this;
    }

    public String getTitle() {
        return title;
    }

    public ChatReferenceInfo setTitle(String title) {
        this.title = title;
        return this;
    }

    public String getContent() {
        return content;
    }

    public ChatReferenceInfo setContent(String content) {
        this.content = content;
        return this;
    }

    public String getUpdateDateTime() {
        return updateDateTime;
    }

    public ChatReferenceInfo setUpdateDateTime(String updateDateTime) {
        this.updateDateTime = updateDateTime;
        return this;
    }

    public String getDocType() {
        return docType;
    }

    public ChatReferenceInfo setDocType(String docType) {
        this.docType = docType;
        return this;
    }

    public String getFilePath() {
        return filePath;
    }

    public ChatReferenceInfo setFilePath(String filePath) {
        this.filePath = filePath;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public ChatReferenceInfo setCategory(String category) {
        this.category = category;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public ChatReferenceInfo setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    public Float getScore() {
        return score;
    }

    public ChatReferenceInfo setScore(Float score) {
        this.score = score;
        return this;
    }

    public String getSubtitle() {
        return subtitle;
    }

    public ChatReferenceInfo setSubtitle(String subtitle) {
        this.subtitle = subtitle;
        return this;
    }

    public String getRepoId() {
        return repoId;
    }

    public ChatReferenceInfo setRepoId(String repoId) {
        this.repoId = repoId;
        return this;
    }

    public List<String> getImageIds() {
        return imageIds;
    }

    public ChatReferenceInfo setImageIds(List<String> imageIds) {
        this.imageIds = imageIds;
        return this;
    }

    public List<String> getImagePaths() {
        return imagePaths;
    }

    public ChatReferenceInfo setImagePaths(List<String> imagePaths) {
        this.imagePaths = imagePaths;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ChatReferenceInfo {\n");

        sb.append("    fileId: ").append(toIndentedString(fileId)).append("\n");
        sb.append("    chunkId: ").append(toIndentedString(chunkId)).append("\n");
        sb.append("    title: ").append(toIndentedString(title)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    updateDateTime: ").append(toIndentedString(updateDateTime)).append("\n");
        sb.append("    docType: ").append(toIndentedString(docType)).append("\n");
        sb.append("    filePath: ").append(toIndentedString(filePath)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    score: ").append(toIndentedString(score)).append("\n");
        sb.append("    subtitle: ").append(toIndentedString(subtitle)).append("\n");
        sb.append("    repoId: ").append(toIndentedString(repoId)).append("\n");
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
        ChatReferenceInfo chatReferenceInfo = (ChatReferenceInfo) o;
        return Objects.equals(this.fileId, chatReferenceInfo.fileId) && Objects.equals(this.chunkId,
            chatReferenceInfo.chunkId) && Objects.equals(this.title, chatReferenceInfo.title) && Objects.equals(
            this.content, chatReferenceInfo.content) && Objects.equals(this.updateDateTime,
            chatReferenceInfo.updateDateTime) && Objects.equals(this.docType, chatReferenceInfo.docType)
            && Objects.equals(this.filePath, chatReferenceInfo.filePath) && Objects.equals(this.category,
            chatReferenceInfo.category) && Objects.equals(this.tags, chatReferenceInfo.tags) && Objects.equals(
            this.score, chatReferenceInfo.score) && Objects.equals(this.subtitle, chatReferenceInfo.subtitle)
            && Objects.equals(this.repoId, chatReferenceInfo.repoId) && Objects.equals(this.imageIds,
            chatReferenceInfo.imageIds) && Objects.equals(this.imagePaths, chatReferenceInfo.imagePaths);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fileId, chunkId, title, content, updateDateTime, docType, filePath, category, tags, score,
            subtitle, repoId, imageIds, imagePaths);
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
