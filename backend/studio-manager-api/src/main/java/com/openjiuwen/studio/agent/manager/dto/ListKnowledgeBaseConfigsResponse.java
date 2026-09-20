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
 * 知识库配置响应体
 */
@ApiModel(description = "知识库配置响应体")

@Validated

public class ListKnowledgeBaseConfigsResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("configs")
    @Schema(description = "configs", example = "[]")
    @Valid
    @Size(max = 200)
    private List<KnowledgeBaseConfig> configs = null;

    public List<KnowledgeBaseConfig> getConfigs() {
        return configs;
    }

    public ListKnowledgeBaseConfigsResponse setConfigs(List<KnowledgeBaseConfig> configs) {
        this.configs = configs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeBaseConfigsResponse {\n");

        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
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
        ListKnowledgeBaseConfigsResponse listKnowledgeBaseConfigsResponse = (ListKnowledgeBaseConfigsResponse) o;
        return Objects.equals(this.configs, listKnowledgeBaseConfigsResponse.configs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(configs);
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
