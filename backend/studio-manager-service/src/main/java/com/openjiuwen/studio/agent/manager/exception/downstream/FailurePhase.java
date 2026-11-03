/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

/**
 * COM-04 §4.1: 下游失败发生的阶段。仅内部诊断，不进入对外响应。
 */
public enum FailurePhase {
    /** 下游返回了 HTTP 响应（非 2xx），可尝试解析 body。 */
    HTTP_RESPONSE,
    /** SSE 流内收到明确 error event。 */
    SSE_EVENT,
    /** 传输层失败（DNS/connect/TLS/read timeout/连接中断/取消），无 HTTP 响应。 */
    TRANSPORT
}
