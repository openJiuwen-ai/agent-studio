/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.enums.v2;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;
import java.util.List;

/**
 * 任务运行状态枚举类
 * 对应状态：0-草稿, 1-等待执行, 2-执行中, 3-执行成功, 4-执行失败
 */
@Getter
@AllArgsConstructor
public enum PromptTaskStatusEnum {

    /**
     * 草稿状态
     */
    DRAFT(0, "草稿", Arrays.asList(OperatorEnum.DELETE, OperatorEnum.EDIT, OperatorEnum.CREATE, OperatorEnum.QUERY)),

    /**
     * 等待执行
     */
    WAITING(1, "等待执行", Arrays.asList(OperatorEnum.COPY, OperatorEnum.DELETE)),

    /**
     * 执行中
     */
    RUNNING(2, "执行中", Arrays.asList(OperatorEnum.COPY, OperatorEnum.PAUSE, OperatorEnum.QUERY)),

    /**
     * 执行成功
     */
    SUCCESS(3, "执行成功", Arrays.asList(OperatorEnum.QUERY, OperatorEnum.COPY, OperatorEnum.DELETE)),

    /**
     * 执行失败
     */
    FAILED(4, "执行失败", Arrays.asList(OperatorEnum.RESTART, OperatorEnum.COPY, OperatorEnum.DELETE, OperatorEnum.CREATE)),

    /**
     * 任务暂停
     * 允许 QUERY：暂停中/已暂停任务需支持详情查询(状态轮询同步、详情页恢复流程均依赖)，
     * 否则 getPromptTask 权限校验失败导致详情页报错
     */
    PAUSE(5, "任务暂停", Arrays.asList(OperatorEnum.RESUME, OperatorEnum.DELETE, OperatorEnum.QUERY)),

    /**
     * 任务暂停中
     * 允许 QUERY：PAUSING 为异步中间态，前端轮询详情驱动状态流转为 PAUSE，禁止查询将导致状态永久卡死
     */
    PAUSING(6, "任务暂停中", List.of(OperatorEnum.QUERY));

    /**
     * 状态编码
     */
    private final int code;

    /**
     * 状态描述
     */
    private final String desc;

    /**
     * 该状态允许的操作
     */
    private final List<OperatorEnum> allowedOperators;

    /**
     * 根据状态编码获取枚举实例
     * @param code 状态编码
     * @return 对应的枚举实例，不存在则返回null
     */
    public static PromptTaskStatusEnum getByCode(int code) {
        for (PromptTaskStatusEnum status : values()) {
            if (status.code == code) {
                return status;
            }
        }
        return null;
    }

    public static PromptTaskStatusEnum getByJiuWenStatus(String jiuWenStatus) {
        if (jiuWenStatus == null) {
            return null;
        }
        return switch (jiuWenStatus) {
            case "finished" -> SUCCESS;
            case "failed" -> FAILED;
            case "running" -> RUNNING;
            case "stopping" -> PAUSING;
            case "stopped" -> PAUSE;
            default -> null;
        };
    }

    public static boolean statusMaybeChange(int code) {
        // RUNNING(2) 时，状态可能变化
        return code == RUNNING.getCode() || code == PAUSING.getCode();
    }

    // 校验操作是否允许（核心方法）
    public boolean isOperatorAllowed(OperatorEnum op) {
        if (op == null) {
            return false;
        }
        return allowedOperators.contains(op);
    }

    public enum OperatorEnum {
        DELETE,  // 删除
        EDIT,    // 编辑
        COPY,    // 复制
        PAUSE,   // 暂停
        QUERY,   // 查询
        RESTART, // 重启
        RESUME,  // 恢复
        CREATE,  // 创建
        STOP;    // 停止
    }
}
