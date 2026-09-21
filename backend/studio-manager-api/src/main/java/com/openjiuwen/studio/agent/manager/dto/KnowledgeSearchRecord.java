/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库命中测试记录
 */
@ApiModel(description = "知识库命中测试记录")

@Validated

public class KnowledgeSearchRecord implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String id = null;

    @JsonProperty("query")
    @Schema(description = "查询内容", example = "查询内容示例", required = true)
    @NotBlank
    @Length(min = 1, max = 65535)
    private String query = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1", required = true)
    @NotNull
    private Long createTime = null;

    public String getId() {
        return id;
    }

    public KnowledgeSearchRecord setId(String id) {
        this.id = id;
        return this;
    }

    public String getQuery() {
        return query;
    }

    public KnowledgeSearchRecord setQuery(String query) {
        this.query = query;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public KnowledgeSearchRecord setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeSearchRecord {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
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
        KnowledgeSearchRecord knowledgeSearchRecord = (KnowledgeSearchRecord) o;
        return Objects.equals(this.id, knowledgeSearchRecord.id) && Objects.equals(this.query,
            knowledgeSearchRecord.query) && Objects.equals(this.createTime, knowledgeSearchRecord.createTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, query, createTime);
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
