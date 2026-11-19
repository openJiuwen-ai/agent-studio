/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.entity;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_EXPORT_MATCHING;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_EXPORT_SIMILARITY;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.LOCAL_NAME_EXPORT_TIME_CONSUMED;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.dto.PeEvalResult;
import com.openjiuwen.studio.prompt.engineering.dto.PeEvaluationResultVo;
import com.openjiuwen.studio.prompt.engineering.dto.PeEvaluationResultsVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptResultVo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptEvaluationResult;
import com.openjiuwen.studio.prompt.engineering.enums.EvaluationMethodType;

import com.openjiuwen.studio.prompt.engineering.utils.II18nHandler;

import lombok.Builder;
import lombok.Data;
import lombok.experimental.Accessors;

import org.apache.commons.lang3.Strings;
import org.springframework.validation.annotation.Validated;

import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.stream.Collectors;


/**
 * 评估结果导出(瘦身修订 2026-11-04 1C:easypoi 注解移除,导出改为
 * EvaluationResultService 的 EasyExcel 动态表头——嵌套集合扁平化 +
 * 父列纵向合并,视觉语义与原 easypoi needMerge 一致)
 *
 */
@Data
@Builder
@Validated
@Accessors(chain = true)
public class EvaluationResultsExportExcel {
    /**
     * 用例编号(导出列:纵向合并)
     */
    private int testNum;

    /**
     * 变量信息
     */
    private List<VariableExport> variableExportList;

    /**
     * 预期结果(导出列:纵向合并,列宽 50)
     */
    private String expectResult;

    /**
     * 提示词结果导出列表
     */
    private List<PromptEvaluationResultExport> promptEvaluationResultExportList;

    public static List<EvaluationResultsExportExcel> convertToEvaluationResultsExcelRows(
            PeEvaluationResultsVo peEvaluationResultsVo, II18nHandler i18nHandler) {
        PeEvaluationResultsVoToEvaluationResultsExcelConverter toEvaluationResultsExcelConverter
            = new PeEvaluationResultsVoToEvaluationResultsExcelConverter();
        return toEvaluationResultsExcelConverter.convert(peEvaluationResultsVo, i18nHandler);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private static String toIndentedString(Object o) {
        if (o == null) {
            return "";
        }
        return o.toString().replace(System.lineSeparator(), System.lineSeparator() + "    ");
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        EvaluationResultsExportExcel that = (EvaluationResultsExportExcel) o;
        return testNum == that.testNum && Objects.equals(variableExportList, that.variableExportList) && Objects.equals(
            expectResult, that.expectResult) && Objects.equals(promptEvaluationResultExportList,
            that.promptEvaluationResultExportList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(testNum, variableExportList, expectResult, promptEvaluationResultExportList);
    }

    private static class PeEvaluationResultsVoToEvaluationResultsExcelConverter
        implements FormConvert<PeEvaluationResultsVo, List<EvaluationResultsExportExcel>> {
        @Override
        public List<EvaluationResultsExportExcel> convert(PeEvaluationResultsVo peEvaluationResultsVo,
            II18nHandler i18nHandler) {
            List<PromptEvaluationResult> resultList = peEvaluationResultsVo.getResultList();
            List<PePromptResultVo> prompts = peEvaluationResultsVo.getPrompts();
            return resultList.stream()
                .map(result -> EvaluationResultsExportExcel.builder()
                    .testNum(result.getTestNum())
                    .variableExportList(result.getVariables()
                        .stream()
                        .map(VariableExport::convertToVariableExport)
                        .collect(Collectors.toList()))
                    .expectResult(result.getExpectResult())
                    .promptEvaluationResultExportList(prompts.stream().map(pePromptResultVo -> {
                        String promptId = pePromptResultVo.getId();
                        String promptName = pePromptResultVo.getName();
                        String promptContent = pePromptResultVo.getContent();
                        List<PeEvaluationResultVo> peEvaluationResultVos = result.getPromptResultList();
                        PeEvaluationResultVo evaluationResultVo = peEvaluationResultVos.stream()
                            .filter(peEvaluationResultVo -> Strings.CS.equals(peEvaluationResultVo.getPromptId(),
                                promptId))
                            .collect(Collectors.toList())
                            .get(0);
                        String generateResult = evaluationResultVo.getGenerateResult();
                        String evalResult = evalResultExcelToString(evaluationResultVo.getEvalResult(),
                            EvaluationMethodType.getEvaluationMethodType(
                                peEvaluationResultsVo.getMethod().toLowerCase(Locale.ENGLISH)), i18nHandler);
                        return PromptEvaluationResultExport.builder()
                            .promptName(promptName)
                            .promptContent(promptContent)
                            .generateResult(generateResult)
                            .evalResult(evalResult)
                            .build();
                    }).collect(Collectors.toList()))
                    .build())
                .collect(Collectors.toList());
        }

        private String evalResultExcelToString(PeEvalResult evalResult, EvaluationMethodType method,
                                               II18nHandler i18nHandler) {
            if (Objects.isNull(evalResult)) {
                return "";
            }
            if (method == null) {
                throw new AgentStudioException(StudioError.EVALUATION_METHOD_ERROR);
            }
            String result = "";
            if (method.equals(EvaluationMethodType.MATCHING)) {
                result += i18nHandler.getLocaleName(LOCAL_NAME_EXPORT_MATCHING) + ": ";
            }
            if (method.equals(EvaluationMethodType.SIMILARITY)) {
                result += i18nHandler.getLocaleName(LOCAL_NAME_EXPORT_SIMILARITY) + ": ";
            }
            result += toIndentedString(evalResult.getScore()) + System.lineSeparator() + "token: " + toIndentedString(
                evalResult.getToken()) + System.lineSeparator() + i18nHandler.getLocaleName(
                LOCAL_NAME_EXPORT_TIME_CONSUMED) + ": " + toIndentedString(evalResult.getTime()) + "s";
            return result;
        }
    }
}
