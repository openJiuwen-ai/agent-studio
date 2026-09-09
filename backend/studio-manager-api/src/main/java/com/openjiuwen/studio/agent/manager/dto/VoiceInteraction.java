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
 * 语音交互配置。
 */
@ApiModel(description = "语音交互配置。")

@Validated

public class VoiceInteraction implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("language")
    @Schema(description = "语音识别语言代码，如 zh-CN、en-US", example = "zh-CN")
    private String language = null;

    @JsonProperty("timbre")
    @Schema(description = "语音合成音色名称", example = "female-default")
    private String timbre = null;

    @JsonProperty("domain")
    @Schema(description = "语音交互领域标识", example = "general")
    private String domain = null;

    public String getLanguage() {
        return language;
    }

    public VoiceInteraction setLanguage(String language) {
        this.language = language;
        return this;
    }

    public String getTimbre() {
        return timbre;
    }

    public VoiceInteraction setTimbre(String timbre) {
        this.timbre = timbre;
        return this;
    }

    public String getDomain() {
        return domain;
    }

    public VoiceInteraction setDomain(String domain) {
        this.domain = domain;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class VoiceInteraction {\n");

        sb.append("    language: ").append(toIndentedString(language)).append("\n");
        sb.append("    timbre: ").append(toIndentedString(timbre)).append("\n");
        sb.append("    domain: ").append(toIndentedString(domain)).append("\n");
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
        VoiceInteraction voiceInteraction = (VoiceInteraction) o;
        return Objects.equals(this.language, voiceInteraction.language) && Objects.equals(this.timbre,
            voiceInteraction.timbre) && Objects.equals(this.domain, voiceInteraction.domain);
    }

    @Override
    public int hashCode() {
        return Objects.hash(language, timbre, domain);
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
