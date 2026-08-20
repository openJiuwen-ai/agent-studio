/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.listenner;

import com.alibaba.excel.context.AnalysisContext;
import com.alibaba.excel.event.AnalysisEventListener;
import com.alibaba.excel.metadata.data.ReadCellData;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.entity.TemplateOneRow;
import com.openjiuwen.studio.prompt.engineering.enums.TemplateImportEnum;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Getter
public class DynamicExcelListener extends AnalysisEventListener<Map<Integer, String>> {
    // 单个Sheet的解析结果：内层List=行数据，最内层=列/变量
    private final List<TemplateOneRow> rowDataList = new ArrayList<>();

    // 表头缓存：列索引 → 变量名（varKey）
    private Map<Integer, String> headerMap;

    private static final int MAX_NUMS = 100;


    /**
     * 解析表头（第一行）
     */
    @Override
    public void invokeHead(Map<Integer, ReadCellData<?>> headMap, AnalysisContext context) {
        headerMap = new HashMap<>();
        // 遍历表头，过滤空值，存储「列索引→变量名」
        headMap.forEach((index, cellData) -> {
            String varKey = cellData.getStringValue();
            if (varKey != null && !varKey.isBlank()) {
                headerMap.put(index, varKey.trim());
            }
        });
        // 表头为空则抛出异常
        if (headerMap.isEmpty()) {
            log.error("excel header is empty");
            throw new AgentStudioException(StudioError.EXCEL_HEADER_ERROR);
        }
    }

    /**
     * 解析数据行（第二行及以后）
     */
    @Override
    public void invoke(Map<Integer, String> rowData, AnalysisContext context) {
        if (headerMap == null || headerMap.isEmpty()) {
            return;
        }
        // 按实际数据行数校验，不将表头计入100条上限
        if (rowDataList.size() >= MAX_NUMS) {
            log.error("prompt template import row count exceeds limit: {}", MAX_NUMS);
            throw new AgentStudioException(StudioError.PROMPT_TEMPLATE_IMPORT_NUM_EXCEED);
        }

        TemplateOneRow templateOneRow = new TemplateOneRow();
        templateOneRow.setTemplateName(rowData.get(TemplateImportEnum.TEMPLATE_NAME.getIndex()));
        templateOneRow.setContent(rowData.get(TemplateImportEnum.CONTENT.getIndex()));
        templateOneRow.setDescription(rowData.get(TemplateImportEnum.DESCRIPTION.getIndex()));
        templateOneRow.setTag(rowData.get(TemplateImportEnum.TAG.getIndex()));
        templateOneRow.setIndustry(rowData.get(TemplateImportEnum.INDUSTRY.getIndex()));
        templateOneRow.setVars(rowData.get(TemplateImportEnum.VARIABLE.getIndex()));
        rowDataList.add(templateOneRow);

    }

    @Override
    public void doAfterAllAnalysed(AnalysisContext analysisContext) {

    }
}
