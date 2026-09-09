/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * This is the result of each prompt
 */
@ApiModel(description = "This is the result of each prompt")

@Validated
public class PeEvaluationResultVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("prompt_id")
    @Schema(description = "提示词ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String promptId = null;

    @JsonProperty("prompt_name")
    @Schema(description = "提示词名称", example = "示例名称")
    @Length(max = 512)
    private String promptName = null;

    @JsonProperty("generate_result")
    @Schema(description = "generate结果", example = "示例文本")
    @Length(max = 512)
    private String generateResult = null;

    @JsonProperty("eval_failed_reason")
    @Schema(description = "评估FailedReason", example = "示例文本")
    @Length(max = 255)
    private String evalFailedReason = null;

    @JsonProperty("eval_result")
    @Schema(description = "评估结果", example = "")
    @Valid
    private PeEvalResult evalResult = null;

    public String getId() {
        return id;
    }

    public PeEvaluationResultVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getPromptId() {
        return promptId;
    }

    public PeEvaluationResultVo setPromptId(String promptId) {
        this.promptId = promptId;
        return this;
    }

    public String getPromptName() {
        return promptName;
    }

    public PeEvaluationResultVo setPromptName(String promptName) {
        this.promptName = promptName;
        return this;
    }

    public String getGenerateResult() {
        return generateResult;
    }

    public PeEvaluationResultVo setGenerateResult(String generateResult) {
        this.generateResult = generateResult;
        return this;
    }

    public String getEvalFailedReason() {
        return evalFailedReason;
    }

    public PeEvaluationResultVo setEvalFailedReason(String evalFailedReason) {
        this.evalFailedReason = evalFailedReason;
        return this;
    }

    public PeEvalResult getEvalResult() {
        return evalResult;
    }

    public PeEvaluationResultVo setEvalResult(PeEvalResult evalResult) {
        this.evalResult = evalResult;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PeEvaluationResultVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    promptId: ").append(toIndentedString(promptId)).append("\n");
        sb.append("    promptName: ").append(toIndentedString(promptName)).append("\n");
        sb.append("    generateResult: ").append(toIndentedString(generateResult)).append("\n");
        sb.append("    evalFailedReason: ").append(toIndentedString(evalFailedReason)).append("\n");
        sb.append("    evalResult: ").append(toIndentedString(evalResult)).append("\n");
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
        PeEvaluationResultVo peEvaluationResultVo = (PeEvaluationResultVo) o;
        return Objects.equals(this.id, peEvaluationResultVo.id) && Objects.equals(this.promptId,
            peEvaluationResultVo.promptId) && Objects.equals(this.promptName, peEvaluationResultVo.promptName)
            && Objects.equals(this.generateResult, peEvaluationResultVo.generateResult) && Objects.equals(
            this.evalFailedReason, peEvaluationResultVo.evalFailedReason) && Objects.equals(this.evalResult,
            peEvaluationResultVo.evalResult);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, promptId, promptName, generateResult, evalFailedReason, evalResult);
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
