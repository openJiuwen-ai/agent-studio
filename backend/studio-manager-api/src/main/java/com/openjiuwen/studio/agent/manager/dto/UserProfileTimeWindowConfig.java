/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 用户画像提取的时间窗配置。
 */
@ApiModel(description = "用户画像提取的时间窗配置。")

@Validated

public class UserProfileTimeWindowConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("time_span")
    @Schema(description = "时间", example = "1")
    @Range(min = 5L, max = 60L)
    private Integer timeSpan = null;

    @JsonProperty("conversation_round")
    @Schema(description = "会话", example = "1")
    @Range(min = 1L, max = 30L)
    private Integer conversationRound = null;

    public Integer getTimeSpan() {
        return timeSpan;
    }

    public UserProfileTimeWindowConfig setTimeSpan(Integer timeSpan) {
        this.timeSpan = timeSpan;
        return this;
    }

    public Integer getConversationRound() {
        return conversationRound;
    }

    public UserProfileTimeWindowConfig setConversationRound(Integer conversationRound) {
        this.conversationRound = conversationRound;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UserProfileTimeWindowConfig {\n");

        sb.append("    timeSpan: ").append(toIndentedString(timeSpan)).append("\n");
        sb.append("    conversationRound: ").append(toIndentedString(conversationRound)).append("\n");
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
        UserProfileTimeWindowConfig userProfileTimeWindowConfig = (UserProfileTimeWindowConfig) o;
        return Objects.equals(this.timeSpan, userProfileTimeWindowConfig.timeSpan) && Objects.equals(
            this.conversationRound, userProfileTimeWindowConfig.conversationRound);
    }

    @Override
    public int hashCode() {
        return Objects.hash(timeSpan, conversationRound);
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
