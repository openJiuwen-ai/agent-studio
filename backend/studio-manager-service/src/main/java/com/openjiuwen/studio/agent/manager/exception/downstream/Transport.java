/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

/**
 * COM-04 §4.1: 下游调用使用的传输通道。仅内部诊断，不进入对外响应。
 */
public enum Transport {
    FEIGN,
    CLIENT_TEMPLATE,
    WEBCLIENT,
    OKHTTP_SSE
}
