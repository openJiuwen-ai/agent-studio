/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Set;

import org.springframework.http.HttpHeaders;

/**
 * Spring {@link HttpHeaders} 出站关联 Header Sink（COM-04 §4.3）。
 *
 * <p>WebClient 与 RestTemplate 适配器共用：{@link CorrelationHeaderProvider#apply} 先大小写不敏感
 * 删除三个关联 Header 的全部既有值（含调用方伪造的重复变体），再写入策略权威值。
 */
public final class HttpHeadersCorrelationSink implements CorrelationHeaderProvider.CorrelationHeaderSink {

    private final HttpHeaders httpHeaders;

    public HttpHeadersCorrelationSink(HttpHeaders httpHeaders) {
        this.httpHeaders = httpHeaders;
    }

    @Override
    public Set<String> headerNames() {
        return httpHeaders.keySet();
    }

    @Override
    public void removeHeader(String name) {
        httpHeaders.remove(name);
    }

    @Override
    public void setHeader(String name, String value) {
        httpHeaders.set(name, value);
    }
}
