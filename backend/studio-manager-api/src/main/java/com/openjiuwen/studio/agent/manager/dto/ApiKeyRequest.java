/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ApiKeyRequest
 */

@Validated

public class ApiKeyRequest implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("apikey_name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5a-zA-Z0-9_.-]{1,35}$")
    @Length(max = 64)
    private String apikeyName = null;

    @JsonProperty("apikey_description")
    @Schema(description = "描述", example = "示例描述")
    @Length(max = 1024)
    private String apikeyDescription = null;

    public String getApikeyName() {
        return apikeyName;
    }

    public ApiKeyRequest setApikeyName(String apikeyName) {
        this.apikeyName = apikeyName;
        return this;
    }

    public String getApikeyDescription() {
        return apikeyDescription;
    }

    public ApiKeyRequest setApikeyDescription(String apikeyDescription) {
        this.apikeyDescription = apikeyDescription;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ApiKeyRequest {\n");

        sb.append("    apikeyName: ").append(toIndentedString(apikeyName)).append("\n");
        sb.append("    apikeyDescription: ").append(toIndentedString(apikeyDescription)).append("\n");
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
        ApiKeyRequest apiKeyRequest = (ApiKeyRequest) o;
        return Objects.equals(this.apikeyName, apiKeyRequest.apikeyName) && Objects.equals(this.apikeyDescription,
            apiKeyRequest.apikeyDescription);
    }

    @Override
    public int hashCode() {
        return Objects.hash(apikeyName, apikeyDescription);
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
