/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.properties;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
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

    private SystemUserConfig systemUser = new SystemUserConfig();

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
             * 用户 ID Claim 路径
             * 配置项: auth.user-info.claims.user-id
             * 支持点号分隔的多层嵌套路径，例如 result.user_id
             */
            private String userId;

            /**
             * 用户名 Claim 路径
             * 配置项: auth.user-info.claims.user-name
             * 支持点号分隔的多层嵌套路径，例如 result.user_name
             */
            private String userName;

            /**
             * 域 ID Claim 路径
             * 配置项: auth.user-info.claims.domain-id
             * 支持点号分隔的多层嵌套路径
             */
            private String domainId;

            /**
             * 域名称 Claim 路径
             * 配置项: auth.user-info.claims.domain-name
             * 支持点号分隔的多层嵌套路径。缺失时取 defaults.domain-name（默认 0），
             * 供 IAM 换 domain token 等场景使用，避免下游空指针。
             */
            private String domainName;

            /**
             * 项目 ID Claim 路径
             * 配置项: auth.user-info.claims.project-id
             * 支持点号分隔的多层嵌套路径
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
             * 默认域名称
             * 配置项: auth.user-info.defaults.domain-name
             */
            private String domainName = "0";

            /**
             * 默认项目 ID
             * 配置项: auth.user-info.defaults.project-id
             */
            private String projectId = "0";
        }
    }

    /**
     * 系统用户配置
     */
    @Data
    public static class SystemUserConfig {
        /**
         * 系统用户 ID 列表（逗号分隔），匹配后跳过空间成员校验和权限校验
         * 配置项: auth.system-user.ids
         * 环境变量: auth_system_user_ids
         */
        private String ids = "";

        /**
         * 保留值黑名单：SSO 响应缺字段时的默认回退值或无意义占位符。
         * <p>这些值一旦被配置为系统用户 ID，会导致所有携带有效 SSO Token 但 SSO 未返回
         * userId 的请求被误判为系统用户，从而跳过空间成员校验和权限校验，形成越权风险。
         * 在 {@link #isSystemUser(String)} 和 {@link #getIdList()} 中均拒绝这些值，作为代码层兜底，
         * 防止运维误配 + SSO 响应异常叠加导致的越权。</p>
         */
        private static final Set<String> RESERVED_IDS = new HashSet<>(Arrays.asList(
            "unknown", "null", "none", "n/a", ""));

        /**
         * 解析 ids 为列表（过滤保留值）
         */
        public List<String> getIdList() {
            if (ids == null || ids.isBlank()) {
                return Collections.emptyList();
            }
            return Arrays.stream(ids.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .filter(s -> !RESERVED_IDS.contains(s))
                .collect(Collectors.toList());
        }

        /**
         * 判断 userId 是否为系统用户
         * <p>拒绝 SSO 默认回退值（如 "unknown"）等保留值，
         * 防止运维误配 auth_system_user_ids=unknown + SSO 响应缺 userId 时形成越权。</p>
         */
        public boolean isSystemUser(String userId) {
            if (userId == null || RESERVED_IDS.contains(userId)) {
                return false;
            }
            return getIdList().contains(userId);
        }
    }
}
