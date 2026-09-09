/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ProviderAuthInfoReq
 */

@Validated

public class ProviderAuthInfoReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("auth_info")
    @Schema(description = "认证", example = "示例字符串", required = true)
    @NotBlank
    private String authInfo = null;

    @JsonProperty("auth_type")
    @Schema(description = "认证类型", example = "example-type", required = true)
    @NotBlank
    private String authType = null;

    public String getAuthInfo() {
        return authInfo;
    }

    public ProviderAuthInfoReq setAuthInfo(String authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getAuthType() {
        return authType;
    }

    public ProviderAuthInfoReq setAuthType(String authType) {
        this.authType = authType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ProviderAuthInfoReq {\n");

        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    authType: ").append(toIndentedString(authType)).append("\n");
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
        ProviderAuthInfoReq providerAuthInfoReq = (ProviderAuthInfoReq) o;
        return Objects.equals(this.authInfo, providerAuthInfoReq.authInfo) && Objects.equals(this.authType,
            providerAuthInfoReq.authType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(authInfo, authType);
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
