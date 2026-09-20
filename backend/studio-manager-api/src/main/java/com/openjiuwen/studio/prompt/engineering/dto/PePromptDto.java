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
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 候选模板创建入参
 */
@ApiModel(description = "候选模板创建入参")

@Validated
public class PePromptDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,18}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    @NotBlank
    @Length(max = 255)
    private String name = null;

    @JsonProperty("model")
    @Schema(description = "模型名称", example = "gpt-4", required = true)
    @NotBlank
    @Length(max = 128)
    private String model = null;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "", required = true)
    @Valid
    @NotNull
    private ModelConfig modelConfig = null;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("source")
    @Schema(description = "来源", example = "PLAYGROUND", required = true)
    @NotBlank
    private String source = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "1", required = true)
    @NotNull
    private Integer type = null;

    @JsonProperty("question")
    @Schema(description = "问题", example = "示例问题", required = true)
    @NotBlank
    private String question = null;

    @JsonProperty("answer")
    @Schema(description = "答案", example = "示例答案")
    private String answer = null;

    @JsonProperty("variables")
    @Schema(description = "变量", example = "")
    @Valid
    @Size(max = 20)
    private List<VariableDto> variables = null;

    @JsonProperty("manual_score")
    @Schema(description = "人工评分", example = "4", required = true)
    @NotNull
    @Range(min = 0L, max = 5L)
    private Integer manualScore = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "2024-01-01T00:00:00.000Z")
    private String updater = null;

    @JsonProperty("file_id")
    @Schema(description = "文件ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String fileId = null;

    public String getId() {
        return id;
    }

    public PePromptDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public PePromptDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getModel() {
        return model;
    }

    public PePromptDto setModel(String model) {
        this.model = model;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public PePromptDto setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public String getTaskId() {
        return taskId;
    }

    public PePromptDto setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getSource() {
        return source;
    }

    public PePromptDto setSource(String source) {
        this.source = source;
        return this;
    }

    public Integer getType() {
        return type;
    }

    public PePromptDto setType(Integer type) {
        this.type = type;
        return this;
    }

    public String getQuestion() {
        return question;
    }

    public PePromptDto setQuestion(String question) {
        this.question = question;
        return this;
    }

    public String getAnswer() {
        return answer;
    }

    public PePromptDto setAnswer(String answer) {
        this.answer = answer;
        return this;
    }

    public List<VariableDto> getVariables() {
        return variables;
    }

    public PePromptDto setVariables(List<VariableDto> variables) {
        this.variables = variables;
        return this;
    }

    public Integer getManualScore() {
        return manualScore;
    }

    public PePromptDto setManualScore(Integer manualScore) {
        this.manualScore = manualScore;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PePromptDto setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public PePromptDto setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public String getFileId() {
        return fileId;
    }

    public PePromptDto setFileId(String fileId) {
        this.fileId = fileId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptDto {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    source: ").append(toIndentedString(source)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    question: ").append(toIndentedString(question)).append("\n");
        sb.append("    answer: ").append(toIndentedString(answer)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    manualScore: ").append(toIndentedString(manualScore)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
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
        PePromptDto pePromptDto = (PePromptDto) o;
        return Objects.equals(this.id, pePromptDto.id) && Objects.equals(this.name, pePromptDto.name) && Objects.equals(
            this.model, pePromptDto.model) && Objects.equals(this.modelConfig, pePromptDto.modelConfig)
            && Objects.equals(this.taskId, pePromptDto.taskId) && Objects.equals(this.source, pePromptDto.source)
            && Objects.equals(this.type, pePromptDto.type) && Objects.equals(this.question, pePromptDto.question)
            && Objects.equals(this.answer, pePromptDto.answer) && Objects.equals(this.variables, pePromptDto.variables)
            && Objects.equals(this.manualScore, pePromptDto.manualScore) && Objects.equals(this.creator,
            pePromptDto.creator) && Objects.equals(this.updater, pePromptDto.updater) && Objects.equals(this.fileId,
            pePromptDto.fileId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, model, modelConfig, taskId, source, type, question, answer, variables,
            manualScore, creator, updater, fileId);
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
