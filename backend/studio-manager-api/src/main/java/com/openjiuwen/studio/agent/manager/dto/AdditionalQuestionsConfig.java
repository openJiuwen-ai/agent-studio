/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 追问配置。
 */
@ApiModel(description = "追问配置。")

@Validated

public class AdditionalQuestionsConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("enable")
    @Schema(description = "是否启用追问", example = "true", required = true)
    @NotNull
    private Boolean enable = null;

    @JsonProperty("rounds")
    @Schema(description = "追问轮数", example = "3")
    private Integer rounds = null;

    @JsonProperty("prompt")
    @Schema(description = "追问提示词", example = "请根据用户回答继续追问")
    @Length(max = 512)
    private String prompt = null;

    public AdditionalQuestionsConfig setEnable(Boolean enable) {
        this.enable = enable;
        return this;
    }

    public Boolean isEnable() {
        return enable;
    }

    public Integer getRounds() {
        return rounds;
    }

    public AdditionalQuestionsConfig setRounds(Integer rounds) {
        this.rounds = rounds;
        return this;
    }

    public String getPrompt() {
        return prompt;
    }

    public AdditionalQuestionsConfig setPrompt(String prompt) {
        this.prompt = prompt;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AdditionalQuestionsConfig {\n");

        sb.append("    enable: ").append(toIndentedString(enable)).append("\n");
        sb.append("    rounds: ").append(toIndentedString(rounds)).append("\n");
        sb.append("    prompt: ").append(toIndentedString(prompt)).append("\n");
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
        AdditionalQuestionsConfig additionalQuestionsConfig = (AdditionalQuestionsConfig) o;
        return Objects.equals(this.enable, additionalQuestionsConfig.enable) && Objects.equals(this.rounds,
            additionalQuestionsConfig.rounds) && Objects.equals(this.prompt, additionalQuestionsConfig.prompt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(enable, rounds, prompt);
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
