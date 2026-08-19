/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.crypt;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * AesGcmCipher 单元测试。
 */
class AesGcmCipherTest {

    private static final String KEY_32_HEX = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";

    @Test
    void name() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        assertEquals("AES_GCM", c.name());
    }

    @Test
    void rejectsBlankKey() {
        assertThrows(AgentStudioException.class, () -> new AesGcmCipher(""));
        assertThrows(AgentStudioException.class, () -> new AesGcmCipher((String) null));
    }

    @Test
    void rejectsShortKey() {
        assertThrows(AgentStudioException.class, () -> new AesGcmCipher("010203"));
    }

    @Test
    void roundTrip() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        String plain = "{\"API Key\":\"sk-test-poc-xyz\"}";
        byte[] ct = c.encrypt(plain);
        assertNotNull(ct);
        String hex = new String(ct, StandardCharsets.UTF_8);
        // nonce 24 hex + tag 32 hex + ct hex ≥ 2
        assertTrue(hex.length() >= 24 + 32 + 2, "hex length: " + hex.length());
        // round trip
        String decrypted = c.decrypt(ct);
        assertEquals(plain, decrypted);
    }

    @Test
    void nonceIsRandom() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        byte[] a = c.encrypt("same plaintext");
        byte[] b = c.encrypt("same plaintext");
        // 前 24 hex 字符是 nonce，必须随机不同
        assertNotEquals(new String(a, StandardCharsets.UTF_8).substring(0, 24),
            new String(b, StandardCharsets.UTF_8).substring(0, 24));
    }

    @Test
    void tamperedCiphertextFails() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        byte[] ct = c.encrypt("secret");
        // 翻转最后一字节（tag/ct 尾部）破坏 tag 校验
        ct[ct.length - 1] ^= (byte) 0xff;
        byte[] ctFinal = ct;
        assertThrows(AgentStudioException.class, () -> c.decrypt(ctFinal));
    }

    @Test
    void nullPlainReturnsNull() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        assertNull(c.encrypt((String) null));
    }

    @Test
    void genIvReturns12Bytes() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        assertEquals(12, c.genIV().length);
    }

    @Test
    void decryptShortCiphertextFails() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        byte[] tooShort = "001122".getBytes(StandardCharsets.UTF_8);
        assertThrows(AgentStudioException.class, () -> c.decrypt(tooShort));
    }

    @Test
    void ivOverloadEncryptsAndDecrypts() {
        AesGcmCipher c = new AesGcmCipher(KEY_32_HEX);
        byte[] iv = c.genIV();
        byte[] ct = c.encrypt("hello iv", iv);
        assertNotNull(ct);
        // encrypt(String, iv) 返回 hex UTF-8 字节，decrypt(byte[]) 走 hex 路径
        String dec = c.decrypt(ct);
        assertEquals("hello iv", dec);
    }
}
