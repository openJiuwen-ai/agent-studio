/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import feign.Request;
import feign.Response;

import java.nio.charset.StandardCharsets;
import java.util.Collections;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;

/**
 * COM-04 §9.3: Feign ErrorDecoder 适配测试。
 */
class DownstreamFeignErrorDecoderTest {

    private DownstreamFeignErrorDecoder builderDecoder;
    private DownstreamFeignErrorDecoder runtimeDecoder;

    @BeforeEach
    void setUp() {
        var catalog = new DownstreamErrorMappingCatalog(new ManagerErrorCatalog());
        var parser = new DownstreamErrorParser(catalog);
        builderDecoder = new DownstreamFeignErrorDecoder(DownstreamService.BUILDER, parser);
        runtimeDecoder = new DownstreamFeignErrorDecoder(DownstreamService.RUNTIME, parser);
    }

    private static Response feignResponse(int status, byte[] body) {
        return Response.builder()
            .status(status)
            .reason("err")
            .request(Request.create(Request.HttpMethod.GET, "http://x",
                Collections.emptyMap(), null, null, null))
            .body(body)
            .headers(Collections.emptyMap())
            .build();
    }

    @Test
    void decode_builder_canonical_body_trusted() {
        byte[] body = "{\"error_code\":\"openjiuwen.13100006\"}".getBytes(StandardCharsets.UTF_8);
        Response resp = feignResponse(400, body);
        Exception ex = builderDecoder.decode("AgentBuilderClient#x", resp);
        DownstreamFailureException dfe = assertInstanceOf(DownstreamFailureException.class, ex);
        assertEquals("openjiuwen.13100006", dfe.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.BUILDER, dfe.getFailure().getService());
        assertEquals(Transport.FEIGN, dfe.getFailure().getTransport());
        assertEquals(400, dfe.getFailure().getDownstreamHttpStatus());
    }

    @Test
    void decode_unknown_body_no_trusted_code() {
        byte[] body = "<html>down</html>".getBytes(StandardCharsets.UTF_8);
        Response resp = feignResponse(500, body);
        Exception ex = builderDecoder.decode("k", resp);
        DownstreamFailureException dfe = assertInstanceOf(DownstreamFailureException.class, ex);
        assertNull(dfe.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.BUILDER, dfe.getFailure().getService());
    }

    @Test
    void decode_null_body_no_code() {
        Response resp = feignResponse(502, null);
        Exception ex = runtimeDecoder.decode("k", resp);
        DownstreamFailureException dfe = assertInstanceOf(DownstreamFailureException.class, ex);
        assertNull(dfe.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.RUNTIME, dfe.getFailure().getService());
    }

    @Test
    void decode_runtime_does_not_trust_builder_code() {
        // Builder canonical code arriving on a RUNTIME client → not trusted
        byte[] body = "{\"error_code\":\"openjiuwen.13100006\"}".getBytes(StandardCharsets.UTF_8);
        Response resp = feignResponse(400, body);
        Exception ex = runtimeDecoder.decode("k", resp);
        DownstreamFailureException dfe = assertInstanceOf(DownstreamFailureException.class, ex);
        assertNull(dfe.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.RUNTIME, dfe.getFailure().getService());
    }
}
