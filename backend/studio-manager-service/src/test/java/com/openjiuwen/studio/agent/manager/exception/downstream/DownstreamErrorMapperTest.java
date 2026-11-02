/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptorDiagnostics;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * COM-04 §9.2: Mapper 参数化测试。
 */
class DownstreamErrorMapperTest {

    private DownstreamErrorMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = new DownstreamErrorMapper(
            new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    }

    private static final String REQUEST_ID = "req-com04-001";

    // ---- 八码默认映射 02001131/502，无 registered reference 不成对外码 ----

    @ParameterizedTest
    @ValueSource(strings = {
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013"
    })
    void map_builder_canonical_defaults_to_dependency_failed(String code) {
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE, 400, code, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);

        assertEquals("openjiuwen.02001131", d.getErrorCode());
        assertEquals(502, d.getHttpStatus());
        assertEquals(REQUEST_ID, d.getRequestId());
        // 下游 400/404/409 不直接决定 descriptor HTTP status（恒为 502）
        // 可信原码写入内部诊断
        assertEquals(DownstreamService.BUILDER, ErrorDescriptorDiagnostics.getDownstreamService(d));
        assertEquals(code, ErrorDescriptorDiagnostics.getDownstreamErrorCode(d));
    }

    @ParameterizedTest
    @ValueSource(ints = {400, 404, 409, 500})
    void map_downstream_http_status_does_not_determine_descriptor_status(int downstreamStatus) {
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE, downstreamStatus,
            "openjiuwen.13100006", null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals(502, d.getHttpStatus());
        assertEquals("openjiuwen.02001131", d.getErrorCode());
    }

    // ---- 无原码 / 未知码 / transport failure → 02001131，仅 downstreamService ----

    @Test
    void map_no_trusted_code_only_service() {
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.WEBCLIENT, 500, null, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.02001131", d.getErrorCode());
        assertEquals(502, d.getHttpStatus());
        assertEquals(DownstreamService.BUILDER, ErrorDescriptorDiagnostics.getDownstreamService(d));
        assertNull(ErrorDescriptorDiagnostics.getDownstreamErrorCode(d));
    }

    @Test
    void map_transport_failure_defaults() {
        DownstreamFailure f = DownstreamFailure.transportFailure(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, new RuntimeException("timeout"));
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.02001131", d.getErrorCode());
        assertEquals(502, d.getHttpStatus());
        assertEquals(DownstreamService.RUNTIME, ErrorDescriptorDiagnostics.getDownstreamService(d));
        assertNull(ErrorDescriptorDiagnostics.getDownstreamErrorCode(d));
    }

    // ---- downstreamService 总存在，可信码成对 ----

    @Test
    void map_external_service_no_code() {
        DownstreamFailure f = DownstreamFailure.transportFailure(
            DownstreamService.EXTERNAL, Transport.FEIGN, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals(DownstreamService.EXTERNAL, ErrorDescriptorDiagnostics.getDownstreamService(d));
        assertNull(ErrorDescriptorDiagnostics.getDownstreamErrorCode(d));
    }

    // ---- Runtime 与 Builder 同名原码不跨服务误用 ----

    @Test
    void map_runtime_does_not_trust_builder_codes() {
        // Builder canonical 13 头码族到 RUNTIME 身份不跨服务误信：
        // 直接构造的 DownstreamFailure 也过不了 mapper 1b 的码形纵深校验
        // （2026-10-27 格式门曾放行此类码，2026-11-02 修订恢复冻结规则）
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, 500,
            "openjiuwen.13100006", null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.02001131", d.getErrorCode());
        assertNull(d.getPassthroughText());
        assertEquals(DownstreamService.RUNTIME, ErrorDescriptorDiagnostics.getDownstreamService(d));
    }

    // ---- descriptor cause 保留 ----

    @Test
    void map_preserves_cause() {
        RuntimeException cause = new RuntimeException("original downstream cause");
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE, 500,
            "openjiuwen.13100009", cause);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals(cause, d.getCause());
    }

    // ---- RUNTIME 透传（COM-04 §5.2 修订，2026-11-02）----

    @Test
    void map_runtime_sse_engine_code_passthrough_with_managed_text() {
        // 试运行场景：SSE 流内 error 帧（无下游 HTTP 状态）+ 引擎 6 位码 + 受管三段文案
        DownstreamFailure f = DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.101003",
            "LLM调用失败：LLM stream failed: Connection error.",
            "LLM组件调用模型服务失败，可能是模型请求参数错误、服务不可用或网络异常",
            "请检查模型服务状态、API配置及网络连接",
            null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        // 原码透传（不再吃进 02001131）；SSE 阶段无状态 → 500
        assertEquals("openjiuwen.101003", d.getErrorCode());
        assertEquals(500, d.getHttpStatus());
        assertEquals(REQUEST_ID, d.getRequestId());
        assertEquals(DownstreamService.RUNTIME, ErrorDescriptorDiagnostics.getDownstreamService(d));
        assertEquals("openjiuwen.101003", ErrorDescriptorDiagnostics.getDownstreamErrorCode(d));
        // 受管三段文案随 descriptor 传递，构建器 i18n 缺失时回退使用
        assertNotNull(d.getPassthroughText());
        assertEquals("LLM调用失败：LLM stream failed: Connection error.",
            d.getPassthroughText().getMessage());
        assertEquals("请检查模型服务状态、API配置及网络连接",
            d.getPassthroughText().getSuggestion());
    }

    @Test
    void map_runtime_http_phase_uses_downstream_status_and_keeps_text() {
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, 403, "openjiuwen.121007",
            "msg", "reason", "suggestion", null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.121007", d.getErrorCode());
        assertEquals(403, d.getHttpStatus());
        assertEquals("msg", d.getPassthroughText().getMessage());
    }

    @Test
    void map_runtime_app_code_without_text_no_passthrough() {
        // 应用层 8 位码（Manager i18n 已覆盖）无帧内文案 → 透传原码、无回退文案
        DownstreamFailure f = DownstreamFailure.httpResponse(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, 400, "openjiuwen.02001003",
            null, null, null, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.02001003", d.getErrorCode());
        assertNull(d.getPassthroughText());
    }

    @Test
    void map_runtime_sse_engine_code_without_text_still_passthrough_code() {
        // 无文案的引擎码仍透传原码（文案由构建器按 i18n/回退语义处理）
        DownstreamFailure f = DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.101905",
            null, null, null, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.101905", d.getErrorCode());
        assertNull(d.getPassthroughText());
    }

    @Test
    void map_runtime_999999_fallback_code_trusted() {
        DownstreamFailure f = DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.999999",
            "系统内部错误", null, null, null);
        ErrorDescriptor d = mapper.map(f, REQUEST_ID);
        assertEquals("openjiuwen.999999", d.getErrorCode());
    }

    // ---- 统一族格式组件标签（COM-04 §5.2 修订二期）----

    @Test
    void map_attaches_component_labels_for_downstream_services() {
        // 用户裁定：RUNTIME 访问 OBS/DB 是其内部依赖，不细分——恒为 runtime；
        // obs/mysql/redis 标签只用于 manager 自身直接访问（DependencyComponentLabels）
        ErrorDescriptor runtime = mapper.map(DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.101003",
            "msg", null, null, null), REQUEST_ID);
        assertEquals("runtime", runtime.getDownstreamComponentLabel());

        ErrorDescriptor runtimeObsCode = mapper.map(DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.100505",
            "Get Object Failed", null, null, null), REQUEST_ID);
        assertEquals("runtime", runtimeObsCode.getDownstreamComponentLabel());

        ErrorDescriptor runtimeObsText = mapper.map(DownstreamFailure.sseEvent(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "openjiuwen.101003",
            "load ir from OBS failed", null, null, null), REQUEST_ID);
        assertEquals("runtime", runtimeObsText.getDownstreamComponentLabel());

        ErrorDescriptor builder = mapper.map(DownstreamFailure.httpResponse(
            DownstreamService.BUILDER, Transport.WEBCLIENT, 500, "openjiuwen.13100009",
            null), REQUEST_ID);
        assertEquals("builder", builder.getDownstreamComponentLabel());
    }
}
