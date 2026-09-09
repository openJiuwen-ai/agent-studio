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
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 优化任务DTO
 */
@ApiModel(description = "优化任务DTO")

@Validated
public class PeOptimizationTaskDto implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("task_id")
    @Schema(description = "任务ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String taskId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z][\\u4e00-\\u9fa5\\w-]{0,32}[\\u4e00-\\u9fa5a-zA-Z0-9]$")
    @NotBlank
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述", required = true)
    @NotBlank
    @Length(max = 100)
    private String description = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "text")
    private String type = null;

    @JsonProperty("prompt_ids")
    @Schema(description = "提示词ID列表", example = "", required = true)
    @Valid
    @NotNull
    @Size(max = 9)
    private List<@Pattern(
        regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$") @Length() String> promptIds
        = new ArrayList<String>();

    @JsonProperty("test_set_id")
    @Schema(description = "测试集ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890", required = true)
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    @NotBlank
    private String testSetId = null;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "")
    @Valid
    private ModelConfig modelConfig = null;

    @JsonProperty("assistant_config")
    @Schema(description = "助手配置", example = "")
    @Valid
    private ModelConfig assistantConfig = null;

    @JsonProperty("num_iter")
    @Schema(description = "迭代次数", example = "3", required = true)
    @NotNull
    @Range(min = 1L, max = 5L)
    private Integer numIter = 3;

    public String getTaskId() {
        return taskId;
    }

    public PeOptimizationTaskDto setTaskId(String taskId) {
        this.taskId = taskId;
        return this;
    }

    public String getName() {
        return name;
    }

    public PeOptimizationTaskDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public PeOptimizationTaskDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getType() {
        return type;
    }

    public PeOptimizationTaskDto setType(String type) {
        this.type = type;
        return this;
    }

    public List<String> getPromptIds() {
        return promptIds;
    }

    public PeOptimizationTaskDto setPromptIds(List<String> promptIds) {
        this.promptIds = promptIds;
        return this;
    }

    public String getTestSetId() {
        return testSetId;
    }

    public PeOptimizationTaskDto setTestSetId(String testSetId) {
        this.testSetId = testSetId;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public PeOptimizationTaskDto setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public ModelConfig getAssistantConfig() {
        return assistantConfig;
    }

    public PeOptimizationTaskDto setAssistantConfig(ModelConfig assistantConfig) {
        this.assistantConfig = assistantConfig;
        return this;
    }

    public Integer getNumIter() {
        return numIter;
    }

    public PeOptimizationTaskDto setNumIter(Integer numIter) {
        this.numIter = numIter;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PeOptimizationTaskDto {\n");
        sb.append("    taskId: ").append(toIndentedString(taskId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    promptIds: ").append(toIndentedString(promptIds)).append("\n");
        sb.append("    testSetId: ").append(toIndentedString(testSetId)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    assistantConfig: ").append(toIndentedString(assistantConfig)).append("\n");
        sb.append("    numIter: ").append(toIndentedString(numIter)).append("\n");
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
        PeOptimizationTaskDto peOptimizationTaskDto = (PeOptimizationTaskDto) o;
        return Objects.equals(this.taskId, peOptimizationTaskDto.taskId) && Objects.equals(this.name,
            peOptimizationTaskDto.name) && Objects.equals(this.description, peOptimizationTaskDto.description)
            && Objects.equals(this.type, peOptimizationTaskDto.type) && Objects.equals(this.promptIds,
            peOptimizationTaskDto.promptIds) && Objects.equals(this.testSetId, peOptimizationTaskDto.testSetId)
            && Objects.equals(this.modelConfig, peOptimizationTaskDto.modelConfig) && Objects.equals(
            this.assistantConfig, peOptimizationTaskDto.assistantConfig) && Objects.equals(this.numIter,
            peOptimizationTaskDto.numIter);
    }

    @Override
    public int hashCode() {
        return Objects.hash(taskId, name, description, type, promptIds, testSetId, modelConfig, assistantConfig,
            numIter);
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
