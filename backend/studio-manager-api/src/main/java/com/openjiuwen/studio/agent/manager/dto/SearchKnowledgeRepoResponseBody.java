/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 知识命中测试响应体
 */
@ApiModel(description = "知识命中测试响应体")

@Validated

public class SearchKnowledgeRepoResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100", required = true)
    @NotNull
    @Range(min = 0L, max = 65535L)
    private Integer total = null;

    @JsonProperty("search_result_list")
    @Schema(description = "搜索", example = "[]")
    @Valid
    @Size(max = 1000)
    private List<ChatReferenceInfo> searchResultList = null;

    public Integer getTotal() {
        return total;
    }

    public SearchKnowledgeRepoResponseBody setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public List<ChatReferenceInfo> getSearchResultList() {
        return searchResultList;
    }

    public SearchKnowledgeRepoResponseBody setSearchResultList(List<ChatReferenceInfo> searchResultList) {
        this.searchResultList = searchResultList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class SearchKnowledgeRepoResponseBody {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    searchResultList: ").append(toIndentedString(searchResultList)).append("\n");
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
        SearchKnowledgeRepoResponseBody searchKnowledgeRepoResponseBody = (SearchKnowledgeRepoResponseBody) o;
        return Objects.equals(this.total, searchKnowledgeRepoResponseBody.total) && Objects.equals(
            this.searchResultList, searchKnowledgeRepoResponseBody.searchResultList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, searchResultList);
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
