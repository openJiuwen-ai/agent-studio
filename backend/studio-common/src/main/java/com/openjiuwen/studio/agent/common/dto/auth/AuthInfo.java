/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto.auth;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import lombok.Data;
import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 工具鉴权信息
 */
@ApiModel(description = "工具鉴权信息")
@Data
@Validated

public class AuthInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("scope")
    private ScopeEnum scope = null;

    @JsonProperty("domain")
    private DomainEnum domain = null;

    @JsonProperty("auth_keys")
    @Valid
    @Size(min = 1, max = 5)
    private List<AuthKeyInfo> authKeys = null;

    @JsonProperty("iam_credentials")
    @Valid
    @Size()
    private Map<@Length() String, @Length() String> iamCredentials = null;

    @JsonProperty("his_iam_info")
    @Valid
    private HisIamInfo hisIamInfo = null;

    @JsonProperty("his_sgov")
    @Valid
    private HisSgov hisSgov = null;

    @JsonProperty("custom_iam_credentials")
    @Valid
    private PluginIAMAuthInfo customIamCredentials = null;

    @JsonProperty("custom_oauth")
    @Valid
    private OauthInfo customOauth = null;

    public ScopeEnum getScope() {
        return scope;
    }

    public AuthInfo setScope(ScopeEnum scope) {
        this.scope = scope;
        return this;
    }

    public DomainEnum getDomain() {
        return domain;
    }

    public AuthInfo setDomain(DomainEnum domain) {
        this.domain = domain;
        return this;
    }

    public List<AuthKeyInfo> getAuthKeys() {
        return authKeys;
    }

    public AuthInfo setAuthKeys(List<AuthKeyInfo> authKeys) {
        this.authKeys = authKeys;
        return this;
    }

    public Map<String, String> getIamCredentials() {
        return iamCredentials;
    }

    public AuthInfo setIamCredentials(Map<String, String> iamCredentials) {
        this.iamCredentials = iamCredentials;
        return this;
    }

    public HisIamInfo getHisIamInfo() {
        return hisIamInfo;
    }

    public AuthInfo setHisIamInfo(HisIamInfo hisIamInfo) {
        this.hisIamInfo = hisIamInfo;
        return this;
    }

    public HisSgov getHisSgov() {
        return hisSgov;
    }

    public AuthInfo setHisSgov(HisSgov hisSgov) {
        this.hisSgov = hisSgov;
        return this;
    }

    public PluginIAMAuthInfo getCustomIamCredentials() {
        return customIamCredentials;
    }

    public AuthInfo setCustomIamCredentials(PluginIAMAuthInfo customIamCredentials) {
        this.customIamCredentials = customIamCredentials;
        return this;
    }

    public OauthInfo getCustomOauth() {
        return customOauth;
    }

    public AuthInfo setCustomOauth(OauthInfo customOauth) {
        this.customOauth = customOauth;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AuthInfo {\n");

        sb.append("    scope: ").append(toIndentedString(scope)).append("\n");
        sb.append("    domain: ").append(toIndentedString(domain)).append("\n");
        sb.append("    authKeys: ").append(toIndentedString(authKeys)).append("\n");
        sb.append("    iamCredentials: ").append(toIndentedString(iamCredentials)).append("\n");
        sb.append("    hisIamInfo: ").append(toIndentedString(hisIamInfo)).append("\n");
        sb.append("    hisSgov: ").append(toIndentedString(hisSgov)).append("\n");
        sb.append("    customIamCredentials: ").append(toIndentedString(customIamCredentials)).append("\n");
        sb.append("    customOauth: ").append(toIndentedString(customOauth)).append("\n");
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
        AuthInfo authInfo = (AuthInfo) o;
        return Objects.equals(this.scope, authInfo.scope) && Objects.equals(this.domain, authInfo.domain)
            && Objects.equals(this.authKeys, authInfo.authKeys) && Objects.equals(this.iamCredentials,
            authInfo.iamCredentials) && Objects.equals(this.hisIamInfo, authInfo.hisIamInfo) && Objects.equals(
            this.hisSgov, authInfo.hisSgov) && Objects.equals(this.customIamCredentials, authInfo.customIamCredentials)
            && Objects.equals(this.customOauth, authInfo.customOauth);
    }

    @Override
    public int hashCode() {
        return Objects.hash(scope, domain, authKeys, iamCredentials, hisIamInfo, hisSgov, customIamCredentials,
            customOauth);
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
     * 工具鉴权方式，分为用户级、服务级和IAM方式
     */
    public enum ScopeEnum {
        USER("USER"),

        SERVICE("SERVICE"),

        // FEAT-093 动态鉴权：凭证值不入库，由工作流节点参数在运行期提供
        DYNAMIC("DYNAMIC"),

        IAM("IAM"),

        HIS_IAM("HIS_IAM"),

        SGOV("SGOV"),

        CUSTOM_IAM("CUSTOM_IAM"),

        OAUTH("OAUTH");

        private String value;

        ScopeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ScopeEnum fromValue(String text) {
            for (ScopeEnum b : ScopeEnum.values()) {
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

    /**
     * 工具鉴权秘钥位置
     */
    public enum DomainEnum {
        HEADERS("HEADERS"),

        QUERY("QUERY");

        private String value;

        DomainEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static DomainEnum fromValue(String text) {
            for (DomainEnum b : DomainEnum.values()) {
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
