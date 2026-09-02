/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 调优所需的prompt信息
 */
@ApiModel(description = "调优所需的prompt信息")

@Validated
public class PromptBody implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "PLAYGROUND", required = true)
    @Pattern(regexp = "PLAYGROUND|EXPERIMENT|CANDIDATE|HORIZONTAL|NO_SOURCE|PRESET")
    @NotBlank
    private String source = null;

    @JsonProperty("question")
    @Schema(description = "问题", example = "示例问题", required = true)
    @NotBlank
    @Length(max = 10000)
    private String question = null;

    @JsonProperty("variables")
    @Schema(description = "变量", example = "")
    @Valid
    @Size(max = 20)
    private List<VariableDto> variables = null;

    @JsonProperty("model")
    @Schema(description = "模型名称", example = "gpt-4", required = true)
    @NotBlank
    @Length(max = 1000)
    private String model = null;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "", required = true)
    @Valid
    @NotNull
    private ModelConfig modelConfig = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "LLM")
    private String modelType = null;

    @JsonProperty("third_model_type")
    @Schema(description = "第三方模型类型", example = "openai")
    private String thirdModelType = null;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String fileId = null;

    public String getTaskId() {
        return taskId;
    }

    public PromptBody setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getSource() {
        return source;
    }

    public PromptBody setSource(String source) {
        this.source = source;
        return this;
    }

    public String getQuestion() {
        return question;
    }

    public PromptBody setQuestion(String question) {
        this.question = question;
        return this;
    }

    public List<VariableDto> getVariables() {
        return variables;
    }

    public PromptBody setVariables(List<VariableDto> variables) {
        this.variables = variables;
        return this;
    }

    public String getModel() {
        return model;
    }

    public PromptBody setModel(String model) {
        this.model = model;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public PromptBody setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public PromptBody setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getThirdModelType() {
        return thirdModelType;
    }

    public PromptBody setThirdModelType(String thirdModelType) {
        this.thirdModelType = thirdModelType;
        return this;
    }

    public String getFileId() {
        return fileId;
    }

    public PromptBody setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PromptBody {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    question: ").append(toIndentedString(question)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    thirdModelType: ").append(toIndentedString(thirdModelType)).append("\n");
        sb.append("    fileId: ").append(toIndentedString(fileId)).append("\n");
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
        PromptBody promptBody = (PromptBody) o;
        return Objects.equals(this.taskId, promptBody.taskId) && Objects.equals(this.source, promptBody.source)
            && Objects.equals(this.question, promptBody.question) && Objects.equals(this.variables,
            promptBody.variables) && Objects.equals(this.model, promptBody.model) && Objects.equals(this.modelConfig,
            promptBody.modelConfig) && Objects.equals(this.modelType, promptBody.modelType) && Objects.equals(
            this.thirdModelType, promptBody.thirdModelType) && Objects.equals(this.fileId, promptBody.fileId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId, source, question, variables, model, modelConfig, modelType, thirdModelType, fileId);
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
