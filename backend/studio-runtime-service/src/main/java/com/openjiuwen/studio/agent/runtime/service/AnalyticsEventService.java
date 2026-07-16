/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventReq;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventResp;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsChannel;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsEventEntity;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsEventType;
import com.openjiuwen.studio.agent.runtime.mapper.AnalyticsEventMapper;
import com.openjiuwen.studio.agent.runtime.utils.AnalyticsEventQueue;
import com.openjiuwen.studio.agent.runtime.utils.CommonUtils;
import com.openjiuwen.studio.agent.runtime.utils.DatetimeUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.ObjectUtils;

import java.util.AbstractMap;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 分析事件
 *
 */
@Slf4j
@Service
public class AnalyticsEventService implements IAnalyticsEventService {
    @Autowired
    private AnalyticsEventMapper analyticsEventMapper;

    @Value("${ANALYTICS_EVENT_ENABLE:false}")
    private boolean analyticsEventEnable;

    private static final int INSERT_BATCH_SIZE = 100;

    public AnalyticsEventResp analyticsEvent(String projectId, String agentId, AnalyticsEventReq body) {
        AnalyticsEventResp resp = new AnalyticsEventResp();
        try {
            String userId = RequestContextUtils.getRequestUserId();
            AnalyticsEventType eventType =
                Enum.valueOf(AnalyticsEventType.class, StringUtils.isEmpty(body.getEventType()) ? body.getEventType()
                    : body.getEventType().toUpperCase(Locale.getDefault()));
            AnalyticsEventEntity event = AnalyticsEventEntity.builder()
                .eventId(body.getEventId())
                .eventType(eventType.toString())
                .appType(body.getAppType())
                .appId(agentId)
                .projectId(projectId)
                .channel(StringUtils.isEmpty(body.getChannel()) ? AnalyticsChannel.API.getText() : body.getChannel())
                .userId(userId)
                .build();
            addEvent(event);
            resp.setEventId(event.getEventId());
        } catch (IllegalArgumentException ex) {
            resp.setErrorMessage("Invalid event type.");
        } catch (Exception ex) {
            resp.setErrorMessage(ex.getLocalizedMessage());
        }
        return resp;
    }

    public void addEvent(AnalyticsEventEntity event) {
        if (!analyticsEventEnable) {
            return;
        }
        if (StringUtils.isEmpty(event.getEventId())) {
            event.setEventId(UUID.randomUUID().toString());
        }
        if (ObjectUtils.isEmpty(event.getEventTime())) {
            event.setEventTime(new Date());
        }
        if (null == event.getIsNewAppUser()) {
            event.setIsNewAppUser(false);
        }
        event.setEventDate(DatetimeUtils.dateFormatDay(event.getEventTime()));
        AnalyticsEventQueue.push(event);
    }

    /**
     * 将缓存中的事件刷入数据库
     *
     * @param time 截止时间点
     */
    public void flushEvent(Date time) {
        Date endTime = ObjectUtils.isEmpty(time) ? new Date() : time;
        List<AnalyticsEventEntity> events = AnalyticsEventQueue.popBatchByTime(endTime);

        if (!analyticsEventEnable) {
            return;
        }
        // 分批插入
        List<List<AnalyticsEventEntity>> groupEvents = CommonUtils.groupList(events, INSERT_BATCH_SIZE);
        for (List<AnalyticsEventEntity> entities : groupEvents) {
            analyticsEventMapper.insertBatch(entities);
        }

        // 更新是否新增用户
        updateNewAppUser(events);
    }

    /**
     * 清除数据库中的数据（老化）
     *
     * @param start 起始
     * @param end 结束
     */
    public void clearEvent(Date start, Date end) {
        if (!analyticsEventEnable) {
            return;
        }
        analyticsEventMapper.clear(start, end);
        log.info("clear analytics event history. start: {}, end: {}", start, end);
    }

    private void updateNewAppUser(List<AnalyticsEventEntity> events) {
        try {
            Map<String, List<AnalyticsEventEntity>> appEventsMap =
                events.stream().collect(Collectors.groupingBy(AnalyticsEventEntity::getAppId));

            appEventsMap.forEach((appId, appEvents) -> {
                Map<AbstractMap.SimpleEntry<String, String>, List<AnalyticsEventEntity>> groupEventsMap = appEvents
                    .stream()
                    .collect(
                        Collectors.groupingBy(evt -> new AbstractMap.SimpleEntry<>(evt.getChannel(), evt.getUserId())));

                groupEventsMap.forEach((channel, groupEvents) -> {
                    AnalyticsEventEntity event = groupEvents.stream()
                        .sorted(Comparator.comparing(AnalyticsEventEntity::getEventTime))
                        .findFirst()
                        .orElse(null);
                    if (StringUtils.isEmpty(analyticsEventMapper.findFirstUserEvent(event))) {
                        analyticsEventMapper.updateFirstUserEvent(event);
                    }
                });
            });
        } catch (Exception e) {
            log.error("update new app user fail. {}", e.getLocalizedMessage(), e);
        }
    }
}
