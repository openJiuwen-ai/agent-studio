/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;

import lombok.extern.slf4j.Slf4j;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import okio.BufferedSource;

import org.apache.commons.lang3.StringUtils;
import org.apache.hc.core5.net.URIBuilder;
import org.quartz.JobDataMap;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.quartz.QuartzJobBean;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * 功能描述
 *
 */
@Slf4j
@Service
public class AgentTriggerService extends QuartzJobBean {
    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    @Override
    protected void executeInternal(JobExecutionContext context) throws JobExecutionException {
        JobDataMap jobDetailMap = context.getJobDetail().getJobDataMap();
        String jobName = context.getJobDetail().getKey().getName();
        log.info("[Task Start] The scheduled task starts to be executed. Task name:{}", jobName);
        String authToken = StringUtils.EMPTY;

        // 2. 判断任务类型并执行
        if (jobDetailMap.containsKey(CommonConstant.AGENT_ID)) {
            handleAgentTask(jobDetailMap, authToken);
        } else if (jobDetailMap.containsKey(CommonConstant.Workflow.ID)) {
            handleWorkflowTask(jobDetailMap, authToken);
        }
    }

    // 处理Agent任务
    private void handleAgentTask(JobDataMap jobDetailMap, String authToken) {
        log.info("[Executing the Agent] Start to invoke the Agent running interface. - AgentID: {}", jobDetailMap
                .getString(CommonConstant.AGENT_ID));
        AgentRunReq agentRunReq = new AgentRunReq();
        agentRunReq.setQuery(jobDetailMap.getString(CommonConstant.PROMPT));
        runAgentStream(jobDetailMap.getString(CommonConstant.PROJECT_ID), jobDetailMap.getString(
                CommonConstant.AGENT_ID), authToken, jobDetailMap, agentRunReq);
    }

    // 处理Workflow任务
    private void handleWorkflowTask(JobDataMap jobDetailMap, String authToken) {
        log.info("[Execute Workflow] Start to invoke the workflow running interface. - WorkflowID: {}", jobDetailMap
                .getString(CommonConstant.Workflow.ID));
        WorkflowRunReq workflowRunReq = new WorkflowRunReq();
        Map<String, Object> inputs = new HashMap<>();
        inputs.put("query", jobDetailMap.getString(CommonConstant.PROMPT));
        workflowRunReq.setInputs(inputs);
        runWorkflowStream(jobDetailMap.getString(CommonConstant.PROJECT_ID), jobDetailMap.getString(
                CommonConstant.Workflow.ID), authToken, jobDetailMap, workflowRunReq);
    }

    // Agent流式调用
    private SseEmitter runAgentStream(String projectId, String agentId, String token, JobDataMap jobDetailMap,
                                      AgentRunReq agentRunReq) {
        SseEmitter sseEmitter = new SseEmitter(CommonConstant.AGENT_STREAM_TIMEOUT);
        SpringBeanUtils.getBean(MgAsyncService.class).callRunAgentStream(() -> {
            try {
                Request request = buildRequest(projectId, agentId, token, jobDetailMap, JSON.toJSONString(agentRunReq),
                        UUID.randomUUID().toString() // Agent运行接口路径需要conversation_id
                );
                executeStreamRequest(request, sseEmitter, jobDetailMap);
            } catch (Exception e) {
                handleError(e, sseEmitter, jobDetailMap);
            }
        });
        return sseEmitter;
    }

    // Workflow流式调用
    private SseEmitter runWorkflowStream(String projectId, String workflowId, String token, JobDataMap jobDetailMap,
                                         WorkflowRunReq workflowRunReq) {
        SseEmitter sseEmitter = new SseEmitter(CommonConstant.WORKFLOW_TIMEOUT);
        SpringBeanUtils.getBean(MgAsyncService.class).callRunAgentStream(() -> {
            try {
                Request request = buildRequest(projectId, workflowId, token, jobDetailMap, JSON.toJSONString(
                        workflowRunReq), UUID.randomUUID().toString() // Workflow需要UUID
                );
                executeStreamRequest(request, sseEmitter, jobDetailMap);
            } catch (Exception e) {
                handleError(e, sseEmitter, jobDetailMap);
            }
        });
        return sseEmitter;
    }

    // 构建HTTP请求
    private Request buildRequest(String projectId, String resourceId, String token, JobDataMap jobDetailMap,
                                 String jsonBody, String uuid) throws Exception {
        String baseUrl = jobDetailMap.getString(CommonConstant.AGENT_RUNTIME_ENDPOINT);
        String pathTemplate = jobDetailMap.getString(CommonConstant.RUN_AGENT_STREAM_URL);

        // 动态构造URL路径
        String formattedPath = (uuid != null) ? String.format(pathTemplate, projectId, resourceId, uuid) : String
                .format(pathTemplate, projectId, resourceId);

        URI uri = new URIBuilder(baseUrl + formattedPath).addParameter(CommonConstant.WORKSPACE_ID, jobDetailMap
                .getString(CommonConstant.WORKSPACE_ID)).build();

        return new Request.Builder().url(uri.toString()).addHeader(CommonConstant.CONTENT_TYPE,
                CommonConstant.APPLICATION_JSON).addHeader(CommonConstant.X_AUTH_TOKEN, token).addHeader(
                CommonConstant.STREAM, CommonConstant.TRUE).post(RequestBody.create(jsonBody, MediaType.get(
                "application/json"))).build();
    }

    // 执行流式请求
    private void executeStreamRequest(Request request, SseEmitter sseEmitter, JobDataMap jobDetailMap) {
        okHttpClientUtils.getHttpClient().newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                handleError(e, sseEmitter, jobDetailMap);
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                if (!response.isSuccessful()) {
                    handleError(new IOException("HTTP request failure: " + response.code()), sseEmitter, jobDetailMap);
                    return;
                }
                try (ResponseBody body = response.body()) {
                    if (body == null) {
                        handleError(new IOException("Response body is empty."), sseEmitter, jobDetailMap);
                        return;
                    }
                    processStreamResponse(body, sseEmitter);
                }
                sendDone(sseEmitter);
            }
        });
    }

    // 处理流式响应
    private void processStreamResponse(ResponseBody body, SseEmitter sseEmitter) throws IOException {
        try (BufferedSource source = body.source()) {
            while (!source.exhausted()) {
                String line = source.readUtf8Line();
                if (line != null && line.startsWith(CommonConstant.EVENT_DATA_PREFIX)) {
                    String data = line.substring(CommonConstant.EVENT_DATA_PREFIX.length()).trim();
                    sseEmitter.send(SseEmitter.event().data(data));
                }
            }
        }
    }

    // 统一错误处理
    private void handleError(Exception e, SseEmitter sseEmitter, JobDataMap jobDetailMap) {
        log.error("Trigger {} run exception.", jobDetailMap.getString(CommonConstant.TRIGGER_ID), e);
        sendDone(sseEmitter);
        sseEmitter.completeWithError(e);
    }

    // 发送完成事件
    private void sendDone(SseEmitter sseEmitter) {
        try {
            sseEmitter.send(SseEmitter.event().name("done").data("[DONE]"));
        } catch (IOException e) {
            log.error("Send done event failed");
        }
    }
}
