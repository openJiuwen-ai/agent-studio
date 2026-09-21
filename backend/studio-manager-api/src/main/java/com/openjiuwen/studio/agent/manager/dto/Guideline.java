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
 * 自主动态规划模式下指南。
 */
@ApiModel(description = "自主动态规划模式下指南。")

@Validated

public class Guideline implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "指南ID", example = "1")
    private Integer id = null;

    @JsonProperty("condition")
    @Schema(description = "条件", example = "condition1")
    private String condition = null;

    @JsonProperty("action")
    @Schema(description = "动作", example = "action1")
    private String action = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[{\"name\":\"tool1\"}]")
    @Valid
    @Size()
    private List<ToolSkills> tools = null;

    public Integer getId() {
        return id;
    }

    public Guideline setId(Integer id) {
        this.id = id;
        return this;
    }

    public String getCondition() {
        return condition;
    }

    public Guideline setCondition(String condition) {
        this.condition = condition;
        return this;
    }

    public String getAction() {
        return action;
    }

    public Guideline setAction(String action) {
        this.action = action;
        return this;
    }

    public List<ToolSkills> getTools() {
        return tools;
    }

    public Guideline setTools(List<ToolSkills> tools) {
        this.tools = tools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Guideline {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    condition: ").append(toIndentedString(condition)).append("\n");
        sb.append("    action: ").append(toIndentedString(action)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
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
        Guideline guideline = (Guideline) o;
        return Objects.equals(this.id, guideline.id) && Objects.equals(this.condition, guideline.condition)
            && Objects.equals(this.action, guideline.action) && Objects.equals(this.tools, guideline.tools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, condition, action, tools);
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
