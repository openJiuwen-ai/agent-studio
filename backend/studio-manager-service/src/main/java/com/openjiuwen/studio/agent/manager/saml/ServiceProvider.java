/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml;

import java.security.KeyStore.PrivateKeyEntry;
import java.security.PublicKey;
import java.security.cert.Certificate;

public interface ServiceProvider {
    String getIssuer();

    /**
     * IdP entityID：SAML Response 的 Issuer 应与该值比较（区别于 SP entityID
     * 的 {@link #getIssuer()}，后者用于 AuthnRequest 标识自身）
     *
     * @return IdP entityID 配置值；未配置返回 {@code null}
     */
    default String getIdpIssuer() {
        return null;
    }

    String getServiceUrl();

    PrivateKeyEntry getPrivateKeyEntry();

    PublicKey getPublicKey();

    Certificate getCertificate();

    /**
     * 消息摘要算法
     *
     * @return
     */
    String getDigestAlgorithm();

    /**
     * 签名算法
     *
     * @return
     */
    String getSignatureAlgorithm();
}
