/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * COM-03 §5: Manager 普通 HTTP 错误响应构建器。
 * <p>
 * 只负责序列化：接受 ErrorDescriptor + Locale，一次产生 ResponseEntity。
 * 不重新读取入站 Header，不调用 UUID，不从 exception message 推断状态/文案，
 * 不序列化 cause/downstream_*，不自行记录第二条错误日志。
 */
public class ManagerHttpErrorResponseBuilder {

    @FunctionalInterface
    public interface I18nResolver {
        String resolve(String key, Locale locale);
    }

    private final I18nResolver resolver;

    public ManagerHttpErrorResponseBuilder(I18nResolver resolver) {
        this.resolver = resolver;
    }

    public ResponseEntity<ErrorRsp> build(ErrorDescriptor descriptor, Locale locale) {
        // 检视意见：HTTP 路径与 SSE 路径共用同一回退序列化——
        // Manager i18n 缺失时回退到下游受管三段文案（PassthroughText），
        // 避免 HTTP 非流式把真实业务原因退成 generic 文案。
        var passthrough = descriptor.getPassthroughText();
        String messageFallback = passthrough != null ? passthrough.getMessage() : null;
        String errorMsg = safeResolve(descriptor.getMessageKey(), locale, messageFallback);
        String errorReason = safeResolve(descriptor.getReasonKey(), locale,
            passthrough != null ? firstNonBlank(passthrough.getReason(), messageFallback) : null);
        String errorSuggestion = safeResolve(descriptor.getSuggestionKey(), locale,
            passthrough != null ? firstNonBlank(passthrough.getSuggestion(), messageFallback) : null);

        ErrorRsp rsp = new ErrorRsp()
            .setErrorCode(descriptor.getErrorCode())
            .setErrorMsg(errorMsg)
            .setErrorReason(errorReason)
            .setErrorSuggestion(errorSuggestion)
            .setRequestId(descriptor.getRequestId());

        if (descriptor.getSafeDetails() != null) {
            List<ErrorDetail> copies = new ArrayList<>(descriptor.getSafeDetails());
            rsp.setDetails(copies);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Request-Id", descriptor.getRequestId());

        return new ResponseEntity<>(rsp, headers, HttpStatus.valueOf(descriptor.getHttpStatus()));
    }

    /**
     * COM-03 §4: fail-closed——resolver 异常时抛出,不返回空串。
     * 调用方 (build) 的调用者 (handler/listener) 应捕获并提供硬编码安全响应。
     */
    private String safeResolve(String key, Locale locale, String fallback) {
        try {
            String result = resolver.resolve(key, locale);
            // 检视意见：I18nUtil 缺资源时返回 key 本身，同样视为未解析（对齐 SSE builder）
            boolean resolved = result != null && !result.isBlank() && !result.equals(key);
            if (resolved) {
                return result;
            }
        } catch (RuntimeException ignored) {
            // 解析异常同样走回退（与 SSE builder 一致），不吞成空串
        }
        if (fallback != null && !fallback.isBlank()) {
            return fallback;
        }
        // COM-03 §4: fail-closed——异常/空串且无回退时抛出，由调用方兜底
        throw new IllegalStateException(
            "i18n resolution returned blank for key=" + key + " locale=" + locale);
    }

    private static String firstNonBlank(String first, String second) {
        return first != null && !first.isBlank() ? first : second;
    }
}
