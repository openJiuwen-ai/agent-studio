/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_CONST_EXPECT_RESULT;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_TEMPLATE_CONST_REAL_RESULT;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.VariableVo;
import com.openjiuwen.studio.prompt.engineering.entity.PeVariable;
import com.openjiuwen.studio.prompt.engineering.mapper.PeVariableMapper;
import com.openjiuwen.studio.prompt.engineering.utils.DateUtil;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelI18nHandler;

import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import javax.annotation.Resource;

/**
 * VariableManager service
 */
@Slf4j
@Service
public class VariableManagerService {
    @Autowired
    private MessageSource messageSource;

    @Resource
    private PeVariableMapper variableMapper;

    @Autowired
    private HttpServletResponse response;

    public List<VariableVo> listVariables(String projectId, String taskId, String workspaceId) {
        List<PeVariable> variableList = variableMapper.queryVariablesByTaskId(taskId, workspaceId);
        ArrayList<VariableVo> variableVos = new ArrayList<>();
        for (PeVariable peVariable : variableList) {
            variableVos.add(peVariable.convertToVariableVo());
        }
        return variableVos;
    }


    public String exportVariableDataset(String projectId, String taskId, String workspaceId) {
        List<VariableVo> variableList = listVariables(projectId, taskId, workspaceId);
        if (variableList.isEmpty()) {
            throw new AgentStudioException(StudioError.DOWNLOAD_VARIABLE_DATASET_EMPTY);
        }
        XSSFWorkbook xssfWorkbook = new XSSFWorkbook();

        II18nHandler i18nHandler = new ExcelI18nHandler(messageSource);
        // 创建变量数据集sheet和表头行
        XSSFSheet sheet = xssfWorkbook.createSheet();
        XSSFRow headRow = sheet.createRow(CommonConstant.NUM_ZERO);
        XSSFRow valueRow = sheet.createRow(CommonConstant.NUM_ONE);
        for (int index = 0; index <= variableList.size(); index++) {
            XSSFCell headCell = headRow.createCell(index);
            headCell.setCellType(CellType.STRING);
            XSSFCell valueCell = valueRow.createCell(index);
            valueCell.setCellType(CellType.STRING);
            if (index == variableList.size()) {
                headCell.setCellValue("result");
                valueCell.setCellValue(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_CONST_EXPECT_RESULT));
                continue;
            }
            headCell.setCellValue(variableList.get(index).getKey());
            valueCell.setCellValue(variableList.get(index).getKey() + "_value");
        }
        XSSFCell remarkCell = valueRow.createCell(variableList.size() + 1);
        remarkCell.setCellType(CellType.STRING);
        remarkCell.setCellValue(i18nHandler.getLocaleName(LOCAL_NAME_TEMPLATE_CONST_REAL_RESULT));

        // 导出文件
        try (OutputStream outputStream = response.getOutputStream()) {
            // 设置返回数据编码请求头信息
            response.setCharacterEncoding("UTF-8");
            response.setContentType("application/vnd.ms-excel;charset=UTF-8");
            String dateTime = DateUtil.formatCompact(new Date());
            String fileName = "VariableDataset_" + dateTime + ".xlsx";
            response.setHeader("Content-Disposition", "attachment; filename=" + fileName);
            xssfWorkbook.write(outputStream);
            return HttpStatus.OK.toString();
        } catch (IOException e) {
            log.error("download variable dataset excel IOException!", e);
            throw new AgentStudioException(StudioError.DOWNLOAD_VARIABLE_DATASET_FAILED);
        } finally {
            try {
                xssfWorkbook.close();
            } catch (IOException e) {
                log.error("dataset excel close failed.");
            }
        }
    }
}
