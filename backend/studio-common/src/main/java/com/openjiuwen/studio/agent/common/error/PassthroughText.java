/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

import java.util.Objects;

/**
 * COM-04 §5.2 契约修订(2026-11-02)：可信 RUNTIME 原码的受管三段文案。
 * <p>
 * 语义边界（区别于被禁止的"下游原文透传"）：
 * <ul>
 *   <li>来源仅限 Runtime 错误帧内由其自身 catalog/i18n 生成的
 *       {@code error_msg/error_reason/error_suggestion} 三字段——是下游服务的
 *       受管错误契约产物，不是原始 body、异常 {@code str()} 或未登记值；</li>
 *   <li>仅在 Manager i18n 无法解析（缺失/回显 key）时作为三段文案的回退值，
 *       不优先于 Manager 自有文案；</li>
 *   <li>构造前已由 parser 有界截断；本类只做非空校验，不再放大信息量。</li>
 * </ul>
 * <p>
 * 与 {@code cause/downstreamService/downstreamErrorCode} 不同，本对象参与
 * HTTP/SSE 构建器的回退序列化；与既有字段一致不参与 equals/hashCode 之外的
 * 任何诊断输出。
 */
public final class PassthroughText {

    private final String message;
    private final String reason;
    private final String suggestion;

    /**
     * @param message   受管 error_msg（必填，非 blank）
     * @param reason    受管 error_reason（可空）
     * @param suggestion 受管 error_suggestion（可空）
     */
    public PassthroughText(String message, String reason, String suggestion) {
        if (message == null || message.isBlank()) {
            throw new IllegalArgumentException("PassthroughText message must not be blank");
        }
        this.message = message;
        this.reason = normalize(reason);
        this.suggestion = normalize(suggestion);
    }

    public String getMessage() {
        return message;
    }

    public String getReason() {
        return reason;
    }

    public String getSuggestion() {
        return suggestion;
    }

    private static String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof PassthroughText that)) {
            return false;
        }
        return Objects.equals(message, that.message)
            && Objects.equals(reason, that.reason)
            && Objects.equals(suggestion, that.suggestion);
    }

    @Override
    public int hashCode() {
        return Objects.hash(message, reason, suggestion);
    }

    @Override
    public String toString() {
        return "PassthroughText{message-present=" + (message != null)
            + ", reason-present=" + (reason != null)
            + ", suggestion-present=" + (suggestion != null) + "}";
        // 文案本体不进 repr，避免诊断输出放大下游文本
    }
}
