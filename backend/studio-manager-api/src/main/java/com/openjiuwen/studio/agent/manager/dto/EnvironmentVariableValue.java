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
 * 环境变量值
 */
@ApiModel(description = "环境变量值")

@Validated

public class EnvironmentVariableValue implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "类型", example = "STRING")
    private TypeEnum type = null;

    @JsonProperty("content")
    @Schema(description = "内容", example = "内容示例")
    @Length(max = 2000)
    private String content = null;

    @JsonProperty("secret")
    @Schema(description = "是否为密钥", example = "true")
    private Boolean secret = null;

    public TypeEnum getType() {
        return type;
    }

    public EnvironmentVariableValue setType(TypeEnum type) {
        this.type = type;
        return this;
    }

    public String getContent() {
        return content;
    }

    public EnvironmentVariableValue setContent(String content) {
        this.content = content;
        return this;
    }

    public EnvironmentVariableValue setSecret(Boolean secret) {
        this.secret = secret;
        return this;
    }

    public Boolean isSecret() {
        return secret;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentVariableValue {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    secret: ").append(toIndentedString(secret)).append("\n");
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
        EnvironmentVariableValue environmentVariableValue = (EnvironmentVariableValue) o;
        return Objects.equals(this.type, environmentVariableValue.type) && Objects.equals(this.content,
            environmentVariableValue.content) && Objects.equals(this.secret, environmentVariableValue.secret);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, content, secret);
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
     * Gets or Sets type
     */
    public enum TypeEnum {
        STRING("string"),

        NUMBER("number");

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
