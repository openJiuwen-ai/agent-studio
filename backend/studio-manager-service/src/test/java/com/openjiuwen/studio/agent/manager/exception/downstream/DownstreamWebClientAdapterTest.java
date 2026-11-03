/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-04 响应 §5.3: DownstreamWebClientAdapter.detectSseErrorEvent 测试。
 * <p>
 * 证明：WebClient 流内 SSE error event（JSON 内嵌 event=error）被正确检测；
 * 普通 data 伪造 error_code 不误判；非 JSON / 非 error event 不触发。
 */
class DownstreamWebClientAdapterTest {

    private final DownstreamErrorParser parser = new DownstreamErrorParser(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));

    // ---- error event 检测 ----

    @Test
    void detectSseErrorEvent_standardError_returnsFailure() {
        // Runtime SSE error envelope: {"event":"error","data":{"error_code":"downstream-runtime-error",...}}
        String chunk = "{\"event\":\"error\",\"data\":{\"error_code\":\"downstream-runtime-error\","
            + "\"error_msg\":\"boom\",\"request_id\":\"r1\"}}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, chunk);

        assertThat(result).isPresent();
        DownstreamFailure f = result.get();
        assertThat(f.getService()).isEqualTo(DownstreamService.RUNTIME);
        assertThat(f.getTransport()).isEqualTo(Transport.WEBCLIENT);
        // Runtime codes not in recognized set → no trusted code
        assertThat(f.getDownstreamErrorCode()).isNull();
    }

    @Test
    void detectSseErrorEvent_builderCanonicalCode_trustedCode() {
        // Builder canonical code in error data
        String chunk = "{\"event\":\"error\",\"data\":{\"error_code\":\"openjiuwen.13100006\","
            + "\"error_msg\":\"param invalid\",\"request_id\":\"r2\"}}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.BUILDER, parser, chunk);

        assertThat(result).isPresent();
        // Builder canonical code is recognized → trusted
        assertThat(result.get().getDownstreamErrorCode()).isEqualTo("openjiuwen.13100006");
        assertThat(result.get().getService()).isEqualTo(DownstreamService.BUILDER);
    }

    @Test
    void detectSseErrorEvent_errorWithMissingData_returnsFailureNoCode() {
        // error event with no data field
        String chunk = "{\"event\":\"error\"}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, chunk);

        assertThat(result).isPresent();
        assertThat(result.get().getDownstreamErrorCode()).isNull();
    }

    // ---- 非 error event 不误判 ----

    @Test
    void detectSseErrorEvent_messageEvent_notError() {
        String chunk = "{\"event\":\"message\",\"data\":{\"text\":\"hello\"}}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, chunk);
        assertThat(result).isEmpty();
    }

    @Test
    void detectSseErrorEvent_doneEvent_notError() {
        String chunk = "{\"event\":\"done\",\"data\":{}}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, chunk);
        assertThat(result).isEmpty();
    }

    @Test
    void detectSseErrorEvent_spoofedErrorCodeInNonErrorEvent_notDetected() {
        // 普通 data 伪造 error_code → 不误判
        String chunk = "{\"event\":\"message\",\"data\":{\"error_code\":\"openjiuwen.13100006\"}}";
        Optional<DownstreamFailure> result = DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.BUILDER, parser, chunk);
        assertThat(result).isEmpty();
    }

    // ---- 非 JSON / 损坏 ----

    @Test
    void detectSseErrorEvent_nonJson_empty() {
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, "[Done]")).isEmpty();
    }

    @Test
    void detectSseErrorEvent_nullOrBlank_empty() {
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, null)).isEmpty();
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, "")).isEmpty();
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, "  ")).isEmpty();
    }

    @Test
    void detectSseErrorEvent_arrayJson_empty() {
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, "[{\"event\":\"error\"}]")).isEmpty();
    }

    @Test
    void detectSseErrorEvent_eventFieldNotString_empty() {
        // event field is number → not error
        assertThat(DownstreamWebClientAdapter.detectSseErrorEvent(
            DownstreamService.RUNTIME, parser, "{\"event\":123}")).isEmpty();
    }
}
