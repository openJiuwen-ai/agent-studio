/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 评估任务Vo
 */
@ApiModel(description = "评估任务Vo")

@Validated
public class PeEvaluationTaskVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("method")
    @Schema(description = "评估方法", example = "similarity")
    private String method = null;

    @JsonProperty("regular_expression")
    @Schema(description = "正则表达式", example = "^[0-9]+$")
    private String regularExpression = null;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String taskId = null;

    @JsonProperty("test_set_id")
    @Schema(description = "测试集ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String testSetId = null;

    @JsonProperty("test_set_name")
    @Schema(description = "测试集名称", example = "示例名称")
    private String testSetName = null;

    @JsonProperty("case_num")
    @Schema(description = "用例数量", example = "1")
    private Integer caseNum = null;

    @JsonProperty("created_on")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000Z")
    private String createdOn = null;

    @JsonProperty("updated_on")
    @Schema(description = "更新时间", example = "2024-01-01T00:00:00.000Z")
    private String updatedOn = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "running")
    private String status = null;

    @JsonProperty("prompt_list")
    @Schema(description = "提示词列表", example = "")
    @Valid
    @Size(max = 500)
    private List<PePromptVo> promptList = null;

    @JsonProperty("prompt_best_name")
    @Schema(description = "最佳提示词名称", example = "示例名称")
    private String promptBestName = null;

    @JsonProperty("prompt_num")
    @Schema(description = "提示词数量", example = "1")
    private Integer promptNum = null;

    @JsonProperty("best_score")
    @Schema(description = "最佳评分", example = "1")
    private Integer bestScore = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    public String getId() {
        return id;
    }

    public PeEvaluationTaskVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public PeEvaluationTaskVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public PeEvaluationTaskVo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getMethod() {
        return method;
    }

    public PeEvaluationTaskVo setMethod(String method) {
        this.method = method;
        return this;
    }

    public String getRegularExpression() {
        return regularExpression;
    }

    public PeEvaluationTaskVo setRegularExpression(String regularExpression) {
        this.regularExpression = regularExpression;
        return this;
    }

    public String getTaskId() {
        return taskId;
    }

    public PeEvaluationTaskVo setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getTestSetId() {
        return testSetId;
    }

    public PeEvaluationTaskVo setTestSetId(String testSetId) {
        this.testSetId = testSetId;
        return this;
    }

    public String getTestSetName() {
        return testSetName;
    }

    public PeEvaluationTaskVo setTestSetName(String testSetName) {
        this.testSetName = testSetName;
        return this;
    }

    public Integer getCaseNum() {
        return caseNum;
    }

    public PeEvaluationTaskVo setCaseNum(Integer caseNum) {
        this.caseNum = caseNum;
        return this;
    }

    public String getCreatedOn() {
        return createdOn;
    }

    public PeEvaluationTaskVo setCreatedOn(String createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public String getUpdatedOn() {
        return updatedOn;
    }

    public PeEvaluationTaskVo setUpdatedOn(String updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public PeEvaluationTaskVo setStatus(String status) {
        this.status = status;
        return this;
    }

    public List<PePromptVo> getPromptList() {
        return promptList;
    }

    public PeEvaluationTaskVo setPromptList(List<PePromptVo> promptList) {
        this.promptList = promptList;
        return this;
    }

    public String getPromptBestName() {
        return promptBestName;
    }

    public PeEvaluationTaskVo setPromptBestName(String promptBestName) {
        this.promptBestName = promptBestName;
        return this;
    }

    public Integer getPromptNum() {
        return promptNum;
    }

    public PeEvaluationTaskVo setPromptNum(Integer promptNum) {
        this.promptNum = promptNum;
        return this;
    }

    public Integer getBestScore() {
        return bestScore;
    }

    public PeEvaluationTaskVo setBestScore(Integer bestScore) {
        this.bestScore = bestScore;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PeEvaluationTaskVo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PeEvaluationTaskVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    method: ").append(toIndentedString(method)).append("\n");
        sb.append("    regularExpression: ").append(toIndentedString(regularExpression)).append("\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    testSetId: ").append(toIndentedString(testSetId)).append("\n");
        sb.append("    testSetName: ").append(toIndentedString(testSetName)).append("\n");
        sb.append("    caseNum: ").append(toIndentedString(caseNum)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    promptList: ").append(toIndentedString(promptList)).append("\n");
        sb.append("    promptBestName: ").append(toIndentedString(promptBestName)).append("\n");
        sb.append("    promptNum: ").append(toIndentedString(promptNum)).append("\n");
        sb.append("    bestScore: ").append(toIndentedString(bestScore)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
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
        PeEvaluationTaskVo peEvaluationTaskVo = (PeEvaluationTaskVo) o;
        return Objects.equals(this.id, peEvaluationTaskVo.id) && Objects.equals(this.name, peEvaluationTaskVo.name)
            && Objects.equals(this.description, peEvaluationTaskVo.description) && Objects.equals(this.method,
            peEvaluationTaskVo.method) && Objects.equals(this.regularExpression, peEvaluationTaskVo.regularExpression)
            && Objects.equals(this.taskId, peEvaluationTaskVo.taskId) && Objects.equals(this.testSetId,
            peEvaluationTaskVo.testSetId) && Objects.equals(this.testSetName, peEvaluationTaskVo.testSetName)
            && Objects.equals(this.caseNum, peEvaluationTaskVo.caseNum) && Objects.equals(this.createdOn,
            peEvaluationTaskVo.createdOn) && Objects.equals(this.updatedOn, peEvaluationTaskVo.updatedOn)
            && Objects.equals(this.status, peEvaluationTaskVo.status) && Objects.equals(this.promptList,
            peEvaluationTaskVo.promptList) && Objects.equals(this.promptBestName, peEvaluationTaskVo.promptBestName)
            && Objects.equals(this.promptNum, peEvaluationTaskVo.promptNum) && Objects.equals(this.bestScore,
            peEvaluationTaskVo.bestScore) && Objects.equals(this.creator, peEvaluationTaskVo.creator);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, method, regularExpression, taskId, testSetId, testSetName, caseNum,
            createdOn, updatedOn, status, promptList, promptBestName, promptNum, bestScore, creator);
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
}
