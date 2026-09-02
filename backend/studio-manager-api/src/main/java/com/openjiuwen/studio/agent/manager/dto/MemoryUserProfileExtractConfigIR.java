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
 * 用户画像的提取规则配置。
 */
@ApiModel(description = "用户画像的提取规则配置。")

@Validated

public class MemoryUserProfileExtractConfigIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("maxChatTurn")
    @Schema(description = "maxchatturn", example = "10")
    private Integer maxChatTurn = null;

    @JsonProperty("timeWindow")
    @Schema(description = "时间window", example = "1")
    private Integer timeWindow = null;

    public Integer getMaxChatTurn() {
        return maxChatTurn;
    }

    public MemoryUserProfileExtractConfigIR setMaxChatTurn(Integer maxChatTurn) {
        this.maxChatTurn = maxChatTurn;
        return this;
    }

    public Integer getTimeWindow() {
        return timeWindow;
    }

    public MemoryUserProfileExtractConfigIR setTimeWindow(Integer timeWindow) {
        this.timeWindow = timeWindow;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemoryUserProfileExtractConfigIR {\n");

        sb.append("    maxChatTurn: ").append(toIndentedString(maxChatTurn)).append("\n");
        sb.append("    timeWindow: ").append(toIndentedString(timeWindow)).append("\n");
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
        MemoryUserProfileExtractConfigIR memoryUserProfileExtractConfigIR = (MemoryUserProfileExtractConfigIR) o;
        return Objects.equals(this.maxChatTurn, memoryUserProfileExtractConfigIR.maxChatTurn) && Objects.equals(
            this.timeWindow, memoryUserProfileExtractConfigIR.timeWindow);
    }

    @Override
    public int hashCode() {
        return Objects.hash(maxChatTurn, timeWindow);
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
