/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.ClientHttpResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * COM-04 §9.3: ClientTemplate 适配测试——全部非 2xx 进入统一 adapter。
 */
class DownstreamClientTemplateErrorHandlerTest {

    private DownstreamClientTemplateErrorHandler handler;

    @BeforeEach
    void setUp() {
        handler = new DownstreamClientTemplateErrorHandler(DownstreamService.BUILDER,
            new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog())));
    }

    private static ClientHttpResponse mockResponse(int status, String body) throws IOException {
        ClientHttpResponse resp = mock(ClientHttpResponse.class);
        when(resp.getStatusCode()).thenReturn(HttpStatusCode.valueOf(status));
        HttpHeaders headers = new HttpHeaders();
        when(resp.getHeaders()).thenReturn(headers);
        if (body == null) {
            when(resp.getBody()).thenReturn(new ByteArrayInputStream(new byte[0]));
        } else {
            when(resp.getBody()).thenReturn(
                new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8)));
        }
        return resp;
    }

    /** 全部非 2xx 判为错误（DEF-06 400/404/409 不再绕过）。 */
    @ParameterizedTest
    @ValueSource(ints = {400, 401, 404, 409, 429, 500, 502, 503})
    void hasError_all_non_2xx(int status) {
        assertTrue(handler.hasError(HttpStatusCode.valueOf(status)),
            status + " must be treated as error");
    }

    @ParameterizedTest
    @ValueSource(ints = {200, 201, 204})
    void hasError_2xx_not_error(int status) {
        assertEquals(false, handler.hasError(HttpStatusCode.valueOf(status)));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013"
    })
    void handleError_builder_canonical_trusted(String code) throws IOException {
        ClientHttpResponse resp = mockResponse(400,
            "{\"error_code\":\"" + code + "\",\"error_msg\":\"x\"}");
        DownstreamFailureException ex = assertThrows(DownstreamFailureException.class,
            () -> handler.handleError(null, null, resp));
        assertEquals(code, ex.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.BUILDER, ex.getFailure().getService());
        assertEquals(Transport.CLIENT_TEMPLATE, ex.getFailure().getTransport());
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 404, 409, 500})
    void handleError_status_recorded_diagnostic_only(int status) throws IOException {
        ClientHttpResponse resp = mockResponse(status, "{\"error_code\":\"openjiuwen.13100006\"}");
        DownstreamFailureException ex = assertThrows(DownstreamFailureException.class,
            () -> handler.handleError(null, null, resp));
        assertEquals(status, ex.getFailure().getDownstreamHttpStatus());
    }

    @Test
    void handleError_html_body_no_trusted_code() throws IOException {
        ClientHttpResponse resp = mockResponse(500, "<html>down</html>");
        DownstreamFailureException ex = assertThrows(DownstreamFailureException.class,
            () -> handler.handleError(null, null, resp));
        assertNull(ex.getFailure().getDownstreamErrorCode());
        assertEquals(DownstreamService.BUILDER, ex.getFailure().getService());
    }

    @Test
    void handleError_unknown_code_no_trust() throws IOException {
        ClientHttpResponse resp = mockResponse(500, "{\"error_code\":\"openjiuwen.99999999\"}");
        DownstreamFailureException ex = assertThrows(DownstreamFailureException.class,
            () -> handler.handleError(null, null, resp));
        assertNull(ex.getFailure().getDownstreamErrorCode());
    }

    @Test
    void handle_downstream_failure_via_mapper_defaults_502() {
        // end-to-end: adapter → mapper → 默认 02001131/502（Builder 400 不透传）
        var mapper = new DownstreamErrorMapper(
            new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE, 400,
            "openjiuwen.13100006", null);
        var d = mapper.map(f, "req-ct-001");
        assertEquals("openjiuwen.02001131", d.getErrorCode());
        assertEquals(502, d.getHttpStatus());
    }
}
