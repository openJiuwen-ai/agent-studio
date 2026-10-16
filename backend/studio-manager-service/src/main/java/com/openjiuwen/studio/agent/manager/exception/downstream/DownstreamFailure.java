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
 * 下游 {@code request_id}、{@code message/reason/suggestion/details} 不作为 Manager
 * 对外字段复用。
 *
 * <p>字段语义：
 * <ul>
 *   <li>{@code service}：由调用点或专用客户端配置显式提供，不按 URL/path/客户端名猜测；</li>
 *   <li>{@code transport}：调用适配器传入的传输通道；</li>
 *   <li>{@code downstreamHttpStatus}：仅诊断，不决定 Manager HTTP status；</li>
 *   <li>{@code downstreamErrorCode}：严格解析且可信时才有，否则 {@code null}；</li>
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
    private final Throwable cause;

    private DownstreamFailure(DownstreamService service, Transport transport, FailurePhase phase,
                              Integer downstreamHttpStatus, String downstreamErrorCode,
                              Throwable cause) {
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
        this.cause = cause;
    }

    /** HTTP 响应阶段失败（非 2xx）。原码严格解析可信时传入，否则 {@code null}。 */
    public static DownstreamFailure httpResponse(DownstreamService service, Transport transport,
                                                 Integer downstreamHttpStatus,
                                                 String downstreamErrorCode, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.HTTP_RESPONSE,
            downstreamHttpStatus, downstreamErrorCode, cause);
    }

    /** SSE 流内明确 error event。原码严格解析可信时传入，否则 {@code null}。 */
    public static DownstreamFailure sseEvent(DownstreamService service, Transport transport,
                                             String downstreamErrorCode, Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.SSE_EVENT,
            null, downstreamErrorCode, cause);
    }

    /** 传输层失败（无 HTTP 响应，无可信原码）。 */
    public static DownstreamFailure transportFailure(DownstreamService service, Transport transport,
                                                     Throwable cause) {
        return new DownstreamFailure(service, transport, FailurePhase.TRANSPORT,
            null, null, cause);
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
