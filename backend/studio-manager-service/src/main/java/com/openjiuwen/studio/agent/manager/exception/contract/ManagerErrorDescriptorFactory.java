/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.ErrorDefinition;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;

import feign.FeignException;

import org.slf4j.MDC;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * COM-03 §4.3: Manager 异常分类器 + descriptor 工厂。
 * <p>
 * 只执行一次分类，输出 ErrorDescriptor。HTTP/SSE 构建器不再选码。
 * request_id 只读 MDC（COM-05 CorrelationContextFilter 设置），不在异常处理器生成。
 */
public class ManagerErrorDescriptorFactory {

    private final ManagerErrorCatalog catalog;

    public ManagerErrorDescriptorFactory(ManagerErrorCatalog catalog) {
        this.catalog = catalog;
    }

    /** 已知业务异常 → 对应已登记定义。 */
    public ErrorDescriptor fromAgentStudioException(AgentStudioException ex) {
        return fromAgentStudioException(ex, currentRequestId());
    }

    /**
     * 已知业务异常 + 显式 request-id——供 reactive 回调线程（MDC 未传播）使用，
     * 避免 {@link #fromAgentStudioException(AgentStudioException)} 读 MDC 得 "unknown"。
     */
    public ErrorDescriptor fromAgentStudioException(AgentStudioException ex, String requestId) {
        ErrorDefinition defn = catalog.resolve(ex.getErrorCode());
        List<ErrorDetail> safeDetails = toSafeDetails(ex.getDetails());
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            requestId, safeDetails, null, null, ex
        );
    }

    /** 框架校验 → 参数校验定义 + allowlist details。 */
    public ErrorDescriptor fromValidation(StudioError error, List<String> detailMessages) {
        ErrorDefinition defn = catalog.resolve(error);
        List<ErrorDetail> safeDetails = toSafeDetails(detailMessages);
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            currentRequestId(), safeDetails, null, null, null
        );
    }

    /** 未知异常 → 安全兜底码 + cause。 */
    public ErrorDescriptor fromUnknown(Exception ex) {
        ErrorDefinition defn = catalog.unexpectedError();
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            currentRequestId(), null, null, null, ex
        );
    }

    /**
     * 指定 StudioError + 原始 cause——保留原始异常栈，不通过新异常替换。
     * 供 DataAccessException 等需特定码但需保留原始栈的场景使用。
     */
    public ErrorDescriptor fromStudioError(StudioError error, Throwable cause) {
        ErrorDefinition defn = catalog.resolve(error);
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            currentRequestId(), null, null, null, cause
        );
    }

    /** 下游依赖失败（502）。 */
    public ErrorDescriptor fromDownstreamDependency(Throwable ex) {
        return fromDownstreamDependencyWithRequestId(currentRequestId(), ex);
    }

    /**
     * COM-03 §5.2: 下游依赖失败 + 显式 request ID——供 listener 等回调线程使用,
     * 避免二次构造 descriptor。
     */
    public ErrorDescriptor fromDownstreamDependencyWithRequestId(String requestId, Throwable ex) {
        ErrorDefinition defn = catalog.downstreamDependencyFailed();
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            requestId, null, null, null, ex
        );
    }

    /** AgentBaseException → 安全兜底码（foundation 旧模型映射为 UNEXPECTED_ERROR）。 */
    public ErrorDescriptor fromAgentBaseException(AgentBaseException ex) {
        ErrorDefinition defn = catalog.unexpectedError();
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            currentRequestId(), null, null, null, ex
        );
    }

    /** FeignException → 下游依赖失败（502）；body 解析由 COM-04 响应单元接入。 */
    public ErrorDescriptor fromFeignException(FeignException ex) {
        ErrorDefinition defn = catalog.downstreamDependencyFailed();
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            currentRequestId(), null, null, null, ex
        );
    }

    private static String currentRequestId() {
        String rid = MDC.get("request-id");
        if (!StringUtils.hasText(rid)) {
            return "unknown";
        }
        return rid;
    }

    private static List<ErrorDetail> toSafeDetails(List<String> messages) {
        if (CollectionUtils.isEmpty(messages)) {
            return null;
        }
        return messages.stream()
            .map(msg -> new ErrorDetail().setErrorCode("openjiuwen.02001003").setErrorMsg(msg))
            .collect(Collectors.toCollection(ArrayList::new));
    }
}
