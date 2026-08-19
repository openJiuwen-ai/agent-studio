/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.security.KeyStore;
import java.util.Calendar;
import java.util.TimeZone;

import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class SAMLUtilTest {

    @Test
    public void testToDate_ValidInput() {
        String input = "2023-10-10T12:34:56Z";
        Calendar expected = Calendar.getInstance(TimeZone.getTimeZone("GMT"));
        expected.set(2023, Calendar.OCTOBER, 10, 12, 34, 56);
        expected.set(Calendar.MILLISECOND, 0);

        Calendar actual = SAMLUtil.toDate(input);

        assertEquals(expected.get(Calendar.YEAR), actual.get(Calendar.YEAR));
        assertEquals(expected.get(Calendar.MONTH), actual.get(Calendar.MONTH));
        assertEquals(expected.get(Calendar.DAY_OF_MONTH), actual.get(Calendar.DAY_OF_MONTH));
        assertEquals(expected.get(Calendar.MINUTE), actual.get(Calendar.MINUTE));
        assertEquals(expected.get(Calendar.SECOND), actual.get(Calendar.SECOND));
    }

    @Test
    public void testToDate_InvalidInput() {
        String input = "invalid-date";
        assertThrows(StringIndexOutOfBoundsException.class, () -> SAMLUtil.toDate(input));
    }

    /**
     * 覆盖 insertSignature/signSignature 中 JSR-105 provider 的实例化路径
     * （不应动态加载类 S2658：由反射 Class.forName 改为直接 new XMLDSigRI()）。
     *
     * <p>行为应保持一致：能对带 ID 的元素成功插入 ds:Signature 子节点。</p>
     */
    @Test
    public void testInsertSignature_addsSignatureElement() throws Exception {
        // 1. 加载测试 keystore（RSA 自签证书 + 私钥）
        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (InputStream is = getClass().getResourceAsStream("/saml/saml-test.p12")) {
            assertNotNull(is, "saml-test.p12 测试 fixture 缺失");
            ks.load(is, "changeit".toCharArray());
        }
        KeyStore.PrivateKeyEntry privateKey = (KeyStore.PrivateKeyEntry) ks.getEntry("saml",
            new KeyStore.PasswordProtection("changeit".toCharArray()));

        // 2. 构造带 ID 的 SAML Response 元素（签名以 #ID 为引用）
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        Document doc = dbf.newDocumentBuilder().newDocument();
        Element root = doc.createElementNS("urn:oasis:names:tc:SAML:2.0:protocol", "samlp:Response");
        root.setAttribute("ID", "test-response");
        Element issuer = doc.createElementNS("urn:oasis:names:tc:SAML:2.0:assertion", "saml:Issuer");
        issuer.setTextContent("https://idp.example.com");
        root.appendChild(issuer);
        doc.appendChild(root);

        // 3. 执行签名（覆盖 provider 实例化路径）
        SAMLUtil.insertSignature(root, privateKey, issuer, "SHA256", "RSA_SHA256");

        // 4. 断言：成功插入 ds:Signature 子节点
        boolean hasSignature = false;
        NodeList children = root.getChildNodes();
        for (int i = 0; i < children.getLength(); i++) {
            if ("Signature".equals(children.item(i).getLocalName())) {
                hasSignature = true;
                break;
            }
        }
        assertTrue(hasSignature, "insertSignature 未生成 ds:Signature 子节点");
    }
}
