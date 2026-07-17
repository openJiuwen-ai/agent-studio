/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.ErrorEvent;
import com.openjiuwen.studio.agent.manager.dto.MessageEvent;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunStreamRsp;
import com.openjiuwen.studio.agent.manager.enums.WorkflowStreamEventEnum;
import com.openjiuwen.studio.agent.manager.dto.SensitiveMessageEvent;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;

import java.util.Locale;

/**
 * 工作流事件工厂类
 *
 */
@Data
@Slf4j
public class WorkflowStreamEventFactory {
    private WorkflowStreamEventFactory() {
    }

    public static WorkflowRunStreamRsp end() {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.END.name().toLowerCase(Locale.ROOT));
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp message(MessageEvent messageEvent) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.MESSAGE.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(messageEvent);
        workflowRunStreamRsp.setCreatedTime(messageEvent.getCreatedTime());
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp sensitive(SensitiveMessageEvent messageEvent) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.SENSITIVE.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(messageEvent);
        workflowRunStreamRsp.setCreatedTime(messageEvent.getCreatedTime());
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp nodeStart(NodeRunInfo nodeRunInfo) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.NODE_STARTED.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(nodeRunInfo);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp nodeWait(NodeRunInfo nodeRunInfo) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.NODE_WAIT.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(nodeRunInfo);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp nodeFinish(NodeRunInfo nodeRunInfo) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.NODE_FINISHED.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(nodeRunInfo);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp error(ErrorEvent errorEvent) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.ERROR.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(errorEvent);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp exception(Object exceptionEvent) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.EXCEPTION.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(exceptionEvent);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp workflowStarted(WorkflowRunInfo workflowRunInfo) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.WORKFLOW_STARTED.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(workflowRunInfo);
        return workflowRunStreamRsp;
    }

    public static WorkflowRunStreamRsp workflowFinished(WorkflowRunInfo workflowRunInfo) {
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(WorkflowStreamEventEnum.WORKFLOW_FINISHED.name().toLowerCase(Locale.ROOT));
        workflowRunStreamRsp.setData(workflowRunInfo);
        return workflowRunStreamRsp;
    }

    /**
     * 构造透传消息事件
     *
     * @param eventString 原始消息的JSONString
     * @param conversationId conversationId
     * @return WorkflowRunStreamRsp
     */
    public static WorkflowRunStreamRsp workflowPassThrough(String eventString, String conversationId) {
        JSONObject jsonObject = JSON.parseObject(eventString);
        if (jsonObject == null) {
            log.error("parse event failed: {}", eventString);
            return null;
        }

        String event = jsonObject.getString(Constants.Workflow.Event.EVENT);
        JSONObject data = jsonObject.getJSONObject(Constants.Workflow.Event.DATA);
        Long createdTime = jsonObject.getLong(Constants.Workflow.Event.CREATED_TIME);

        return new WorkflowRunStreamRsp().setEvent(StringUtils.toRootLowerCase(event))
            .setData(data)
            .setCreatedTime(createdTime)
            .setConversationId(conversationId);
    }
}
