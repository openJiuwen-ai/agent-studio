/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 删除校验参数返回体
 */
@ApiModel(description = "删除校验参数返回体")

@Validated
public class TaskConfirmVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("eval_task_num")
    @Schema(description = "评估任务数量", example = "1")
    private Integer evalTaskNum = null;

    @JsonProperty("variable_num")
    @Schema(description = "变量数量", example = "1")
    private Integer variableNum = null;

    @JsonProperty("prompt_num")
    @Schema(description = "提示词数量", example = "1")
    private Integer promptNum = null;

    @JsonProperty("history_prompt_num")
    @Schema(description = "history提示词数量", example = "1")
    private Integer historyPromptNum = null;

    @JsonProperty("executing_eval_task_num")
    @Schema(description = "executing评估任务数量", example = "1")
    private Integer executingEvalTaskNum = null;

    public Integer getEvalTaskNum() {
        return evalTaskNum;
    }

    public TaskConfirmVo setEvalTaskNum(Integer evalTaskNum) {
        this.evalTaskNum = evalTaskNum;
        return this;
    }

    public Integer getVariableNum() {
        return variableNum;
    }

    public TaskConfirmVo setVariableNum(Integer variableNum) {
        this.variableNum = variableNum;
        return this;
    }

    public Integer getPromptNum() {
        return promptNum;
    }

    public TaskConfirmVo setPromptNum(Integer promptNum) {
        this.promptNum = promptNum;
        return this;
    }

    public Integer getHistoryPromptNum() {
        return historyPromptNum;
    }

    public TaskConfirmVo setHistoryPromptNum(Integer historyPromptNum) {
        this.historyPromptNum = historyPromptNum;
        return this;
    }

    public Integer getExecutingEvalTaskNum() {
        return executingEvalTaskNum;
    }

    public TaskConfirmVo setExecutingEvalTaskNum(Integer executingEvalTaskNum) {
        this.executingEvalTaskNum = executingEvalTaskNum;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TaskConfirmVo {\n");
        sb.append("    evalTaskNum: ").append(toIndentedString(evalTaskNum)).append("\n");
        sb.append("    variableNum: ").append(toIndentedString(variableNum)).append("\n");
        sb.append("    promptNum: ").append(toIndentedString(promptNum)).append("\n");
        sb.append("    historyPromptNum: ").append(toIndentedString(historyPromptNum)).append("\n");
        sb.append("    executingEvalTaskNum: ").append(toIndentedString(executingEvalTaskNum)).append("\n");
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
        TaskConfirmVo taskConfirmVo = (TaskConfirmVo) o;
        return Objects.equals(this.evalTaskNum, taskConfirmVo.evalTaskNum) && Objects.equals(this.variableNum,
            taskConfirmVo.variableNum) && Objects.equals(this.promptNum, taskConfirmVo.promptNum) && Objects.equals(
            this.historyPromptNum, taskConfirmVo.historyPromptNum) && Objects.equals(this.executingEvalTaskNum,
            taskConfirmVo.executingEvalTaskNum);
    }

    @Override
    public int hashCode() {
        return Objects.hash(evalTaskNum, variableNum, promptNum, historyPromptNum, executingEvalTaskNum);
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
