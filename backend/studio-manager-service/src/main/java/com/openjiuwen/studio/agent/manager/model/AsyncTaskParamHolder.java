/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model;

import lombok.Data;
import okhttp3.sse.EventSource;

/**
 * 异步任务参数Holder，存储异步信息和资源
 *
 */
@Data
public class AsyncTaskParamHolder {
    private boolean isAsync;

    private int timeout;

    private EventSource eventSource;

    public AsyncTaskParamHolder(boolean isAsync, int timeout) {
        this.isAsync = isAsync;
        this.timeout = timeout;
        this.eventSource = null;
    }
}
