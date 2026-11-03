/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.Strings;
import org.quartz.CronScheduleBuilder;
import org.quartz.CronTrigger;
import org.quartz.JobDetail;
import org.quartz.JobKey;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.quartz.SimpleScheduleBuilder;
import org.quartz.SimpleTrigger;
import org.quartz.Trigger;
import org.quartz.TriggerBuilder;
import org.quartz.TriggerKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;

/**
 * 功能描述
 *
 */
@Slf4j
@Service
public class QuartzManagerService {
    private static final String QUARTZ_JOB_LOCK_KEY = "quartz:lock:%s";

    private static final int QUARTZ_JOB_LOCK_TIME = 10;

    @Autowired
    private Scheduler scheduler;

    @Autowired
    private RedisClient redisClient;

    /**
     * 创建或更新任务
     *
     * @param jobDetail 任务调度程序
     * @param jobName 任务名称
     * @param jobGroupName 任务组名称
     * @param cronExpression cron表达式
     */
    public void addOrUpdateJob(JobDetail jobDetail, String jobName, String jobGroupName, String cronExpression) {
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(String.format(QUARTZ_JOB_LOCK_KEY, jobName));
            if (lock.tryLock(Duration.ofSeconds(QUARTZ_JOB_LOCK_TIME))) {
                TriggerKey triggerKey = TriggerKey.triggerKey(jobName, jobGroupName);
                CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);
                if (trigger == null) {
                    addJob(jobDetail, jobName, jobGroupName, cronExpression);
                } else {
                    if (Strings.CS.equals(trigger.getCronExpression(), cronExpression)) {
                        return;
                    }
                    updateJob(jobName, jobGroupName, cronExpression);
                }
            } else {
                log.warn("Fail get {} lock.", String.format(QUARTZ_JOB_LOCK_KEY, jobName));
            }
        } catch (Exception e) {
            log.error("Scheduler configure job failed.", e);
            throw new AgentStudioException(StudioError.ADD_QUARTZ_JOB_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * Creates or updates a fixed-interval job.
     *
     * @param jobDetail job definition
     * @param triggerName trigger name
     * @param triggerGroupName trigger group name
     * @param intervalSeconds execution interval in seconds
     */
    public void addOrUpdateIntervalJob(JobDetail jobDetail, String triggerName, String triggerGroupName,
        int intervalSeconds) {
        if (intervalSeconds <= 0) {
            throw new AgentStudioException(StudioError.INVALID_PARAMETER_ERROR, "intervalSeconds");
        }

        RedisLock lock = null;
        boolean lockAcquired = false;
        try {
            lock = redisClient.getLock(String.format(QUARTZ_JOB_LOCK_KEY, triggerName));
            lockAcquired = lock.tryLock(Duration.ofSeconds(QUARTZ_JOB_LOCK_TIME));
            if (!lockAcquired) {
                log.warn("Fail get {} lock.", String.format(QUARTZ_JOB_LOCK_KEY, triggerName));
                throw new AgentStudioException(StudioError.ADD_QUARTZ_JOB_FAILED);
            }

            TriggerKey triggerKey = TriggerKey.triggerKey(triggerName, triggerGroupName);
            Trigger existingTrigger = scheduler.getTrigger(triggerKey);
            if (existingTrigger == null) {
                addIntervalJob(jobDetail, triggerKey, intervalSeconds);
                return;
            }
            if (!(existingTrigger instanceof SimpleTrigger)) {
                throw new SchedulerException("Existing trigger is not a SimpleTrigger: " + triggerKey);
            }

            scheduler.addJob(jobDetail, true, true);
            long intervalMillis = Duration.ofSeconds(intervalSeconds).toMillis();
            if (((SimpleTrigger) existingTrigger).getRepeatInterval() == intervalMillis) {
                return;
            }
            updateIntervalJob(triggerKey, intervalSeconds);
        } catch (Exception e) {
            log.error("Scheduler configure interval job failed.", e);
            throw new AgentStudioException(StudioError.ADD_QUARTZ_JOB_FAILED);
        } finally {
            if (lockAcquired) {
                lock.unlock();
            }
        }
    }

    /**
     * 创建任务
     *
     * @param jobDetail 任务调度程序
     * @param jobName 任务名称
     * @param jobGroupName 任务组名称
     * @param cronExpression cron表达式
     */
    private void addJob(JobDetail jobDetail, String jobName, String jobGroupName, String cronExpression) {
        try {
            Trigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(jobName, jobGroupName)
                .withSchedule(CronScheduleBuilder.cronSchedule(cronExpression))
                .build();
            scheduler.scheduleJob(jobDetail, trigger);
            if (!scheduler.isShutdown()) {
                scheduler.start();
            }
        } catch (SchedulerException e) {
            log.error("Scheduler add job failed.", e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
    }

    private void addIntervalJob(JobDetail jobDetail, TriggerKey triggerKey, int intervalSeconds)
        throws SchedulerException {
        Trigger trigger = TriggerBuilder.newTrigger()
            .withIdentity(triggerKey)
            .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                .withIntervalInSeconds(intervalSeconds)
                .repeatForever()
                .withMisfireHandlingInstructionNextWithRemainingCount())
            .build();
        scheduler.scheduleJob(jobDetail, trigger);
        if (!scheduler.isShutdown()) {
            scheduler.start();
        }
    }

    /**
     * 更新任务
     *
     * @param jobName 任务名称
     * @param jobGroupName 任务组名称
     * @param cronExpression cron表达式
     */
    private void updateJob(String jobName, String jobGroupName, String cronExpression) {
        try {
            TriggerKey triggerKey = TriggerKey.triggerKey(jobName, jobGroupName);
            CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);
            trigger = trigger.getTriggerBuilder()
                .withIdentity(triggerKey)
                .withSchedule(CronScheduleBuilder.cronSchedule(cronExpression))
                .build();
            scheduler.rescheduleJob(triggerKey, trigger);
        } catch (SchedulerException e) {
            log.error("Scheduler update job failed.", e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
    }

    private void updateIntervalJob(TriggerKey triggerKey, int intervalSeconds) throws SchedulerException {
        SimpleTrigger currentTrigger = (SimpleTrigger) scheduler.getTrigger(triggerKey);
        SimpleTrigger trigger = currentTrigger.getTriggerBuilder()
            .withIdentity(triggerKey)
            .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                .withIntervalInSeconds(intervalSeconds)
                .repeatForever()
                .withMisfireHandlingInstructionNextWithRemainingCount())
            .build();
        scheduler.rescheduleJob(triggerKey, trigger);
    }

    /**
     * 删除任务
     *
     * @param jobName 任务名称
     * @param jobGroupName 任务组名称
     */
    public void deleteJob(String jobName, String jobGroupName) {
        try {
            scheduler.pauseTrigger(TriggerKey.triggerKey(jobName, jobGroupName));
            scheduler.unscheduleJob(TriggerKey.triggerKey(jobName, jobGroupName));
            scheduler.deleteJob(new JobKey(jobName, jobGroupName));
        } catch (SchedulerException e) {
            log.error("Scheduler delete job failed.", e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION);
        }
    }

    /**
     * 立即执行一个任务
     *
     * @param jobName 任务名称
     * @param jobGroupName 任务组名称
     */
    public void runJobNow(String jobName, String jobGroupName) {
        try {
            JobKey jobKey = JobKey.jobKey(jobName, jobGroupName);
            scheduler.triggerJob(jobKey);
        } catch (SchedulerException e) {
            log.error("Run job failed.", e);
            throw new AgentStudioException(StudioError.SCHEDULER_EXCEPTION_RUN_JOB);
        }
    }
}
