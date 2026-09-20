/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 查询模型列表响应体
 */
@ApiModel(description = "查询模型列表响应体")

@Validated

public class ListKnowledgeModelsResponseBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    @Range(min = 0L, max = 10000L)
    private Integer total = null;

    @JsonProperty("models")
    @Schema(description = "模型列表", example = "[]")
    @Valid
    @Size(max = 200)
    private List<ModelInfo> models = null;

    public Integer getTotal() {
        return total;
    }

    public ListKnowledgeModelsResponseBody setTotal(Integer total) {
        this.total = total;
        return this;
    }

    public List<ModelInfo> getModels() {
        return models;
    }

    public ListKnowledgeModelsResponseBody setModels(List<ModelInfo> models) {
        this.models = models;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListKnowledgeModelsResponseBody {\n");

        sb.append("    total: ").append(toIndentedString(total)).append("\n");
        sb.append("    models: ").append(toIndentedString(models)).append("\n");
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
        ListKnowledgeModelsResponseBody listKnowledgeModelsResponseBody = (ListKnowledgeModelsResponseBody) o;
        return Objects.equals(this.total, listKnowledgeModelsResponseBody.total) && Objects.equals(this.models,
            listKnowledgeModelsResponseBody.models);
    }

    @Override
    public int hashCode() {
        return Objects.hash(total, models);
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
