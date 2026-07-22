/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service.md.adapter.req;

import static com.openjiuwen.studio.agent.runtime.constant.Constant.REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.TASK_ID;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.runtime.dto.md.RankDocumentsRequest;
import com.openjiuwen.studio.agent.runtime.enums.ModelRespContentType;
import com.openjiuwen.studio.agent.runtime.exception.OpenAiHttpException;
import com.openjiuwen.studio.agent.runtime.http.HttpResponse;
import com.openjiuwen.studio.agent.runtime.http.SseEmitterUTF8;
import com.openjiuwen.studio.agent.runtime.model.ModelApiLog;
import com.openjiuwen.studio.agent.runtime.service.md.RuntimeModelApiLogService;
import com.openjiuwen.studio.agent.runtime.service.security.SecurityService;
import com.openjiuwen.studio.agent.runtime.thread.ModelApiLogThreadLocal;
import com.openjiuwen.studio.agent.runtime.utils.ModelInvokeExceptionUtil;

import lombok.extern.slf4j.Slf4j;

import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Future;

@Slf4j
public abstract class AbstractRequestAdapter implements RequestAdapter {
    static final String USAGE = "usage";

    @Autowired
    @Qualifier("modelRequestThreadPool")
    protected ThreadPoolTaskExecutor executor;

    @Autowired
    @Qualifier("securityCheckThreadPool")
    protected ThreadPoolTaskExecutor securityCheckExecutor;

    @Autowired
    protected SecurityService securityService;

    @Autowired
    protected RuntimeModelApiLogService apiLogService;


    @Override
    public Object requestBodyConvert(Map<String, String> headers, Object body, boolean stream) {
        if (body instanceof ChatCompletionRequest chat) {
            chat.setThinking(null);
        }
        return body;
    }

    @Override
    public Object streamResBodyConvert(String url, HttpResponse<String> response) {
        if (response.getStatusCode() >= 300 || (response.getHeaders() != null && response.getHeaders()
            .containsKey("Content-Type") && !response.getHeaders().get("Content-Type").contains("stream"))) {
            log.error("Stream Request Invoke model service error. url:{} status:{} response:{}", url,
                response.getStatusCode(), response.getErrorResponseBody());
            throw httpExceptionHandler(response.getStatusCode(), response.getErrorResponseBody());
        }
        SseEmitterUTF8 sseEmitter = new SseEmitterUTF8(15 * 60 * 1000L);
        ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
        String requestId = MDC.get(REQUEST_ID);
        String taskId = MDC.get(TASK_ID);
        executor.execute(() -> {
            try {
                MDC.put(REQUEST_ID, requestId);
                MDC.put(TASK_ID, taskId);
                streamResBodyHandler(sseEmitter, apiLog, url, response);
            } finally {
                ModelApiLogThreadLocal.clear();
            }
        });
        return sseEmitter;
    }

    void streamResBodyHandler(SseEmitter sseEmitter, ModelApiLog apiLog, String url, HttpResponse<String> response) {
        try (BufferedReader reader = new BufferedReader(
            new InputStreamReader(response.getStreamResponse(), StandardCharsets.UTF_8))) {
            String message;
            int streamEvents = 0;

            Map<Integer, Future<String>> jobFutureMap = new HashMap<Integer, Future<String>>();
            StringBuilder stringBuilder = new StringBuilder();
            boolean isSensitive = false;
            boolean haveEnd = false;
            while ((message = reader.readLine()) != null) {
                if (!message.startsWith("data:")) {
                    if (!message.isBlank()) {
                        log.warn("stream response message format error, message: {}", message);
                    }
                    continue;
                }
                if (streamEvents == 0) {
                    apiLog.setFirstToken(System.currentTimeMillis() - apiLog.getStartTime());
                }
                ++streamEvents;

                String content = message.substring(5).trim();
                JSONObject chunk = convertToChatCompletionChunk(content);
                ModelRespContentType contentType = getContentType(chunk);
                switch (contentType) {
                    case CONTENT_SIGNAL: {
                        // 正文
                        submitSecurityCheckJob(streamEvents, chunk, stringBuilder, apiLog, jobFutureMap);
                        String msg = getContentWithRequestId(content, chunk, apiLog);
                        sseEmitter.send(msg.startsWith(" ") ? msg : " " + msg);
                        break;
                    }
                    case FINISH_SIGNAL: {
                        finishHandler(sseEmitter, apiLog, content, chunk);
                        break;
                    }
                    case END_SIGNAL:
                        endHandler(sseEmitter, apiLog, content, chunk);
                        haveEnd = true;
                        break;
                    default:
                        break;
                }

                // 风控结果实时检查
                for (Map.Entry<Integer, Future<String>> entry : jobFutureMap.entrySet()) {
                    if (!entry.getValue().isDone()) {
                        continue;
                    }
                    if (entry.getValue().get().equals("block")) {
                        log.error("Contain security work. blocked.");
                        sseEmitter.send(genSensitiveMessage());
                        sseEmitter.send("[DONE]");
                        apiLog.setStatus("fail").setOutput(stringBuilder.toString()).setReason("block");
                        sseEmitter.complete();
                        isSensitive = true;
                        break;
                    }
                }
                if (isSensitive) {
                    break;
                }
            }
            apiLog.setOutput(stringBuilder.toString());
            if (!isSensitive) {
                waitSecurityCheckJob(jobFutureMap, sseEmitter, apiLog);
                apiLog.setStatus("success").setReason("");
                if (!haveEnd) {
                    sseEmitter.send(" [DONE]");
                }
                sseEmitter.complete();
            }
            apiLog.setApiStatus(response.getStatusCode())
                .setDuration(System.currentTimeMillis() - apiLog.getStartTime())
                .setStreamEvents(streamEvents);
            apiLogService.saveModelApiLog(apiLog);
        } catch (Exception e) {
            apiLog.setStatus("fail").setOutput(e.getMessage()).setReason("exception");
            sseEmitter.complete();
            if (e instanceof AgentStudioException exp) {
                apiLog.setApiStatus(exp.getErrorCode().getHttpStatus().value())
                    .setDuration(System.currentTimeMillis() - apiLog.getStartTime());
            } else {
                apiLog.setApiStatus(500).setDuration(System.currentTimeMillis() - apiLog.getStartTime());
                log.error("OpenAi stream chat error.", e);
            }
            apiLogService.saveModelApiLog(apiLog);
        } finally {
            response.close();
            ModelApiLogThreadLocal.clear();
        }
    }

    protected void endHandler(SseEmitter sseEmitter, ModelApiLog apiLog, String content, JSONObject chunk)
        throws IOException {
        // 返回结束标记
        sseEmitter.send(" " + content);
    }

    protected void finishHandler(SseEmitter sseEmitter, ModelApiLog apiLog, String content, JSONObject chunk)
        throws IOException {
        // 结束处理
        String msg = getContentWithRequestId(content, chunk, apiLog);
        sseEmitter.send(msg.startsWith(" ") ? msg : " " + msg);
    }

    protected void waitSecurityCheckJob(Map<Integer, Future<String>> jobFutureMap, SseEmitter sseEmitter,
        ModelApiLog apiLog) throws Exception {
        int sum = jobFutureMap.size();
        int doneNum = 0;

        while (doneNum < sum) {
            for (Map.Entry<Integer, Future<String>> entry : jobFutureMap.entrySet()) {
                if (!entry.getValue().isDone()) {
                    continue;
                }
                if (entry.getValue().get().equals("block")) {
                    log.error("Contain security work. blocked.");
                    sseEmitter.send(genSensitiveMessage());
                    sseEmitter.send("[DONE]");
                    apiLog.setReason("block").setStatus("fail");
                    sseEmitter.complete();
                    doneNum = sum;
                    break;
                }
                doneNum += 1;
            }
            if (doneNum < sum) {
                Thread.sleep(10);
            }
        }
    }

    protected String genSensitiveMessage() {
        long time = System.currentTimeMillis() / 1000;
        return String.format(Locale.ROOT,
            "{\"choices\":[{\"delta\":{\"audio\":null,\"content\":\"\nSecurity block.\",\"reasoning_content\":null,\"role\":"
                + "\"assistant\"},\"finish_reason\":\"sensitive\",\"index\":0}],\"created\":%d,\"model\":\"\""
                + ",\"object\":\"chat.completion.chunk\",\"request_id\":\"\"}", time);
    }

    protected String getContentWithRequestId(String content, JSONObject chunk, ModelApiLog apiLog) {
        if (chunk == null) {
            return content;
        }

        JSONArray choices = chunk.getJSONArray("choices");
        JSONObject usage = null;
        if (choices != null && !choices.isEmpty()) {
            String finishReason = (String) ((JSONObject) choices.get(0)).get("finish_reason");
            if (finishReason != null && finishReason.equals("stop")) {
                usage = chunk.getJSONObject(USAGE);
            }
        } else {
            usage = chunk.getJSONObject(USAGE);
        }

        if (usage != null) {
            apiLog.setTotalTokens(String.valueOf(usage.get("total_tokens")));
            apiLog.setCompletionTokens(String.valueOf(usage.get("completion_tokens")));
            apiLog.setPromptTokens(String.valueOf(usage.get("prompt_tokens")));
        }

        chunk.put("request_id", apiLog.getRequestId());
        return chunk.toString();
    }

    protected ModelRespContentType getContentType(JSONObject chunk) {
        if (chunk == null) {
            return ModelRespContentType.END_SIGNAL;
        }
        JSONArray choices = chunk.getJSONArray("choices");
        if (choices == null || choices.isEmpty()) {
            return ModelRespContentType.FINISH_SIGNAL;
        }

        if (((JSONObject) choices.get(0)).get("finish_reason") == null) {
            return ModelRespContentType.CONTENT_SIGNAL;
        }
        return ModelRespContentType.FINISH_SIGNAL;
    }

    protected JSONObject convertToChatCompletionChunk(String content) {
        if (content.equals("[DONE]")) {
            return null;
        }
        return JSON.parseObject(content);
    }

    protected void submitSecurityCheckJob(int count, JSONObject eventData, StringBuilder existContent,
        ModelApiLog apiLog, Map<Integer, Future<String>> jobFutureMap) {
        if (!apiLog.isResponseVerify()) {
            return;
        }
        try {
            JSONArray choices = eventData.getJSONArray("choices");
            if (choices == null || choices.isEmpty()) {
                return;
            }
            StringBuilder builder = new StringBuilder();
            for (Object obj : choices) {
                if (obj instanceof JSONObject jsonObj) {
                    JSONObject delta = jsonObj.getJSONObject("delta");
                    if (delta != null) {
                        String content = delta.get("content") == null ? "" : delta.get("content").toString();
                        if (!content.isEmpty()) {
                            builder.append(content);
                        }
                    }
                }
            }
            if (builder.isEmpty()) {
                return;
            }
            existContent.append(builder.toString());
        } catch (Exception e) {
            log.error("Submit security check job exception.", e);
        }
    }

    @Override
    public JSONObject resBodyConvert(String url, HttpResponse<String> response, Object request) {
        // rerank 响应结构不同于 chat, 需要单独处理: 按 index 排序 + topN 截断
        // 复用 MaasRerankRequestAdaptor 的静态方法, 保证 rerank 逻辑只有一份实现
        if (request instanceof RankDocumentsRequest rankReq) {
            return MaasRerankRequestAdaptor.convertRerankResponseBody(url, response, rankReq.getTopN());
        }
        return resBodyConvert(url, response);
    }

    @Override
    public JSONObject resBodyConvert(String url, HttpResponse<String> response) {
        if (response.getResponseBody() == null) {
            log.error("Empty http response! Api path: '{}'", url);
            throw new AgentStudioException(StudioError.MD_INVOKE_MODEL_SERVICE_FAIL);
        }
        if (response.getStatusCode() >= 300) {
            log.error("Invoke model service error. url:{} status:{} response:{}", url, response.getStatusCode(),
                response.getErrorResponseBody());
            throw httpExceptionHandler(response.getStatusCode(), response.getErrorResponseBody());
        }
        try {
            JSONObject object = JSONObject.parseObject(response.getResponseBody());
            JSONObject usage = object.getJSONObject(USAGE);
            if (usage != null) {
                ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
                apiLog.setTotalTokens(String.valueOf(usage.get("total_tokens")));
                apiLog.setCompletionTokens(String.valueOf(usage.get("completion_tokens")));
                apiLog.setPromptTokens(String.valueOf(usage.get("prompt_tokens")));
            }
            return object;
        } catch (Exception e) {
            log.error("Model response body paras to object exception.", e);
            throw new AgentStudioException(StudioError.MD_INVOKE_MODEL_SERVICE_FAIL);
        }
    }

    @Override
    public AgentStudioException requestExceptionHandler(Exception exp) {
        if (exp instanceof AgentStudioException) {
            return (AgentStudioException) exp;
        }
        if (exp instanceof OpenAiHttpException) {
            return openAiHttpExceptionHandler((OpenAiHttpException) exp);
        }
        return exceptionHandler(exp);
    }

    protected AgentStudioException openAiHttpExceptionHandler(OpenAiHttpException exp) {
        return ModelInvokeExceptionUtil.commonHttpExceptionHandler(exp.getStatusCode().value(), exp.getErrorResponse());
    }

    protected AgentStudioException exceptionHandler(Exception exp) {
        log.error("Model text rerank exception.", exp);
        return new AgentStudioException(StudioError.UNEXPECTED_ERROR);
    }

    protected AgentStudioException httpExceptionHandler(int statusCode, String message) {
        return ModelInvokeExceptionUtil.commonHttpExceptionHandler(statusCode, message);
    }
}
