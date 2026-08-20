/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.crypt;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

public interface Cipher {
    /**
     * 加密
     *
     * @param plainText  明文
     * @param initVector IV
     * @return 密文
     * @throws AgentStudioException 异常
     */
    byte[] encrypt(final String plainText, final byte[] initVector) throws AgentStudioException;

    /**
     * 解密
     *
     * @param cipherText 密文
     * @param initVector IV
     * @return 明文
     * @throws AgentStudioException 异常
     */
    String decrypt(final byte[] cipherText, final byte[] initVector) throws AgentStudioException;

    /**
     * 生成IV
     *
     * @return IV
     * @throws AgentStudioException 异常
     */
    byte[] genIV() throws AgentStudioException;

    /**
     * 加密
     *
     * @param plainText 明文
     * @return 密文
     * @throws AgentStudioException 异常
     */
    byte[] encrypt(final String plainText) throws AgentStudioException;

    /**
     * 解密
     *
     * @param cipherText 密文
     * @return 明文
     * @throws AgentStudioException 异常
     */
    String decrypt(final byte[] cipherText) throws AgentStudioException;

    /**
     * 算法名称
     *
     * @return 名称
     */
    String name();
}