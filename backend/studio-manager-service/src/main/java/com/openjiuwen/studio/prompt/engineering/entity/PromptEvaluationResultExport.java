/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.entity;

import lombok.Builder;
import lombok.Data;
import lombok.experimental.Accessors;

import org.springframework.validation.annotation.Validated;

/**
 * 提示词结果导出列表(瘦身修订 2026-11-04 1C:easypoi @Excel 注解移除,
 * 导出列名由 EvaluationResultService 动态表头预解析)
 *
 */
@Data
@Accessors(chain = true)
@Builder
@Validated
public class PromptEvaluationResultExport {
    /**
     * 提示词名称(默认列宽)
     */
    private String promptName;

    /**
     * 提示词文本(导出列宽 25)
     */
    private String promptContent;

    /**
     * 生成结果(导出列宽 75)
     */
    private String generateResult;

    /**
     * 评分结果(默认列宽)
     */
    private String evalResult;
}
