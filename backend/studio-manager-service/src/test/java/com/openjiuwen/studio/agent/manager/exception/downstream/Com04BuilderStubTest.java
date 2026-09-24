/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptorDiagnostics;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder;

import feign.Request;
import feign.Response;

import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.Collections;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-04 响应 §10 联调1: Manager → Builder 可控 stub 全链路测试。
 * <p>
 * 证明：DEF-06 八码（400/404/409/500 canonical）经 Feign adapter → parser → mapper →
 * Manager HTTP builder 后：
 * - 对外仅出现 Manager 定义（openjiuwen.02001131 / 502）；
 * - 内部诊断字段包含 BUILDER 身份和可信原码；
 * - 下游 body / 原码不进入 HTTP 响应 JSON。
 */
class Com04BuilderStubTest {

    private final DownstreamErrorParser parser = new DownstreamErrorParser(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    private final DownstreamErrorMapper mapper = new DownstreamErrorMapper(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    private final ManagerHttpErrorResponseBuilder httpBuilder =
        new ManagerHttpErrorResponseBuilder((key, locale) -> {
            if (key.endsWith(".reason")) return "A downstream service returned an error.";
            if (key.endsWith(".suggestion")) return "Please retry later.";
            return "Downstream service call failed.";
        });

    private static final Map<String, Collection<String>> JSON_HEADERS =
        Map.of("Content-Type", Collections.singletonList("application/json"));

    private Response feignResponse(int status, String body) {
        return Response.builder()
            .status(status)
            .headers(JSON_HEADERS)
            .body(body.getBytes(StandardCharsets.UTF_8))
            .request(Request.create(Request.HttpMethod.POST, "http://builder/x",
                Collections.emptyMap(), null, null, null))
            .build();
    }

    /**
     * 联调1-a: Builder 400 + openjiuwen.13100006 → 对外 502，诊断含 BUILDER + 13100006
     */
    @Test
    void builder400_13100006_fullChain_managerDefinitionOnly() {
        assertFullChain(400, "openjiuwen.13100006",
            "openjiuwen.13100006", DownstreamService.BUILDER);
    }

    /**
     * 联调1-b: Builder 404 + openjiuwen.13100007
     */
    @Test
    void builder404_13100007_fullChain_managerDefinitionOnly() {
        assertFullChain(404, "openjiuwen.13100007",
            "openjiuwen.13100007", DownstreamService.BUILDER);
    }

    /**
     * 联调1-c: Builder 409 + openjiuwen.13100008
     */
    @Test
    void builder409_13100008_fullChain_managerDefinitionOnly() {
        assertFullChain(409, "openjiuwen.13100008",
            "openjiuwen.13100008", DownstreamService.BUILDER);
    }

    /**
     * 联调1-d: Builder 500 + openjiuwen.13100009
     */
    @Test
    void builder500_13100009_fullChain_managerDefinitionOnly() {
        assertFullChain(500, "openjiuwen.13100009",
            "openjiuwen.13100009", DownstreamService.BUILDER);
    }

    /**
     * 联调1-e: Builder 400 + 未知码 → 无可信原码，仍 502，诊断仅 BUILDER
     */
    @Test
    void builder400_unknownCode_fullChain_noTrustedCode() {
        assertFullChain(400, "unknown-error-code",
            null, DownstreamService.BUILDER);
    }

    /**
     * 联调1-f: Builder 503 + HTML body → 无可信原码，仍 502
     */
    @Test
    void builder503_htmlBody_fullChain_noTrustedCode() {
        Response response = Response.builder()
            .status(503)
            .headers(Map.of("Content-Type", Collections.singletonList("text/html")))
            .body("<html>boom</html>".getBytes(StandardCharsets.UTF_8))
            .request(Request.create(Request.HttpMethod.POST, "http://builder/x",
                Collections.emptyMap(), null, null, null))
            .build();

        DownstreamFeignErrorDecoder decoder = new DownstreamFeignErrorDecoder(
            DownstreamService.BUILDER, parser);
        DownstreamFailureException dfe = (DownstreamFailureException) decoder.decode("key", response);

        ErrorDescriptor descriptor = mapper.map(dfe.getFailure(), "req-stub-html");
        ResponseEntity<?> rsp = httpBuilder.build(descriptor, java.util.Locale.ENGLISH);

        assertThat(rsp.getStatusCodeValue()).isEqualTo(502);
        ErrorRsp body = (ErrorRsp) rsp.getBody();
        assertThat(body.getErrorCode()).isEqualTo("openjiuwen.02001131");
        assertThat(body.getErrorMsg()).doesNotContain("boom");
        assertThat(body.getErrorMsg()).doesNotContain("<html");
    }

    private void assertFullChain(int downstreamStatus, String downstreamCode,
                                 String expectedTrustedCode, DownstreamService expectedService) {
        String body = String.format(
            "{\"error_code\":\"%s\",\"error_msg\":\"downstream boom\",\"request_id\":\"r1\"}",
            downstreamCode);
        Response feignResp = feignResponse(downstreamStatus, body);

        // 1. Feign adapter → DownstreamFailureException
        DownstreamFeignErrorDecoder decoder = new DownstreamFeignErrorDecoder(
            expectedService, parser);
        DownstreamFailureException dfe = (DownstreamFailureException) decoder.decode("key", feignResp);
        assertThat(dfe.getFailure().getService()).isEqualTo(expectedService);

        // 2. Mapper 一次 → ErrorDescriptor
        ErrorDescriptor descriptor = mapper.map(dfe.getFailure(), "req-stub-" + downstreamStatus);

        // 3. 对外：Manager 定义 02001131 / 502
        assertThat(descriptor.getErrorCode()).isEqualTo("openjiuwen.02001131");
        assertThat(descriptor.getHttpStatus()).isEqualTo(502);

        // 4. 内部诊断：service + 可信原码
        Map<String, Object> diag = ErrorDescriptorDiagnostics.toSafeLogFields(descriptor);
        assertThat(diag.get("downstream_service")).isEqualTo(expectedService.toString());
        if (expectedTrustedCode != null) {
            assertThat(diag.get("downstream_error_code")).isEqualTo(expectedTrustedCode);
        } else {
            assertThat(diag.get("downstream_error_code")).isNull();
        }

        // 5. HTTP builder → ResponseEntity<ErrorRsp> → 下游原码不出现
        ResponseEntity<?> rsp = httpBuilder.build(descriptor, java.util.Locale.ENGLISH);
        assertThat(rsp.getStatusCodeValue()).isEqualTo(502);
        ErrorRsp rspBody = (ErrorRsp) rsp.getBody();
        assertThat(rspBody.getErrorCode()).isEqualTo("openjiuwen.02001131");
        assertThat(rspBody.getRequestId()).isEqualTo("req-stub-" + downstreamStatus);
        // 下游原码和 body 不泄漏
        assertThat(rspBody.getErrorMsg()).doesNotContain(downstreamCode);
        assertThat(rspBody.getErrorMsg()).doesNotContain("downstream boom");
    }
}
