/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.impl;

import com.openjiuwen.studio.agent.manager.saml.ConfigurationException;
import com.openjiuwen.studio.agent.manager.saml.ServiceProvider;
import com.openjiuwen.studio.agent.manager.saml.keystore.KeyInfoException;
import com.openjiuwen.studio.agent.manager.saml.keystore.KeystoreInfo;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.KeyStore.PrivateKeyEntry;
import java.security.PublicKey;
import java.security.cert.Certificate;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.util.Properties;
public class ServiceProviderImpl implements ServiceProvider {
    private static String issuer;
    private static String serviceUrl;
    private static KeystoreInfo keyInfo;
    private static Certificate certificate;
    private static String digestAlgorithm;
    private static String signatureAlgorithm;

    private static final Logger logger = LoggerFactory.getLogger(ServiceProviderImpl.class.getName());


    private ServiceProviderImpl() {
        InputStream jks = null;
        InputStream cer = null;
        Properties properties = new Properties();
        try {
            issuer = getConfigValue("issuer", "issuer", "aa", false);
            serviceUrl = getConfigValue("serviceUrl", "serviceUrl", "serviceUrl", false);
            String store = getConfigValue("keystore", "keystore", "keystore", false);
            jks = new FileInputStream(store);
            String spass = getConfigValue("storepassword", "storepassword", "storepassword", true);
            String kpass = getConfigValue("keypassword", "keypassword", "keypassword", true);
            String alias = getConfigValue("keyalias", "keyalias", "keyalias", false);
            keyInfo = new KeystoreInfo(jks, spass.toCharArray(), kpass.toCharArray(), alias);
            CertificateFactory caf = CertificateFactory.getInstance("X.509");

            cer = new FileInputStream(getConfigValue("certificatepath", "certificatepath", "certificatepath", false));
            certificate = caf.generateCertificate(cer);
            digestAlgorithm = getConfigValue("digestAlgorithm", "digestAlgorithm", "digestAlgorithm", false);
            signatureAlgorithm =
                getConfigValue("signatureAlgorithm", "signatureAlgorithm", "signatureAlgorithm", false);
        } catch (IOException | KeyInfoException | CertificateException e) {
            throw new ConfigurationException("Resource operation failed", e);
        } finally {
            try {
                if (jks != null)
                    jks.close();
                if (cer != null)
                    cer.close();
            } catch (IOException e) {
                logger.error("Failed to close resources", e);
            }
        }
    }

    public static ServiceProviderImpl getInstance() {
        return Holder.INSTANCE;
    }

    private static final class Holder {
        private static final ServiceProviderImpl INSTANCE = new ServiceProviderImpl();
    }

    @Override
    public String getIssuer() {
        return issuer;
    }

    @Override
    public String getServiceUrl() {
        return serviceUrl;
    }

    @Override
    public PrivateKeyEntry getPrivateKeyEntry() {
        return keyInfo.getPrivateKeyEntry();
    }

    @Override
    public PublicKey getPublicKey() {
        return keyInfo.getPublicKey();
    }

    @Override
    public Certificate getCertificate() {
        return certificate;
    }

    @Override
    public String getDigestAlgorithm() {
        return digestAlgorithm;
    }

    @Override
    public String getSignatureAlgorithm() {
        return signatureAlgorithm;
    }

    private String getConfigValue(String envVar, String propKey, String defaultValue, boolean decrypt) {
        // 1. 首先检查环境变量
        String envValue;
        if (decrypt) {
            envValue = CryptoUtils.decrypt(System.getenv(envVar));
        } else {
            envValue = System.getenv(envVar);
        }
        if (envValue != null && !envValue.trim().isEmpty()) {
            return envValue;
        }

        // 2. 检查系统属性
        String sysValue = System.getProperty(envVar);
        if (sysValue != null && !sysValue.trim().isEmpty()) {
            return sysValue;
        }

        // 3. 读取 properties 文件
        Properties props = new Properties();
        try (InputStream input = getClass().getClassLoader().getResourceAsStream("aaa.properties")) {
            if (input != null) {
                props.load(input);
                String propValue = props.getProperty(propKey);
                if (propValue != null && !propValue.trim().isEmpty()) {
                    return propValue;
                }
            }
        } catch (IOException e) {
            // 忽略错误，使用默认值
        }

        // 4. 使用默认值
        return defaultValue;
    }
}
