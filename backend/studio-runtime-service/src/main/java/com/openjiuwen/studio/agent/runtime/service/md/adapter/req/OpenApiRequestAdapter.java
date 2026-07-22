/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import com.openjiuwen.studio.agent.runtime.dto.md.RankDocumentsRequest;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 默认 OpenAI 协议适配器, 同时作为未识别协议的 fallback 实现.
 *
 * rerank 场景的请求/响应转换统一委托给 {@link MaasRerankRequestAdaptor} 的静态方法,
 * 保证 rerank 逻辑只有一份实现, 避免多处冗余.
 */
@Slf4j
@Component("openApiRequestAdapterRun")
public class OpenApiRequestAdapter extends AbstractRequestAdapter {
    @Override
    public String getName() {
        return "openai";
    }

    @Override
    public Object requestBodyConvert(Map<String, String> headers, Object body, boolean stream) {
        // rerank 请求委托给 MaasRerankRequestAdaptor 统一处理 (docs -> documents)
        if (body instanceof RankDocumentsRequest) {
            return MaasRerankRequestAdaptor.convertRerankRequestBody(body);
        }
        return body;
    }
}
