/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.ServiceProvider;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore.PrivateKeyEntry;
import java.security.PublicKey;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class SAMLResponseValidatorImplTest {

    private static final String IDP_ISSUER = "https://10.4.100.33/authn-api";

    private static final Pattern CERTIFICATE_PATTERN =
        Pattern.compile("<(?:\\w+:)?X509Certificate>(.*?)</(?:\\w+:)?X509Certificate>", Pattern.DOTALL);

    private static String responseXml;

    private static ServiceProvider idpProvider;

    @BeforeAll
    static void loadResponse() throws Exception {
        responseXml = readResource("/saml/idp-response.xml");
        idpProvider = providerWith(certificateFrom(responseXml));
    }

    @Test
    void parsesNameIdAndDisplayName() throws SAMLException {
        SAMLResponseValidatorImpl validator = validator(IDP_ISSUER);

        assertThat(validator.getNameId()).contains("系统管理员");
        assertThat(validator.getDisplayName()).contains("系统管理员");
    }

    @Test
    void validate_rejectsIssuerThatDoesNotMatchSamlIdpIssuer() throws SAMLException {
        SAMLResponseValidatorImpl validator = validator("https://other.example/authn-api");

        assertThatThrownBy(validator::validate)
            .isInstanceOf(SAMLException.class)
            .hasMessage("UnknownServiceProvider");
    }

    @Test
    void validate_matchingSamlIdpIssuer_rejectsExpiredConditions() throws SAMLException {
        SAMLResponseValidatorImpl validator = validator(IDP_ISSUER);

        assertThatThrownBy(validator::validate)
            .isInstanceOf(SAMLException.class)
            .hasMessage("Expire");
    }

    private static SAMLResponseValidatorImpl validator(String expectedIdpIssuer) throws SAMLException {
        return new SAMLResponseValidatorImpl(responseXml, expectedIdpIssuer, idpProvider);
    }

    private static String readResource(String path) throws IOException {
        try (InputStream input = SAMLResponseValidatorImplTest.class.getResourceAsStream(path)) {
            if (input == null) {
                throw new IOException("Missing test resource: " + path);
            }
            return new String(input.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static X509Certificate certificateFrom(String xml) throws Exception {
        Matcher matcher = CERTIFICATE_PATTERN.matcher(xml);
        if (!matcher.find()) {
            throw new IllegalStateException("SAML response has no X509Certificate");
        }
        byte[] der = Base64.getMimeDecoder().decode(matcher.group(1));
        CertificateFactory factory = CertificateFactory.getInstance("X.509");
        return (X509Certificate) factory.generateCertificate(new ByteArrayInputStream(der));
    }

    private static ServiceProvider providerWith(X509Certificate certificate) {
        return new ServiceProvider() {
            @Override
            public String getIssuer() {
                return null;
            }

            @Override
            public String getServiceUrl() {
                return null;
            }

            @Override
            public PrivateKeyEntry getPrivateKeyEntry() {
                return null;
            }

            @Override
            public PublicKey getPublicKey() {
                return certificate.getPublicKey();
            }

            @Override
            public Certificate getCertificate() {
                return certificate;
            }

            @Override
            public String getDigestAlgorithm() {
                return null;
            }

            @Override
            public String getSignatureAlgorithm() {
                return null;
            }
        };
    }
}
