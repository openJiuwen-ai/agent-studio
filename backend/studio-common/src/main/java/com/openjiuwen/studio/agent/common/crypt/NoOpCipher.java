/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.crypt;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.apache.commons.lang3.StringUtils;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;

public class NoOpCipher implements Cipher {
    @Override
    public byte[] encrypt(String plainText, byte[] initVector) throws AgentStudioException {
        return encrypt(plainText);
    }

    @Override
    public String decrypt(byte[] cipherText, byte[] initVector) throws AgentStudioException {
        if (cipherText == null) {
            return null;
        }

        return decrypt(cipherText);
    }

    @Override
    public byte[] genIV() throws AgentStudioException {
        return new byte[0];
    }

    @Override
    public byte[] encrypt(String plainText) throws AgentStudioException {
        if (StringUtils.isBlank(plainText)) {
            return null;
        }

        return plainText.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String decrypt(byte[] cipherText) throws AgentStudioException {
        if (cipherText == null) {
            return null;
        }

        if (cipherText.length == 0) {
            throw new AgentStudioException("Invalid cipher text");
        }

        return new String(cipherText, StandardCharsets.UTF_8);
    }

    @Override
    public String name() {
        return "NO_OP_CIPHER";
    }
}
