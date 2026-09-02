/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 自主动态规划模式下指南技能。
 */
@ApiModel(description = "自主动态规划模式下指南技能。")

@Validated

public class ToolSkills implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "ID", example = "example-id-123")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "example-type")
    private String type = null;

    public String getId() {
        return id;
    }

    public ToolSkills setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ToolSkills setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ToolSkills setType(String type) {
        this.type = type;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ToolSkills {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
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
        ToolSkills toolSkills = (ToolSkills) o;
        return Objects.equals(this.id, toolSkills.id) && Objects.equals(this.name, toolSkills.name) && Objects.equals(
            this.type, toolSkills.type);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type);
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
