/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.insight;

import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;

import lombok.Data;

import java.util.List;

@Data
public class WorkflowInstanceEntity {
    private String id;
    private String externalId;
    private String userId;
    private String conversationId;
    private String workflowId;
    private String projectId;
    private Object inputs;
    private Object outputs;
    private String status;
    private String runInfo;
    private Long startTime;
    private Long endTime;
    private String errorInfo;
    private List<JiuwenEvent> eventList;
}
