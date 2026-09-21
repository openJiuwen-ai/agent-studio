/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 扩展参数。
 */
@ApiModel(description = "扩展参数。")

@Validated

public class Extension implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("key")
    @Schema(description = "密钥", example = "example-token-value", required = true)
    @NotBlank
    private String key = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "示例字符串", required = true)
    @NotBlank
    private String value = null;

    @JsonProperty("secretLevel")
    @Schema(description = "密钥level", example = "{}")
    private SecretLevel secretLevel = null;

    public String getKey() {
        return key;
    }

    public Extension setKey(String key) {
        this.key = key;
        return this;
    }

    public String getValue() {
        return value;
    }

    public Extension setValue(String value) {
        this.value = value;
        return this;
    }

    public SecretLevel getSecretLevel() {
        return secretLevel;
    }

    public Extension setSecretLevel(SecretLevel secretLevel) {
        this.secretLevel = secretLevel;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Extension {\n");

        sb.append("    key: ").append(toIndentedString(key)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
        sb.append("    secretLevel: ").append(toIndentedString(secretLevel)).append("\n");
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
        Extension extension = (Extension) o;
        return Objects.equals(this.key, extension.key) && Objects.equals(this.value, extension.value) && Objects.equals(
            this.secretLevel, extension.secretLevel);
    }

    @Override
    public int hashCode() {
        return Objects.hash(key, value, secretLevel);
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
