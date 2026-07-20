/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

/**
 * 异步任务专用的工作流监听器。
 * 继承WorkflowListener，复用事件解析和调试记录保存逻辑，
 * 额外处理异步任务场景下的四个特殊需求：
 *
 * 1. passThrough()为空操作：异步任务无前端消费SseEmitter，跳过SSE转发。
 *
 * 2. 捕获message事件内容：WorkflowListener对message事件仅passThrough，
 *    但异步任务需要保存assistant回复到会话历史，因此在此提取message事件中的文本。
 *
 * 3. onFailure时标记taskEnd=true：解除TaskRuntimeService的轮询阻塞。
 *    原WorkflowListener的onFailure不设置taskEnd，因为流式场景由前端SSE连接关闭驱动。
 *
 * 4. onFailure时设置instance状态为FAILED并保存调试记录。
 *    OkHttp SSE的onFailure和onClosed互斥（只触发其一），
 *    原WorkflowListener仅在onClosed->saveInstance()中保存，
 *    导致onFailure路径下调试记录丢失。
 */
@Slf4j
public class AsyncWorkflowListener extends WorkflowListener {

    /**
     * 从message事件中提取的工作流输出内容，用于保存assistant回复到会话历史。
     * 使用StringBuilder累积多次message事件的文本。
     */
    @Getter
    private final StringBuilder messageContent = new StringBuilder();

    public AsyncWorkflowListener(String requestId, ExecuteParams executeParams, WorkflowRunResult result,
        HttpHeaders headers) {
        super(requestId, executeParams, result, headers);
    }

    /**
     * 获取WorkflowRunResult（包含instance和nodeRunInfoList）。
     * result字段继承自WorkflowListener（protected），此getter供TaskRuntimeService访问。
     */
    public WorkflowRunResult getResult() {
        return result;
    }

    /**
     * 异步任务无前端消费SseEmitter，跳过SSE转发避免无意义的send error日志。
     */
    @Override
    protected void passThrough(String data) {
        // no-op: 异步任务不转发SSE事件
    }

    /**
     * 在每个事件被process()处理后，额外捕获message事件中的文本内容。
     * 工作流的assistant回复通过message事件推送，WorkflowListener本身不存储这些内容，
     * 异步任务需要在此提取以便后续保存到会话历史。
     */
    @Override
    public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        super.onEvent(eventSource, id, type, data);
        captureMessageContent(data);
    }

    /**
     * 从message类型的SSE事件中提取文本内容。
     * 九问引擎的message事件结构：{"event":"message","data":{"text":"...","answer":"...",...},...}
     *
     * 字段语义：
     * - text: 增量文本片段（流式LLM节点每帧推送一小段）
     * - answer: 完整累积文本（流式LLM节点包含截至当前帧的全部文本）
     *
     * 策略：
     * - 优先使用answer字段（完整文本，直接替换）
     * - 无answer时累积text字段（增量chunk，逐帧追加）
     */
    private void captureMessageContent(String eventStr) {
        try {
            JSONObject eventObj = JSONObject.parseObject(eventStr);
            if (!"message".equals(eventObj.getString("event"))) {
                return;
            }
            JSONObject dataObj = eventObj.getJSONObject("data");
            if (dataObj == null) {
                return;
            }
            // answer字段存在时，包含完整累积文本，直接替换
            Object answer = dataObj.get("answer");
            if (answer != null) {
                String answerStr = answer.toString();
                if (!answerStr.isEmpty()) {
                    messageContent.setLength(0);
                    messageContent.append(answerStr);
                }
                return;
            }
            // 无answer字段时，text为增量内容，累积追加
            String text = dataObj.getString("text");
            if (text != null && !text.isEmpty()) {
                messageContent.append(text);
            }
        } catch (Exception e) {
            log.warn("Failed to capture message content from event", e);
        }
    }

    @Override
    public void onFailure(@NotNull EventSource eventSource, @Nullable Throwable t, @Nullable Response response) {
        MDC.put(REQUEST_ID, requestId);
        try {
            executeParams.setSuccess(-1);
            log.error("Async workflow process failed. Throwable: {}, Response: {}", t, response);

            // 标记任务结束，解除TaskRuntimeService.waitForWorkflowCompletion()的轮询阻塞
            result.setTaskEnd(true);

            // 设置instance为FAILED状态（saveInstance内部会判断：
            // 如果status是RUNNING且workflowEnd=false，会错误地覆盖为SUCCEEDED，
            // 所以必须在saveInstance之前显式设为FAILED）
            WorkflowInstanceEntity instance = result.getInstance();
            if (instance != null) {
                instance.setStatus(WorkflowRunStatus.FAILED.getStatus().getDesc());
                instance.setEndTime(System.currentTimeMillis());
                if (t != null) {
                    instance.setErrorInfo(t.getMessage());
                } else if (response != null) {
                    instance.setErrorInfo("Runtime request failed, HTTP " + response.code());
                }
            }

            // onFailure与onClosed互斥，必须在此保存调试记录，否则丢失
            saveInstance();

            this.errorRsp = createErrorRsp(t, response);
            this.openConnect = true;
        } catch (Exception e) {
            log.error("Fail handler response. {}", e.getMessage());
            this.openConnect = true;
        } finally {
            try {
                sseEmitter.complete();
            } catch (Throwable e) {
                log.warn("Fail close sse. {}", e.getMessage());
            }
        }
    }
}
