/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import feign.Client;
import feign.Request;
import feign.Response;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.Collections;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 响应 P1-2: ServiceAwareFeignClient transport failure 身份测试。
 * <p>
 * 证明：Feign Client.execute 抛 IOException 时，装饰器捕获并转为
 * 携带 RUNTIME/BUILDER 身份的 DownstreamFailureException（不经 EXTERNAL 兜底）。
 */
class ServiceAwareFeignClientTest {

    private final DownstreamErrorParser parser = new DownstreamErrorParser(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));

    private static Request dummyRequest() {
        return Request.create(Request.HttpMethod.GET, "http://runtime/x",
            Collections.emptyMap(), null, null, null);
    }

    private static final Request.Options OPTS = new Request.Options(5000, 10000);

    @Test
    void transportFailure_runtimeService_identityPreserved() {
        Client delegate = (request, options) -> {
            throw new IOException("connection refused");
        };
        ServiceAwareFeignClient client =
            new ServiceAwareFeignClient(DownstreamService.RUNTIME, delegate, parser);

        assertThatThrownBy(() -> client.execute(dummyRequest(), OPTS))
            .isInstanceOf(DownstreamFailureException.class)
            .satisfies(ex -> {
                DownstreamFailure f = ((DownstreamFailureException) ex).getFailure();
                assertThat(f.getService()).isEqualTo(DownstreamService.RUNTIME);
                assertThat(f.getTransport()).isEqualTo(Transport.FEIGN);
                // transport failure → no trusted code
                assertThat(f.getDownstreamErrorCode()).isNull();
                // cause preserved
                assertThat(f.getCause()).isInstanceOf(IOException.class);
            });
    }

    @Test
    void transportFailure_builderService_identityPreserved() {
        Client delegate = (request, options) -> {
            throw new IOException("read timeout");
        };
        ServiceAwareFeignClient client =
            new ServiceAwareFeignClient(DownstreamService.BUILDER, delegate, parser);

        assertThatThrownBy(() -> client.execute(dummyRequest(), OPTS))
            .isInstanceOf(DownstreamFailureException.class)
            .satisfies(ex -> {
                DownstreamFailure f = ((DownstreamFailureException) ex).getFailure();
                assertThat(f.getService()).isEqualTo(DownstreamService.BUILDER);
            });
    }

    @Test
    void successfulResponse_notIntercepted() throws IOException {
        Response response = Response.builder()
            .request(dummyRequest())
            .status(200)
            .build();
        Client delegate = (request, options) -> response;
        ServiceAwareFeignClient client =
            new ServiceAwareFeignClient(DownstreamService.RUNTIME, delegate, parser);

        Response result = client.execute(dummyRequest(), OPTS);
        assertThat(result.status()).isEqualTo(200);
    }

    @Test
    void nullService_rejected() {
        assertThatThrownBy(() ->
            new ServiceAwareFeignClient(null, (r, o) -> null, parser))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
