/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListKnowledgeRepoReq
 */

@Validated

public class ListKnowledgeRepoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "知识库名称", example = "my-knowledge-base")
    private String name = null;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    private Integer pageNum = null;

    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "10")
    private Integer pageSize = null;

    @JsonProperty("knowledge_base_type")
    @Schema(description = "知识库类型", example = "1")
    private Integer knowledgeBaseType = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "file")
    @Length(max = 64)
    private String type = null;

    public String getName() {
        return name;
    }

    public ListKnowledgeRepoReq setName(String name) {
        this.name = name;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListKnowledgeRepoReq setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListKnowledgeRepoReq setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    public Integer getKnowledgeBaseType() {
        return knowledgeBaseType;
    }

    public ListKnowledgeRepoReq setKnowledgeBaseType(Integer knowledgeBaseType) {
        this.knowledgeBaseType = knowledgeBaseType;
        return this;
    }

    public String getType() {
        return type;
    }

    public ListKnowledgeRepoReq setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeRepoReq {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
        sb.append("    knowledgeBaseType: ").append(toIndentedString(knowledgeBaseType)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        ListKnowledgeRepoReq listKnowledgeRepoReq = (ListKnowledgeRepoReq) o;
        return Objects.equals(this.name, listKnowledgeRepoReq.name) && Objects.equals(this.pageNum,
            listKnowledgeRepoReq.pageNum) && Objects.equals(this.pageSize, listKnowledgeRepoReq.pageSize)
            && Objects.equals(this.knowledgeBaseType, listKnowledgeRepoReq.knowledgeBaseType)
            && Objects.equals(this.type, listKnowledgeRepoReq.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, pageNum, pageSize, knowledgeBaseType, type);
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
