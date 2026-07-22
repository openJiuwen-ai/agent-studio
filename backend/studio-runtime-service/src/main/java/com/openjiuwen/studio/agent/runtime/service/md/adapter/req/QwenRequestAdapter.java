/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;

import lombok.extern.slf4j.Slf4j;

import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.Map;

/**
 * 添加类的描述
 *
 */
@Slf4j
@Component("qwenRequestAdapter")
public class QwenRequestAdapter extends AbstractRequestAdapter {
    @Override
    public String getName() {
        return "qwen";
    }

    @Override
    public Object requestBodyConvert(Map<String, String> headers, Object body, boolean stream) {
        if (!stream) {
            return body;
        }
        Map<String, Boolean> streamOptions = Collections.singletonMap("include_usage", true);
        if (body instanceof Map) {
            @SuppressWarnings("unchecked") Map<String, Object> bodyMap = (Map<String, Object>) body;
            bodyMap.put("stream_options", streamOptions);
            return bodyMap;
        } else if (body instanceof ChatCompletionRequest chatReq) {
            chatReq.setStreamOptions(streamOptions);

            if (chatReq.getThinking() == null) {
                return body;
            }
            if ("disabled".equals(chatReq.getThinking().getType())) {
                chatReq.setThinking(null);
                chatReq.setEnableThinking(false);
            } else {
                chatReq.setThinking(null);
                chatReq.setEnableThinking(true);
            }

            return body;
        } else {
            return body;
        }
    }
}
