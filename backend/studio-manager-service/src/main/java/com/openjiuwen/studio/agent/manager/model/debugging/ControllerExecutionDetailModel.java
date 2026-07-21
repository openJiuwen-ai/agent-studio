/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import java.util.List;

/**
 * ControllerExecutionModel
 *
 */
@Slf4j
@Data
@NoArgsConstructor
public class ControllerExecutionDetailModel {
    private String userId;

    private String agentId;

    private String version;

    private String conversationId;

    private String executionId;

    private String query;

    private String input;

    private String output;

    private String status;

    private String error;

    private Long startTime;

    private Long endTime;

    private List<ControllerExecutionInvokeModel> invocations;

    private List<String> nestedWorkflowIds;
}
