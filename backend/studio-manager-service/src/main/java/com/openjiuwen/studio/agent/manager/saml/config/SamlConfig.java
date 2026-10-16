/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.config;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * SAML 2.0 配置类
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "saml")
public class SamlConfig {
    /**
     * 是否启用SAML认证
     */
    private boolean enabled = false;

    /**
     * 身份提供商元数据URL
     */
    private String idpMetadataUrl;

    /**
     * 身份提供商 Issuer，对应配置项 saml_idp_issuer
     */
    private String idpIssuer;

    /**
     * SAML服务的基础URL
     */
    private String baseUrl;

    /**
     * SAML配置文件路径
     */
    private String configFilePath;

    /**
     * 排除的资源路径（如静态文件）
     */
    private String exclusions;

    /**
     * SAML服务的发行者
     */
    private String issuer;

    /**
     * SAML服务的登录URL
     */
    private String serviceUrl;

    /**
     * 密钥库密码
     */
    private String storePassword;

    /**
     * 密钥密码
     */
    private String keyPassword;

    /**
     * 密钥别名
     */
    private String keyAlias;

    /**
     * 密钥库路径
     */
    private String keystore;

    /**
     * 证书路径
     */
    private String certificatePath;

    /**
     * 摘要算法
     */
    private String digestAlgorithm;

    /**
     * 签名算法
     */
    private String signatureAlgorithm;

}
