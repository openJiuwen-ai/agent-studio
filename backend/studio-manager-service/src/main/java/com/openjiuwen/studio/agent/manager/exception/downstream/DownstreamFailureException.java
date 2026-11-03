/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

/**
 * COM-04 §5.1/§8: 携带 {@link DownstreamFailure} 的内部异常。
 * <p>
 * 由各传输 adapter（Feign ErrorDecoder / ClientTemplate ResponseErrorHandler /
 * WebClient operator / OkHttp SSE listener）在解析下游响应后抛出，供统一 Advice
 * 捕获后调用 {@link DownstreamErrorMapper} 一次。该异常本身不选 Manager 码、
 * 不构造 ResponseEntity、不进对外响应。
 *
 * <p>这是 RuntimeException（非 checked），避免在 Reactor/WebClient 链路强加 throws。
 */
public class DownstreamFailureException extends RuntimeException {

    private final DownstreamFailure failure;

    public DownstreamFailureException(DownstreamFailure failure) {
        super(requireValid(failure).toString(), null, false, false);
        this.failure = failure;
    }

    /** 校验须在 super() 求值前完成——静态辅助函数先行抛出 IllegalArgumentException。 */
    private static DownstreamFailure requireValid(DownstreamFailure failure) {
        if (failure == null) {
            throw new IllegalArgumentException("DownstreamFailure must not be null");
        }
        return failure;
    }

    /** 由统一 Advice 取出，交给 mapper 一次。 */
    public DownstreamFailure getFailure() {
        return failure;
    }
}
