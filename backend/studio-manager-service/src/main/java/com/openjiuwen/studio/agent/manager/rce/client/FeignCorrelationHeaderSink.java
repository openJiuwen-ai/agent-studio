/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.manager.observability.CorrelationHeaderProvider;

import java.util.Set;

import feign.RequestTemplate;

/**
 * Feign {@link RequestTemplate} 的关联 Header Sink——覆盖算法的 Feign 适配
 * （COM-04 §4.3/§6.1）。
 */
final class FeignCorrelationHeaderSink implements CorrelationHeaderProvider.CorrelationHeaderSink {

    private final RequestTemplate template;

    FeignCorrelationHeaderSink(RequestTemplate template) {
        this.template = template;
    }

    @Override
    public Set<String> headerNames() {
        return template.headers().keySet();
    }

    @Override
    public void removeHeader(String name) {
        template.removeHeader(name);
    }

    @Override
    public void setHeader(String name, String value) {
        template.header(name, value);
    }
}
