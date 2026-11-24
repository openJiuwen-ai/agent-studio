/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Map;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;

import org.springframework.web.bind.annotation.RequestHeader;

/**
 * issue #1750: 非流式 Runtime 调用必须显式请求非流式并透传调测头。
 */
class AgentRuntimeStreamHeaderContractTest {

    @Test
    void run_agent_with_conversation_sends_stream_and_invoke_mode_headers() {
        assertHeaders("runAgentWithConversation");
    }

    @Test
    void run_workflow_with_conversation_sends_stream_and_invoke_mode_headers() {
        assertHeaders("runWorkflowWithConversation");
    }

    private void assertHeaders(String methodName) {
        Method method = Arrays.stream(AgentRuntimeClient.class.getDeclaredMethods())
            .filter(item -> item.getName().equals(methodName))
            .findFirst()
            .orElseThrow();
        Map<String, String> headers = Arrays.stream(method.getParameters())
            .filter(parameter -> parameter.isAnnotationPresent(RequestHeader.class))
            .collect(Collectors.toMap(
                parameter -> parameter.getAnnotation(RequestHeader.class).value(),
                parameter -> parameter.getType().getSimpleName()));
        assertThat(headers).containsKeys("stream", "X-Invoke-Mode");
    }
}
