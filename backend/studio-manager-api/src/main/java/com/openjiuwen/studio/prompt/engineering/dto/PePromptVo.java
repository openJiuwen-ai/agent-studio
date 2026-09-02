/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * PePromptVo
 */

@Validated
public class PePromptVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "唯一标识", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "示例内容")
    private String content = null;

    @JsonProperty("answer")
    @Schema(description = "答案", example = "示例答案")
    private String answer = null;

    @JsonProperty("model")
    @Schema(description = "模型名称", example = "gpt-4")
    private String model = null;

    @JsonProperty("manual_score")
    @Schema(description = "人工评分", example = "4")
    private Integer manualScore = null;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "")
    @Valid
    private ModelConfig modelConfig = null;

    @JsonProperty("evaluation_avg")
    @Schema(description = "平均评分", example = "1")
    private Integer evaluationAvg = null;

    @JsonProperty("variable_vo")
    @Schema(description = "变量列表", example = "")
    @Valid
    @Size(max = 20)
    private List<VariableVo> variableVo = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "2024-01-01T00:00:00.000Z")
    private String updater = null;

    @JsonProperty("created_on")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000Z")
    private Date createdOn = null;

    @JsonProperty("updated_on")
    @Schema(description = "更新时间", example = "2024-01-01T00:00:00.000Z")
    private Date updatedOn = null;

    @JsonProperty("file_info")
    @Schema(description = "文件信息", example = "")
    @Valid
    private FileInfoVo fileInfo = null;

    public String getId() {
        return id;
    }

    public PePromptVo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public PePromptVo setName(String name) {
        this.name = name;
        return this;
    }

    public String getContent() {
        return content;
    }

    public PePromptVo setContent(String content) {
        this.content = content;
        return this;
    }

    public String getAnswer() {
        return answer;
    }

    public PePromptVo setAnswer(String answer) {
        this.answer = answer;
        return this;
    }

    public String getModel() {
        return model;
    }

    public PePromptVo setModel(String model) {
        this.model = model;
        return this;
    }

    public Integer getManualScore() {
        return manualScore;
    }

    public PePromptVo setManualScore(Integer manualScore) {
        this.manualScore = manualScore;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public PePromptVo setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    public Integer getEvaluationAvg() {
        return evaluationAvg;
    }

    public PePromptVo setEvaluationAvg(Integer evaluationAvg) {
        this.evaluationAvg = evaluationAvg;
        return this;
    }

    public List<VariableVo> getVariableVo() {
        return variableVo;
    }

    public PePromptVo setVariableVo(List<VariableVo> variableVo) {
        this.variableVo = variableVo;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public PePromptVo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public PePromptVo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public Date getCreatedOn() {
        return createdOn;
    }

    public PePromptVo setCreatedOn(Date createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public Date getUpdatedOn() {
        return updatedOn;
    }

    public PePromptVo setUpdatedOn(Date updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public FileInfoVo getFileInfo() {
        return fileInfo;
    }

    public PePromptVo setFileInfo(FileInfoVo fileInfo) {
        this.fileInfo = fileInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptVo {\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    answer: ").append(toIndentedString(answer)).append("\n");
        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    manualScore: ").append(toIndentedString(manualScore)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
        sb.append("    evaluationAvg: ").append(toIndentedString(evaluationAvg)).append("\n");
        sb.append("    variableVo: ").append(toIndentedString(variableVo)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    fileInfo: ").append(toIndentedString(fileInfo)).append("\n");
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
        PePromptVo pePromptVo = (PePromptVo) o;
        return Objects.equals(this.id, pePromptVo.id) && Objects.equals(this.name, pePromptVo.name) && Objects.equals(
            this.content, pePromptVo.content) && Objects.equals(this.answer, pePromptVo.answer) && Objects.equals(
            this.model, pePromptVo.model) && Objects.equals(this.manualScore, pePromptVo.manualScore) && Objects.equals(
            this.modelConfig, pePromptVo.modelConfig) && Objects.equals(this.evaluationAvg, pePromptVo.evaluationAvg)
            && Objects.equals(this.variableVo, pePromptVo.variableVo) && Objects.equals(this.creator,
            pePromptVo.creator) && Objects.equals(this.updater, pePromptVo.updater) && Objects.equals(this.createdOn,
            pePromptVo.createdOn) && Objects.equals(this.updatedOn, pePromptVo.updatedOn) && Objects.equals(
            this.fileInfo, pePromptVo.fileInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, content, answer, model, manualScore, modelConfig, evaluationAvg, variableVo,
            creator, updater, createdOn, updatedOn, fileInfo);
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
