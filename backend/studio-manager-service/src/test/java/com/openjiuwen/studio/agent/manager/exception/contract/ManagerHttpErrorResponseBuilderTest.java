/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Locale;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * COM-03 §10.2: Manager HTTP builder 契约测试。
 */
class ManagerHttpErrorResponseBuilderTest {

    private static final String CODE = "openjiuwen.02001129";
    private static final String MSG_KEY = "openjiuwen.02001129";
    private static final String REASON_KEY = "openjiuwen.02001129.reason";
    private static final String SUGGESTION_KEY = "openjiuwen.02001129.suggestion";
    private static final String REQ_ID = "req-test-001";

    // Resolver: message 段把 args 拼进返回值（验证 args 透传），reason/suggestion（args=null）只返回 key。
    private final ManagerHttpErrorResponseBuilder.I18nResolver resolver =
        (key, args, locale) -> args != null && args.length > 0 ? key + "::" + args[0] : key + "::resolved";

    private final ManagerHttpErrorResponseBuilder builder =
        new ManagerHttpErrorResponseBuilder(resolver);

    private ErrorDescriptor descriptor() {
        return new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, null);
    }

    @Test
    void fiveFieldsNonEmptyStrings() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        ErrorRsp body = resp.getBody();
        assertNotNull(body);
        assertEquals(CODE, body.getErrorCode());
        assertEquals(MSG_KEY + "::resolved", body.getErrorMsg());
        assertEquals(REASON_KEY + "::resolved", body.getErrorReason());
        assertEquals(SUGGESTION_KEY + "::resolved", body.getErrorSuggestion());
        assertEquals(REQ_ID, body.getRequestId());
    }

    @Test
    void bodyRequestIdEqualsHeader() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        ErrorRsp body = resp.getBody();
        assertNotNull(body);
        assertEquals(REQ_ID, body.getRequestId());
        assertEquals(REQ_ID, resp.getHeaders().getFirst("X-Request-Id"));
    }

    @Test
    void httpStatusFromDescriptor() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertEquals(404, resp.getStatusCode().value());
    }

    @Test
    void contentTypeJson() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertEquals("application/json", resp.getHeaders().getFirst("Content-Type"));
    }

    @Test
    void detailsOmittedWhenNull() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertNull(resp.getBody().getDetails());
    }

    @Test
    void detailsPresentWhenNonEmpty() {
        ErrorDetail detail = new ErrorDetail()
            .setErrorCode("test-fake-detail-code").setErrorMsg("Invalid field");
        ErrorDescriptor d = new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, List.of(detail), null, null, null);
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        assertNotNull(resp.getBody().getDetails());
        assertEquals(1, resp.getBody().getDetails().size());
        assertEquals("test-fake-detail-code", resp.getBody().getDetails().get(0).getErrorCode());
    }

    @Test
    void causeNotInBody() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, new IllegalStateException("secret"));
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        String bodyStr = resp.getBody().toString();
        assertFalse(bodyStr.contains("secret"), "cause message must not appear in body");
    }

    @Test
    void downstreamNotInBody() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.BUILDER,
            "test-fake-code", null);
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        String bodyStr = resp.getBody().toString();
        assertFalse(bodyStr.contains("BUILDER"), "downstream must not appear in body");
        assertFalse(bodyStr.contains("downstream"), "downstream must not appear in body");
    }

    @Test
    void differentStatusProducesCorrectHttpStatus() {
        ErrorDescriptor d500 = new ErrorDescriptor(CODE, 500, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, null);
        ResponseEntity<ErrorRsp> resp = builder.build(d500, Locale.CHINA);
        assertEquals(500, resp.getStatusCode().value());
    }

    // ---- 受管三段文案回退（COM-04 §5.2 修订，2026-11-02）----

    private static final String ENGINE_CODE = "openjiuwen.101003";

    private ErrorDescriptor engineDescriptor(PassthroughText passthrough) {
        return new ErrorDescriptor(ENGINE_CODE, 500, ENGINE_CODE,
            ENGINE_CODE + ".reason", ENGINE_CODE + ".suggestion", REQ_ID, null, null, null,
            null, passthrough);
    }

    @Test
    void passthroughTextUsedWhenI18nMisses() {
        // I18nUtil 语义：key 缺失回显 key 本身（视为未命中）→ 使用受管文案
        ManagerHttpErrorResponseBuilder b =
            new ManagerHttpErrorResponseBuilder((key, args, locale) -> key);
        ResponseEntity<ErrorRsp> resp = b.build(
            engineDescriptor(new PassthroughText("LLM调用失败：Connection error",
                "LLM组件调用模型服务失败", "请检查模型服务状态")), Locale.CHINA);
        assertEquals(ENGINE_CODE, resp.getBody().getErrorCode());
        assertEquals("LLM调用失败：Connection error", resp.getBody().getErrorMsg());
        assertEquals("LLM组件调用模型服务失败", resp.getBody().getErrorReason());
        assertEquals("请检查模型服务状态", resp.getBody().getErrorSuggestion());
    }

    @Test
    void i18nHitWinsOverPassthrough() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, null, null, null, null, new PassthroughText("passthrough-msg", null, null));
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        assertEquals(MSG_KEY + "::resolved", resp.getBody().getErrorMsg());
    }

    @Test
    void blankResolveWithoutPassthroughFailsClosed() {
        ManagerHttpErrorResponseBuilder b =
            new ManagerHttpErrorResponseBuilder((key, args, locale) -> "");
        org.junit.jupiter.api.Assertions.assertThrows(IllegalStateException.class,
            () -> b.build(descriptor(), Locale.CHINA));
    }

    // ---- 统一族格式（COM-04 §5.2 修订二期）----

    @Test
    void unifiedFamilyFormatForManagerSqlCode() {
        // factory 对 SQL_EXECUTE_FAILED 挂 mysql 标签（manager 直接访问数据库失败）
        com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory f =
            new com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory(
                new com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog());
        ErrorDescriptor d = f.fromStudioError(
            com.openjiuwen.studio.agent.common.enums.StudioError.SQL_EXECUTE_FAILED,
            new RuntimeException("connection refused"));
        org.junit.jupiter.api.Assertions.assertEquals("mysql", d.getDownstreamComponentLabel());

        ManagerHttpErrorResponseBuilder b = new ManagerHttpErrorResponseBuilder((key, args, locale) -> {
            if ("openjiuwen.02001042".equals(key)) {
                return "SQL执行失败。";
            }
            if ("openjiuwen.02001042.suggestion".equals(key)) {
                return "请检查数据库状态。";
            }
            return key; // 其余（含族 key）视为未命中 → 字面量兜底
        });
        ResponseEntity<ErrorRsp> resp = b.build(d, Locale.CHINA);
        assertEquals("下游依赖访问失败。", resp.getBody().getErrorMsg());
        assertEquals("组件mysql：SQL执行失败。", resp.getBody().getErrorReason());
        assertEquals("请检查数据库状态。", resp.getBody().getErrorSuggestion());
    }

    @Test
    void unifiedFamilyFormatForModelServiceUnavailableBuilderLabel() {
        // 02501037 回归本职（上游模型探活失败的业务码）：不带下游组件标签，
        // 构建器退回 i18n 三键原格式（用户裁定 builder 掉线走 02001131 兜底，
        // 2026-11-02）
        com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory f =
            new com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory(
                new com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog());
        ErrorDescriptor d = f.fromStudioError(
            com.openjiuwen.studio.agent.common.enums.StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE,
            new RuntimeException("model check failed"));
        org.junit.jupiter.api.Assertions.assertNull(d.getDownstreamComponentLabel());

        ManagerHttpErrorResponseBuilder b = new ManagerHttpErrorResponseBuilder((key, args, locale) -> {
            if ("openjiuwen.02501037".equals(key)) {
                return "模型服务不可用";
            }
            if ("openjiuwen.02501037.reason".equals(key)) {
                return "模型服务探活失败";
            }
            if ("openjiuwen.02501037.suggestion".equals(key)) {
                return "请检查第三方模型配置是否正确";
            }
            return key;
        });
        ResponseEntity<ErrorRsp> resp = b.build(d, Locale.CHINA);
        assertEquals("openjiuwen.02501037", resp.getBody().getErrorCode());
        assertEquals("模型服务不可用", resp.getBody().getErrorMsg());
        assertEquals("模型服务探活失败", resp.getBody().getErrorReason());
    }

    /** bug009 根因2: cause 为 ASE 时, args 透传给 resolver 填占位符, locale 不被误填。 */
    @Test
    void causeAgentStudioException_argsPassedToResolver() {
        // EXPORT_RESOURCE_NOT_EXISTS 抛出时 args=["agent"]（resourceType），三段同传。
        AgentStudioException cause = new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS,
            "agent");
        ErrorDescriptor d = new ErrorDescriptor(CODE, 400, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, cause);
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        assertEquals(MSG_KEY + "::agent", resp.getBody().getErrorMsg(),
            "args 应透传给 message resolver 填占位符,而非被 locale 误填");
        assertEquals(REASON_KEY + "::agent", resp.getBody().getErrorReason(),
            "reason 段同样透传 args");
        assertEquals(SUGGESTION_KEY + "::agent", resp.getBody().getErrorSuggestion(),
            "suggestion 段同样透传 args");
    }
}
