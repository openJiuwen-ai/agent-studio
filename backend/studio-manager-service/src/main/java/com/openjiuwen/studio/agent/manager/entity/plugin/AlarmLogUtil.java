/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.plugin;

import com.alibaba.fastjson.JSONObject;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 告警日志工具类
 * 支持obs、redis、模型、工作流调用失败的告警信息单独输出到指定文件
 * 包含告警类型、详细信息、发生时间，利用log4j2框架进行日志分级和文件管理
 *
 */
@Slf4j
@Component
public class AlarmLogUtil {
    private static final Logger ALARM_LOGGER = LoggerFactory.getLogger("ALARM_LOGGER");

    /**
     * 告警工具类开关，默认关闭
     */
    @Value("${alarm.log-enable:false}")
    private boolean enabled;

    /**
     * 打印告警信息到日志文件
     *
     * @param source 告警来源
     * @param message 告警消息
     * @param detail 详细信息，可为空
     */
    public void logAlarm(String source, String message, String detail) {
        logAlarm(source, source, "ERROR", message + "  detail:" + detail);
    }

    /**
     * 打印告警信息到日志文件
     *
     * @param source 来源
     * @param resource 资源
     * @param severity 告警级别
     * @param cause 原因
     */
    public void logAlarm(String source, String resource, String severity, String cause) {
        if (!enabled) {
            return;
        }
        JSONObject obj = new JSONObject(5);
        obj.put("source", source);
        obj.put("resource", resource);
        obj.put("severity", severity);
        obj.put("cause", cause);
        obj.put("create_time", System.currentTimeMillis());
        ALARM_LOGGER.info(obj.toJSONString());
    }
}
