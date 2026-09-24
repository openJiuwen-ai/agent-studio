/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.PollingTriggerStateEntity;
import com.openjiuwen.studio.agent.manager.mapper.PollingTriggerStateMapper;

import lombok.extern.slf4j.Slf4j;

import org.quartz.JobDataMap;
import org.quartz.JobDetail;
import org.quartz.JobKey;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Date;
import java.util.Objects;

/**
 * Manages the runtime state of Polling triggers.
 */
@Slf4j
@Service
public class PollingStateService {
    private final PollingTriggerStateMapper pollingTriggerStateMapper;

    @Autowired
    private Scheduler scheduler;

    @Autowired
    private AgentTriggerService agentTriggerService;

    public PollingStateService(PollingTriggerStateMapper pollingTriggerStateMapper) {
        this.pollingTriggerStateMapper = pollingTriggerStateMapper;
    }

    public boolean initializeState(String triggerId) {
        return pollingTriggerStateMapper.initialize(triggerId) == 1;
    }

    public PollingTriggerStateEntity getState(String triggerId) {
        return pollingTriggerStateMapper.selectByTriggerId(triggerId);
    }

    /** Must be called within the edit/delete transaction so the lock survives until commit. */
    public PollingTriggerStateEntity lockState(String triggerId) {
        return pollingTriggerStateMapper.selectForUpdate(triggerId);
    }

    public boolean isCurrentConfiguration(JobKey jobKey, JobDataMap snapshot) {
        try {
            JobDetail current = scheduler.getJobDetail(jobKey);
            return current != null && current.getJobClass() == PollingTriggerService.class
                && current.getJobDataMap().equals(snapshot);
        } catch (SchedulerException exception) {
            throw new IllegalStateException("Cannot verify polling configuration", exception);
        }
    }

    /**
     * The row lock is also taken by edit/delete before changing Quartz, so a completed download
     * cannot submit an obsolete configuration. No database lock is held while downloading.
     */
    @Transactional
    public void completeCheck(JobKey jobKey, JobDataMap snapshot, String currentHash) {
        String triggerId = snapshot.getString(CommonConstant.TRIGGER_ID);
        PollingTriggerStateEntity state = lockState(triggerId);
        if (state == null || !isCurrentConfiguration(jobKey, snapshot)) {
            log.info("Polling trigger {} configuration is obsolete; discard the check result.", triggerId);
            return;
        }
        updateLastCheckedAt(triggerId, new Date());
        if (currentHash == null || Objects.equals(state.getLastSeenHash(), currentHash)) {
            return;
        }
        if (compareAndSetLastSeenHash(triggerId, state.getLastSeenHash(), currentHash)) {
            try {
                agentTriggerService.executeTarget(snapshot);
            } catch (RuntimeException exception) {
                // Preserve the existing best-effort policy: target failure does not retry the same content.
                log.error("Polling trigger {} failed to submit its target.", triggerId, exception);
            }
        }
    }

    public boolean compareAndSetLastSeenHash(String triggerId, String expectedHash, String newHash) {
        return pollingTriggerStateMapper.compareAndSetLastSeenHash(triggerId, expectedHash, newHash) == 1;
    }

    public boolean updateLastCheckedAt(String triggerId, Date lastCheckedAt) {
        return pollingTriggerStateMapper.updateLastCheckedAt(triggerId, lastCheckedAt) == 1;
    }

    public boolean deleteState(String triggerId) {
        return pollingTriggerStateMapper.deleteByTriggerId(triggerId) == 1;
    }

    /**
     * Clears the hash when a trigger starts polling a different URL.
     *
     * @param triggerId trigger identifier
     */
    @Transactional
    public void resetState(String triggerId) {
        pollingTriggerStateMapper.deleteByTriggerId(triggerId);
        pollingTriggerStateMapper.initialize(triggerId);
    }
}
