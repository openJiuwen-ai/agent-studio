/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.prompt.engineering.entity.EvaluationResultsExportExcel;
import com.openjiuwen.studio.prompt.engineering.entity.PromptEvaluationResultExport;
import com.openjiuwen.studio.prompt.engineering.entity.VariableExport;
import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;
import com.openjiuwen.studio.prompt.engineering.utils.EntityBlockMergeStrategy;

import com.alibaba.excel.EasyExcel;

import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Set;

/**
 * 1C 迁移读回验证(v2,评审修订 2026-11-04):
 * EntityBlockMergeStrategy 预计算合并 + flattenRows 实体行区间。
 */
class EvaluationExportEasyExcelTest {

    /** 直透 i18n(key 即列名)——测试聚焦结构,不测翻译。 */
    private static final II18nHandler PASS_THROUGH = key -> key;

    @Test
    void flattenAndWriteReadBack_structureEquivalent() throws Exception {
        // 构造:2 实体——实体1(2变量+2提示词,索引配对=2行)、实体2(1变量+0提示词=1行)
        List<EvaluationResultsExportExcel> rows = List.of(
            EvaluationResultsExportExcel.builder()
                .testNum(1)
                .variableExportList(List.of(
                    VariableExport.builder().variableKey("k1").variableValue("v1").build(),
                    VariableExport.builder().variableKey("k2").variableValue("v2").build()))
                .expectResult("预期A")
                .promptEvaluationResultExportList(List.of(
                    PromptEvaluationResultExport.builder().promptName("p1").promptContent("c1")
                        .generateResult("g1").evalResult("e1").build(),
                    PromptEvaluationResultExport.builder().promptName("p2").promptContent("c2")
                        .generateResult("g2").evalResult("e2").build()))
                .build(),
            EvaluationResultsExportExcel.builder()
                .testNum(2)
                .variableExportList(List.of(
                    VariableExport.builder().variableKey("k3").variableValue("v3").build()))
                .expectResult("预期B")
                .promptEvaluationResultExportList(List.of())
                .build());

        // 扁平化(v2:含实体行区间)
        List<List<Object>> flat = new ArrayList<>();
        List<int[]> ranges = new ArrayList<>();
        EvaluationResultService.flattenRows(rows, flat, ranges);
        assertEquals(3, flat.size(), "实体1索引配对2行 + 实体2单行1行");
        assertEquals(Arrays.asList(1, "k1", "v1", "预期A", "p1", "c1", "g1", "e1"), flat.get(0));
        assertEquals(Arrays.asList(1, "k2", "v2", "预期A", "p2", "c2", "g2", "e2"), flat.get(1));
        assertEquals(Arrays.asList(2, "k3", "v3", "预期B", "", "", "", ""), flat.get(2));
        // 实体行区间:实体1=[0,1],实体2=[2,2]
        assertArrayEquals(new int[]{0, 1}, ranges.get(0));
        assertArrayEquals(new int[]{2, 2}, ranges.get(1));

        // 预计算合并区 + 写入
        List<CellRangeAddress> mergeRegions = EntityBlockMergeStrategy.buildMergeRegions(
            ranges, Set.of(0, 3));
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        EasyExcel.write(bos)
            .head(buildHead())
            .sheet("评估结果")
            .registerWriteHandler(new EntityBlockMergeStrategy(mergeRegions))
            .doWrite(flat);

        // 读回断言
        try (XSSFWorkbook wb = new XSSFWorkbook(new ByteArrayInputStream(bos.toByteArray()))) {
            Sheet sheet = wb.getSheet("评估结果");
            assertEquals("评估结果", sheet.getSheetName());
            assertEquals("excel.export.evaluation.test.num",
                sheet.getRow(0).getCell(0).getStringCellValue());
            assertEquals(4, sheet.getPhysicalNumberOfRows(), "1表头+3数据行");
            assertEquals(1, (int) sheet.getRow(1).getCell(0).getNumericCellValue());
            assertEquals("k1", sheet.getRow(1).getCell(1).getStringCellValue());
            // 合并:testNum 列(0)实体1块[行1..行2]、expectResult 列(3)同
            // (读回时表头行偏移+1:实体1=[数据行0-1] → sheet行[1-2])
            assertTrue(merged(sheet, 1, 2, 0), "testNum 列实体1块须合并");
            assertTrue(merged(sheet, 1, 2, 3), "expectResult 列实体1块须合并");
            // 实体2单行,无跨实体合并
            assertTrue(!merged(sheet, 2, 3, 3), "expectResult 列不得跨实体合并(实体2与实体1同值场景)");
        }
    }

    @Test
    void crossEntity_sameValue_notMerged() throws Exception {
        // 评审关键场景:两个实体 expectResult 同值(空串典型),v1 会跨实体合并,v2 不会
        List<EvaluationResultsExportExcel> rows = List.of(
            EvaluationResultsExportExcel.builder()
                .testNum(1)
                .variableExportList(List.of(
                    VariableExport.builder().variableKey("k1").variableValue("v1").build(),
                    VariableExport.builder().variableKey("k2").variableValue("v2").build()))
                .expectResult("")
                .promptEvaluationResultExportList(List.of())
                .build(),
            EvaluationResultsExportExcel.builder()
                .testNum(2)
                .variableExportList(List.of(
                    VariableExport.builder().variableKey("k3").variableValue("v3").build(),
                    VariableExport.builder().variableKey("k4").variableValue("v4").build()))
                .expectResult("")
                .promptEvaluationResultExportList(List.of())
                .build());

        List<List<Object>> flat = new ArrayList<>();
        List<int[]> ranges = new ArrayList<>();
        EvaluationResultService.flattenRows(rows, flat, ranges);
        assertEquals(4, flat.size());
        // 实体1=[0,1],实体2=[2,3],两个实体 expectResult 都是 ""
        assertArrayEquals(new int[]{0, 1}, ranges.get(0));
        assertArrayEquals(new int[]{2, 3}, ranges.get(1));

        List<CellRangeAddress> mergeRegions = EntityBlockMergeStrategy.buildMergeRegions(
            ranges, Set.of(0, 3));
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        EasyExcel.write(bos)
            .head(buildHead())
            .sheet("test")
            .registerWriteHandler(new EntityBlockMergeStrategy(mergeRegions))
            .doWrite(flat);

        try (XSSFWorkbook wb = new XSSFWorkbook(new ByteArrayInputStream(bos.toByteArray()))) {
            Sheet sheet = wb.getSheet("test");
            // 实体1块合并(行1-2):两个实体的 expectResult 同为空串,但只在本实体内合并
            assertTrue(merged(sheet, 1, 2, 3), "实体1内须合并");
            assertTrue(merged(sheet, 3, 4, 3), "实体2内须合并");
            // 跨实体不合并(v1 缺陷的修正验证):
            assertTrue(!merged(sheet, 1, 4, 3), "expectResult 列不得跨实体合并(v1缺陷场景)");
            assertTrue(!merged(sheet, 2, 3, 3), "实体边界行不得合并");
        }
    }

    private static List<List<String>> buildHead() {
        List<List<String>> head = new ArrayList<>();
        for (String key : Arrays.asList("excel.export.evaluation.test.num",
            "excel.export.variable.key", "excel.export.variable.value",
            "excel.export.evaluation.result.expect", "excel.export.prompt.name",
            "excel.export.prompt.content", "excel.export.generate.result",
            "excel.export.eval.result")) {
            head.add(List.of(PASS_THROUGH.getLocaleName(key)));
        }
        return head;
    }

    private static boolean merged(Sheet sheet, int firstRow, int lastRow, int col) {
        for (CellRangeAddress region : sheet.getMergedRegions()) {
            if (region.getFirstRow() == firstRow && region.getLastRow() == lastRow
                    && region.getFirstColumn() == col && region.getLastColumn() == col) {
                return true;
            }
        }
        return false;
    }
}
