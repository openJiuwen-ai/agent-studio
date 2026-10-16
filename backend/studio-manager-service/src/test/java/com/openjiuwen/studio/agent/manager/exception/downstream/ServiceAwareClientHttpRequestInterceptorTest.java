/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpResponse;

import java.io.IOException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * COM-04 响应 P1（审视意见 §3.1）: ClientTemplate transport failure 统一适配测试。
 * <p>
 * 证明：连接拒绝/DNS/超时/无响应等 IOException 被拦截器捕获并转为
 * 携带 BUILDER 身份的 DownstreamFailureException。
 */
class ServiceAwareClientHttpRequestInterceptorTest {

    private final DownstreamErrorParser parser = new DownstreamErrorParser(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));

    private static final byte[] EMPTY_BODY = new byte[0];

    @Test
    void connectionRefused_ioException_downstreamFailureWithBuilderIdentity() throws Exception {
        HttpRequest request = mock(HttpRequest.class);
        ClientHttpRequestExecution execution = mock(ClientHttpRequestExecution.class);
        when(execution.execute(request, EMPTY_BODY))
            .thenThrow(new IOException("Connection refused"));

        ServiceAwareClientHttpRequestInterceptor interceptor =
            new ServiceAwareClientHttpRequestInterceptor(DownstreamService.BUILDER, parser);

        assertThatThrownBy(() -> interceptor.intercept(request, EMPTY_BODY, execution))
            .isInstanceOf(DownstreamFailureException.class)
            .satisfies(ex -> {
                DownstreamFailure f = ((DownstreamFailureException) ex).getFailure();
                assertThat(f.getService()).isEqualTo(DownstreamService.BUILDER);
                assertThat(f.getTransport()).isEqualTo(Transport.CLIENT_TEMPLATE);
                assertThat(f.getDownstreamErrorCode()).isNull();
                assertThat(f.getCause()).isInstanceOf(IOException.class);
            });
    }

    @Test
    void readTimeout_ioException_downstreamFailureNoTrustedCode() throws Exception {
        HttpRequest request = mock(HttpRequest.class);
        ClientHttpRequestExecution execution = mock(ClientHttpRequestExecution.class);
        when(execution.execute(request, EMPTY_BODY))
            .thenThrow(new java.net.SocketTimeoutException("Read timed out"));

        ServiceAwareClientHttpRequestInterceptor interceptor =
            new ServiceAwareClientHttpRequestInterceptor(DownstreamService.BUILDER, parser);

        assertThatThrownBy(() -> interceptor.intercept(request, EMPTY_BODY, execution))
            .isInstanceOf(DownstreamFailureException.class)
            .satisfies(ex -> {
                DownstreamFailure f = ((DownstreamFailureException) ex).getFailure();
                assertThat(f.getService()).isEqualTo(DownstreamService.BUILDER);
                assertThat(f.getDownstreamErrorCode()).isNull();
            });
    }

    @Test
    void successfulResponse_notIntercepted() throws IOException {
        HttpRequest request = mock(HttpRequest.class);
        ClientHttpResponse response = mock(ClientHttpResponse.class);
        ClientHttpRequestExecution execution = mock(ClientHttpRequestExecution.class);
        when(execution.execute(request, EMPTY_BODY)).thenReturn(response);

        ServiceAwareClientHttpRequestInterceptor interceptor =
            new ServiceAwareClientHttpRequestInterceptor(DownstreamService.BUILDER, parser);

        ClientHttpResponse result = interceptor.intercept(request, EMPTY_BODY, execution);
        assertThat(result).isSameAs(response);
    }

    @Test
    void nullService_rejected() {
        assertThatThrownBy(() ->
            new ServiceAwareClientHttpRequestInterceptor(null, parser))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
