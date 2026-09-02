/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

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
 * 用户画像信息。
 */
@ApiModel(description = "用户画像信息。")

@Validated

public class MemoryUserProfileIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("enable")
    @Schema(description = "enable", example = "true")
    private Boolean enable = null;

    @JsonProperty("extractConfig")
    @Schema(description = "extract配置", example = "{}")
    @Valid
    private MemoryUserProfileExtractConfigIR extractConfig = null;

    @JsonProperty("topics")
    @Schema(description = "主题列表", example = "[]")
    @Valid
    @Size()
    private List<MemoryUserProfileTopicInfoIR> topics = null;

    public MemoryUserProfileIR setEnable(Boolean enable) {
        this.enable = enable;
        return this;
    }

    public Boolean isEnable() {
        return enable;
    }

    public MemoryUserProfileExtractConfigIR getExtractConfig() {
        return extractConfig;
    }

    public MemoryUserProfileIR setExtractConfig(MemoryUserProfileExtractConfigIR extractConfig) {
        this.extractConfig = extractConfig;
        return this;
    }

    public List<MemoryUserProfileTopicInfoIR> getTopics() {
        return topics;
    }

    public MemoryUserProfileIR setTopics(List<MemoryUserProfileTopicInfoIR> topics) {
        this.topics = topics;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryUserProfileIR {\n");

        sb.append("    enable: ").append(toIndentedString(enable)).append("\n");
        sb.append("    extractConfig: ").append(toIndentedString(extractConfig)).append("\n");
        sb.append("    topics: ").append(toIndentedString(topics)).append("\n");
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
        MemoryUserProfileIR memoryUserProfileIR = (MemoryUserProfileIR) o;
        return Objects.equals(this.enable, memoryUserProfileIR.enable) && Objects.equals(this.extractConfig,
            memoryUserProfileIR.extractConfig) && Objects.equals(this.topics, memoryUserProfileIR.topics);
    }

    @Override
    public int hashCode() {
        return Objects.hash(enable, extractConfig, topics);
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
