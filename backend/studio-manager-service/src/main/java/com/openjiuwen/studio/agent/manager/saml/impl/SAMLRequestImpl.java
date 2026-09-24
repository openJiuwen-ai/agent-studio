/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.impl;

import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.SAMLRequest;
import com.openjiuwen.studio.agent.manager.saml.ServiceProvider;
import com.openjiuwen.studio.agent.manager.saml.response.RequestBuilder;

public class SAMLRequestImpl implements SAMLRequest {
    @Override
    public String generate() throws SAMLException {
        return generate(null);
    }

    @Override
    public String generate(String destination) throws SAMLException {
        ServiceProvider sp = ServiceProviderImpl.getInstance();
        RequestBuilder requestBuilder =
            new RequestBuilder(sp.getIssuer(), sp.getServiceUrl(), destination, sp.getPrivateKeyEntry());
        requestBuilder.setDigestAlgorithm(sp.getDigestAlgorithm());
        requestBuilder.setSignatureAlgorithm(sp.getSignatureAlgorithm());
        return requestBuilder.build();
    }
}
