/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 模型信息
 */
@ApiModel(description = "模型信息")

@Validated

public class ModelInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "模型名称", example = "gpt-4")
    @Length(min = 1, max = 32)
    private String name = null;

    @JsonProperty("id")
    @Schema(description = "模型ID", example = "model-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("type")
    @Schema(description = "模型类型", example = "chat")
    @Pattern(regexp = "^.*$")
    @Length(min = 1, max = 64)
    private String type = null;

    @JsonProperty("status")
    @Schema(description = "模型状态", example = "active")
    @Length(min = 1, max = 16)
    private String status = null;

    public String getName() {
        return name;
    }

    public ModelInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getId() {
        return id;
    }

    public ModelInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getType() {
        return type;
    }

    public ModelInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ModelInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelInfo {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        ModelInfo modelInfo = (ModelInfo) o;
        return Objects.equals(this.name, modelInfo.name) && Objects.equals(this.id, modelInfo.id) && Objects.equals(
            this.type, modelInfo.type) && Objects.equals(this.status, modelInfo.status);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, id, type, status);
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
