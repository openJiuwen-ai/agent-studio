/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 第三方知识库列表信息
 */
@ApiModel(description = "第三方知识库列表信息")

@Validated

public class ListExternalKnowledgeBasesResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1")
    @Range(min = 0L, max = 10000L)
    private Long count = null;

    @JsonProperty("knowledge_base_list")
    @Schema(description = "知识库", example = "[]")
    @Valid
    @Size(max = 200)
    private List<ExternalKnowledgeItem> knowledgeBaseList = null;

    public Long getCount() {
        return count;
    }

    public ListExternalKnowledgeBasesResponseBody setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<ExternalKnowledgeItem> getKnowledgeBaseList() {
        return knowledgeBaseList;
    }

    public ListExternalKnowledgeBasesResponseBody setKnowledgeBaseList(List<ExternalKnowledgeItem> knowledgeBaseList) {
        this.knowledgeBaseList = knowledgeBaseList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListExternalKnowledgeBasesResponseBody {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    knowledgeBaseList: ").append(toIndentedString(knowledgeBaseList)).append("\n");
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
        ListExternalKnowledgeBasesResponseBody listExternalKnowledgeBasesResponseBody
            = (ListExternalKnowledgeBasesResponseBody) o;
        return Objects.equals(this.count, listExternalKnowledgeBasesResponseBody.count) && Objects.equals(
            this.knowledgeBaseList, listExternalKnowledgeBasesResponseBody.knowledgeBaseList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, knowledgeBaseList);
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
