/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建知识库文档标签请求体
 */
@ApiModel(description = "创建知识库文档标签请求体")

@Validated

public class CreateKnowledgeRepoTagsReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(
        regexp = "^[a-zA-Z0-9\\u4e00-\\u9fa5][a-zA-Z0-9\\u4e00-\\u9fa5:\\-\\_/\\.?&=@#%+~!\\$'\\(\\),;\\*\\[\\]]{0,254}$")
    @Length(min = 1, max = 100)
    private String name = null;

    public String getName() {
        return name;
    }

    public CreateKnowledgeRepoTagsReq setName(String name) {
        this.name = name;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateKnowledgeRepoTagsReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
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
        CreateKnowledgeRepoTagsReq createKnowledgeRepoTagsReq = (CreateKnowledgeRepoTagsReq) o;
        return Objects.equals(this.name, createKnowledgeRepoTagsReq.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name);
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
