/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

/**
 * 默认 OpenAI 协议适配器, 同时作为未识别协议的 fallback 实现.
 */
@Slf4j
@Component("openApiRequestAdapterRun")
public class OpenApiRequestAdapter extends AbstractRequestAdapter {
    @Override
    public String getName() {
        return "openai";
    }
}
