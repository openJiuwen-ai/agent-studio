/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.properties;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 认证配置属性
 *
 * <p>所有配置项均支持环境变量覆盖，前缀为 auth。</p>
 */
@Data
@Component
@ConfigurationProperties(prefix = "auth")
public class AuthProperties {

    private PathConfig path = new PathConfig();

    private UserInfoConfig userInfo = new UserInfoConfig();

    private SsoConfig sso = new SsoConfig();

    /**
     * SSO 远程鉴权配置
     */
    @Data
    public static class SsoConfig {
        /**
         * SSO 鉴权接口 URL
         * 配置项: auth.sso.validate-url
         */
        private String validateUrl;

        /**
         * SSO 请求头名称（用于传递 Access-Token）
         * 配置项: auth.sso.header
         */
        private String header;
    }

    /**
     * 免鉴权路径配置
     */
    @Data
    public static class PathConfig {

        /**
         * 免鉴权路径列表（支持 Ant 模式），默认包含 /health 和 /v3/**
         */
        private List<String> excluded = Arrays.asList("/health", "/v3/**");

        /**
         * 逗号分隔的免鉴权路径字符串，设置后覆盖 excluded 列表
         */
        public void setExcluded(String excluded) {
            if (StringUtils.hasText(excluded)) {
                this.excluded = Arrays.stream(excluded.split(","))
                    .map(String::trim)
                    .filter(StringUtils::hasText)
                    .collect(Collectors.toList());
            }
        }
    }

    /**
     * 用户信息映射配置
     */
    @Data
    public static class UserInfoConfig {
        private ClaimsConfig claims = new ClaimsConfig();

        private DefaultsConfig defaults = new DefaultsConfig();

        @Data
        public static class ClaimsConfig {
            /**
             * 用户 ID Claim
             * 配置项: auth.user-info.claims.user-id
             */
            private String userId;

            /**
             * 用户名 Claim
             * 配置项: auth.user-info.claims.user-name
             */
            private String userName;

            /**
             * 域 ID Claim
             * 配置项: auth.user-info.claims.domain-id
             */
            private String domainId;

            /**
             * 项目 ID Claim
             * 配置项: auth.user-info.claims.project-id
             */
            private String projectId;
        }

        @Data
        public static class DefaultsConfig {
            /**
             * 默认域 ID
             * 配置项: auth.user-info.defaults.domain-id
             */
            private String domainId = "0";

            /**
             * 默认项目 ID
             * 配置项: auth.user-info.defaults.project-id
             */
            private String projectId = "0";
        }
    }
}
