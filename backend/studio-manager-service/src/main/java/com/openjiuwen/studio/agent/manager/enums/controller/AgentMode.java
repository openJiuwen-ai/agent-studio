/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.enums.controller;

import lombok.Getter;

import org.apache.commons.lang3.StringUtils;

/**
 * 控制器节点类型
 *
 */
public enum AgentMode {
    /**
     * 多智能体类型
     */
    CONTROLLER("Controller"),

    /**
     * PlanExecute类型单智能体
     */
    PLANEXECUTE("PlanExecute"),

    /**
     * ReAct类型单智能体（通用模式）
     */
    REACT("ReAct");

    @Getter
    private final String mode;

    AgentMode(String mode) {
        this.mode = mode;
    }

    /**
     * 判断控制器 agents 成员是否为单智能体模式。
     * 单智能体（PlanExecute/ReAct 等）与子多智能体（Controller）共用 agents 列表，
     * 非空且不等于 Controller 即视为单智能体；与运行时 AgentMetaData.mode 语义对齐
     * （运行时按 mode 透传给 PlannerFactory/ControlFactory，未知模式按成员自身 IR 执行）。
     *
     * @param mode 控制器 agents 成员的 mode 字段
     * @return true 表示单智能体成员
     */
    public static boolean isSingleAgentMode(String mode) {
        return StringUtils.isNotBlank(mode) && !CONTROLLER.getMode().equals(mode);
    }
}
