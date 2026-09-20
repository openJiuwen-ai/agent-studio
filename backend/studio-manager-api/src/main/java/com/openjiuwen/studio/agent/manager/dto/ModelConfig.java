/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 大模型参数配置。
 */
@ApiModel(description = "大模型参数配置。")

@Validated

public class ModelConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("top_p")
    @Schema(description = "Top-P 采样参数，控制生成多样性，取值范围 0~1", example = "1.0")
    private Double topP = 1.0d;

    @JsonProperty("temperature")
    @Schema(description = "Temperature 采样参数，控制生成随机性，取值范围 0~2", example = "0.0")
    private Double temperature = 0.0d;

    @JsonProperty("history_size")
    @Schema(description = "对话历史轮次数量", example = "20")
    private Integer historySize = 20;

    @JsonProperty("output_format")
    @Schema(description = "输出格式，可选值：text、json", example = "text")
    private String outputFormat = "text";

    @JsonProperty("max_tokens")
    @Schema(description = "生成最大 token 数量", example = "4096")
    private Integer maxTokens = 4096;

    @JsonProperty("frequency_penalty")
    @Schema(description = "频率惩罚参数，降低已出现 token 的重复率，取值范围 -2~2", example = "0.0")
    private Double frequencyPenalty = 0.0d;

    @JsonProperty("enable_thinking")
    @Schema(description = "是否启用思考链（Chain-of-Thought）", example = "true")
    private Boolean enableThinking = true;

    public Double getTopP() {
        return topP;
    }

    public ModelConfig setTopP(Double topP) {
        this.topP = topP;
        return this;
    }

    public Double getTemperature() {
        return temperature;
    }

    public ModelConfig setTemperature(Double temperature) {
        this.temperature = temperature;
        return this;
    }

    public Integer getHistorySize() {
        return historySize;
    }

    public ModelConfig setHistorySize(Integer historySize) {
        this.historySize = historySize;
        return this;
    }

    public String getOutputFormat() {
        return outputFormat;
    }

    public ModelConfig setOutputFormat(String outputFormat) {
        this.outputFormat = outputFormat;
        return this;
    }

    public Integer getMaxTokens() {
        return maxTokens;
    }

    public ModelConfig setMaxTokens(Integer maxTokens) {
        this.maxTokens = maxTokens;
        return this;
    }

    public Double getFrequencyPenalty() {
        return frequencyPenalty;
    }

    public ModelConfig setFrequencyPenalty(Double frequencyPenalty) {
        this.frequencyPenalty = frequencyPenalty;
        return this;
    }

    public ModelConfig setEnableThinking(Boolean enableThinking) {
        this.enableThinking = enableThinking;
        return this;
    }

    public Boolean isEnableThinking() {
        return enableThinking;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelConfig {\n");

        sb.append("    topP: ").append(toIndentedString(topP)).append("\n");
        sb.append("    temperature: ").append(toIndentedString(temperature)).append("\n");
        sb.append("    historySize: ").append(toIndentedString(historySize)).append("\n");
        sb.append("    outputFormat: ").append(toIndentedString(outputFormat)).append("\n");
        sb.append("    maxTokens: ").append(toIndentedString(maxTokens)).append("\n");
        sb.append("    frequencyPenalty: ").append(toIndentedString(frequencyPenalty)).append("\n");
        sb.append("    enableThinking: ").append(toIndentedString(enableThinking)).append("\n");
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
        ModelConfig modelConfig = (ModelConfig) o;
        return Objects.equals(this.topP, modelConfig.topP) && Objects.equals(this.temperature, modelConfig.temperature)
            && Objects.equals(this.historySize, modelConfig.historySize) && Objects.equals(this.outputFormat,
            modelConfig.outputFormat) && Objects.equals(this.maxTokens, modelConfig.maxTokens) && Objects.equals(
            this.frequencyPenalty, modelConfig.frequencyPenalty) && Objects.equals(this.enableThinking,
            modelConfig.enableThinking);
    }

    @Override
    public int hashCode() {
        return Objects.hash(topP, temperature, historySize, outputFormat, maxTokens, frequencyPenalty, enableThinking);
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
