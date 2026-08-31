/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml;

import org.apache.jcp.xml.dsig.internal.dom.DOMTransform;
import org.apache.jcp.xml.dsig.internal.dom.XMLDSigRI;
import org.dom4j.Document;
import org.dom4j.DocumentHelper;
import org.dom4j.Element;
import org.dom4j.io.DOMReader;
import org.w3c.dom.Node;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

import java.io.IOException;
import java.io.Serializable;
import java.io.StringReader;
import java.security.InvalidAlgorithmParameterException;
import java.security.KeyStore.PrivateKeyEntry;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.Provider;
import java.security.cert.X509Certificate;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.TimeZone;

import javax.xml.XMLConstants;
import javax.xml.crypto.MarshalException;
import javax.xml.crypto.dsig.CanonicalizationMethod;
import javax.xml.crypto.dsig.Reference;
import javax.xml.crypto.dsig.SignatureMethod;
import javax.xml.crypto.dsig.SignedInfo;
import javax.xml.crypto.dsig.Transform;
import javax.xml.crypto.dsig.TransformService;
import javax.xml.crypto.dsig.XMLSignature;
import javax.xml.crypto.dsig.XMLSignatureException;
import javax.xml.crypto.dsig.XMLSignatureFactory;
import javax.xml.crypto.dsig.dom.DOMSignContext;
import javax.xml.crypto.dsig.keyinfo.KeyInfo;
import javax.xml.crypto.dsig.keyinfo.KeyInfoFactory;
import javax.xml.crypto.dsig.keyinfo.X509Data;
import javax.xml.crypto.dsig.spec.C14NMethodParameterSpec;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

/**
 * <SAML封装的工具类>
 */
@SuppressWarnings("unchecked")
public class SAMLUtil {

    public static void insertSignature(org.w3c.dom.Element element, PrivateKeyEntry privateKey, Node insertBefore,
        String digestAlgorithm, String signatureAlgorithm) throws SAMLException {
        signSignature(element, privateKey, insertBefore, digestAlgorithm, signatureAlgorithm);
    }

    private static void signSignature(org.w3c.dom.Element element, PrivateKeyEntry privateKey, Node insertBefore,
        String digestAlgorithm, String signatureAlgorithm) throws SAMLException {
        try {
            // 直接实例化 JSR-105 provider（Apache Santuario XMLDSigRI），不再动态反射加载（S2658）
            Provider provider = new XMLDSigRI();

            // 创建XML签名工厂
            XMLSignatureFactory factory = XMLSignatureFactory.getInstance("DOM", provider);
            TransformService ts = TransformService.getInstance(Transform.ENVELOPED, "DOM", provider);
            DOMTransform domTrasform = new DOMTransform(ts);
            CanonicalizationMethod canMethod =
                factory.newCanonicalizationMethod(CanonicalizationMethod.EXCLUSIVE, (C14NMethodParameterSpec) null);
            element.setIdAttribute("ID", true);
            String refId = element.getAttribute("ID");

            // 消息摘要包括：
            // MD(Message Digest，消息摘要算法)、
            // SHA(Secure Hash Algorithm，安全散列算法)、
            // MAC(Message AuthenticationCode，消息认证码算法)
            // 这里采用 安全散列算法SHA
            Reference ref = factory.newReference("#" + refId,
                factory.newDigestMethod(SAMLAlgorithmUtil.getDigestAlgorithmValue(digestAlgorithm), null),
                Collections.singletonList(domTrasform), null, null);

            // 数字签名算法 MD5和SHA1分别是MD、SHA算法系列中最有代表性的算法
            SignatureMethod signatureMethod =
                factory.newSignatureMethod(SAMLAlgorithmUtil.getSignatureAlgorithmValue(signatureAlgorithm), null);

            SignedInfo signedInfo = factory.newSignedInfo(canMethod, signatureMethod, Collections.singletonList(ref));

            X509Certificate cert = (X509Certificate) privateKey.getCertificate();
            KeyInfoFactory kif = factory.getKeyInfoFactory();
            List<Serializable> x509Content = new ArrayList<Serializable>();
            x509Content.add(cert);
            X509Data xd = kif.newX509Data(x509Content);
            KeyInfo keyInfo = kif.newKeyInfo(Collections.singletonList(xd));
            PrivateKey key = privateKey.getPrivateKey();
            DOMSignContext dsc = new DOMSignContext(key, element);
            dsc.setNextSibling(insertBefore);
            XMLSignature signature = factory.newXMLSignature(signedInfo, keyInfo);
            signature.sign(dsc);
        } catch (MarshalException | XMLSignatureException | NoSuchAlgorithmException
            | InvalidAlgorithmParameterException e) {
            throw new SAMLException("Error insertSignature:" + e.getMessage(), e);
        }
    }

    public static org.w3c.dom.Document toDom(Document doc) throws SAMLException {

        /** dom4j 方式 **/
        if (doc == null) {
            return (null);
        }
        try (StringReader reader = new StringReader(doc.asXML())) {
            InputSource source = new InputSource(reader);
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setNamespaceAware(true);
            setDocumentBuilderFeature(dbf);
            org.w3c.dom.Document parse = dbf.newDocumentBuilder().parse(source);
            return parse;
        } catch (IOException | ParserConfigurationException | SAXException e) {
            throw new SAMLException("Error JDOM to W3 DOM: " + e.getMessage(), e);
        }
    }

    public static org.w3c.dom.Document toDomcument(Element element) throws SAMLException {
        Document doc = DocumentHelper.createDocument(element);
        if (doc == null) {
            throw new SAMLException("Invalid JDOM element");
        }
        return toDom(doc);
    }

    /**
     * @return
     * @throws SAMLException
     */
    public static Element toDom4jElement(org.w3c.dom.Document doc1) throws SAMLException {

        DOMReader reader = new DOMReader();
        Document doc2 = reader.read(doc1);

        return doc2.getRootElement();
    }

    public static void setDocumentBuilderFeature(DocumentBuilderFactory dbf) throws ParserConfigurationException {
        // 必选
        dbf.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        // 必选
        dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);

        // 新增安全配置
        dbf.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        dbf.setFeature("http://xml.sax/features/resolve-dtd-entities", false);
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.setXIncludeAware(false);
        dbf.setExpandEntityReferences(false);
    }

    public static Calendar toDate(String t) {
        String date = t.substring(0, t.indexOf('T'));
        String time = t.substring(t.indexOf('T') + 1, t.length() - 1);
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd");
        SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss");
        TimeZone zone = TimeZone.getTimeZone("GMT");
        dateFormat.setTimeZone(zone);
        timeFormat.setTimeZone(zone);
        try {
            Date dd = dateFormat.parse(date);
            Date tt = timeFormat.parse(time);
            long m = dd.getTime() + tt.getTime();
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(m);
            return cal;
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid SAML time");
        }
    }

}
