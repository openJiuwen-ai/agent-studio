/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
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
    protected void onEventBusinessHook(@Nullable String id, @Nullable String type, @NotNull String data) {
        super.onEventBusinessHook(id, type, data);
        captureMessageContent(data);
    }

    /**
     * COM-04 响应 §5.5: 异步路径无 HTTP/SSE 对外输出——不调用 builder。
     * descriptor 已由 {@link #handleSseErrorEvent} / {@link #handleTerminalFailure}
     * 存入 {@code lastErrorDescriptor}，供任务终态使用稳定码。
     */
    @Override
    protected void sendErrorToConsumer(ErrorDescriptor descriptor) {
        // no-op: 异步无前端 SSE 消费者
    }

    /**
     * COM-04 响应 §5.5: 异步路径不构造 ResponseEntity——无 HTTP 消费者。
     */
    @Override
    protected void setErrorResponse(ErrorDescriptor descriptor) {
        // no-op: 异步无 HTTP 消费者
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
    protected void onFailureInternal(@Nullable Throwable t, @Nullable Response response) {
        // COM-04 响应 §5.5: 异步路径无 HTTP/SSE 对外输出——不构造 ResponseEntity，
        // 不调用 HTTP/SSE builder；仍满足一次解析、一次映射、内部 downstream_* 可诊断、
        // 原文零泄漏。guard 竞争由 handleTerminalFailure 统一——非赢家只做幂等清理。
        try {
            ErrorDescriptor descriptor = handleTerminalFailure(t, response);
            if (descriptor != null) {
                // COM-04 响应 §5.5.1: 赢家——一次映射的既成 descriptor 驱动安全任务终态
                executeParams.setSuccess(-1);
                result.setTaskEnd(true);

                WorkflowInstanceEntity instance = result.getInstance();
                if (instance != null) {
                    instance.setStatus(WorkflowRunStatus.FAILED.getStatus().getDesc());
                    instance.setEndTime(System.currentTimeMillis());
                    // COM-04 响应 §5.5.3: 实例诊断只用 Manager 稳定错误码/安全文案，
                    // 不保存 throwable message、下游 body 或 Response 字符串
                    instance.setErrorInfo(descriptor.getErrorCode());
                }

                // onFailure与onClosed互斥，必须在此保存调试记录，否则丢失
                saveInstance();
            }
        } catch (Exception e) {
            log.error("Fail handler response. {}", e.getMessage());
        } finally {
            latch.countDown();
            try {
                sseEmitter.complete();
            } catch (Throwable e) {
                log.warn("Fail close sse. {}", e.getMessage());
            }
        }
    }
}
