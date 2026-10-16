/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.assertion;

import com.openjiuwen.studio.agent.manager.saml.response.SecureIdGenerator;

import org.dom4j.DocumentHelper;
import org.dom4j.Element;
import org.dom4j.Namespace;
import org.dom4j.QName;

public class AuthnRequest {

    public static final Namespace SAMLP =
        DocumentHelper.createNamespace("samlp", "urn:oasis:names:tc:SAML:2.0:protocol");

    public static final Namespace SAML =
        DocumentHelper.createNamespace("saml", "urn:oasis:names:tc:SAML:2.0:assertion");

    private final String issuer;

    private final String issueInstant;

    private final String serviceUrl;

    /**
     * IdP SSO 接收地址。已签名的 Redirect/POST 请求按 Binding 要求应设置 Destination。
     */
    private final String destination;

    private String digestAlgorithm;

    private String signatureAlgorithm;

    public AuthnRequest(String issuer, String issueInstant, String serviceUrl) {
        this(issuer, issueInstant, serviceUrl, null);
    }

    public AuthnRequest(String issuer, String issueInstant, String serviceUrl, String destination) {
        this.issuer = issuer;
        this.issueInstant = issueInstant;
        this.serviceUrl = serviceUrl;
        this.destination = destination;
    }

    /**
     * @return
     */
    public Element toXML() {

        Element request = DocumentHelper.createElement(new QName("AuthnRequest", SAMLP));
        request.addAttribute("ID", new SecureIdGenerator().generateSecureId());
        request.addAttribute("Version", "2.0");
        request.addAttribute("IssueInstant", this.issueInstant);
        if (destination != null && !destination.isBlank()) {
            request.addAttribute("Destination", destination.trim());
        }
        request.addAttribute("ProtocolBinding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST");
        request.addAttribute("AssertionConsumerServiceIndex", "0");
        request.addAttribute("AssertionConsumerServiceURL", this.serviceUrl);
        request.addAttribute("AttributeConsumingServiceIndex", "0");
        request.addAttribute("source", "");
        request.addAttribute("uiType", "0");

        if (digestAlgorithm != null) {
            request.addAttribute("digestAlgorithm", digestAlgorithm);
        }
        if (signatureAlgorithm != null) {
            request.addAttribute("signatureAlgorithm", signatureAlgorithm);
        }
        Element issuerElement = DocumentHelper.createElement(new QName("Issuer", SAML));
        issuerElement.setText(this.issuer);
        Element nameIDPolicy = DocumentHelper.createElement(new QName("NameIDPolicy", SAMLP));
        nameIDPolicy.addAttribute("AllowCreate", "False");
        request.add(issuerElement);
        request.add(nameIDPolicy);
        return request;
    }

    public String getDigestAlgorithm() {
        return digestAlgorithm;
    }

    public void setDigestAlgorithm(String digestAlgorithm) {
        this.digestAlgorithm = digestAlgorithm;
    }

    public String getSignatureAlgorithm() {
        return signatureAlgorithm;
    }

    public void setSignatureAlgorithm(String signatureAlgorithm) {
        this.signatureAlgorithm = signatureAlgorithm;
    }

}
