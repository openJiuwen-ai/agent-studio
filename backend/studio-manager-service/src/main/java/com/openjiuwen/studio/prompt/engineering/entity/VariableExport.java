/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.entity;

import com.openjiuwen.studio.prompt.engineering.dto.VariableVo;

import lombok.Builder;
import lombok.Data;
import lombok.experimental.Accessors;

import org.springframework.validation.annotation.Validated;

/**
 * 变量信息(瘦身修订 2026-11-04 1C:easypoi @Excel 注解移除,导出列名由
 * EvaluationResultService 动态表头预解析——见 II18nHandler 迁移说明)
 *
 */
@Data
@Accessors(chain = true)
@Builder
@Validated
public class VariableExport {
    /**
     * 变量key(导出列宽 30)
     */
    private String variableKey;

    /**
     * 变量值(导出列宽 100)
     */
    private String variableValue;

    public static VariableExport convertToVariableExport(VariableVo variableVo) {
        VariableVoToVariableExportConverter toVariableExportConverter
            = new VariableVoToVariableExportConverter();
        return toVariableExportConverter.convert(variableVo);
    }

    private static class VariableVoToVariableExportConverter implements FormConvert<VariableVo, VariableExport> {
        @Override
        public VariableExport convert(VariableVo variableVo) {
            return VariableExport.builder()
                .variableKey(variableVo.getKey())
                .variableValue(variableVo.getValue())
                .build();
        }
    }
}
