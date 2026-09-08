/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 智能生成（添加）的返回体。
 */
@ApiModel(description = "智能生成（添加）的返回体。")

@Validated

public class AutoAddResultJsonObject implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "my_agent")
    private String name = null;

    @JsonProperty("prologue")
    @Schema(description = "开场白", example = "你好，我是智能助手")
    private String prologue = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "这是一个智能助手")
    private String description = null;

    @JsonProperty("questions")
    @Schema(description = "问题列表", example = "[\"如何使用？\"]")
    @Valid
    @Size()
    private List<@Length() String> questions = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[]")
    @Valid
    @Size()
    private List<ToolReference> tools = null;

    @JsonProperty("workflows")
    @Schema(description = "工作流列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowReference> workflows = null;

    @JsonProperty("icons")
    @Schema(description = "图标", example = "{}")
    @Valid
    private Icon icons = null;

    @JsonProperty("skills")
    @Schema(description = "技能列表", example = "[]")
    @Valid
    @Size()
    private List<SkillReference> skills = null;

    public String getName() {
        return name;
    }

    public AutoAddResultJsonObject setName(String name) {
        this.name = name;
        return this;
    }

    public String getPrologue() {
        return prologue;
    }

    public AutoAddResultJsonObject setPrologue(String prologue) {
        this.prologue = prologue;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AutoAddResultJsonObject setDescription(String description) {
        this.description = description;
        return this;
    }

    public List<String> getQuestions() {
        return questions;
    }

    public AutoAddResultJsonObject setQuestions(List<String> questions) {
        this.questions = questions;
        return this;
    }

    public List<ToolReference> getTools() {
        return tools;
    }

    public AutoAddResultJsonObject setTools(List<ToolReference> tools) {
        this.tools = tools;
        return this;
    }

    public List<WorkflowReference> getWorkflows() {
        return workflows;
    }

    public AutoAddResultJsonObject setWorkflows(List<WorkflowReference> workflows) {
        this.workflows = workflows;
        return this;
    }

    public Icon getIcons() {
        return icons;
    }

    public AutoAddResultJsonObject setIcons(Icon icons) {
        this.icons = icons;
        return this;
    }

    public List<SkillReference> getSkills() {
        return skills;
    }

    public AutoAddResultJsonObject setSkills(List<SkillReference> skills) {
        this.skills = skills;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AutoAddResultJsonObject {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    prologue: ").append(toIndentedString(prologue)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    questions: ").append(toIndentedString(questions)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
        sb.append("    workflows: ").append(toIndentedString(workflows)).append("\n");
        sb.append("    icons: ").append(toIndentedString(icons)).append("\n");
        sb.append("    skills: ").append(toIndentedString(skills)).append("\n");
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
        AutoAddResultJsonObject autoAddResultJsonObject = (AutoAddResultJsonObject) o;
        return Objects.equals(this.name, autoAddResultJsonObject.name) && Objects.equals(this.prologue,
            autoAddResultJsonObject.prologue) && Objects.equals(this.description, autoAddResultJsonObject.description)
            && Objects.equals(this.questions, autoAddResultJsonObject.questions) && Objects.equals(this.tools,
            autoAddResultJsonObject.tools) && Objects.equals(this.workflows, autoAddResultJsonObject.workflows)
            && Objects.equals(this.icons, autoAddResultJsonObject.icons) && Objects.equals(this.skills,
            autoAddResultJsonObject.skills);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, prologue, description, questions, tools, workflows, icons, skills);
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
