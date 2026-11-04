/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.utils;

import com.alibaba.excel.write.handler.SheetWriteHandler;
import com.alibaba.excel.write.metadata.holder.WriteSheetHolder;
import com.alibaba.excel.write.metadata.holder.WriteWorkbookHolder;

import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.util.CellRangeAddress;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * 实体块纵向合并策略(瘦身修订 2026-11-04 1C,评审修订 2026-11-04 v2)。
 *
 * <p>v1(SameValueVerticalMergeStrategy)的两个评审缺陷:
 * <ul>
 *   <li>跨实体合并:相邻实体同值(典型:expectResult 均为空串)时,合并区
 *       跨越实体边界,与原 easypoi needMerge(仅同一父记录内合并)不符;</li>
 *   <li>finish() 时序:doWrite() 后 workbook 已序列化,补合并不可见
 *       (且可能修改已完成的 workbook 抛运行时异常)。</li>
 * </ul>
 *
 * <p>v2 设计:预计算合并区(在写流前,由 Service 基于 flattenRows 的
 * 实体行区间算出 CellRangeAddress 列表),afterSheetCreate 时一次性应用。
 * 不依赖 CellWriteHandler 的逐行回调,不存在收尾/跨实体问题。
 */
public class EntityBlockMergeStrategy implements SheetWriteHandler {

    private final List<CellRangeAddress> mergeRegions;

    /**
     * 构造合并策略。
     *
     * @param mergeRegions 预计算的合并区列表(Service 在写流前从实体行区间算出)
     */
    public EntityBlockMergeStrategy(List<CellRangeAddress> mergeRegions) {
        this.mergeRegions = mergeRegions;
    }

    @Override
    public void afterSheetCreate(WriteWorkbookHolder writeWorkbookHolder, WriteSheetHolder writeSheetHolder) {
        Sheet sheet = writeSheetHolder.getSheet();
        for (CellRangeAddress region : mergeRegions) {
            sheet.addMergedRegionUnsafe(region);
        }
    }

    /**
     * 从实体行区间构建合并区(静态工厂,供 Service 调用)。
     *
     * <p>对每个实体的 [startRow, endRow] 区间(数据行,0 起,不含表头),
     * 为指定列生成纵向合并区——与原 easypoi needMerge 语义一致:
     * 只在同一父记录的多行内合并,不跨实体。
     *
     * <p>行号偏移:EasyExcel 动态表头写行 0,数据行从 1 起——
     * 实体行区间基于数据行索引(0 起),合并区须 +1 对齐 sheet 行号。
     *
     * @param entityRowRanges 实体行区间列表(每个元素 = [startRow, endRow] 数据行索引)
     * @param mergeColumns 需要合并的列索引集合
     * @return 合并区列表(单行实体不产生合并区)
     */
    public static List<CellRangeAddress> buildMergeRegions(
            List<int[]> entityRowRanges, Set<Integer> mergeColumns) {
        List<CellRangeAddress> regions = new ArrayList<>();
        int headerOffset = 1;
        for (int[] range : entityRowRanges) {
            int startRow = range[0] + headerOffset;
            int endRow = range[1] + headerOffset;
            if (endRow > startRow) {
                for (int column : mergeColumns) {
                    regions.add(new CellRangeAddress(startRow, endRow, column, column));
                }
            }
        }
        return regions;
    }
}
