/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.enums;

import com.fasterxml.jackson.annotation.JsonValue;

import lombok.Getter;

/**
 * IR文件类型
 */
@Getter
public enum AgentIrType {
    AGENT("agent"),
    WORKFLOW("workflow"),
    MULTI_AGENTS("multiagents"),
    DEEP_RESEARCH("deepresearch"),
    PLAN_EXECUTE("plan"),
    UNKNOWN("unknown");

    private final String value;

    AgentIrType(String value) {
        this.value = value;
    }

    @Override
    @JsonValue
    public String toString() {
        return String.valueOf(value);
    }

    public static AgentIrType fromValue(String source) {
        for (AgentIrType irType : AgentIrType.values()) {
            if (irType.value.equalsIgnoreCase(source)) {
                return irType;
            }
        }
        return UNKNOWN;
    }
}
