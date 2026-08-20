/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.crypt;

import lombok.extern.slf4j.Slf4j;

import com.google.common.collect.ImmutableMap;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.StringUtils;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;
import java.util.Map;

@Slf4j
public class Ciphers {
    private final Map<String, Cipher> cipherMap;

    private final String defaultCipherName;

    public Ciphers(List<Cipher> ciphers, String defaultCipherName) {
        ImmutableMap.Builder<String, Cipher> ciphersBuilder = new ImmutableMap.Builder<>();

        NoOpCipher noOpCipher = new NoOpCipher();
        ciphersBuilder.put(noOpCipher.name(), noOpCipher);

        this.defaultCipherName = StringUtils.isNotBlank(defaultCipherName) ? defaultCipherName : noOpCipher.name();

        if (CollectionUtils.isNotEmpty(ciphers)) {
            ciphers.forEach(cipher -> {
                ciphersBuilder.put(cipher.name(), cipher);
            });
        }

        this.cipherMap = ciphersBuilder.build();
    }

    public String encrypt(final String plainText, final byte[] vector) {
        if (StringUtils.isBlank(plainText)) {
            return plainText;
        }

        if (MapUtils.isEmpty(cipherMap) || StringUtils.isBlank(defaultCipherName)) {
            return plainText;
        }

        return encrypt(defaultCipherName, plainText, vector);
    }

    public String encrypt(final String cipherName, final String plainText, final byte[] vector) {
        if (StringUtils.isBlank(plainText)) {
            return plainText;
        }

        if (MapUtils.isEmpty(cipherMap)) {
            return plainText;
        }

        Cipher cipher = cipherMap.get(cipherName);
        if (cipher == null) {
            throw new AgentStudioException(cipherName + " not support!");
        }

        final byte[] cipherText = cipher.encrypt(plainText, vector);
        return new String(cipherText, StandardCharsets.UTF_8);
    }

    public String decrypt(final String cipherText, final byte[] vector) {
        if (StringUtils.isBlank(cipherText)) {
            return cipherText;
        }

        if (MapUtils.isEmpty(cipherMap)) {
            return cipherText;
        }

        final byte[] cipherByte = cipherText.getBytes(StandardCharsets.UTF_8);

        Cipher cipher = cipherMap.get(defaultCipherName);
        if (cipher == null) {
            throw new AgentStudioException(defaultCipherName + "not support!");
        }

        return cipher.decrypt(cipherByte, vector);
    }

    public String decrypt(final String cipherText, final String vector) {
        if (StringUtils.isBlank(cipherText)) {
            return StringUtils.EMPTY;
        }
        final byte[] vectorByte = Base64.getDecoder().decode(vector);
        return decrypt(cipherText, vectorByte);
    }

    public byte[] genIV(final String cipherName) {
        Cipher cipher = cipherMap.get(cipherName);
        if (cipher == null) {
            throw new AgentStudioException(cipherName + " not support!");
        }
        return cipher.genIV();
    }

    public String encrypt(final String plainText) {
        if (StringUtils.isBlank(plainText)) {
            return StringUtils.EMPTY;
        }

        if (MapUtils.isEmpty(cipherMap) || StringUtils.isBlank(defaultCipherName)) {
            return plainText;
        }

        return encrypt(defaultCipherName, plainText);
    }

    public String encrypt(final String cipherName, final String plainText) {
        if (StringUtils.isBlank(plainText)) {
            return StringUtils.EMPTY;
        }

        Cipher cipher = cipherMap.get(cipherName);
        if (cipher == null) {
            throw new AgentStudioException(cipherName + " not support!");
        }

        final byte[] cipherText = cipher.encrypt(plainText);
        return new String(cipherText, StandardCharsets.UTF_8);
    }

    public String decrypt(final String cipherText) {
        if (StringUtils.isBlank(cipherText)) {
            return StringUtils.EMPTY;
        }
        final byte[] cipherByte = cipherText.getBytes(StandardCharsets.UTF_8);

        Cipher cipher = cipherMap.get(defaultCipherName);
        if (cipher == null) {
            throw new AgentStudioException(defaultCipherName + "not support!");
        }

        return cipher.decrypt(cipherByte);
    }
}