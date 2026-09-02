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
 * ApiKeys
 */

@Validated

public class ApiKeys implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("api_key_id")
    @Schema(description = "API密钥ID", example = "key-001")
    private String apiKeyId = null;

    @JsonProperty("api_key_name")
    @Schema(description = "API密钥名称", example = "测试密钥")
    private String apiKeyName = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "API密钥描述")
    private String description = null;

    @JsonProperty("created_date")
    @Schema(description = "创建时间", example = "1700000000000")
    private Long createdDate = null;

    public String getApiKeyId() {
        return apiKeyId;
    }

    public ApiKeys setApiKeyId(String apiKeyId) {
        this.apiKeyId = apiKeyId;
        return this;
    }

    public String getApiKeyName() {
        return apiKeyName;
    }

    public ApiKeys setApiKeyName(String apiKeyName) {
        this.apiKeyName = apiKeyName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ApiKeys setDescription(String description) {
        this.description = description;
        return this;
    }

    public Long getCreatedDate() {
        return createdDate;
    }

    public ApiKeys setCreatedDate(Long createdDate) {
        this.createdDate = createdDate;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ApiKeys {\n");

        sb.append("    apiKeyId: ").append(toIndentedString(apiKeyId)).append("\n");
        sb.append("    apiKeyName: ").append(toIndentedString(apiKeyName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    createdDate: ").append(toIndentedString(createdDate)).append("\n");
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
        ApiKeys apiKeys = (ApiKeys) o;
        return Objects.equals(this.apiKeyId, apiKeys.apiKeyId) && Objects.equals(this.apiKeyName, apiKeys.apiKeyName)
            && Objects.equals(this.description, apiKeys.description) && Objects.equals(this.createdDate,
            apiKeys.createdDate);
    }

    @Override
    public int hashCode() {
        return Objects.hash(apiKeyId, apiKeyName, description, createdDate);
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
