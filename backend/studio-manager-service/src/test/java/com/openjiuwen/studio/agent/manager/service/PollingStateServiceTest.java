/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.PollingTriggerStateEntity;
import com.openjiuwen.studio.agent.manager.mapper.PollingTriggerStateMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.quartz.*;
import org.springframework.test.util.ReflectionTestUtils;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class PollingStateServiceTest {
    private final PollingTriggerStateMapper mapper = mock(PollingTriggerStateMapper.class);
    private final Scheduler scheduler = mock(Scheduler.class);
    private final AgentTriggerService target = mock(AgentTriggerService.class);
    private final PollingStateService service = new PollingStateService(mapper);
    private final JobKey key = new JobKey("poll-1");
    private JobDataMap snapshot;

    @BeforeEach
    void setUp() throws Exception {
        ReflectionTestUtils.setField(service, "scheduler", scheduler);
        ReflectionTestUtils.setField(service, "agentTriggerService", target);
        JobDetail job = job("https://example.com/old-feed");
        snapshot = new JobDataMap(job.getJobDataMap());
        when(scheduler.getJobDetail(key)).thenReturn(job);
        PollingTriggerStateEntity state = new PollingTriggerStateEntity();
        state.setTriggerId("poll-1");
        state.setLastSeenHash("before");
        when(mapper.selectForUpdate("poll-1")).thenReturn(state);
        when(mapper.compareAndSetLastSeenHash("poll-1", "before", "after")).thenReturn(1);
    }

    @Test
    void unchangedOrFailedCheckOnlyUpdatesTimestamp() {
        service.completeCheck(key, snapshot, "before");
        service.completeCheck(key, snapshot, null);
        verify(mapper, times(2)).updateLastCheckedAt(eq("poll-1"), any());
        verifyNoInteractions(target);
    }

    @Test
    void changedContentSubmitsTargetAfterTakingStateLock() throws Exception {
        service.completeCheck(key, snapshot, "after");
        var order = inOrder(mapper, scheduler, target);
        order.verify(mapper).selectForUpdate("poll-1");
        order.verify(scheduler).getJobDetail(key);
        order.verify(mapper).updateLastCheckedAt(eq("poll-1"), any());
        order.verify(mapper).compareAndSetLastSeenHash("poll-1", "before", "after");
        order.verify(target).executeTarget(snapshot);
    }

    @Test
    void editedConfigurationDiscardsOldDownloadWithoutTouchingNewState() throws Exception {
        when(scheduler.getJobDetail(key)).thenReturn(job("https://example.com/new-feed"));
        service.completeCheck(key, snapshot, "after");
        verify(mapper, never()).updateLastCheckedAt(anyString(), any());
        verify(mapper, never()).compareAndSetLastSeenHash(anyString(), any(), any());
        verifyNoInteractions(target);
    }

    @Test
    void deletedTriggerCannotSubmitTarget() {
        when(mapper.selectForUpdate("poll-1")).thenReturn(null);
        service.completeCheck(key, snapshot, "after");
        verifyNoInteractions(target);
    }

    @Test
    void targetRejectionPreservesExistingBestEffortPolicy() {
        doThrow(new IllegalStateException("target rejected")).when(target).executeTarget(any());
        service.completeCheck(key, snapshot, "after");
        verify(mapper).compareAndSetLastSeenHash("poll-1", "before", "after");
    }

    private JobDetail job(String pollUrl) {
        return JobBuilder.newJob(PollingTriggerService.class).withIdentity(key)
            .usingJobData(CommonConstant.TRIGGER_ID, "poll-1")
            .usingJobData(CommonConstant.POLL_URL, pollUrl).build();
    }
}
