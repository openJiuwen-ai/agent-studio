/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

/**
 * COM-03 §4.1: 直接下游服务类别。仅内部使用，不进入对外 HTTP/SSE 响应。
 */
public enum DownstreamService {
    RUNTIME,
    BUILDER,
    EXTERNAL
}
