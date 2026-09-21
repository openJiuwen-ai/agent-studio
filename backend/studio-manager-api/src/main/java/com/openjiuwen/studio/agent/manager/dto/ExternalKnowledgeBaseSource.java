/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 第三方知识库的来源
 */
@ApiModel(description = "第三方知识库的来源")

@Validated

public class ExternalKnowledgeBaseSource implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("knowledge_base_connector_id")
    @Schema(description = "知识库连接器ID", example = "conn-001")
    @Length(min = 1, max = 100)
    private String knowledgeBaseConnectorId = null;

    @JsonProperty("knowledge_base_connection_id")
    @Schema(description = "知识库连接ID", example = "kb-conn-001")
    @Length(min = 1, max = 100)
    private String knowledgeBaseConnectionId = null;

    @JsonProperty("knowledge_base_connection_name")
    @Schema(description = "知识库连接名称", example = "外部知识库连接")
    @Length(max = 100)
    private String knowledgeBaseConnectionName = null;

    @JsonProperty("detail_page_url")
    @Schema(description = "详情页地址", example = "https://example.com/detail")
    @Length(max = 1000)
    private String detailPageUrl = null;

    public String getKnowledgeBaseConnectorId() {
        return knowledgeBaseConnectorId;
    }

    public ExternalKnowledgeBaseSource setKnowledgeBaseConnectorId(String knowledgeBaseConnectorId) {
        this.knowledgeBaseConnectorId = knowledgeBaseConnectorId;
        return this;
    }

    public String getKnowledgeBaseConnectionId() {
        return knowledgeBaseConnectionId;
    }

    public ExternalKnowledgeBaseSource setKnowledgeBaseConnectionId(String knowledgeBaseConnectionId) {
        this.knowledgeBaseConnectionId = knowledgeBaseConnectionId;
        return this;
    }

    public String getKnowledgeBaseConnectionName() {
        return knowledgeBaseConnectionName;
    }

    public ExternalKnowledgeBaseSource setKnowledgeBaseConnectionName(String knowledgeBaseConnectionName) {
        this.knowledgeBaseConnectionName = knowledgeBaseConnectionName;
        return this;
    }

    public String getDetailPageUrl() {
        return detailPageUrl;
    }

    public ExternalKnowledgeBaseSource setDetailPageUrl(String detailPageUrl) {
        this.detailPageUrl = detailPageUrl;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExternalKnowledgeBaseSource {\n");

        sb.append("    knowledgeBaseConnectorId: ").append(toIndentedString(knowledgeBaseConnectorId)).append("\n");
        sb.append("    knowledgeBaseConnectionId: ").append(toIndentedString(knowledgeBaseConnectionId)).append("\n");
        sb.append("    knowledgeBaseConnectionName: ")
            .append(toIndentedString(knowledgeBaseConnectionName))
            .append("\n");
        sb.append("    detailPageUrl: ").append(toIndentedString(detailPageUrl)).append("\n");
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
        ExternalKnowledgeBaseSource externalKnowledgeBaseSource = (ExternalKnowledgeBaseSource) o;
        return Objects.equals(this.knowledgeBaseConnectorId, externalKnowledgeBaseSource.knowledgeBaseConnectorId)
            && Objects.equals(this.knowledgeBaseConnectionId, externalKnowledgeBaseSource.knowledgeBaseConnectionId)
            && Objects.equals(this.knowledgeBaseConnectionName, externalKnowledgeBaseSource.knowledgeBaseConnectionName)
            && Objects.equals(this.detailPageUrl, externalKnowledgeBaseSource.detailPageUrl);
    }

    @Override
    public int hashCode() {
        return Objects.hash(knowledgeBaseConnectorId, knowledgeBaseConnectionId, knowledgeBaseConnectionName,
            detailPageUrl);
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
