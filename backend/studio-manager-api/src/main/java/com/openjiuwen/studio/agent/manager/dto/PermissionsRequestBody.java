/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 可见范围
 */
@ApiModel(description = "可见范围")

@Validated

public class PermissionsRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("share_scope")
    @Schema(description = "sharescope", example = "STRING")
    private ShareScopeEnum shareScope = ShareScopeEnum.SELF;

    @JsonProperty("auth_workspace_id_list")
    @Schema(description = "认证", example = "[]")
    @Valid
    @Size(max = 50)
    private List<@Length(min = 1, max = 64) String> authWorkspaceIdList = null;

    public ShareScopeEnum getShareScope() {
        return shareScope;
    }

    public PermissionsRequestBody setShareScope(ShareScopeEnum shareScope) {
        this.shareScope = shareScope;
        return this;
    }

    public List<String> getAuthWorkspaceIdList() {
        return authWorkspaceIdList;
    }

    public PermissionsRequestBody setAuthWorkspaceIdList(List<String> authWorkspaceIdList) {
        this.authWorkspaceIdList = authWorkspaceIdList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PermissionsRequestBody {\n");

        sb.append("    shareScope: ").append(toIndentedString(shareScope)).append("\n");
        sb.append("    authWorkspaceIdList: ").append(toIndentedString(authWorkspaceIdList)).append("\n");
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
        PermissionsRequestBody permissionsRequestBody = (PermissionsRequestBody) o;
        return Objects.equals(this.shareScope, permissionsRequestBody.shareScope) && Objects.equals(
            this.authWorkspaceIdList, permissionsRequestBody.authWorkspaceIdList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(shareScope, authWorkspaceIdList);
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

    /**
     * Gets or Sets shareScope
     */
    public enum ShareScopeEnum {
        SELF("SELF"),

        GLOBAL("GLOBAL"),

        ALL("ALL"),

        PARTIAL("PARTIAL");

        private String value;

        ShareScopeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ShareScopeEnum fromValue(String text) {
            for (ShareScopeEnum b : ShareScopeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
