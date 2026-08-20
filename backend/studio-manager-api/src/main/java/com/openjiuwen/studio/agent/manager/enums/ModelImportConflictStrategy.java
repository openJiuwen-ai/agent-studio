/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 模型导入冲突策略。
 *
 * <p>冲突判定键 = serviceName + providerId（对齐 {@code ModelServiceMapper.queryByName}）。
 * 跨环境迁移时目标环境可能已存在同名模型，由此策略决定处置方式。
 */
@AllArgsConstructor
@Getter
public enum ModelImportConflictStrategy {
    SKIP("SKIP", "同名(serviceName+providerId)跳过，保留目标环境已有记录"),
    COVER("COVER", "覆盖：删除目标环境同名旧记录，按导入数据重新插入(保留导入id)");

    private final String code;

    private final String desc;
}
