/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.crypt;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;

import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * AES-256-GCM 加解密实现，对齐 Python 侧 {@code openjiuwen.core.common.security.crypt_utils.AesGcmCrypt} 的
 * 输出格式：{@code hex(nonce 12B) + hex(tag 16B) + hex(ciphertext)}。
 *
 * <p>仅在配置 {@code system.crypt.name=AES_GCM} 时注册；32 字节密钥通过
 * {@code system.crypt.key}（hex 编码，64 字符）注入。与 Python 侧一致：每次加密随机 12B nonce，
 * 相同明文 + 相同密钥输出不同密文；tag 校验失败抛 {@link AgentStudioException}。
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "system.crypt.name", havingValue = "AES_GCM")
public class AesGcmCipher implements com.openjiuwen.studio.agent.common.crypt.Cipher {
    private static final String ALG = "AES/GCM/NoPadding";
    private static final int NONCE_LEN = 12;
    private static final int TAG_LEN_BITS = 128;
    private static final int KEY_LEN_BYTES = 32;

    private final byte[] key;
    private final SecureRandom random = new SecureRandom();

    public AesGcmCipher(@Value("${system.crypt.key:}") String hexKey) {
        if (StringUtils.isBlank(hexKey)) {
            throw new AgentStudioException("system.crypt.key required when system.crypt.name=AES_GCM");
        }
        byte[] k = hexToBytes(hexKey);
        if (k.length != KEY_LEN_BYTES) {
            throw new AgentStudioException(
                "system.crypt.key must be 32 bytes (64 hex chars); actual " + k.length + " bytes");
        }
        this.key = k;
        log.info("AesGcmCipher registered (name={})", name());
    }

    @Override
    public byte[] encrypt(String plainText, byte[] initVector) throws AgentStudioException {
        if (plainText == null) {
            return null;
        }
        // 返回 hex(nonce||ct||tag) 的 UTF-8 字节，对齐 encrypt(String) 与 Python AesGcmCrypt 输出格式。
        String hex = encryptToHex(plainText, initVector);
        return hex == null ? null : hex.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String decrypt(byte[] cipherText, byte[] initVector) throws AgentStudioException {
        // 无 IV 重载路径：从 hex 字符串中拆 nonce/tag/ct
        throw new AgentStudioException("AesGcmCipher.decrypt(byte[],byte[]): use decrypt(byte[]) instead");
    }

    @Override
    public byte[] genIV() throws AgentStudioException {
        byte[] nonce = new byte[NONCE_LEN];
        random.nextBytes(nonce);
        return nonce;
    }

    @Override
    public byte[] encrypt(String plainText) throws AgentStudioException {
        if (plainText == null) {
            return null;
        }
        // 对齐 Python：返回 hex(nonce)+hex(tag)+hex(ct) 字符串的 UTF-8 字节
        String hex = encryptToHex(plainText, null);
        return hex == null ? null : hex.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String decrypt(byte[] cipherText) throws AgentStudioException {
        if (cipherText == null || cipherText.length == 0) {
            return null;
        }
        String hex = new String(cipherText, StandardCharsets.UTF_8);
        return decryptFromHex(hex);
    }

    @Override
    public String name() {
        return "AES_GCM";
    }

    private byte[] encryptInner(String plainText, byte[] nonceIn) {
        if (plainText == null) {
            return null;
        }
        try {
            byte[] nonce = nonceIn != null && nonceIn.length == NONCE_LEN ? nonceIn : genIV();
            javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance(ALG);
            cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"),
                new GCMParameterSpec(TAG_LEN_BITS, nonce));
            byte[] ctWithTag = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            ByteBuffer bb = ByteBuffer.allocate(NONCE_LEN + ctWithTag.length);
            bb.put(nonce);
            bb.put(ctWithTag);
            return bb.array();
        } catch (Exception e) {
            throw new AgentStudioException("AES-GCM encrypt failed: " + e.getMessage());
        }
    }

    private String encryptToHex(String plainText, byte[] nonceIn) {
        if (plainText == null) {
            return null;
        }
        byte[] raw = encryptInner(plainText, nonceIn);
        // raw = nonce(12) || ct(?) || tag(16)
        return bytesToHex(raw);
    }

    private String decryptFromHex(String hex) {
        try {
            byte[] raw = hexToBytes(hex);
            if (raw.length < NONCE_LEN + TAG_LEN_BITS / 8) {
                throw new AgentStudioException("AES-GCM ciphertext too short");
            }
            byte[] nonce = new byte[NONCE_LEN];
            System.arraycopy(raw, 0, nonce, 0, NONCE_LEN);
            // raw[NONCE_LEN..end] = ct || tag — GCM cipher.init(DECRYPT) + doFinal 自动验 tag
            javax.crypto.Cipher cipher = javax.crypto.Cipher.getInstance(ALG);
            cipher.init(javax.crypto.Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"),
                new GCMParameterSpec(TAG_LEN_BITS, nonce));
            byte[] pt = cipher.doFinal(raw, NONCE_LEN, raw.length - NONCE_LEN);
            return new String(pt, StandardCharsets.UTF_8);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            throw new AgentStudioException("AES-GCM decrypt failed (tag mismatch or tampered): " + e.getMessage());
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b & 0xff));
        }
        return sb.toString();
    }

    private static byte[] hexToBytes(String hex) {
        if (hex == null || hex.length() % 2 != 0) {
            throw new AgentStudioException("Invalid hex string");
        }
        int len = hex.length() / 2;
        byte[] out = new byte[len];
        for (int i = 0; i < len; i++) {
            int hi = Character.digit(hex.charAt(i * 2), 16);
            int lo = Character.digit(hex.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) {
                throw new AgentStudioException("Invalid hex character");
            }
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }
}
