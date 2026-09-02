/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建知识库文档标签响应体
 */
@ApiModel(description = "创建知识库文档标签响应体")

@Validated

public class CreateKnowledgeRepoTagsRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tag_id")
    @Schema(description = "标签ID", example = "example-id-123")
    private String tagId = null;

    public String getTagId() {
        return tagId;
    }

    public CreateKnowledgeRepoTagsRsp setTagId(String tagId) {
        this.tagId = tagId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeRepoTagsRsp {\n");

        sb.append("    tagId: ").append(toIndentedString(tagId)).append("\n");
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
        CreateKnowledgeRepoTagsRsp createKnowledgeRepoTagsRsp = (CreateKnowledgeRepoTagsRsp) o;
        return Objects.equals(this.tagId, createKnowledgeRepoTagsRsp.tagId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(tagId);
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
