/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 长期记忆抽取策略
 */
@ApiModel(description = "长期记忆抽取策略")

@Validated

public class LongTermMemoryStrategy implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "类型", example = "STRING")
    private TypeEnum type = null;

    @JsonProperty("prompt")
    @Schema(description = "提示词", example = "请输入...")
    @Length(max = 1000)
    private String prompt = null;

    public TypeEnum getType() {
        return type;
    }

    public LongTermMemoryStrategy setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public String getPrompt() {
        return prompt;
    }

    public LongTermMemoryStrategy setPrompt(String prompt) {
        this.prompt = prompt;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class LongTermMemoryStrategy {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        LongTermMemoryStrategy longTermMemoryStrategy = (LongTermMemoryStrategy) o;
        return Objects.equals(this.type, longTermMemoryStrategy.type) && Objects.equals(this.prompt,
            longTermMemoryStrategy.prompt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, prompt);
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

    /**
     * 策略类型，semantic_memory-语义记忆，user_profile-用户偏好
     */
    public enum TypeEnum {
        SEMANTIC_MEMORY("semantic_memory"),

        USER_PROFILE("user_profile");

        private String value;

        TypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static TypeEnum fromValue(String text) {
            for (TypeEnum b : TypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
