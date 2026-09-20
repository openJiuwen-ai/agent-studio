/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * IAM用户信息。
 */
@ApiModel(description = "IAM用户信息。")

@Validated

public class IamUserInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("iamUserId")
    @Schema(description = "iam用户ID", example = "example-id-123")
    private String iamUserId = null;

    @JsonProperty("iamUserName")
    @Schema(description = "iam用户名称", example = "示例名称")
    private String iamUserName = null;

    public String getIamUserId() {
        return iamUserId;
    }

    public IamUserInfo setIamUserId(String iamUserId) {
        this.iamUserId = iamUserId;
        return this;
    }

    public String getIamUserName() {
        return iamUserName;
    }

    public IamUserInfo setIamUserName(String iamUserName) {
        this.iamUserName = iamUserName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class IamUserInfo {\n");

        sb.append("    iamUserId: ").append(toIndentedString(iamUserId)).append("\n");
        sb.append("    iamUserName: ").append(toIndentedString(iamUserName)).append("\n");
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
        IamUserInfo iamUserInfo = (IamUserInfo) o;
        return Objects.equals(this.iamUserId, iamUserInfo.iamUserId) && Objects.equals(this.iamUserName,
            iamUserInfo.iamUserName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(iamUserId, iamUserName);
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
