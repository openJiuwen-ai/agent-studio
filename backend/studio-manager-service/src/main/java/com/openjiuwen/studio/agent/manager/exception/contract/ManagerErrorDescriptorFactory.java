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
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;

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
        return newDescriptor(defn, requestId, safeDetails, ex);
    }

    /** 框架校验 → 参数校验定义 + allowlist details。 */
    public ErrorDescriptor fromValidation(StudioError error, List<String> detailMessages) {
        ErrorDefinition defn = catalog.resolve(error);
        List<ErrorDetail> safeDetails = toSafeDetails(detailMessages);
        return newDescriptor(defn, currentRequestId(), safeDetails, null);
    }

    /** 未知异常 → 安全兜底码 + cause。 */
    public ErrorDescriptor fromUnknown(Exception ex) {
        ErrorDefinition defn = catalog.unexpectedError();
        return newDescriptor(defn, currentRequestId(), null, ex);
    }

    /**
     * 指定 StudioError + 原始 cause——保留原始异常栈，不通过新异常替换。
     * 供 DataAccessException 等需特定码但需保留原始栈的场景使用。
     */
    public ErrorDescriptor fromStudioError(StudioError error, Throwable cause) {
        ErrorDefinition defn = catalog.resolve(error);
        return newDescriptor(defn, currentRequestId(), null, cause);
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
        // 统一族格式（2026-11-02 二期）：此兜底路径未知具体下游服务身份
        // （正常路径由 DownstreamErrorMapper 判定并打标签），不标组件——
        // 构建器退回 i18n 三键原格式，避免臆测组件名。
        return newDescriptor(defn, requestId, null, ex);
    }

    /**
     * AgentBaseException → 按 foundation ErrorCode 的原始 HTTP 状态码映射，
     * 不再一律返回 500。cause 保留异常栈。
     */
    public ErrorDescriptor fromAgentBaseException(AgentBaseException ex) {
        ErrorCode foundationErrorCode = ex.getErrorCode();
        if (foundationErrorCode == null) {
            ErrorDefinition defn = catalog.unexpectedError();
            return newDescriptor(defn, currentRequestId(), null, ex);
        }
        String code = foundationErrorCode.getCode();
        int httpStatus = foundationErrorCode.getHttpCode();
        return new ErrorDescriptor(
            code, httpStatus,
            code, code + ".reason", code + ".suggestion",
            currentRequestId(), null, null, null, ex, null,
            DependencyComponentLabels.forManagerErrorCode(code)
        );
    }

    /** FeignException → 下游依赖失败（502）；body 解析由 COM-04 响应单元接入。 */
    public ErrorDescriptor fromFeignException(FeignException ex) {
        ErrorDefinition defn = catalog.downstreamDependencyFailed();
        return newDescriptor(defn, currentRequestId(), null, ex);
    }

    /**
     * 统一构造入口（COM-04 §5.2 修订二期，2026-11-02；评审修订 2026-11-04）。
     * <p>
     * 评审修订（2026-11-04）：Manager 自有码（SQL/OBS/Redis 族）不再挂依赖组件
     * 标签——统一族格式会把既有接口的具体 error_msg 替换为族前缀
     * "下游依赖访问失败。"并改写 error_reason 结构，属破坏性对外契约变更（自检
     * 未做前向兼容评估）。自有码保持原三段 i18n 契约；组件标签只保留在真实
     * 下游路径（{@code DownstreamErrorMapper} 按服务身份判定，不由码族反推）。
     */
    private ErrorDescriptor newDescriptor(ErrorDefinition defn, String requestId,
                                          List<ErrorDetail> safeDetails, Throwable cause) {
        return new ErrorDescriptor(
            defn.getErrorCode(), defn.getHttpStatus(),
            defn.getMessageKey(), defn.getReasonKey(), defn.getSuggestionKey(),
            requestId, safeDetails, null, null, cause, null,
            null
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
