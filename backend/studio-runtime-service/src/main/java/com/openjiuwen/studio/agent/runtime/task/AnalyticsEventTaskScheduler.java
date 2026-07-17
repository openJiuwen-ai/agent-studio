/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.task;

import com.openjiuwen.studio.agent.runtime.service.AnalyticsEventService;
import com.openjiuwen.studio.agent.runtime.utils.DatetimeUtils;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;

/**
 * 分析事件定时任务
 *
 */

@Slf4j
@Component
@ConditionalOnProperty(name = "ANALYTICS_EVENT_ENABLE", havingValue = "true")
public class AnalyticsEventTaskScheduler {
    @Value("${ANALYTICS_EVENT_RETENTION_PERIOD_DAY:180}")
    private int retentionPeriodDay;

    @Autowired
    private AnalyticsEventService analyticsEventService;

    // 默认延迟30分钟，避免新插入的事件干扰
    private static final int DELAY_FLUSH_MINUTES = 30;

    /**
     * 暂时不考虑事务管理，当前阶段实现功能，dfx后续再单独讨论
     * 1小时同步一次
     */
    @Scheduled(fixedRate = 1000 * 60 * 60)
    public void flushTask() {
        LocalDateTime localDateTime = LocalDateTime.now().minusMinutes(DELAY_FLUSH_MINUTES);
        Date end = Date.from(localDateTime.atZone(ZoneId.systemDefault()).toInstant());
        analyticsEventService.flushEvent(end);

        log.info(String.format("flush task finished. {}", DatetimeUtils.dateFormat(end)));
    }

    /**
     * 暂时不考虑事务管理，当前阶段实现功能，dfx后续再单独讨论
     * 1小时同步一次
     */
    @Scheduled(fixedRate = 1000 * 60 * 60 * 24)
    public void clearTask() {
        if (retentionPeriodDay < 0) {
            return;
        }

        // 起始时间占位
        Date start = new Date(0);
        LocalDateTime localDateTime = LocalDateTime.now().minusDays(retentionPeriodDay);
        Date end = Date.from(localDateTime.atZone(ZoneId.systemDefault()).toInstant());
        analyticsEventService.clearEvent(start, end);

        log.info(String.format("clear task finished. {} - {}", DatetimeUtils.dateFormat(start),
            DatetimeUtils.dateFormat(end)));
    }
}
