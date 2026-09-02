/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

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
 * 知识命中测试请求体
 */
@ApiModel(description = "知识命中测试请求体")

@Validated

public class SearchKnowledgeRepoRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_repo_id")
    @Schema(description = "知识仓ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String knowledgeRepoId = null;

    @JsonProperty("query")
    @Schema(description = "查询内容", example = "查询内容示例", required = true)
    @NotBlank
    @Length(min = 1, max = 4096)
    private String query = null;

    @JsonProperty("search_mode")
    @Schema(description = "搜索", example = "STRING", required = true)
    @NotNull
    private SearchModeEnum searchMode = SearchModeEnum.DOC;

    public String getKnowledgeRepoId() {
        return knowledgeRepoId;
    }

    public SearchKnowledgeRepoRequestBody setKnowledgeRepoId(String knowledgeRepoId) {
        this.knowledgeRepoId = knowledgeRepoId;
        return this;
    }

    public String getQuery() {
        return query;
    }

    public SearchKnowledgeRepoRequestBody setQuery(String query) {
        this.query = query;
        return this;
    }

    public SearchModeEnum getSearchMode() {
        return searchMode;
    }

    public SearchKnowledgeRepoRequestBody setSearchMode(SearchModeEnum searchMode) {
        this.searchMode = searchMode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SearchKnowledgeRepoRequestBody {\n");

        sb.append("    knowledgeRepoId: ").append(toIndentedString(knowledgeRepoId)).append("\n");
        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    searchMode: ").append(toIndentedString(searchMode)).append("\n");
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
        SearchKnowledgeRepoRequestBody searchKnowledgeRepoRequestBody = (SearchKnowledgeRepoRequestBody) o;
        return Objects.equals(this.knowledgeRepoId, searchKnowledgeRepoRequestBody.knowledgeRepoId) && Objects.equals(
            this.query, searchKnowledgeRepoRequestBody.query) && Objects.equals(this.searchMode,
            searchKnowledgeRepoRequestBody.searchMode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeRepoId, query, searchMode);
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

    /**
     * 检索策略模式，有4种取值： - doc，语义检索 - keyword，关键词检索 - mix，混合检索 - faq，FAQ检索
     */
    public enum SearchModeEnum {
        DOC("doc"),

        KEYWORD("keyword"),

        MIX("mix"),

        FAQ("faq");

        private String value;

        SearchModeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static SearchModeEnum fromValue(String text) {
            for (SearchModeEnum b : SearchModeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
