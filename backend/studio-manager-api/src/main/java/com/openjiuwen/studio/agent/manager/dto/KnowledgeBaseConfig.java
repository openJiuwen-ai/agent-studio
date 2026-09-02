/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 知识库配置
 */
@ApiModel(description = "知识库配置")

@Validated

public class KnowledgeBaseConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("key")
    @Schema(description = "密钥", example = "example-token-value")
    private String key = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "{}")
    @Valid
    private Object value = null;

    public String getKey() {
        return key;
    }

    public KnowledgeBaseConfig setKey(String key) {
        this.key = key;
        return this;
    }

    public Object getValue() {
        return value;
    }

    public KnowledgeBaseConfig setValue(Object value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class KnowledgeBaseConfig {\n");

        sb.append("    key: ").append(toIndentedString(key)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
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
        KnowledgeBaseConfig knowledgeBaseConfig = (KnowledgeBaseConfig) o;
        return Objects.equals(this.key, knowledgeBaseConfig.key) && Objects.equals(this.value,
            knowledgeBaseConfig.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(key, value);
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
