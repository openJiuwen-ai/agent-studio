/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.utils;

import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsEventEntity;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * 分析事件缓存队列
 *
 */
@Slf4j
public class AnalyticsEventQueue {
    private static final LinkedBlockingQueue<AnalyticsEventEntity> EVENTS =
        new LinkedBlockingQueue<>(100000);

    private AnalyticsEventQueue() {
    }

    public static boolean isEmpty() {
        return EVENTS.isEmpty();
    }

    /**
     * 添加事件
     *
     * @param event 事件
     */
    public static void push(AnalyticsEventEntity event) {
        if (!EVENTS.offer(event)) {
            log.warn("Analytics event queue full (capacity={}), event discarded. eventType={}, eventId={}",
                100000, event.getEventType(), event.getEventId());
        }
    }

    /**
     * 取出事件，基于截止时间
     *
     * @param endTime 截止时间
     */
    public static List<AnalyticsEventEntity> popBatchByTime(Date endTime) {
        List<AnalyticsEventEntity> events = new ArrayList<>();
        AnalyticsEventEntity first;
        while ((first = EVENTS.peek()) != null) {
            if (first.getEventTime().before(endTime)) {
                EVENTS.poll();
                events.add(first);
            } else {
                break;
            }
        }
        return events;
    }
}
