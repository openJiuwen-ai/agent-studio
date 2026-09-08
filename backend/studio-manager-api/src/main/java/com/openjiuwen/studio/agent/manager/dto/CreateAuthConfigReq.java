/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * CreateAuthConfigReq
 */

@Validated

public class CreateAuthConfigReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("metadata_id")
    @Schema(description = "元数据", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    @NotBlank
    private String metadataId = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证", example = "示例字符串", required = true)
    @Valid
    @NotNull
    @Size()
    private Map<@Length() String, @Length() String> authInfo = new HashMap<String, String>();

    public String getMetadataId() {
        return metadataId;
    }

    public CreateAuthConfigReq setMetadataId(String metadataId) {
        this.metadataId = metadataId;
        return this;
    }

    public Map<String, String> getAuthInfo() {
        return authInfo;
    }

    public CreateAuthConfigReq setAuthInfo(Map<String, String> authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class CreateAuthConfigReq {\n");

        sb.append("    metadataId: ").append(toIndentedString(metadataId)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
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
        CreateAuthConfigReq createAuthConfigReq = (CreateAuthConfigReq) o;
        return Objects.equals(this.metadataId, createAuthConfigReq.metadataId) && Objects.equals(this.authInfo,
            createAuthConfigReq.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(metadataId, authInfo);
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
