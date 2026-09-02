/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ModelServiceProviderReq
 */

@Validated

public class ModelServiceProviderReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("provider_name")
    @Schema(description = "模型服务商名称", example = "华为云", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9_ |.\\\\:/-]{2,64}$")
    @NotBlank
    private String providerName = null;

    @JsonProperty("provider_name_en")
    @Schema(description = "模型服务商英文名称", example = "HuaweiCloud", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_.|: /\\\\-]{2,64}$")
    @NotBlank
    private String providerNameEn = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "华为云模型服务")
    @Length(max = 1000)
    private String description = null;

    @JsonProperty("logo")
    @Schema(description = "Logo", example = "logo.png")
    private String logo = null;

    @JsonProperty("tags")
    @Schema(description = "标签", example = "AI,大模型")
    @Length(max = 1000)
    private String tags = null;

    @JsonProperty("provider_url")
    @Schema(description = "服务商URL", example = "https://www.huaweicloud.com")
    @Length(max = 255)
    private String providerUrl = null;

    @JsonProperty("auth_type")
    @Schema(description = "认证类型", example = "API_KEY", required = true)
    @Pattern(regexp = "(API_KEY|NO_AUTH|APP_CODE|AK_SK|CUSTOM_APIKEY|CUSTOM_IAM|HIS_IAM|SGOV|HMAC)")
    @NotBlank
    private String authType = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{\"api_key\":\"sk-xxx\"}")
    @Length(max = 5000)
    private String authInfo = null;

    public String getProviderName() {
        return providerName;
    }

    public ModelServiceProviderReq setProviderName(String providerName) {
        this.providerName = providerName;
        return this;
    }

    public String getProviderNameEn() {
        return providerNameEn;
    }

    public ModelServiceProviderReq setProviderNameEn(String providerNameEn) {
        this.providerNameEn = providerNameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ModelServiceProviderReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getLogo() {
        return logo;
    }

    public ModelServiceProviderReq setLogo(String logo) {
        this.logo = logo;
        return this;
    }

    public String getTags() {
        return tags;
    }

    public ModelServiceProviderReq setTags(String tags) {
        this.tags = tags;
        return this;
    }

    public String getProviderUrl() {
        return providerUrl;
    }

    public ModelServiceProviderReq setProviderUrl(String providerUrl) {
        this.providerUrl = providerUrl;
        return this;
    }

    public String getAuthType() {
        return authType;
    }

    public ModelServiceProviderReq setAuthType(String authType) {
        this.authType = authType;
        return this;
    }

    public String getAuthInfo() {
        return authInfo;
    }

    public ModelServiceProviderReq setAuthInfo(String authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelServiceProviderReq {\n");

        sb.append("    providerName: ").append(toIndentedString(providerName)).append("\n");
        sb.append("    providerNameEn: ").append(toIndentedString(providerNameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    logo: ").append(toIndentedString(logo)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    providerUrl: ").append(toIndentedString(providerUrl)).append("\n");
        sb.append("    authType: ").append(toIndentedString(authType)).append("\n");
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
        ModelServiceProviderReq modelServiceProviderReq = (ModelServiceProviderReq) o;
        return Objects.equals(this.providerName, modelServiceProviderReq.providerName) && Objects.equals(
            this.providerNameEn, modelServiceProviderReq.providerNameEn) && Objects.equals(this.description,
            modelServiceProviderReq.description) && Objects.equals(this.logo, modelServiceProviderReq.logo)
            && Objects.equals(this.tags, modelServiceProviderReq.tags) && Objects.equals(this.providerUrl,
            modelServiceProviderReq.providerUrl) && Objects.equals(this.authType, modelServiceProviderReq.authType)
            && Objects.equals(this.authInfo, modelServiceProviderReq.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(providerName, providerNameEn, description, logo, tags, providerUrl, authType, authInfo);
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
