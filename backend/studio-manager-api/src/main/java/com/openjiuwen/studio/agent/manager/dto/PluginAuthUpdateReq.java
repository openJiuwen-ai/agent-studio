/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 更新插件鉴权信息请求体
 */
@ApiModel(description = "更新插件鉴权信息请求体")

@Validated

public class PluginAuthUpdateReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("authInfo")
    @Schema(description = "认证信息", example = "{}", required = true)
    @Valid
    @NotNull
    private AuthInfo authInfo = null;

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public PluginAuthUpdateReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PluginAuthUpdateReq {\n");

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
        PluginAuthUpdateReq pluginAuthUpdateReq = (PluginAuthUpdateReq) o;
        return Objects.equals(this.authInfo, pluginAuthUpdateReq.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(authInfo);
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
