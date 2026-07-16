/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.service.MgAsyncService;

import okhttp3.OkHttpClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.quartz.JobDataMap;
import org.quartz.JobDetail;
import org.quartz.JobExecutionContext;
import org.quartz.JobKey;
import java.lang.ref.WeakReference;
import org.springframework.context.ApplicationContext;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class AgentTriggerServiceTest {

    @Mock
    private OkHttpClientUtils okHttpClientUtils;

    @Mock
    private JobExecutionContext jobExecutionContext;

    @Mock
    private JobDetail jobDetail;

    @Mock
    private JobKey jobKey;

    @Mock
    private OkHttpClient okHttpClient;

    @InjectMocks
    private AgentTriggerService agentTriggerService;

    private JobDataMap jobDataMap;

    @BeforeEach
    void setUp() {
        jobDataMap = new JobDataMap();
        lenient().when(jobExecutionContext.getJobDetail()).thenReturn(jobDetail);
        lenient().when(jobDetail.getJobDataMap()).thenReturn(jobDataMap);
        lenient().when(jobDetail.getKey()).thenReturn(jobKey);
        lenient().when(jobKey.getName()).thenReturn("test-job");
        lenient().when(okHttpClientUtils.getHttpClient()).thenReturn(okHttpClient);

        // 设置 SpringBeanUtils.applicationContext，使 getBean(MgAsyncService.class) 返回 mock
        MgAsyncService mgAsyncService = org.mockito.Mockito.mock(MgAsyncService.class);
        ApplicationContext mockCtx = org.mockito.Mockito.mock(ApplicationContext.class);
        lenient().when(mockCtx.getBean(MgAsyncService.class)).thenReturn(mgAsyncService);
        ReflectionTestUtils.setField(SpringBeanUtils.class, "applicationContextRef", new WeakReference<>(mockCtx));
    }

    @Test
    void testExecuteInternal_AgentTask() {
        jobDataMap.put(CommonConstant.AGENT_ID, "agent-1");
        jobDataMap.put(CommonConstant.PROMPT, "hello");
        jobDataMap.put(CommonConstant.PROJECT_ID, "proj-1");
        jobDataMap.put(CommonConstant.AGENT_RUNTIME_ENDPOINT, "http://runtime");
        jobDataMap.put(CommonConstant.RUN_AGENT_STREAM_URL, "/api/%s/%s/stream");
        jobDataMap.put(CommonConstant.WORKSPACE_ID, "ws-1");

        assertDoesNotThrow(() -> agentTriggerService.executeInternal(jobExecutionContext));
    }

    @Test
    void testExecuteInternal_WorkflowTask() {
        jobDataMap.put(CommonConstant.Workflow.ID, "wf-1");
        jobDataMap.put(CommonConstant.PROMPT, "hello");
        jobDataMap.put(CommonConstant.PROJECT_ID, "proj-1");
        jobDataMap.put(CommonConstant.AGENT_RUNTIME_ENDPOINT, "http://runtime");
        jobDataMap.put(CommonConstant.RUN_AGENT_STREAM_URL, "/api/%s/%s/stream/%s");
        jobDataMap.put(CommonConstant.WORKSPACE_ID, "ws-1");

        assertDoesNotThrow(() -> agentTriggerService.executeInternal(jobExecutionContext));
    }

    @Test
    void testExecuteInternal_NoTaskType() {
        assertDoesNotThrow(() -> agentTriggerService.executeInternal(jobExecutionContext));
    }
}
