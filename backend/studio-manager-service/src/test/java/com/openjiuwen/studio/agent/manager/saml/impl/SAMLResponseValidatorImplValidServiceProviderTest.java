/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.impl;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.manager.saml.SAMLResponse;
import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.ServiceProvider;

import org.junit.jupiter.api.Test;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * {@link SAMLResponseValidatorImpl#validServiceProvider()} 的 IdP entityID 校验单测。
 *
 * <p>覆盖三种场景：idpIssuer 配置匹配（标准部署）、idpIssuer 配置不匹配（非法响应）、
 * idpIssuer 未配置时的存量兼容回退（与 issuer/SP entityID 比较）。
 */
class SAMLResponseValidatorImplValidServiceProviderTest {

    private static final String SP_ENTITY_ID = "https://sp.example.com";
    private static final String IDP_ENTITY_ID = "https://idp.example.com";

    private SAMLResponse responseWithIssuer(String issuer) {
        SAMLResponse response = mock(SAMLResponse.class);
        when(response.getIssuer()).thenReturn(issuer);
        when(response.getNotBefore()).thenReturn("2000-01-01T00:00:00Z");
        when(response.getNotOnOrAfter()).thenReturn("2099-01-01T00:00:00Z");
        return response;
    }

    private ServiceProvider providerWith(String spIssuer, String idpIssuer) {
        ServiceProvider provider = mock(ServiceProvider.class);
        when(provider.getIssuer()).thenReturn(spIssuer);
        when(provider.getIdpIssuer()).thenReturn(idpIssuer);
        return provider;
    }

    private boolean validate(String responseIssuer, String spIssuer, String idpIssuer)
        throws SAMLException {
        SAMLResponseValidatorImpl validator =
            new SAMLResponseValidatorImpl(responseWithIssuer(responseIssuer), providerWith(spIssuer, idpIssuer));
        return validator.isValidServiceProviderForTest();
    }

    @Test
    void testIdpIssuerConfigured_Match_ReturnsTrue() throws SAMLException {
        // 标准 SAML 部署：Response Issuer（IdP entityID）与 idpIssuer 配置一致
        assertTrue(validate(IDP_ENTITY_ID, SP_ENTITY_ID, IDP_ENTITY_ID));
    }

    @Test
    void testIdpIssuerConfigured_Mismatch_ReturnsFalse() throws SAMLException {
        // 非法响应：Issuer 与 idpIssuer 配置不一致
        assertFalse(validate("https://evil.example.com", SP_ENTITY_ID, IDP_ENTITY_ID));
    }

    @Test
    void testIdpIssuerConfigured_CaseInsensitive() throws SAMLException {
        // entityID 主机部分大小写差异仍视为一致（与既有 equalsIgnoreCase 语义一致）
        assertTrue(validate("HTTPS://IDP.Example.com", SP_ENTITY_ID, IDP_ENTITY_ID));
    }

    @Test
    void testIdpIssuerNotConfigured_FailClosed() throws SAMLException {
        // fail-closed：未配置 idpIssuer 时直接拒绝（保留原硬编码校验的安全语义）
        assertFalse(validate(SP_ENTITY_ID, SP_ENTITY_ID, null));
        assertFalse(validate(IDP_ENTITY_ID, SP_ENTITY_ID, null));
    }

    @Test
    void testIdpIssuerBlank_FailClosed() throws SAMLException {
        // 空白配置视为未配置，同样 fail-closed
        assertFalse(validate(SP_ENTITY_ID, SP_ENTITY_ID, "  "));
    }
}
