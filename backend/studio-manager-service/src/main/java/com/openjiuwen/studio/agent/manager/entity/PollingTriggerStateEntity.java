/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import lombok.Data;

import java.util.Date;

/**
 * Polling trigger runtime state.
 */
@Data
public class PollingTriggerStateEntity {
    private String triggerId;

    private String lastSeenHash;

    private Date lastCheckedAt;

    private Date createdAt;

    private Date updatedAt;
}
