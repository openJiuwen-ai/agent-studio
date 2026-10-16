/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Map;

/**
 * Provider 返回的不可变关联 Header 集合（COM-04 §4.2）。
 *
 * <p>构造时防御复制来源 Map；{@link #asMap()} 返回不可修改视图。
 */
public final class CorrelationHeaders {

    private final Map<String, String> headers;

    private CorrelationHeaders(Map<String, String> headers) {
        this.headers = Map.copyOf(headers);
    }

    /** 以来源 Map 的防御副本构造。 */
    public static CorrelationHeaders of(Map<String, String> headers) {
        return new CorrelationHeaders(headers);
    }

    /** 不可修改视图。 */
    public Map<String, String> asMap() {
        return headers;
    }
}
