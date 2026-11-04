/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;

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
        String resolve(String key, Object[] args, Locale locale);
    }

    private final I18nResolver resolver;

    public ManagerHttpErrorResponseBuilder(I18nResolver resolver) {
        this.resolver = resolver;
    }

    public ResponseEntity<ErrorRsp> build(ErrorDescriptor descriptor, Locale locale) {
        // 从异常 cause 提取 args 填 i18n 占位符（origin 10f62b9cd 特性）；族格式
        // 文案无占位符, 多传 args 被 MessageFormat 忽略, 与统一族格式兼容。
        Object[] args = extractArgs(descriptor);
        String label = descriptor.getDownstreamComponentLabel();
        String errorMsg;
        String errorReason;
        String errorSuggestion;
        if (label != null) {
            // 统一族格式（COM-04 §5.2 修订二期，2026-11-02 用户裁定）：
            // error_msg=族前缀，error_reason="组件{label}：{错误信息}"
            errorMsg = DownstreamFamilyFormat.message(resolver, args, locale);
            errorReason = DownstreamFamilyFormat.reason(resolver, descriptor, label, args, locale);
            errorSuggestion = DownstreamFamilyFormat.suggestion(resolver, descriptor, args, locale);
        } else {
            PassthroughText passthrough = descriptor.getPassthroughText();
            String messageFallback = passthrough != null ? passthrough.getMessage() : null;
            errorMsg = safeResolve(descriptor.getMessageKey(), args, locale, messageFallback);
            errorReason = safeResolve(descriptor.getReasonKey(), args, locale,
                passthrough != null ? firstNonBlank(passthrough.getReason(), messageFallback) : null);
            errorSuggestion = safeResolve(descriptor.getSuggestionKey(), args, locale,
                passthrough != null ? firstNonBlank(passthrough.getSuggestion(), messageFallback) : null);
        }

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

        return new ResponseEntity<>(rsp, headers, resolveHttpStatus(descriptor.getHttpStatus()));
    }

    /**
     * descriptor 状态 → HttpStatus 安全解析（评审修订 2026-11-04）。
     * <p>
     * {@code HttpStatus.valueOf(int)} 对未注册状态（499/599 等）抛
     * {@code IllegalArgumentException}——透传/兜底路径把本应正常返回的下游错误
     * 升级为未处理异常；且 safeBuild 的 catch 分支再次构造响应时同样会抛。
     * {@code HttpStatus.resolve(int)} 对未注册状态返回 null——此处回退 502
     * （下游失败族语义），错误体仍正常返回。全局唯一状态出口：HTTP/SSE
     * 构建器与兜底分支一律经由本方法。
     */
    public static HttpStatus resolveHttpStatus(int statusCode) {
        HttpStatus resolved = HttpStatus.resolve(statusCode);
        return resolved != null ? resolved : HttpStatus.BAD_GATEWAY;
    }

    /**
     * COM-03 §4 fail-closed + COM-04 §5.2 修订（2026-11-02）回退：
     * 优先 i18n 解析（含"回显 key"视为未命中——I18nUtil 以 key 作默认值返回）；
     * 未命中且有受管三段文案回退值时使用回退值；否则按原 fail-closed 语义
     * 抛出（resolver 异常原样重抛，空值抛 IllegalStateException），不返回空串。
     * 调用方 (build) 的调用者 (handler/listener) 应捕获并提供硬编码安全响应。
     */
    private String safeResolve(String key, Object[] args, Locale locale, String passthroughFallback) {
        String result = null;
        RuntimeException resolveError = null;
        try {
            result = resolver.resolve(key, args, locale);
        } catch (RuntimeException e) {
            resolveError = e;
        }
        boolean miss = result == null || result.isBlank() || key.equals(result);
        if (miss && passthroughFallback != null && !passthroughFallback.isBlank()) {
            return passthroughFallback;
        }
        if (resolveError != null) {
            throw resolveError;
        }
        if (result == null || result.isBlank()) {
            throw new IllegalStateException(
                "i18n resolution returned blank for key=" + key + " locale=" + locale);
        }
        return result;
    }

    /** 字段级回退链的第二跳：字段文案缺失时回退到 message（mapper 兜底之外的双保险）。 */
    private static String firstNonBlank(String primary, String secondary) {
        if (primary != null && !primary.isBlank()) {
            return primary;
        }
        if (secondary != null && !secondary.isBlank()) {
            return secondary;
        }
        return null;
    }

    /** 从 descriptor.cause 提取 i18n 占位符 args; cause 非 ASE 时返回 null。 */
    private Object[] extractArgs(ErrorDescriptor descriptor) {
        Throwable cause = descriptor.getCause();
        if (cause instanceof com.openjiuwen.studio.agent.common.exception.AgentStudioException ase) {
            return ase.getArgs();
        }
        return null;
    }
}
