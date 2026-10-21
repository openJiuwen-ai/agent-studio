/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.response;

import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.assertion.AuthnRequest;

import org.dom4j.Document;
import org.dom4j.DocumentHelper;

import java.security.KeyStore.PrivateKeyEntry;

/**
 * <RequestBuilder实例类用户提供服务提供者的登录地址实例>
 */
public class RequestBuilder {
    final String issuer;

    private final String serviceUrl;

    private final String destination;

    private final PrivateKeyEntry privateKeyEntry;

    private String digestAlgorithm;

    private String signatureAlgorithm;

    public RequestBuilder(String issuer, String serviceUrl, PrivateKeyEntry privateKeyEntry) {
        this(issuer, serviceUrl, null, privateKeyEntry);
    }

    public RequestBuilder(String issuer, String serviceUrl, String destination, PrivateKeyEntry privateKeyEntry) {
        this.issuer = issuer;
        this.serviceUrl = serviceUrl;
        this.destination = destination;
        this.privateKeyEntry = privateKeyEntry;
    }

    /**
     * @return
     * @throws SAMLException
     */
    public String build() throws SAMLException {
        String issueInstant = java.time.format.DateTimeFormatter
            .ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'")
            .withZone(java.time.ZoneOffset.UTC)
            .format(java.time.Instant.now());
        AuthnRequest authnRequest = new AuthnRequest(this.issuer, issueInstant, this.serviceUrl, this.destination);
        authnRequest.setDigestAlgorithm(digestAlgorithm);
        authnRequest.setSignatureAlgorithm(signatureAlgorithm);
        Request request = new Request(authnRequest, this.privateKeyEntry);
        Document doc = DocumentHelper.createDocument();
        doc.setRootElement(request.toXML());
        return doc.asXML();
    }

    public void setDigestAlgorithm(String digestAlgorithm) {
        this.digestAlgorithm = digestAlgorithm;
    }

    public void setSignatureAlgorithm(String signatureAlgorithm) {
        this.signatureAlgorithm = signatureAlgorithm;
    }

}
