/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.utils;

import com.alibaba.excel.metadata.Head;
import com.alibaba.excel.metadata.data.WriteCellData;
import com.alibaba.excel.write.handler.CellWriteHandler;
import com.alibaba.excel.write.metadata.holder.WriteSheetHolder;
import com.alibaba.excel.write.metadata.holder.WriteTableHolder;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.util.CellRangeAddress;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * 同值纵向合并策略(瘦身修订 2026-11-04 1C,EasyExcel 版)。
 *
 * <p>背景:原 easypoi 的 {@code needMerge = true}(父列纵向合并)在三套
 * Excel 栈归一到 easyexcel 后无原生对应——本处理器对指定列做"相邻同值
 * 纵向合并",覆盖扁平化后父列(testNum/expectResult 等)的合并语义。
 *
 * <p>机制:行按序写入,每行回调记录"本行值 == 上一行值"的列;值中断时
 * 对连续段补 {@code addMergedRegionUnsafe}(段长 &gt; 1 才合并)。表头行(行0)
 * 不参与。空串与空串视为同值(与 easypoi needMerge 对空段的处理一致)。
 */
public class SameValueVerticalMergeStrategy implements CellWriteHandler {

    private final Set<Integer> mergeColumns;
    private final Map<Integer, String> lastValues = new HashMap<>();
    private final Map<Integer, Integer> mergeStartRows = new HashMap<>();
    private int lastRowIndex = -1;
    private Sheet currentSheet;

    /**
     * 构造合并策略。
     *
     * @param mergeColumns 需要同值纵向合并的列索引集合(0 起,不含表头)
     */
    public SameValueVerticalMergeStrategy(Set<Integer> mergeColumns) {
        this.mergeColumns = mergeColumns;
    }

    /**
     * 收尾:合并末段(评审修订 2026-11-04——closeOpenSegments 只在新行
     * 开始时被调用,末行起的不闭合段会在无后续行时永远丢失)。
     * 调用方须在 EasyExcel doWrite() 之后调用本方法。
     */
    public void finish() {
        if (currentSheet != null && lastRowIndex >= 0) {
            closeOpenSegments(currentSheet, lastRowIndex);
        }
    }

    @Override
    public void afterCellDispose(WriteSheetHolder writeSheetHolder, WriteTableHolder writeTableHolder,
            java.util.List<WriteCellData<?>> cellDataList, Cell cell, Head head, Integer relativeRowIndex,
            Boolean isHead) {
        if (Boolean.TRUE.equals(isHead) || !mergeColumns.contains(cell.getColumnIndex())) {
            return;
        }
        currentSheet = writeSheetHolder.getSheet();
        int sheetRowIndex = cell.getRowIndex();
        // 新行开始:先把上一行各列的未闭合段收尾
        if (sheetRowIndex != lastRowIndex) {
            closeOpenSegments(writeSheetHolder.getSheet(), sheetRowIndex - 1);
            lastRowIndex = sheetRowIndex;
        }
        String value = readCellString(cell);
        String last = lastValues.get(cell.getColumnIndex());
        if (Objects.equals(value, last)) {
            mergeStartRows.computeIfAbsent(cell.getColumnIndex(), k -> sheetRowIndex - 1);
        } else {
            mergeStartRows.remove(cell.getColumnIndex());
        }
        lastValues.put(cell.getColumnIndex(), value);
    }

    private void closeOpenSegments(Sheet sheet, int endRow) {
        mergeStartRows.forEach((column, startRow) -> {
            if (endRow > startRow) {
                sheet.addMergedRegionUnsafe(new CellRangeAddress(startRow, endRow, column, column));
            }
        });
        mergeStartRows.clear();
    }

    private static String readCellString(Cell cell) {
        if (cell == null || cell.getCellType() == CellType.BLANK) {
            return "";
        }
        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case NUMERIC -> String.valueOf(cell.getNumericCellValue());
            case BOOLEAN -> String.valueOf(cell.getBooleanCellValue());
            default -> "";
        };
    }
}
