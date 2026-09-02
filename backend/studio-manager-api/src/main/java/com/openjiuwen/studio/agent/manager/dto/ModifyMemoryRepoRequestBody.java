/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 修改记忆库请求体
 */
@ApiModel(description = "修改记忆库请求体")

@Validated

public class ModifyMemoryRepoRequestBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "记忆库名称", example = "我的记忆库", required = true)
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$")
    @NotBlank
    @Length(min = 1, max = 50)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "记忆库描述", example = "用于存储用户对话记忆")
    @Length(max = 1000)
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "记忆库图标", example = "memory-icon")
    private String icon = null;

    @JsonProperty("long_term_memory_strategies")
    @Schema(description = "长期记忆策略列表", example = "[{\"type\":\"summary\"}]")
    @Valid
    @Size(max = 200)
    private List<LongTermMemoryStrategy> longTermMemoryStrategies = null;

    @JsonProperty("conversation_round")
    @Schema(description = "对话轮次", example = "10")
    private Integer conversationRound = null;

    @JsonProperty("time_span")
    @Schema(description = "时间跨度（秒）", example = "3600")
    private Integer timeSpan = null;

    public String getName() {
        return name;
    }

    public ModifyMemoryRepoRequestBody setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ModifyMemoryRepoRequestBody setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ModifyMemoryRepoRequestBody setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<LongTermMemoryStrategy> getLongTermMemoryStrategies() {
        return longTermMemoryStrategies;
    }

    public ModifyMemoryRepoRequestBody setLongTermMemoryStrategies(
        List<LongTermMemoryStrategy> longTermMemoryStrategies) {
        this.longTermMemoryStrategies = longTermMemoryStrategies;
        return this;
    }

    public Integer getConversationRound() {
        return conversationRound;
    }

    public ModifyMemoryRepoRequestBody setConversationRound(Integer conversationRound) {
        this.conversationRound = conversationRound;
        return this;
    }

    public Integer getTimeSpan() {
        return timeSpan;
    }

    public ModifyMemoryRepoRequestBody setTimeSpan(Integer timeSpan) {
        this.timeSpan = timeSpan;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModifyMemoryRepoRequestBody {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    longTermMemoryStrategies: ").append(toIndentedString(longTermMemoryStrategies)).append("\n");
        sb.append("    conversationRound: ").append(toIndentedString(conversationRound)).append("\n");
        sb.append("    timeSpan: ").append(toIndentedString(timeSpan)).append("\n");
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
        ModifyMemoryRepoRequestBody modifyMemoryRepoRequestBody = (ModifyMemoryRepoRequestBody) o;
        return Objects.equals(this.name, modifyMemoryRepoRequestBody.name) && Objects.equals(this.description,
            modifyMemoryRepoRequestBody.description) && Objects.equals(this.icon, modifyMemoryRepoRequestBody.icon)
            && Objects.equals(this.longTermMemoryStrategies, modifyMemoryRepoRequestBody.longTermMemoryStrategies)
            && Objects.equals(this.conversationRound, modifyMemoryRepoRequestBody.conversationRound)
            && Objects.equals(this.timeSpan, modifyMemoryRepoRequestBody.timeSpan);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description, icon, longTermMemoryStrategies, conversationRound, timeSpan);
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
