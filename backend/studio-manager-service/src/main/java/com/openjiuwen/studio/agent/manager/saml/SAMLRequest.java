/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml;

public interface SAMLRequest {
    String generate() throws SAMLException;

    /**
     * @param destination IdP SSO URL，写入 AuthnRequest/@Destination（已签名 Redirect 请求必填）
     */
    String generate(String destination) throws SAMLException;
}
