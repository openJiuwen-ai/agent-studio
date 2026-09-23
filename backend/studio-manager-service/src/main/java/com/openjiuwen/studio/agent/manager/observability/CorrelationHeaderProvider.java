/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.MDC;

/**
 * Manager 唯一只读出站关联 Header Provider（COM-04 §4.2/§4.3）。
 *
 * <p>只从 Manager MDC 读取权威关联 ID，不选择、生成、修正或推断任何值：
 * 不读入站 Header/URL/DTO，不调 UUID，不用 request 回退 trace/execution，
 * 不修改 MDC，不记录 Header 值。MDC 值应由 COM-05 入口与 DEF-02 执行链确定。
 *
 * <p>任一策略必需值为空（null 或空串——COM-05 入口外层 scope 会显式置空
 * execution/conversation）时抛 {@link MissingContextException}，由调用适配层
 * 映射为现有安全的内部调用失败语义；异常消息只含策略与缺失字段名。
 */
public final class CorrelationHeaderProvider {

    /** 出站 Header 名：X-Request-Id。 */
    public static final String REQUEST_ID_HEADER = "X-Request-Id";

    /** 出站 Header 名：TraceID。 */
    public static final String TRACE_ID_HEADER = "TraceID";

    /** 出站 Header 名：X-Execution-Id（仅 RUNTIME_EXECUTION 输出）。 */
    public static final String EXECUTION_ID_HEADER = "X-Execution-Id";

    /** MDC key → 出站 Header 名的固定映射。 */
    private static final Map<String, String> MDC_TO_HEADER = Map.of(
        MdcKeys.REQUEST_ID, REQUEST_ID_HEADER,
        MdcKeys.TRACE_ID, TRACE_ID_HEADER,
        MdcKeys.EXECUTION_ID, EXECUTION_ID_HEADER);

    private CorrelationHeaderProvider() {
    }

    /** 缺失必需 MDC 上下文时抛出；消息只含策略与字段名，不含任何 Header 值。 */
    public static final class MissingContextException extends IllegalStateException {
        MissingContextException(String message) {
            super(message);
        }
    }

    /** 出站 Header 目标抽象：由各客户端适配器实现，覆盖算法统一调用。 */
    public interface CorrelationHeaderSink {
        /** 当前全部 Header 名（用于大小写不敏感匹配）。 */
        Set<String> headerNames();

        /** 删除指定名称的全部值。 */
        void removeHeader(String name);

        /** 写入唯一权威值。 */
        void setHeader(String name, String value);
    }

    /**
     * 按策略读取 MDC 并返回不可变 Header 集合。
     *
     * @throws MissingContextException 任一必需值为 null 或空串
     */
    public static CorrelationHeaders provide(OutboundCorrelationPolicy policy) {
        List<String> missing = new ArrayList<>();
        Map<String, String> out = new java.util.LinkedHashMap<>();
        for (String mdcKey : policy.requiredMdcKeys()) {
            String value = MDC.get(mdcKey);
            if (value == null || value.isEmpty()) {
                missing.add(mdcKey);
            } else {
                out.put(MDC_TO_HEADER.get(mdcKey), value);
            }
        }
        if (!missing.isEmpty()) {
            throw new MissingContextException(
                "missing correlation context for policy " + policy + ": " + String.join(", ", missing));
        }
        return CorrelationHeaders.of(out);
    }

    /**
     * 覆盖算法（§4.3）：对既有 Header 名做大小写不敏感匹配，先删除三个关联 Header
     * 的全部既有值，再按策略写入权威值。非执行/Builder 策略删除后不写 execution，
     * 天然保持其不存在。
     */
    public static void apply(CorrelationHeaders headers, CorrelationHeaderSink sink) {
        // 1. 大小写不敏感删除三个关联 Header 的全部既有值（含调用方伪造的重复变体）
        for (String existing : new ArrayList<>(sink.headerNames())) {
            if (isCorrelationHeader(existing)) {
                sink.removeHeader(existing);
            }
        }
        // 2. 写入策略唯一允许的权威值
        headers.asMap().forEach(sink::setHeader);
    }

    private static boolean isCorrelationHeader(String name) {
        return REQUEST_ID_HEADER.equalsIgnoreCase(name) || TRACE_ID_HEADER.equalsIgnoreCase(name)
            || EXECUTION_ID_HEADER.equalsIgnoreCase(name);
    }
}
