/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.listenner;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

import com.alibaba.excel.context.AnalysisContext;
import com.alibaba.excel.metadata.data.ReadCellData;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.entity.TemplateOneRow;
import com.openjiuwen.studio.prompt.engineering.enums.TemplateImportEnum;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * DynamicExcelListener 单元测试用例
 * 覆盖场景：表头解析、数据行解析、行数限制、异常场景
 */
@ExtendWith(MockitoExtension.class)
class DynamicExcelListenerTest {

    private DynamicExcelListener listener;

    @Mock
    private AnalysisContext analysisContext;

    @Mock
    private ReadCellData<?> readCellData; // 仅声明，不在setUp中stub

    private Map<Integer, String> mockRowData;

    @BeforeEach
    void setUp() {
        listener = new DynamicExcelListener();

        // 只初始化通用的mockRowData和AnalysisContext，不做不必要的stub
        mockRowData = new HashMap<>();
        mockRowData.put(TemplateImportEnum.TEMPLATE_NAME.getIndex(), "测试模板");
        mockRowData.put(TemplateImportEnum.CONTENT.getIndex(), "测试内容");
        mockRowData.put(TemplateImportEnum.DESCRIPTION.getIndex(), "测试描述");
        mockRowData.put(TemplateImportEnum.TAG.getIndex(), "测试标签");
        mockRowData.put(TemplateImportEnum.INDUSTRY.getIndex(), "测试行业");
        mockRowData.put(TemplateImportEnum.VARIABLE.getIndex(), "测试变量");

    }

    /**
     * 测试场景1：正常解析表头（非空表头）
     */

    /**
     * 测试场景4：正常解析数据行（未超过行数限制）
     */
    @Test
    void testInvoke_NormalRow() {
        // 先模拟表头（仅必要的stub）
        Map<Integer, ReadCellData<?>> mockHeadMap = new HashMap<>();
        when(readCellData.getStringValue()).thenReturn("任意值"); // 表头值不影响数据解析
        mockHeadMap.put(0, readCellData);
        listener.invokeHead(mockHeadMap, analysisContext);

        // 执行数据解析
        listener.invoke(mockRowData, analysisContext);

        // 断言
        List<TemplateOneRow> rowDataList = listener.getRowDataList();
        assertNotNull(rowDataList);
        assertEquals(1, rowDataList.size());

        TemplateOneRow row = rowDataList.get(0);
        assertEquals("测试模板", row.getTemplateName());
        assertEquals("测试内容", row.getContent());
    }

    /**
     * 测试场景6：解析数据行超过100行限制（抛出JSON_CONTENT_LENGTH_EXCEED异常）
     */
    @Test
    void testInvoke_ExceedMaxRowCount() {
        // 先模拟表头
        Map<Integer, ReadCellData<?>> mockHeadMap = new HashMap<>();
        when(readCellData.getStringValue()).thenReturn("任意值");
        mockHeadMap.put(0, readCellData);
        listener.invokeHead(mockHeadMap, analysisContext);

        // 前100条数据均允许导入
        for (int index = 0; index < 100; index++) {
            listener.invoke(mockRowData, analysisContext);
        }
        assertEquals(100, listener.getRowDataList().size());

        // 第101条数据触发模板导入条数超限错误
        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> listener.invoke(mockRowData, analysisContext));
        assertEquals(StudioError.PROMPT_TEMPLATE_IMPORT_NUM_EXCEED, exception.getErrorCode());
    }

    /**
     * 测试场景7：解析数据行时部分字段为空（不影响解析，空值正常存储）
     */
    @Test
    void testInvoke_RowWithNullField() {
        // 先模拟表头
        Map<Integer, ReadCellData<?>> mockHeadMap = new HashMap<>();
        when(readCellData.getStringValue()).thenReturn("任意值");
        mockHeadMap.put(0, readCellData);
        listener.invokeHead(mockHeadMap, analysisContext);

        // 准备含空值的数据行
        Map<Integer, String> rowWithNull = new HashMap<>();
        rowWithNull.put(TemplateImportEnum.TEMPLATE_NAME.getIndex(), "测试模板");
        rowWithNull.put(TemplateImportEnum.CONTENT.getIndex(), null);
        rowWithNull.put(TemplateImportEnum.DESCRIPTION.getIndex(), "");

        listener.invoke(rowWithNull, analysisContext);

        TemplateOneRow row = listener.getRowDataList().get(0);
        assertEquals("测试模板", row.getTemplateName());
        assertNull(row.getContent());
        assertEquals("", row.getDescription());
    }
}
