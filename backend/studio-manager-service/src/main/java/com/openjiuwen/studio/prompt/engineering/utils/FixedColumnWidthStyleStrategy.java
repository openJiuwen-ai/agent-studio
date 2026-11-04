/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.utils;

import com.alibaba.excel.write.handler.SheetWriteHandler;
import com.alibaba.excel.write.metadata.holder.WriteSheetHolder;
import com.alibaba.excel.write.metadata.holder.WriteWorkbookHolder;

import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;

import java.util.Map;

/**
 * 固定列宽策略(瘦身修订 2026-11-04 1C,EasyExcel 版)。
 *
 * <p>背景:原 easypoi @Excel(width=...) 的列宽语义。EasyExcel 无注解
 * 动态表头模式下,列宽需以 SheetWriteHandler 在 sheet 创建后逐列设置
 * (单位=字符数,POI setColumnWidth 每字符 256)。
 */
public class FixedColumnWidthStyleStrategy implements SheetWriteHandler {

    private static final int DEFAULT_WIDTH = 12;
    private static final int WIDTH_UNIT = 256;

    private final Map<Integer, Integer> columnWidths;

    /**
     * 构造固定列宽策略。
     *
     * @param columnWidths 列索引 → 宽度(字符数);缺省列用默认 12
     */
    public FixedColumnWidthStyleStrategy(Map<Integer, Integer> columnWidths) {
        this.columnWidths = columnWidths;
    }

    @Override
    public void afterSheetCreate(WriteWorkbookHolder writeWorkbookHolder, WriteSheetHolder writeSheetHolder) {
        Sheet sheet = writeSheetHolder.getSheet();
        // 表头行高与默认行风格交给 EasyExcel;此处仅列宽
        int maxColumn = columnWidths.keySet().stream().max(Integer::compareTo).orElse(0) + 1;
        for (int column = 0; column < maxColumn; column++) {
            int width = columnWidths.getOrDefault(column, DEFAULT_WIDTH);
            sheet.setColumnWidth(column, width * WIDTH_UNIT);
        }
        // 触发列宽应用到已存在的表头行(EasyExcel 表头先行写入)
        Row headerRow = sheet.getRow(0);
        if (headerRow != null) {
            headerRow.setHeightInPoints(20);
        }
    }
}
