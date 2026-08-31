/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.impl;

import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.SAMLResponse;
import com.openjiuwen.studio.agent.manager.saml.SAMLResponseValidator;
import com.openjiuwen.studio.agent.manager.saml.SAMLUtil;
import com.openjiuwen.studio.agent.manager.saml.ServiceProvider;
import com.openjiuwen.studio.agent.manager.saml.UserInfoBean;

import org.apache.jcp.xml.dsig.internal.dom.XMLDSigRI;
import org.w3c.dom.Node;

import java.security.PublicKey;
import java.security.cert.CertificateExpiredException;
import java.security.cert.CertificateNotYetValidException;
import java.security.cert.X509Certificate;
import java.util.Calendar;
import java.util.Date;

import javax.xml.crypto.MarshalException;
import javax.xml.crypto.dsig.XMLSignature;
import javax.xml.crypto.dsig.XMLSignatureException;
import javax.xml.crypto.dsig.XMLSignatureFactory;
import javax.xml.crypto.dsig.dom.DOMValidateContext;

public class SAMLResponseValidatorImpl implements SAMLResponseValidator {

    private final SAMLResponse response;

    private final ServiceProvider provider;

    public SAMLResponseValidatorImpl(String response) throws SAMLException {
        this.response = new SAMLResponseImpl(response);
        this.provider = ServiceProviderImpl.getInstance();
    }

    // 静态代码检查G.OTH.01：实现接口方法应加@Override注解，确保编译期校验方法签名一致性
    @Override
    public void validate() throws SAMLException {
        if (!validServiceProvider()) {
            throw new SAMLException("UnknownServiceProvider");
        }
        if (timeNoReache()) {
            throw new SAMLException("TimeNoReache");
        }
        if (expire()) {
            throw new SAMLException("Expire");
        }
        if (!validCertificate()) {
            throw new SAMLException("InValidCertificate");
        }
        if (!isValidXMLSign()) {
            throw new SAMLException("InValidSignature");
        }
    }

    public String getUserId() {
        return response.getNameId();
    }

    private boolean validServiceProvider() {
        return response.getIssuer().equalsIgnoreCase("www.demo.com");
    }

    private boolean timeNoReache() {
        Calendar now = Calendar.getInstance();
        return SAMLUtil.toDate(response.getNotBefore()).after(now);
    }

    private boolean expire() {
        Calendar now = Calendar.getInstance();
        return SAMLUtil.toDate(response.getNotOnOrAfter()).before(now);
    }

    private boolean validCertificate() throws SAMLException {
        try {
            ((X509Certificate) provider.getCertificate()).checkValidity(new Date());
        } catch (CertificateExpiredException | CertificateNotYetValidException e) {
            throw new SAMLException(e);
        }
        return true;
    }

    public boolean isValidXMLSign() throws SAMLException {
        boolean coreValidity;
        Node signatreuNode = response.getSignature();
        // 直接实例化 JSR-105 provider（Apache Santuario XMLDSigRI），不再动态反射加载（S2658）
        XMLSignatureFactory fac = XMLSignatureFactory.getInstance("DOM", new XMLDSigRI());
        X509Certificate x509Certificate = (X509Certificate) provider.getCertificate();
        PublicKey publicKey = x509Certificate.getPublicKey();
        DOMValidateContext valContext = new DOMValidateContext(publicKey, signatreuNode);
        try {
            XMLSignature signature = fac.unmarshalXMLSignature(valContext);
            coreValidity = signature.validate(valContext);
        } catch (MarshalException e) {
            throw new SAMLException("Cannot unmarshalXMLSignature:" + e.getMessage(), e);
        } catch (XMLSignatureException e) {
            throw new SAMLException("XMLSignatureException:" + e.getMessage(), e);
        }
        return coreValidity;
    }

    @Override
    public String getNameId() {
        return response.getNameId();
    }

    @Override
    public String getCn() {
        return response.getCn();
    }

    @Override
    public String getSn() {
        return response.getSn();
    }

    @Override
    public String getGivenName() {
        return response.getGivenName();
    }

    @Override
    public String getDisplayName() {
        return response.getDisplayName();
    }

    @Override
    public String getEmployeeNumber() {
        return response.getEmployeeNumber();
    }

    @Override
    public String getEmployeeType() {
        return response.getEmployeeType();
    }

    @Override
    public String getUid() {
        return response.getUid();
    }

    @Override
    public String getUuid() {
        return response.getUuid();
    }

    @Override
    public String getRegisterPhone() {
        return response.getRegisterPhone();
    }

    @Override
    public String getTelephoneNumber() {
        return response.getTelephoneNumber();
    }

    @Override
    public String getMail() {
        return response.getMail();
    }

    @Override
    public String getDepartmentName() {
        return response.getDepartmentName();
    }

    @Override
    public String getSource() {
        return response.getSource();
    }

    @Override
    public UserInfoBean getUIBean() {
        return response.getUIBean();
    }
}
