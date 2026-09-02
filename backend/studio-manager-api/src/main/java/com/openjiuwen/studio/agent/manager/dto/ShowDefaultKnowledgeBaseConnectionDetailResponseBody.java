/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 查询m默认知识库连接详情返回体
 */
@ApiModel(description = "查询m默认知识库连接详情返回体")

@Validated

public class ShowDefaultKnowledgeBaseConnectionDetailResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_connection_detail")
    @Schema(description = "知识库", example = "{}")
    @Valid
    private DefaultKnowledgeBaseConnectionDetail knowledgeBaseConnectionDetail = null;

    public DefaultKnowledgeBaseConnectionDetail getKnowledgeBaseConnectionDetail() {
        return knowledgeBaseConnectionDetail;
    }

    public ShowDefaultKnowledgeBaseConnectionDetailResponseBody setKnowledgeBaseConnectionDetail(
        DefaultKnowledgeBaseConnectionDetail knowledgeBaseConnectionDetail) {
        this.knowledgeBaseConnectionDetail = knowledgeBaseConnectionDetail;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShowDefaultKnowledgeBaseConnectionDetailResponseBody {\n");

        sb.append("    knowledgeBaseConnectionDetail: ")
            .append(toIndentedString(knowledgeBaseConnectionDetail))
            .append("\n");
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
        ShowDefaultKnowledgeBaseConnectionDetailResponseBody showDefaultKnowledgeBaseConnectionDetailResponseBody
            = (ShowDefaultKnowledgeBaseConnectionDetailResponseBody) o;
        return Objects.equals(this.knowledgeBaseConnectionDetail,
            showDefaultKnowledgeBaseConnectionDetailResponseBody.knowledgeBaseConnectionDetail);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseConnectionDetail);
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
