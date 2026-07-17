/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import lombok.Data;

/**
 * ControllerExecutionBriefModel
 *
 */
@Data
public class ControllerExecutionBriefModel {
    private String executionId;

    private String query;

    private String status;

    private String error;

    private Long startTime;
}
