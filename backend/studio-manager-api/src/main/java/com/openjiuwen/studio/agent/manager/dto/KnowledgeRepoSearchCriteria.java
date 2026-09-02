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
 * 知识库列表搜索条件。
 */
@ApiModel(description = "知识库列表搜索条件。")

@Validated

public class KnowledgeRepoSearchCriteria implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "知识库ID", example = "kr001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "知识库名称", example = "产品知识库")
    @Length(min = 1, max = 50)
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "vector")
    @Length(min = 1, max = 16)
    private String type = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "internal")
    @Length(min = 1, max = 16)
    private String source = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    @Length(min = 1, max = 16)
    private String status = null;

    public String getId() {
        return id;
    }

    public KnowledgeRepoSearchCriteria setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public KnowledgeRepoSearchCriteria setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public KnowledgeRepoSearchCriteria setType(String type) {
        this.type = type;
        return this;
    }

    public String getSource() {
        return source;
    }

    public KnowledgeRepoSearchCriteria setSource(String source) {
        this.source = source;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public KnowledgeRepoSearchCriteria setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeRepoSearchCriteria {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        KnowledgeRepoSearchCriteria knowledgeRepoSearchCriteria = (KnowledgeRepoSearchCriteria) o;
        return Objects.equals(this.id, knowledgeRepoSearchCriteria.id) && Objects.equals(this.name,
            knowledgeRepoSearchCriteria.name) && Objects.equals(this.type, knowledgeRepoSearchCriteria.type)
            && Objects.equals(this.source, knowledgeRepoSearchCriteria.source) && Objects.equals(this.status,
            knowledgeRepoSearchCriteria.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, source, status);
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
