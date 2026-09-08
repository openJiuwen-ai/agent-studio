/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 创建提示词任务请求
 */
@ApiModel(description = "创建提示词任务请求")

@Validated
public class PromptTaskCreateReq implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @NotBlank
    @Length(min = 1, max = 34)
    private String name = null;

    @JsonProperty("desc")
    @Length(max = 256)
    private String desc = null;

    @JsonProperty("promptId")
    @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    private String promptId = null;

    @JsonProperty("execTime")
    private Long execTime = null;

    @JsonProperty("ptType")
    private PtTypeEnum ptType = null;

    @JsonProperty("ptText")
    @Length(max = 10000)
    private String ptText = null;

    @JsonProperty("ptVars")
    @Length(max = 1200)
    private String ptVars = null;

    @JsonProperty("dataSetId")
    @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    private String dataSetId = null;

    @JsonProperty("ptObject")
    @Valid
    private ExecConfig ptObject = null;

    @JsonProperty("assitantObject")
    @Valid
    private ExecConfig assitantObject = null;

    @JsonProperty("maxIterNum")
    @Range(min = 1L, max = 20L)
    private Integer maxIterNum = null;

    @JsonProperty("targetAcc")
    private String targetAcc = null;

    @JsonProperty("showCaseNum")
    @Range(min = 0L, max = 5L)
    private Integer showCaseNum = null;

    @JsonProperty("targetType")
    private TargetTypeEnum targetType = null;

    @JsonProperty("scoreStandard")
    @Length(max = 5000)
    private String scoreStandard = null;

    @JsonProperty("backKnowledge")
    @Length(max = 5000)
    private String backKnowledge = null;

    @JsonProperty("algorithm")
    private AlgorithmEnum algorithm = null;

    public String getName() {
        return name;
    }

    public PromptTaskCreateReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public PromptTaskCreateReq setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getPromptId() {
        return promptId;
    }

    public PromptTaskCreateReq setPromptId(String promptId) {
        this.promptId = promptId;
        return this;
    }

    public Long getExecTime() {
        return execTime;
    }

    public PromptTaskCreateReq setExecTime(Long execTime) {
        this.execTime = execTime;
        return this;
    }

    public PtTypeEnum getPtType() {
        return ptType;
    }

    public PromptTaskCreateReq setPtType(PtTypeEnum ptType) {
        this.ptType = ptType;
        return this;
    }

    public String getPtText() {
        return ptText;
    }

    public PromptTaskCreateReq setPtText(String ptText) {
        this.ptText = ptText;
        return this;
    }

    public String getPtVars() {
        return ptVars;
    }

    public PromptTaskCreateReq setPtVars(String ptVars) {
        this.ptVars = ptVars;
        return this;
    }

    public String getDataSetId() {
        return dataSetId;
    }

    public PromptTaskCreateReq setDataSetId(String dataSetId) {
        this.dataSetId = dataSetId;
        return this;
    }

    public ExecConfig getPtObject() {
        return ptObject;
    }

    public PromptTaskCreateReq setPtObject(ExecConfig ptObject) {
        this.ptObject = ptObject;
        return this;
    }

    public ExecConfig getAssitantObject() {
        return assitantObject;
    }

    public PromptTaskCreateReq setAssitantObject(ExecConfig assitantObject) {
        this.assitantObject = assitantObject;
        return this;
    }

    public Integer getMaxIterNum() {
        return maxIterNum;
    }

    public PromptTaskCreateReq setMaxIterNum(Integer maxIterNum) {
        this.maxIterNum = maxIterNum;
        return this;
    }

    public String getTargetAcc() {
        return targetAcc;
    }

    public PromptTaskCreateReq setTargetAcc(String targetAcc) {
        this.targetAcc = targetAcc;
        return this;
    }

    public Integer getShowCaseNum() {
        return showCaseNum;
    }

    public PromptTaskCreateReq setShowCaseNum(Integer showCaseNum) {
        this.showCaseNum = showCaseNum;
        return this;
    }

    public TargetTypeEnum getTargetType() {
        return targetType;
    }

    public PromptTaskCreateReq setTargetType(TargetTypeEnum targetType) {
        this.targetType = targetType;
        return this;
    }

    public String getScoreStandard() {
        return scoreStandard;
    }

    public PromptTaskCreateReq setScoreStandard(String scoreStandard) {
        this.scoreStandard = scoreStandard;
        return this;
    }

    public String getBackKnowledge() {
        return backKnowledge;
    }

    public PromptTaskCreateReq setBackKnowledge(String backKnowledge) {
        this.backKnowledge = backKnowledge;
        return this;
    }

    public AlgorithmEnum getAlgorithm() {
        return algorithm;
    }

    public PromptTaskCreateReq setAlgorithm(AlgorithmEnum algorithm) {
        this.algorithm = algorithm;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptTaskCreateReq {\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    promptId: ").append(toIndentedString(promptId)).append("\n");
        sb.append("    execTime: ").append(toIndentedString(execTime)).append("\n");
        sb.append("    ptType: ").append(toIndentedString(ptType)).append("\n");
        sb.append("    ptText: ").append(toIndentedString(ptText)).append("\n");
        sb.append("    ptVars: ").append(toIndentedString(ptVars)).append("\n");
        sb.append("    dataSetId: ").append(toIndentedString(dataSetId)).append("\n");
        sb.append("    ptObject: ").append(toIndentedString(ptObject)).append("\n");
        sb.append("    assitantObject: ").append(toIndentedString(assitantObject)).append("\n");
        sb.append("    maxIterNum: ").append(toIndentedString(maxIterNum)).append("\n");
        sb.append("    targetAcc: ").append(toIndentedString(targetAcc)).append("\n");
        sb.append("    showCaseNum: ").append(toIndentedString(showCaseNum)).append("\n");
        sb.append("    targetType: ").append(toIndentedString(targetType)).append("\n");
        sb.append("    scoreStandard: ").append(toIndentedString(scoreStandard)).append("\n");
        sb.append("    backKnowledge: ").append(toIndentedString(backKnowledge)).append("\n");
        sb.append("    algorithm: ").append(toIndentedString(algorithm)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        PromptTaskCreateReq promptTaskCreateReq = (PromptTaskCreateReq) o;
        return Objects.equals(this.name, promptTaskCreateReq.name) && Objects.equals(this.desc,
            promptTaskCreateReq.desc) && Objects.equals(this.promptId, promptTaskCreateReq.promptId) && Objects.equals(
            this.execTime, promptTaskCreateReq.execTime) && Objects.equals(this.ptType, promptTaskCreateReq.ptType)
            && Objects.equals(this.ptText, promptTaskCreateReq.ptText) && Objects.equals(this.ptVars,
            promptTaskCreateReq.ptVars) && Objects.equals(this.dataSetId, promptTaskCreateReq.dataSetId)
            && Objects.equals(this.ptObject, promptTaskCreateReq.ptObject) && Objects.equals(this.assitantObject,
            promptTaskCreateReq.assitantObject) && Objects.equals(this.maxIterNum, promptTaskCreateReq.maxIterNum)
            && Objects.equals(this.targetAcc, promptTaskCreateReq.targetAcc) && Objects.equals(this.showCaseNum,
            promptTaskCreateReq.showCaseNum) && Objects.equals(this.targetType, promptTaskCreateReq.targetType)
            && Objects.equals(this.scoreStandard, promptTaskCreateReq.scoreStandard) && Objects.equals(
            this.backKnowledge, promptTaskCreateReq.backKnowledge) && Objects.equals(this.algorithm,
            promptTaskCreateReq.algorithm);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, desc, promptId, execTime, ptType, ptText, ptVars, dataSetId, ptObject, assitantObject,
            maxIterNum, targetAcc, showCaseNum, targetType, scoreStandard, backKnowledge, algorithm);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }

    /**
     * 提示词优化任务类型
     */
    public enum PtTypeEnum {

        TEXT("text"),
        MULTI("multi");

        private String value;

        PtTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static PtTypeEnum fromValue(String text) {
            for (PtTypeEnum b : PtTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }

    /**
     * 用例的目标类型
     */
    public enum TargetTypeEnum {

        OBJECTIVE("objective"),
        SUBJECTIVE("subjective");

        private String value;

        TargetTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static TargetTypeEnum fromValue(String text) {
            for (TargetTypeEnum b : TargetTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }

    /**
     * 优化算法
     */
    public enum AlgorithmEnum {

        GREEDY("greedy"),
        BEAMSEARCH("beamsearch");

        private String value;

        AlgorithmEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static AlgorithmEnum fromValue(String text) {
            for (AlgorithmEnum b : AlgorithmEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
