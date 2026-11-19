/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.utils;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.NUM_ONE;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.NUM_ZERO;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;

import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;


/**
 * 表格解析工具类
 *
 */
@Slf4j
@Component
public class ExcelUtil {
    /**
     * 解析出的文件缓存时间
     */
    private static final int FILE_CACHE_TIME = 30 * 60;

    /**
     * 最大的缓存数目
     */
    private static final int MAX_CACHE_NUM = 99;

    /**
     * 最大表头(key)数目
     */
    private static final int MAX_HEADER_CELL_NUM = 20;

    /**
     * 最大内容长度
     */
    private static final int MAX_VALUE_LENGTH = 1000;

    private static final List<Map<String, String>> EMPTY_LIST = new ArrayList<>();

    private static final LoadingCache<String, List<Map<String, String>>> FILE_CACHE = CacheBuilder.newBuilder()
        .maximumSize(MAX_CACHE_NUM)
        .expireAfterWrite(FILE_CACHE_TIME, TimeUnit.SECONDS)
        .build(new CacheLoader<String, List<Map<String, String>>>() {
            @Override
            public List<Map<String, String>> load(String s) {
                return EMPTY_LIST;
            }
        });

    private static I18nUtil i18nUtil;

    @Autowired
    private ObsUtil obsUtil;

    /**
     * 从OBS文件中获取数据集内容
     *
     * @param bucket 桶名
     * @param filePath 桶内文件路径
     * @return mapList
     */
    public List<Map<String, String>> obtainDataSetContent(String xAuthToken, String bucket, String filePath) {
        InputStream is = obsUtil.downloadObsFile(xAuthToken, bucket, filePath);
        XSSFWorkbook workbook = null;
        List<Map<String, String>> list = new ArrayList<>();
        try {
            workbook = new XSSFWorkbook(is);

            // 获取第一个sheet页
            XSSFSheet sheet = workbook.getSheetAt(0);
            XSSFRow headerRow = sheet.getRow(0);
            if (isEmptyRow(headerRow)) {
                throw new AgentStudioException(StudioError.DATASET_HEADER_ROW_IS_NULL_ERROR);
            }

            // 表头个数校验
            if (headerRow.getLastCellNum() > MAX_HEADER_CELL_NUM) {
                throw new AgentStudioException(StudioError.DATASET_KEY_NUMBER_LIMIT);
            }
            for (int rowIndex = 1; rowIndex <= sheet.getLastRowNum(); rowIndex++) {
                XSSFRow valueRow = sheet.getRow(rowIndex);
                if (isEmptyRow(valueRow)) {
                    throw new AgentStudioException(StudioError.DATASET_VALUE_ROW_IS_NULL_ERROR);
                }
                Map<String, String> map = new HashMap<>();
                for (int cellIndex = 0; cellIndex < headerRow.getLastCellNum(); cellIndex++) {
                    XSSFCell valueCell = valueRow.getCell(cellIndex);
                    if (headerRow.getCell(cellIndex) == null) {
                        throw new AgentStudioException(StudioError.DATASET_WITH_NULL_KEY_ERROR);
                    }
                    String key = headerRow.getCell(cellIndex).getStringCellValue();

                    // 表头相同key校验
                    if (map.containsKey(key)) {
                        throw new AgentStudioException(StudioError.DATASET_WITH_SAME_KEY);
                    }

                    // 数据集内容长度校验
                    if (valueCell != null && getCellStringOrNull(valueCell).length() > MAX_VALUE_LENGTH) {
                        throw new AgentStudioException(StudioError.DATASET_CONTENT_LENGTH_LIMIT);
                    }
                    if ("result".equals(key)) {
                        if (Objects.isNull(valueCell) || valueCell.getCellType() == CellType.BLANK) {
                            throw new AgentStudioException(StudioError.DATASET_RESULT_EMPTY);
                        }
                    }
                    map.put(key, getCellStringOrNull(valueCell));
                }
                list.add(map);
            }
        } catch (IOException e) {
            log.error("read dataset excel failed.");
            throw new AgentStudioException(StudioError.READ_DATASET_EXCEPTION);
        } finally {
            if (Objects.nonNull(workbook)) {
                try {
                    workbook.close();
                } catch (IOException e) {
                    log.error("dataset excel close failed.");
                }
            }
            if (Objects.nonNull(is)) {
                try {
                    is.close();
                } catch (IOException e) {
                    log.error("input stream close failed.");
                }
            }
        }
        return list;
    }

    /**
     * 检查excel文件row是否为空
     *
     * @param row
     * @return
     */
    public boolean isEmptyRow(XSSFRow row) {
        // 只判断row == null不全面
        if (row == null || row.toString().isEmpty()) {
            return true;
        } else {
            Iterator<Cell> it = row.iterator();
            boolean isEmpty = false;
            while (it.hasNext()) {
                Cell cell = it.next();
                if (cell == null || cell.getCellType() == CellType.BLANK) {
                    isEmpty = true;
                } else {
                    isEmpty = false;
                    break;
                }
            }
            return isEmpty;
        }
    }

    /**
     * 获取表格中的单个元素并转换成String类型
     *
     * @param cell 表格元素
     * @return String
     */
    public String getCellStringOrNull(XSSFCell cell) {
        if (null == cell) {
            return "";
        } else {
            cell.setCellType(CellType.STRING);
            return cell.getStringCellValue();
        }
    }

    public int getExcelLineLength(String xAuthToken, String bucket, String filePath) {
        InputStream inputStream = obsUtil.downloadObsFile(xAuthToken, bucket, filePath);
        XSSFWorkbook workbook = null;
        int lineLength = 0;
        try {
            workbook = new XSSFWorkbook(inputStream);
            XSSFSheet sheet = workbook.getSheetAt(0);
            lineLength = sheet.getLastRowNum();
        } catch (IOException e) {
            log.error("read excel fileLength failed.");
        } finally {
            if (workbook != null) {
                try {
                    workbook.close();
                } catch (IOException var2) {
                    log.error("close workbook stream fail, {}", var2.getMessage());
                }
            }
            if (inputStream != null) {
                try {
                    inputStream.close();
                } catch (IOException var2) {
                    log.error("close input stream fail, {}", var2.getMessage());
                }
            }
        }
        return lineLength;
    }

    /**
     * 从缓存中获取并解析变量集数据
     *
     * @param bucket 桶名
     * @param filePath 文件路径
     * @return list 解析结果
     * @throws IOException 解析失败异常
     * @throws ExecutionException 缓存获取异常
     */
    public List<Map<String, String>> obtainCasesByObsFile(String xAuthToken, String bucket, String filePath) {
        try {
            if (!CollectionUtils.isEmpty(FILE_CACHE.get(filePath))) {
                return FILE_CACHE.get(filePath);
            }
        } catch (ExecutionException e) {
            log.error("read dataset cache failed.");
            throw new AgentStudioException(StudioError.READ_DATASET_CACHE_EXCEPTION);
        }
        List<Map<String, String>> list = obtainDataSetContent(xAuthToken, bucket, filePath);
        FILE_CACHE.put(filePath, list);
        return list;
    }

    @NotNull
    public static void exportExcelFile(Workbook workbook, HttpServletResponse response, StudioError studioError) {
        if (!validateExportExcel(workbook)) {
            throw new AgentStudioException(StudioError.EXPORT_EXCEL_VALIDATE_FAILED);
        }
        try (OutputStream outputStream = response.getOutputStream()) {
            response.setCharacterEncoding("UTF-8");
            response.setContentType("application/vnd.ms-excel;charset=UTF-8");
            String dateTime = DateUtil.formatCompact(new Date());
            String fileName = "TemplateExport_" + dateTime + ".xlsx";
            response.setHeader("Content-Disposition", "attachment; filename=" + fileName);
            workbook.write(outputStream);
        } catch (IOException e) {
            log.error("download excel IOException! {}", i18nUtil.getMessage(studioError));
            throw new AgentStudioException(studioError);
        } finally {
            try {
                workbook.close();
            } catch (IOException e) {
                log.error("excel close failed. {}", i18nUtil.getMessage(studioError));
            }
        }
    }

    private static Boolean validateExportExcel(Workbook workbook) {
        int numberOfSheets = workbook.getNumberOfSheets();
        for (int indOfSheet = NUM_ZERO; indOfSheet < numberOfSheets; indOfSheet++) {
            Sheet sheet = workbook.getSheetAt(indOfSheet);
            if (sheet != null) {
                int numberOfRows = sheet.getPhysicalNumberOfRows();
                for (int indOfRow = NUM_ZERO; indOfRow < numberOfRows; indOfRow++) {
                    if (!validateRow(sheet.getRow(indOfRow), indOfRow)) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    private static Boolean validateRow(Row row, int indOfRow) {
        if (row != null) {
            int numberOfCells = row.getPhysicalNumberOfCells();
            for (int indOfCell = NUM_ZERO; indOfCell < numberOfCells; indOfCell++) {
                Cell cell = row.getCell(indOfCell);
                if (cell != null && StringUtil.isStartWithSpecialCharacter(cell.getStringCellValue())) {
                    log.error("row {} col {} is start with special character", indOfRow + NUM_ONE, indOfCell + NUM_ONE);
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * 导出值前置校验(瘦身修订 2026-11-04 1C)。
     *
     * <p>EasyExcel 动态表头模式下无 Workbook 中间产物,原
     * validateExportExcel(Workbook) 的 DDE 特殊字符前缀检查改为对
     * 扁平行值在写流前执行——语义一致(=,+,-,@ 起头拒绝导出),
     * 失败抛原 EXPORT_EXCEL_VALIDATE_FAILED。
     *
     * <p>注:exportExcelFile(Workbook,...) 仍被 PromptTemplateService 的
     * 原生 POI 导出路径调用(评审修订 2026-11-04:review 误判死代码),
     * 保留不动。
     *
     * @param flatRows 扁平化导出行(值列,不含表头)
     */
    public static void validateExportValues(List<List<Object>> flatRows) {
        for (int indOfRow = NUM_ZERO; indOfRow < flatRows.size(); indOfRow++) {
            List<Object> row = flatRows.get(indOfRow);
            for (int indOfCell = NUM_ZERO; indOfCell < row.size(); indOfCell++) {
                Object value = row.get(indOfCell);
                if (value != null && StringUtil.isStartWithSpecialCharacter(String.valueOf(value))) {
                    log.error("row {} col {} is start with special character", indOfRow + NUM_ONE, indOfCell + NUM_ONE);
                    throw new AgentStudioException(StudioError.EXPORT_EXCEL_VALIDATE_FAILED);
                }
            }
        }
    }
}
