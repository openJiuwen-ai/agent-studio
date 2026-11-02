/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import java.util.Objects;

/**
 * COM-04 §4.1: 不可变下游事实对象。
 * <p>
 * 只表达"下游发生了什么"，不包含 Manager 对外码、i18n 文案或 {@code ResponseEntity}。
 * 原始 body 只在受限解析函数局部存在，不进入此对象、不进异常 message、不进日志。
 * 下游 {@code request_id} 不作为 Manager 对外字段复用。
 *
 * <p>契约修订（2026-11-02，方案 1）：可信 RUNTIME 原码的错误帧内
 * {@code error_msg/error_reason/error_suggestion} 三字段是 Runtime 自身
 * catalog/i18n 产物（受管三段文案，非原始 body/异常原文），由 parser 有界
 * 截断后进入本对象，供 mapper 构建回退文案。除此之外，
 * {@code message/reason/suggestion/details} 仍不作为 Manager 对外字段复用。
 *
 * <p>字段语义：
 * <ul>
 *   <li>{@code service}：由调用点或专用客户端配置显式提供，不按 URL/path/客户端名猜测；</li>
 *   <li>{@code transport}：调用适配器传入的传输通道；</li>
 *   <li>{@code downstreamHttpStatus}：仅诊断，不决定 Manager HTTP status；</li>
 *   <li>{@code downstreamErrorCode}：严格解析且可信时才有，否则 {@code null}；</li>
 *   <li>{@code downstreamMessage/Reason/Suggestion}：受管三段文案（见契约修订），
 *       仅可信 RUNTIME 错误帧提取，否则 {@code null}；</li>
 *   <li>{@code phase}：失败阶段；</li>
 *   <li>{@code cause}：原始 cause，仅内部日志，不进对外响应。</li>
 * </ul>
 */
public final class DownstreamFailure {

    private final DownstreamService service;
    private final Transport transport;
    private final FailurePhase phase;
    private final Integer downstreamHttpStatus;
    private final String downstreamErrorCode;
    private final String downstreamMessage;
    private final String downstreamReason;
    private final String downstreamSuggestion;
    private final Throwable cause;

    private DownstreamFailure(DownstreamService service, Transport transport, FailurePhase phase,
                              Integer downstreamHttpStatus, String downstreamErrorCode,
                              String downstreamMessage, String downstreamReason,
                              String downstreamSuggestion, Throwable cause) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamFailure service must not be null");
        }
        if (transport == null) {
            throw new IllegalArgumentException("DownstreamFailure transport must not be null");
        }
        if (phase == null) {
            throw new IllegalArgumentException("DownstreamFailure phase must not be null");
        }
        this.service = service;
        this.transport = transport;
        this.phase = phase;
        this.downstreamHttpStatus = downstreamHttpStatus;
        this.downstreamErrorCode = downstreamErrorCode;
        this.downstreamMessage = downstreamMessage;
        this.downstreamReason = downstreamReason;
        this.downstreamSuggestion = downstreamSuggestion;
        this.cause = cause;
    }

    /** HTTP 响应阶段失败（非 2xx）。原码严格解析可信时传入，否则 {@code null}。 */
    public static DownstreamFailure httpResponse(DownstreamService service, Transport transport,
                                                 Integer downstreamHttpStatus,
                                                 String downstreamErrorCode, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.HTTP_RESPONSE,
            downstreamHttpStatus, downstreamErrorCode, null, null, null, cause);
    }

    /**
     * HTTP 响应阶段失败（非 2xx），携带受管三段文案（可信 RUNTIME 错误体）。
     */
    public static DownstreamFailure httpResponse(DownstreamService service, Transport transport,
                                                 Integer downstreamHttpStatus,
                                                 String downstreamErrorCode,
                                                 String downstreamMessage, String downstreamReason,
                                                 String downstreamSuggestion, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.HTTP_RESPONSE,
            downstreamHttpStatus, downstreamErrorCode, downstreamMessage, downstreamReason,
            downstreamSuggestion, cause);
    }

    /** SSE 流内明确 error event。原码严格解析可信时传入，否则 {@code null}。 */
    public static DownstreamFailure sseEvent(DownstreamService service, Transport transport,
                                             String downstreamErrorCode, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.SSE_EVENT,
            null, downstreamErrorCode, null, null, null, cause);
    }

    /**
     * SSE 流内明确 error event，携带受管三段文案（可信 RUNTIME 错误帧）。
     */
    public static DownstreamFailure sseEvent(DownstreamService service, Transport transport,
                                             String downstreamErrorCode,
                                             String downstreamMessage, String downstreamReason,
                                             String downstreamSuggestion, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.SSE_EVENT,
            null, downstreamErrorCode, downstreamMessage, downstreamReason,
            downstreamSuggestion, cause);
    }

    /** 传输层失败（无 HTTP 响应，无可信原码）。 */
    public static DownstreamFailure transportFailure(DownstreamService service, Transport transport,
                                                     Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.TRANSPORT,
            null, null, null, null, null, cause);
    }

    public DownstreamService getService() {
        return service;
    }

    public Transport getTransport() {
        return transport;
    }

    public FailurePhase getPhase() {
        return phase;
    }

    /** 仅诊断，不决定 Manager HTTP status。传输阶段为 {@code null}。 */
    public Integer getDownstreamHttpStatus() {
        return downstreamHttpStatus;
    }

    /** 严格解析且可信时才有；不可信/无原码/传输失败为 {@code null}。 */
    public String getDownstreamErrorCode() {
        return downstreamErrorCode;
    }

    /** 受管 error_msg（契约修订 2026-11-02）；非可信 RUNTIME 错误帧为 {@code null}。 */
    public String getDownstreamMessage() {
        return downstreamMessage;
    }

    /** 受管 error_reason；可空。 */
    public String getDownstreamReason() {
        return downstreamReason;
    }

    /** 受管 error_suggestion；可空。 */
    public String getDownstreamSuggestion() {
        return downstreamSuggestion;
    }

    /** 原始 cause，仅内部日志，不进对外响应。 */
    public Throwable getCause() {
        return cause;
    }

    /** 是否携带可信原码（用于 mapper 决策）。 */
    public boolean hasTrustedErrorCode() {
        return downstreamErrorCode != null && !downstreamErrorCode.isBlank();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof DownstreamFailure that)) {
            return false;
        }
        return service == that.service
            && transport == that.transport
            && phase == that.phase
            && Objects.equals(downstreamHttpStatus, that.downstreamHttpStatus)
            && Objects.equals(downstreamErrorCode, that.downstreamErrorCode);
        // cause intentionally excluded（不参与相等性）
    }

    @Override
    public int hashCode() {
        return Objects.hash(service, transport, phase, downstreamHttpStatus, downstreamErrorCode);
    }

    @Override
    public String toString() {
        return "DownstreamFailure{service=" + service + ", transport=" + transport
            + ", phase=" + phase
            + (downstreamHttpStatus != null ? ", downstreamHttpStatus=" + downstreamHttpStatus : "")
            + (hasTrustedErrorCode() ? ", downstreamErrorCode='" + downstreamErrorCode + "'" : "")
            + "}";
        // cause, raw body intentionally omitted from repr for safety
    }
}
