/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import lombok.extern.slf4j.Slf4j;

import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.quartz.QuartzJobBean;
import org.springframework.stereotype.Service;

/**
 * 自动化定时任务的 Quartz Job，到点后委托 {@link SchedulerTaskService} 执行。
 */
@Slf4j
@Service
public class SchedulerTaskJob extends QuartzJobBean {
    @Autowired
    private SchedulerTaskService schedulerTaskService;

    @Override
    protected void executeInternal(JobExecutionContext context) throws JobExecutionException {
        String taskId = context.getJobDetail().getJobDataMap().getString(SchedulerTaskService.JOB_DATA_TASK_ID);
        log.info("[Scheduled Task] Start to execute. taskId={}", taskId);
        schedulerTaskService.executeTask(taskId, "scheduled");
    }
}
