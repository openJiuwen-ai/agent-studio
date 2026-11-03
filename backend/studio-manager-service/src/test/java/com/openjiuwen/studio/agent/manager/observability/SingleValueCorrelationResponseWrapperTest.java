/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SUT-01 CD-013：{@link SingleValueCorrelationResponseWrapper} 单元测试。
 *
 * <p>证明 wrapper 把 X-Request-Id / TraceID 的 {@code addHeader} 收敛为单值（大小写不敏感），
 * 且不压平 Set-Cookie / Allow 等合法多值 Header。
 */
class SingleValueCorrelationResponseWrapperTest {

    private MockHttpServletResponse wrapped() {
        return new MockHttpServletResponse();
    }

    @Test
    void addHeader_correlationHeader_collapsedToSingleValue() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("X-Request-Id", "req-1");
        w.addHeader("X-Request-Id", "req-1");

        assertThat(delegate.getHeaders("X-Request-Id")).containsExactly("req-1");
    }

    @Test
    void addHeader_correlationHeaderCaseInsensitive_collapsed() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("X-Request-Id", "req-1");
        w.addHeader("x-request-id", "req-1");
        w.addHeader("X-REQUEST-ID", "req-1");

        assertThat(delegate.getHeaders("X-Request-Id")).hasSize(1);
    }

    @Test
    void addHeader_traceId_collapsedToSingleValue() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("TraceID", "trace-1");
        w.addHeader("TraceID", "trace-1");

        assertThat(delegate.getHeaders("TraceID")).containsExactly("trace-1");
    }

    @Test
    void setHeader_preservesServletReplaceSemantics() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.setHeader("X-Request-Id", "first");
        w.setHeader("X-Request-Id", "second");

        assertThat(delegate.getHeaders("X-Request-Id")).containsExactly("second");
    }

    @Test
    void addHeader_setCookieNotFlattened() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("Set-Cookie", "a=1");
        w.addHeader("Set-Cookie", "b=2");

        assertThat(delegate.getHeaders("Set-Cookie")).containsExactly("a=1", "b=2");
    }

    @Test
    void addHeader_allowNotFlattened() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("Allow", "GET");
        w.addHeader("Allow", "POST");

        // Allow may legitimately carry multiple methods
        assertThat(delegate.getHeaders("Allow")).containsExactly("GET", "POST");
    }

    @Test
    void addHeader_arbitraryHeaderDelegatedUntouched() {
        MockHttpServletResponse delegate = wrapped();
        SingleValueCorrelationResponseWrapper w = new SingleValueCorrelationResponseWrapper(delegate);

        w.addHeader("X-Custom", "v1");
        w.addHeader("X-Custom", "v2");

        assertThat(delegate.getHeaders("X-Custom")).containsExactly("v1", "v2");
    }
}
