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

    /**
     * 已落盘到 insight_exec_events_* List 的事件数量。
     * 仅写入 meta key 时填充，作为"新格式"标记：读取时若该字段非空，则从 events List 合并 eventList；
     * 为空则按老格式直接使用 meta 内联的 eventList（兼容存量数据）。
     */
    private Long eventCount;
}
