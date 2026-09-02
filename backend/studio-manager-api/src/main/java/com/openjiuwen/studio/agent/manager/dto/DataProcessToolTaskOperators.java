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
 * 编排对象
 */
@ApiModel(description = "编排对象")

@Validated

public class DataProcessToolTaskOperators implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "类型", example = "example-type")
    private String type = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    private String description = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "[]")
    @Valid
    @Size()
    private List<TaskOperator> value = null;

    public String getType() {
        return type;
    }

    public DataProcessToolTaskOperators setType(String type) {
        this.type = type;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public DataProcessToolTaskOperators setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<TaskOperator> getValue() {
        return value;
    }

    public DataProcessToolTaskOperators setValue(List<TaskOperator> value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DataProcessToolTaskOperators {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        DataProcessToolTaskOperators dataProcessToolTaskOperators = (DataProcessToolTaskOperators) o;
        return Objects.equals(this.type, dataProcessToolTaskOperators.type) && Objects.equals(this.description,
            dataProcessToolTaskOperators.description) && Objects.equals(this.value, dataProcessToolTaskOperators.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, description, value);
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
