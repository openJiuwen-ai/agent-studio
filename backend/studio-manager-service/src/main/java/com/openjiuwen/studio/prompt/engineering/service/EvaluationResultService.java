/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_EVALUATION_TASK;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_EXPORT_RESULT;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.DatasetDto;
import com.openjiuwen.studio.prompt.engineering.dto.FileInfoVo;
import com.openjiuwen.studio.prompt.engineering.dto.PeEvaluationResultVo;
import com.openjiuwen.studio.prompt.engineering.dto.PeEvaluationResultsVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptResultVo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptEvaluationResult;
import com.openjiuwen.studio.prompt.engineering.dto.VariableVo;
import com.openjiuwen.studio.prompt.engineering.entity.EvaluationResultsExportExcel;
import com.openjiuwen.studio.prompt.engineering.entity.PeEvaluationResult;
import com.openjiuwen.studio.prompt.engineering.entity.PeEvaluationTask;
import com.openjiuwen.studio.prompt.engineering.entity.PromptEvaluationResultExport;
import com.openjiuwen.studio.prompt.engineering.entity.VariableExport;
import com.openjiuwen.studio.prompt.engineering.entity.PePrompt;
import com.openjiuwen.studio.prompt.engineering.enums.EvaluationTaskStatus;
import com.openjiuwen.studio.prompt.engineering.mapper.DatasetMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PeEvaluationTaskMapper;
import com.openjiuwen.studio.prompt.engineering.utils.DateUtil;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelI18nHandler;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelUtil;
import com.openjiuwen.studio.prompt.engineering.utils.EntityBlockMergeStrategy;
import com.openjiuwen.studio.prompt.engineering.utils.FixedColumnWidthStyleStrategy;
import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;
import com.openjiuwen.studio.prompt.engineering.utils.PromptUtil;
import com.openjiuwen.studio.prompt.engineering.vo.ResultNumCount;

import com.alibaba.excel.EasyExcel;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.util.CellRangeAddress;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.MessageSource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;


/**
 * 功能描述
 *
 */
@Slf4j
@Service
public class EvaluationResultService {
    @Autowired
    private MessageSource messageSource;

    @Resource
    private PeEvaluationTaskMapper peEvaluationTaskMapper;

    @Resource
    private DatasetMapper datasetMapper;

    @Resource
    private PromptObsService promptObsService;

    @Resource
    private EvaluationMethodService evaluationMethodService;

    @Resource
    private PromptService promptService;

    @Autowired
    private ExcelUtil excelUtil;

    @Autowired
    private HttpServletResponse response;

    private static List<PromptEvaluationResult> getPePromptEvaluationResultVOS(List<Map<String, String>> list,
                                                                               Map<Integer, List<PeEvaluationResult>> splitMap, Map<String, PePrompt> pePromptMap) {
        List<PromptEvaluationResult> resultList = new ArrayList<>();
        for (int testNum = 1; testNum <= list.size(); testNum++) {
            List<VariableVo> variableVos = new ArrayList<>();
            Map<String, String> variables = list.get(testNum - 1);
            for (Map.Entry<String, String> variable : variables.entrySet()) {
                String variableKey = variable.getKey();
                String variableValue = variable.getValue();
                if (!"result".equals(variableKey)) {
                    VariableVo variableVo = new VariableVo();
                    variableVo.setKey(variableKey);
                    variableVo.setValue(variableValue);
                    variableVos.add(variableVo);
                }
            }
            List<PeEvaluationResultVo> resultVOS = new ArrayList<>();
            for (Map.Entry<String, PePrompt> pePromptEntry : pePromptMap.entrySet()) {
                String pePromptEntryKey = pePromptEntry.getKey();
                PePrompt pePromptEntryValue = pePromptEntry.getValue();
                PeEvaluationResultVo resultVO = new PeEvaluationResultVo();
                resultVO.setPromptId(pePromptEntryKey);
                resultVO.setPromptName(pePromptEntryValue.getName());
                if (splitMap.containsKey(testNum)) {
                    for (PeEvaluationResult item : splitMap.get(testNum)) {
                        if (item.getPromptId().equals(pePromptEntryKey)) {
                            resultVO.setId(item.getId());
                            resultVO.setGenerateResult(item.getGenerateResult());
                            resultVO.setEvalResult(item.getEvalResult());
                            resultVO.setEvalFailedReason(item.getEvalFailedReason());
                        }
                    }
                }
                resultVOS.add(resultVO);
            }
            PromptEvaluationResult promptEvaluationResult = new PromptEvaluationResult();
            promptEvaluationResult.setTestNum(testNum);
            promptEvaluationResult.setVariables(variableVos);
            promptEvaluationResult.setExpectResult(variables.get("result"));
            promptEvaluationResult.setPromptResultList(resultVOS);
            resultList.add(promptEvaluationResult);
        }
        return resultList;
    }

    /**
     * 通过行号分隔结果，相同行号的结果存到一起
     *
     * @param results 总结果
     * @return map 分隔好的结果
     */
    private static Map<Integer, List<PeEvaluationResult>> splitResultList(List<PeEvaluationResult> results) {
        Map<Integer, List<PeEvaluationResult>> splitMap = new HashMap<>();
        results.forEach(item -> {
            Integer testNum = item.getTestNum();
            if (!splitMap.containsKey(testNum)) {
                splitMap.put(testNum, new ArrayList<>());
            }
            splitMap.get(testNum).add(item);
        });
        return splitMap;
    }

    public PeEvaluationResultsVo showEvaluationResults(String projectId, String evaluationTaskId, String workspaceId) {
        if (!Boolean.TRUE.equals(peEvaluationTaskMapper.isEvaluationTaskExist(evaluationTaskId, workspaceId))) {
            throw new AgentStudioException(StudioError.EVALUATION_TASK_IS_NOT_EXIST);
        }
        PeEvaluationResultsVo resultsVO = new PeEvaluationResultsVo();
        PeEvaluationTask peEvaluationTask = peEvaluationTaskMapper.queryEvaluationTaskDetailsByIds(
            Collections.singletonList(evaluationTaskId), workspaceId).get(0);
        Map<String, PePrompt> pePromptMap = peEvaluationTask.getPrompts()
            .stream()
            .collect(Collectors.toMap(PePrompt::getId, Function.identity(), (k, v) -> k));
        List<PeEvaluationResult> results = peEvaluationTaskMapper.queryEvalResultsByEvalTaskId(evaluationTaskId, workspaceId);
        DatasetDto datasetById = datasetMapper.getDatasetById(projectId, peEvaluationTask.getTestSetId(), workspaceId);
        if (datasetById == null) {
            throw new AgentStudioException(StudioError.READ_DATASET_CACHE_EXCEPTION);
        }
        String path = datasetById.getObsPath();
        String bucket = path.split(CommonConstant.FOLDER_SEPARATOR)[0];
        String filePath = path.substring(path.indexOf('/') + 1);
        List<Map<String, String>> list = excelUtil.obtainCasesByObsFile(RequestContextUtils.getRequestAuthToken(), bucket, filePath);
        List<PePromptResultVo> promptVOS = getPePromptVOs(peEvaluationTask, results, list.size());
        resultsVO.setPrompts(promptVOS);
        if (EvaluationTaskStatus.success.equals(peEvaluationTask.getStatus())) {
            Comparator<PePromptResultVo> comparator = Comparator.comparing(PePromptResultVo::getScore)
                .reversed()
                .thenComparing(PePromptResultVo::getToken)
                .thenComparing(PePromptResultVo::getTime);
            promptVOS.sort(comparator);
            resultsVO.setOptimalPromptId(promptVOS.get(0).getId());
        }
        resultsVO.setName(peEvaluationTask.getName());
        resultsVO.setTotal(list.size());
        resultsVO.setStatus(peEvaluationTask.getStatus().name());
        Map<Integer, List<PeEvaluationResult>> splitMap = splitResultList(results);
        resultsVO.setCount(splitMap.size());
        resultsVO.setMethod(peEvaluationTask.getMethod().name());

        List<PromptEvaluationResult> resultList = getPePromptEvaluationResultVOS(list, splitMap, pePromptMap);

        resultsVO.setResultList(resultList);
        return resultsVO;
    }

    public List<PePromptResultVo> getPePromptVOs(PeEvaluationTask peEvaluationTask, List<PeEvaluationResult> results,
        int resultNum) {
        List<PePromptResultVo> promptVOS = new ArrayList<>();
        Map<String, ResultNumCount> promptMap = new HashMap<>();
        if (EvaluationTaskStatus.success.equals(peEvaluationTask.getStatus())) {
            promptMap = evaluationMethodService.parsePromptResult(results);
        }
        List<PePrompt> prompts = peEvaluationTask.getPrompts();
        for (PePrompt item : prompts) {
            PePromptResultVo pePromptVO = item.convertToPePromptResultVO();
            pePromptVO.setVariableVo(promptService.getVariableVos(item.getVariables(), peEvaluationTask.getWorkspaceId()));
            if (item.getFileId() != null) pePromptVO.setFileInfo(new FileInfoVo().setFileId(item.getFileId()).setTempUrl(promptObsService.getObsTempUrl(String.format("%s/%s", "image", item.getFileId()), 3600L)));
            if (EvaluationTaskStatus.success.equals(peEvaluationTask.getStatus())) {
                ResultNumCount numCount = promptMap.getOrDefault(item.getId(), new ResultNumCount());
                pePromptVO.setScore(numCount.getScore());
                pePromptVO.setToken(numCount.getToken());
                pePromptVO.setCorrectNum(numCount.getCorrect());
                pePromptVO.setErrorNum(resultNum - numCount.getCorrect());
                pePromptVO.setTime(PromptUtil.formatDouble(numCount.getTime()));
            }
            promptVOS.add(pePromptVO);
        }
        return promptVOS;
    }

    public String exportEvaluationResults(String projectId, String evaluationTaskId, String workspaceId) {
        PeEvaluationResultsVo resultList = showEvaluationResults(projectId, evaluationTaskId, workspaceId);
        EvaluationTaskStatus status = EvaluationTaskStatus.getEvaluationTaskStatus(resultList.getStatus());
        if (!EvaluationTaskStatus.canExport(status)) {
            throw new AgentStudioException(StudioError.EXPORT_EVALUATION_RESULT_FAILED);
        }
        String evaluationTaskName = resultList.getName();

        II18nHandler i18nHandler = new ExcelI18nHandler(messageSource);
        List<EvaluationResultsExportExcel> rows = EvaluationResultsExportExcel.convertToEvaluationResultsExcelRows(
            resultList, i18nHandler);

        String time = DateUtil.format(new Date());

        String fileNameHeader = "EvaluationResultExport_" + time + ".xlsx";
        response.setContentType("application/octet-stream;charset=utf-8");
        response.setHeader("Content-Disposition", "attachment;filename=" + fileNameHeader);
        String sheetName = i18nHandler.getLocaleName(LOCAL_NAME_EVALUATION_TASK) + " " + evaluationTaskName + " "
            + i18nHandler.getLocaleName(LOCAL_NAME_EXPORT_RESULT);
        exportByEasyExcel(rows, i18nHandler, sheetName);
        return null;
    }

    /**
     * EasyExcel 导出(瘦身修订 2026-11-04 1C:原 easypoi ExcelExportUtil 移除)。
     *
     * <p>与原 easypoi 输出语义对齐:
     * <ul>
     *   <li>动态表头——列名 i18n key 预解析(原 easypoi 的 i18nHandler 渲染链);</li>
     *   <li>嵌套集合扁平化——每行 = 变量 × 提示词结果,父列(testNum/预期结果)
     *       经 SameValueVerticalMergeStrategy 纵向合并(原 needMerge);</li>
     *   <li>列宽按原注解 width 对齐;</li>
     *   <li>导出校验(DDE 特殊字符前缀检查)在写流前对扁平行值执行,语义与
     *       原 validateExportExcel(Workbook) 一致。</li>
     * </ul>
     */
    void exportByEasyExcel(List<EvaluationResultsExportExcel> rows, II18nHandler i18nHandler,
            String sheetName) {
        List<List<String>> head = buildExportHead(i18nHandler);
        List<List<Object>> flatRows = new ArrayList<>();
        List<int[]> entityRowRanges = new ArrayList<>();
        flattenRows(rows, flatRows, entityRowRanges);
        ExcelUtil.validateExportValues(flatRows);
        // 评审修订 2026-11-04 v2:预计算合并区(写流前,基于实体行区间)——
        // v1 的 SameValueVerticalMergeStrategy 有两个缺陷:跨实体合并
        // (相邻实体同值时合并区跨越边界)+ finish() 在 doWrite() 后调
        // (workbook 已序列化,合并不可见)。v2 改为 EntityBlockMergeStrategy
        // 在 afterSheetCreate 一次性应用预计算区,语义与 easypoi needMerge
        // 对齐(仅同一父记录内合并,不跨实体)。
        List<CellRangeAddress> mergeRegions = EntityBlockMergeStrategy.buildMergeRegions(
            entityRowRanges, Set.of(0, 3));
        try {
            OutputStream out = response.getOutputStream();
            response.setCharacterEncoding("UTF-8");
            response.setContentType("application/vnd.ms-excel;charset=UTF-8");
            EasyExcel.write(out)
                .head(head)
                .sheet(sheetName)
                .registerWriteHandler(new EntityBlockMergeStrategy(mergeRegions))
                .registerWriteHandler(new FixedColumnWidthStyleStrategy(buildColumnWidths(), 8))
                .doWrite(flatRows);
        } catch (IOException e) {
            log.error("export evaluation results IO failed: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.EXPORT_EVALUATION_RESULT_FAILED);
        } catch (RuntimeException e) {
            log.error("export evaluation results runtime failed: {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.EXPORT_EVALUATION_RESULT_FAILED);
        }
    }

    private static List<List<String>> buildExportHead(II18nHandler i18nHandler) {
        return Arrays.asList(
            List.of(i18nHandler.getLocaleName("excel.export.evaluation.test.num")),
            List.of(i18nHandler.getLocaleName("excel.export.variable.key")),
            List.of(i18nHandler.getLocaleName("excel.export.variable.value")),
            List.of(i18nHandler.getLocaleName("excel.export.evaluation.result.expect")),
            List.of(i18nHandler.getLocaleName("excel.export.prompt.name")),
            List.of(i18nHandler.getLocaleName("excel.export.prompt.content")),
            List.of(i18nHandler.getLocaleName("excel.export.generate.result")),
            List.of(i18nHandler.getLocaleName("excel.export.eval.result")));
    }

    /**
     * 扁平化(评审修订 2026-11-04 v2):每行 = 变量(第 i 个) × 提示词结果(第 i 个)。
     * 两个集合按各自下标对齐(超出补空)——与 easypoi 多 ExcelCollection
     * 的"逐行配对、不足留空"展开形态一致。
     * 同时输出实体行区间(供 EntityBlockMergeStrategy 预计算合并区)。
     *
     * @param rows 输入实体列表
     * @param flatRows 输出:扁平化数据行
     * @param entityRowRanges 输出:每个实体的 [startRow, endRow] 数据行索引(0 起,不含表头)
     */
    static void flattenRows(List<EvaluationResultsExportExcel> rows,
            List<List<Object>> flatRows, List<int[]> entityRowRanges) {
        for (EvaluationResultsExportExcel row : rows) {
            List<VariableExport> vars = row.getVariableExportList() == null
                ? Collections.emptyList() : row.getVariableExportList();
            List<PromptEvaluationResultExport> prompts = row.getPromptEvaluationResultExportList() == null
                ? Collections.emptyList() : row.getPromptEvaluationResultExportList();
            int startRow = flatRows.size();
            int lineCount = Math.max(vars.size(), prompts.size());
            for (int i = 0; i < lineCount; i++) {
                VariableExport var = i < vars.size() ? vars.get(i) : null;
                PromptEvaluationResultExport prompt = i < prompts.size() ? prompts.get(i) : null;
                flatRows.add(Arrays.asList(
                    row.getTestNum(),
                    var == null ? "" : var.getVariableKey(),
                    var == null ? "" : var.getVariableValue(),
                    Objects.toString(row.getExpectResult(), ""),
                    prompt == null ? "" : prompt.getPromptName(),
                    prompt == null ? "" : prompt.getPromptContent(),
                    prompt == null ? "" : prompt.getGenerateResult(),
                    prompt == null ? "" : prompt.getEvalResult()));
            }
            entityRowRanges.add(new int[]{startRow, flatRows.size() - 1});
        }
    }

    /**
     * 列宽(字符数,与原 easypoi width 注解对齐:varKey 30/varValue 100/
     * expectResult 50/promptContent 25/generateResult 75,其余默认 12)。
     */
    private static Map<Integer, Integer> buildColumnWidths() {
        Map<Integer, Integer> widths = new HashMap<>();
        widths.put(1, 30);
        widths.put(2, 100);
        widths.put(3, 50);
        widths.put(5, 25);
        widths.put(6, 75);
        return widths;
    }
}
