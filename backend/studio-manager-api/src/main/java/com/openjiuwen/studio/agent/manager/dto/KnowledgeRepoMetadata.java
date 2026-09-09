/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * KnowledgeRepoMetadata
 */

@Validated

public class KnowledgeRepoMetadata implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("endpoint")
    @Schema(description = "端点", example = "示例字符串")
    private String endpoint = null;

    @JsonProperty("authorization")
    @Schema(description = "authorization", example = "示例字符串")
    private String authorization = null;

    public String getEndpoint() {
        return endpoint;
    }

    public KnowledgeRepoMetadata setEndpoint(String endpoint) {
        this.endpoint = endpoint;
        return this;
    }

    public String getAuthorization() {
        return authorization;
    }

    public KnowledgeRepoMetadata setAuthorization(String authorization) {
        this.authorization = authorization;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeRepoMetadata {\n");

        sb.append("    endpoint: ").append(toIndentedString(endpoint)).append("\n");
        sb.append("    authorization: ").append(toIndentedString(authorization)).append("\n");
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
        KnowledgeRepoMetadata knowledgeRepoMetadata = (KnowledgeRepoMetadata) o;
        return Objects.equals(this.endpoint, knowledgeRepoMetadata.endpoint) && Objects.equals(this.authorization,
            knowledgeRepoMetadata.authorization);
    }

    @Override
    public int hashCode() {
        return Objects.hash(endpoint, authorization);
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
