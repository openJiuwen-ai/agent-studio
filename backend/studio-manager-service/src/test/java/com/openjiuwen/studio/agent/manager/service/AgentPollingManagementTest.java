/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.PollingTriggerConfigValidator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.quartz.*;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AgentPollingManagementTest {
    private final AgentManagementService service = mock(AgentManagementService.class, CALLS_REAL_METHODS);
    private final AgentMapper mapper = mock(AgentMapper.class);
    private final Scheduler scheduler = mock(Scheduler.class);
    private final PollingStateService state = mock(PollingStateService.class);
    private final Agent agent = new Agent();

    @BeforeEach
    void setUp() {
        agent.setAgentId("agent");
        agent.setProjectId("project");
        agent.setWorkspaceId("workspace");
        agent.setModel("keep-model");
        agent.setTriggerList(List.of(config()));
        doReturn(agent).when(service).getAgent("project", "workspace", "agent");
        doReturn(agent).when(service).getAgent("project", "agent");
        ReflectionTestUtils.setField(service, "agentMapper", mapper);
        ReflectionTestUtils.setField(service, "scheduler", scheduler);
        ReflectionTestUtils.setField(service, "pollingStateService", state);
        ReflectionTestUtils.setField(service, "pollingTriggerConfigValidator",
            new PollingTriggerConfigValidator(300, 60, 86400, 2048));
        ReflectionTestUtils.setField(service, "agentRuntimeEndpoint", "http://runtime");
        ReflectionTestUtils.setField(service, "runAgentStreamUrl", "/agents/%s/%s");
        AgentImportExportService export = mock(AgentImportExportService.class);
        when(export.parseMetadata(any())).thenReturn(Map.of());
        ReflectionTestUtils.setField(service, "agentImportExportService", export);
        IrAdapterService adapter = mock(IrAdapterService.class);
        when(adapter.adaptAgent(any(), any())).thenReturn(Map.of());
        ReflectionTestUtils.setField(service, "irAdapterService", adapter);
        ReflectionTestUtils.setField(service, "mgObsService", mock(MgObsService.class));
        when(mapper.updateTriggerList(eq("project"), eq("workspace"), eq("agent"), anyList(), any())).thenReturn(1);
        when(state.initializeState(anyString())).thenReturn(true);
    }

    @Test
    void createsPollingJobOnlyAfterScopedConfigurationUpdate() throws Exception {
        agent.setTriggerList(List.of());
        try (var request = mockStatic(RequestContextUtils.class)) {
            request.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain");
            TriggerConfig result = service.addTrigger("project", "agent", "workspace", config());
            ArgumentCaptor<JobDetail> job = ArgumentCaptor.forClass(JobDetail.class);
            var order = inOrder(mapper, state, scheduler);
            order.verify(mapper).updateTriggerList(eq("project"), eq("workspace"), eq("agent"), eq(List.of(result)), any());
            order.verify(state).initializeState(result.getTriggerId());
            order.verify(scheduler).getTrigger(any());
            order.verify(scheduler).scheduleJob(job.capture(), any(Trigger.class));
            assertEquals(result.getPollUrl(), job.getValue().getJobDataMap().getString(CommonConstant.POLL_URL));
            verify(mapper, never()).updateByPrimaryKeySelective(any());
        }
    }

    @Test
    void missingAgentUpdateStopsBeforeCreatingStateOrSchedule() {
        when(mapper.updateTriggerList(any(), any(), any(), any(), any())).thenReturn(0);
        assertThrows(AgentStudioException.class,
            () -> service.addTrigger("project", "agent", "workspace", config()));
        verifyNoInteractions(state, scheduler);
    }

    @Test
    void editsTakeStateLockBeforeReplacingJobAndUpdatePrompt() throws Exception {
        try (var request = mockStatic(RequestContextUtils.class)) {
            request.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain");
            service.editTrigger("project", "agent", "workspace", config().setPrompt("new prompt"));
            var order = inOrder(state, scheduler);
            order.verify(state).lockState("poll-1");
            order.verify(scheduler).pauseTrigger(new TriggerKey("poll-1"));
            ArgumentCaptor<JobDetail> job = ArgumentCaptor.forClass(JobDetail.class);
            verify(scheduler).scheduleJob(job.capture(), any(Trigger.class));
            assertEquals("new prompt", job.getValue().getJobDataMap().getString(CommonConstant.PROMPT));
            verify(mapper).updateTriggerList(eq("project"), eq("workspace"), eq("agent"), anyList(), any());
        }
    }

    @Test
    void deletesTakeStateLockAndPersistAnEmptyList() throws Exception {
        service.deleteTrigger("project", "agent", "poll-1", "workspace");
        verify(mapper).updateTriggerList(eq("project"), eq("workspace"), eq("agent"), eq(List.of()), any());
        verify(state).lockState("poll-1");
        verify(state).deleteState("poll-1");
        verify(scheduler).pauseTrigger(new TriggerKey("poll-1"));
        verify(scheduler).unscheduleJob(new TriggerKey("poll-1"));
        verify(scheduler).deleteJob(new JobKey("poll-1"));
    }

    private static TriggerConfig config() {
        return new TriggerConfig().setTriggerId("poll-1").setName("poll").setType("POLLING")
            .setPollUrl("https://example.com/feed").setPollIntervalSeconds(60).setPrompt("prompt");
    }
}
