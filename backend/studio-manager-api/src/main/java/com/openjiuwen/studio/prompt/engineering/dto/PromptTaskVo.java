/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 提示词优化任务详情
 */
@ApiModel(description = "提示词优化任务详情")

@Validated
public class PromptTaskVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String name = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "示例描述", required = true)
    @NotBlank
    @Length(max = 1024)
    private String desc = null;

    @JsonProperty("dataSetId")
    @Schema(description = "数据集ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String dataSetId = null;

    @JsonProperty("ptType")
    @Schema(description = "提示词类型", example = "text")
    private String ptType = null;

    @JsonProperty("ptText")
    @Schema(description = "提示词文本", example = "示例文本")
    @Length(min = 1, max = 10000)
    private String ptText = null;

    @JsonProperty("ptVar")
    @Schema(description = "提示词变量", example = "示例文本")
    private String ptVar = null;

    @JsonProperty("execTime")
    @Schema(description = "执行时间", example = "1700000000000")
    private Long execTime = null;

    @JsonProperty("ptModel")
    @Schema(description = "提示词模型", example = "示例文本")
    private String ptModel = null;

    @JsonProperty("execObject")
    @Schema(description = "执行对象", example = "示例文本")
    private String execObject = null;

    @JsonProperty("maxIterNum")
    @Schema(description = "最大迭代次数", example = "10")
    @Range(min = 1L, max = 100L)
    private Integer maxIterNum = null;

    @JsonProperty("targetAcc")
    @Schema(description = "目标准确率", example = "0.95")
    private String targetAcc = null;

    @JsonProperty("showCaseNum")
    @Schema(description = "展示用例数量", example = "3")
    private Integer showCaseNum = null;

    @JsonProperty("targetType")
    @Schema(description = "目标类型", example = "objective")
    private TargetTypeEnum targetType = null;

    @JsonProperty("scoreStandard")
    @Schema(description = "评分标准", example = "示例文本")
    private String scoreStandard = null;

    @JsonProperty("backKnowledge")
    @Schema(description = "背景知识", example = "示例文本")
    @Length(min = 1, max = 65535)
    private String backKnowledge = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "1")
    private Integer status = null;

    @JsonProperty("projectId")
    @Schema(description = "项目ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String projectId = null;

    @JsonProperty("workspaceId")
    @Schema(description = "工作空间ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String workspaceId = null;

    @JsonProperty("createdTime")
    @Schema(description = "创建时间", example = "1700000000000")
    private Long createdTime = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    @Length(min = 1, max = 64)
    private String creator = null;

    @JsonProperty("creatorId")
    @Schema(description = "创建者ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String creatorId = null;

    @JsonProperty("updatedTime")
    @Schema(description = "更新时间", example = "1700000000000")
    private Long updatedTime = null;

    @JsonProperty("iterationResults")
    @Schema(description = "迭代结果列表", example = "")
    @Valid
    private List<PromptIterationResultVo> iterationResults = null;

    public String getId() {
        return id;
    }

    public PromptTaskVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public PromptTaskVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public PromptTaskVo setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getDataSetId() {
        return dataSetId;
    }

    public PromptTaskVo setDataSetId(String dataSetId) {
        this.dataSetId = dataSetId;
        return this;
    }

    public String getPtType() {
        return ptType;
    }

    public PromptTaskVo setPtType(String ptType) {
        this.ptType = ptType;
        return this;
    }

    public String getPtText() {
        return ptText;
    }

    public PromptTaskVo setPtText(String ptText) {
        this.ptText = ptText;
        return this;
    }

    public String getPtVar() {
        return ptVar;
    }

    public PromptTaskVo setPtVar(String ptVar) {
        this.ptVar = ptVar;
        return this;
    }

    public Long getExecTime() {
        return execTime;
    }

    public PromptTaskVo setExecTime(Long execTime) {
        this.execTime = execTime;
        return this;
    }

    public String getPtModel() {
        return ptModel;
    }

    public PromptTaskVo setPtModel(String ptModel) {
        this.ptModel = ptModel;
        return this;
    }

    public String getExecObject() {
        return execObject;
    }

    public PromptTaskVo setExecObject(String execObject) {
        this.execObject = execObject;
        return this;
    }

    public Integer getMaxIterNum() {
        return maxIterNum;
    }

    public PromptTaskVo setMaxIterNum(Integer maxIterNum) {
        this.maxIterNum = maxIterNum;
        return this;
    }

    public String getTargetAcc() {
        return targetAcc;
    }

    public PromptTaskVo setTargetAcc(String targetAcc) {
        this.targetAcc = targetAcc;
        return this;
    }

    public Integer getShowCaseNum() {
        return showCaseNum;
    }

    public PromptTaskVo setShowCaseNum(Integer showCaseNum) {
        this.showCaseNum = showCaseNum;
        return this;
    }

    public TargetTypeEnum getTargetType() {
        return targetType;
    }

    public PromptTaskVo setTargetType(TargetTypeEnum targetType) {
        this.targetType = targetType;
        return this;
    }

    public String getScoreStandard() {
        return scoreStandard;
    }

    public PromptTaskVo setScoreStandard(String scoreStandard) {
        this.scoreStandard = scoreStandard;
        return this;
    }

    public String getBackKnowledge() {
        return backKnowledge;
    }

    public PromptTaskVo setBackKnowledge(String backKnowledge) {
        this.backKnowledge = backKnowledge;
        return this;
    }

    public Integer getStatus() {
        return status;
    }

    public PromptTaskVo setStatus(Integer status) {
        this.status = status;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public PromptTaskVo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public PromptTaskVo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public PromptTaskVo setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PromptTaskVo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public PromptTaskVo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Long getUpdatedTime() {
        return updatedTime;
    }

    public PromptTaskVo setUpdatedTime(Long updatedTime) {
        this.updatedTime = updatedTime;
        return this;
    }

    public List<PromptIterationResultVo> getIterationResults() {
        return iterationResults;
    }

    public PromptTaskVo setIterationResults(List<PromptIterationResultVo> iterationResults) {
        this.iterationResults = iterationResults;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptTaskVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    dataSetId: ").append(toIndentedString(dataSetId)).append("\n");
        sb.append("    ptType: ").append(toIndentedString(ptType)).append("\n");
        sb.append("    ptText: ").append(toIndentedString(ptText)).append("\n");
        sb.append("    ptVar: ").append(toIndentedString(ptVar)).append("\n");
        sb.append("    execTime: ").append(toIndentedString(execTime)).append("\n");
        sb.append("    ptModel: ").append(toIndentedString(ptModel)).append("\n");
        sb.append("    execObject: ").append(toIndentedString(execObject)).append("\n");
        sb.append("    maxIterNum: ").append(toIndentedString(maxIterNum)).append("\n");
        sb.append("    targetAcc: ").append(toIndentedString(targetAcc)).append("\n");
        sb.append("    showCaseNum: ").append(toIndentedString(showCaseNum)).append("\n");
        sb.append("    targetType: ").append(toIndentedString(targetType)).append("\n");
        sb.append("    scoreStandard: ").append(toIndentedString(scoreStandard)).append("\n");
        sb.append("    backKnowledge: ").append(toIndentedString(backKnowledge)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    updatedTime: ").append(toIndentedString(updatedTime)).append("\n");
        sb.append("    iterationResults: ").append(toIndentedString(iterationResults)).append("\n");
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
        PromptTaskVo promptTaskVo = (PromptTaskVo) o;
        return Objects.equals(this.id, promptTaskVo.id) && Objects.equals(this.name, promptTaskVo.name)
            && Objects.equals(this.desc, promptTaskVo.desc) && Objects.equals(this.dataSetId, promptTaskVo.dataSetId)
            && Objects.equals(this.ptType, promptTaskVo.ptType) && Objects.equals(this.ptText, promptTaskVo.ptText)
            && Objects.equals(this.ptVar, promptTaskVo.ptVar) && Objects.equals(this.execTime, promptTaskVo.execTime)
            && Objects.equals(this.ptModel, promptTaskVo.ptModel) && Objects.equals(this.execObject,
            promptTaskVo.execObject) && Objects.equals(this.maxIterNum, promptTaskVo.maxIterNum) && Objects.equals(
            this.targetAcc, promptTaskVo.targetAcc) && Objects.equals(this.showCaseNum, promptTaskVo.showCaseNum)
            && Objects.equals(this.targetType, promptTaskVo.targetType) && Objects.equals(this.scoreStandard,
            promptTaskVo.scoreStandard) && Objects.equals(this.backKnowledge, promptTaskVo.backKnowledge)
            && Objects.equals(this.status, promptTaskVo.status) && Objects.equals(this.projectId,
            promptTaskVo.projectId) && Objects.equals(this.workspaceId, promptTaskVo.workspaceId) && Objects.equals(
            this.createdTime, promptTaskVo.createdTime) && Objects.equals(this.creator, promptTaskVo.creator)
            && Objects.equals(this.creatorId, promptTaskVo.creatorId) && Objects.equals(this.updatedTime,
            promptTaskVo.updatedTime) && Objects.equals(this.iterationResults, promptTaskVo.iterationResults);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, desc, dataSetId, ptType, ptText, ptVar, execTime, ptModel, execObject, maxIterNum,
            targetAcc, showCaseNum, targetType, scoreStandard, backKnowledge, status, projectId, workspaceId,
            createdTime, creator, creatorId, updatedTime, iterationResults);
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
}
