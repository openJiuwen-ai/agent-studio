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
 * ApikeyResponse
 */

@Validated

public class ApikeyResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,64}$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("apikey")
    @Schema(description = "apikey", example = "example-token-value")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,64}$")
    @Length(max = 64)
    private String apikey = null;

    public String getId() {
        return id;
    }

    public ApikeyResponse setId(String id) {
        this.id = id;
        return this;
    }

    public String getApikey() {
        return apikey;
    }

    public ApikeyResponse setApikey(String apikey) {
        this.apikey = apikey;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ApikeyResponse {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    apikey: ").append(toIndentedString(apikey)).append("\n");
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
        ApikeyResponse apikeyResponse = (ApikeyResponse) o;
        return Objects.equals(this.id, apikeyResponse.id) && Objects.equals(this.apikey, apikeyResponse.apikey);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, apikey);
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
