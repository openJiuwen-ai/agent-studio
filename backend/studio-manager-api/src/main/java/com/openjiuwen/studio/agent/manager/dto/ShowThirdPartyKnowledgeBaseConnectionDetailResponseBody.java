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
 * 查询第三方知识库连接详情返回体
 */
@ApiModel(description = "查询第三方知识库连接详情返回体")

@Validated

public class ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_connection_detail")
    @Schema(description = "知识库", example = "{}")
    @Valid
    private ThirdPartyKnowledgeBaseConnectionDetail knowledgeBaseConnectionDetail = null;

    public ThirdPartyKnowledgeBaseConnectionDetail getKnowledgeBaseConnectionDetail() {
        return knowledgeBaseConnectionDetail;
    }

    public ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody setKnowledgeBaseConnectionDetail(
        ThirdPartyKnowledgeBaseConnectionDetail knowledgeBaseConnectionDetail) {
        this.knowledgeBaseConnectionDetail = knowledgeBaseConnectionDetail;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody {\n");

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
        ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody showThirdPartyKnowledgeBaseConnectionDetailResponseBody
            = (ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody) o;
        return Objects.equals(this.knowledgeBaseConnectionDetail,
            showThirdPartyKnowledgeBaseConnectionDetailResponseBody.knowledgeBaseConnectionDetail);
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
